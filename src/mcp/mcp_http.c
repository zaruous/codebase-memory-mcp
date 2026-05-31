/*
 * mcp_http.c — MCP Streamable HTTP transport (2025-03-26 spec).
 *
 * Only exposes code-search / query tools.  Indexing and write tools
 * (index_repository, delete_project, index_status, ingest_traces) are
 * intentionally blocked so the HTTP endpoint is safe to expose without
 * giving remote callers write access to the knowledge graph.
 *
 * Endpoints (relative to configured base_path, default "/mcp"):
 *   POST   <base_path>          → JSON-RPC request or notification
 *   GET    <base_path>          → SSE stream for server notifications
 *   GET    <base_path>/health   → liveness probe
 *   OPTIONS <base_path>         → CORS preflight
 *
 * Session lifecycle:
 *   1. Client  POST initialize            (no Mcp-Session-Id)
 *   2. Server  200 + Mcp-Session-Id header
 *   3. Client  POST initialized           (Mcp-Session-Id required)
 *   4. Client  POST tools/call, etc.      (Mcp-Session-Id required)
 */
#include "mcp/mcp_http.h"
#include "mcp/mcp.h"
#include "foundation/log.h"
#include "foundation/platform.h"
#include "foundation/compat_thread.h"
#include "foundation/constants.h"

#include <mongoose/mongoose.h>
#include <yyjson/yyjson.h>

#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* ── Compile-time constants ───────────────────────────────────── */

enum {
    MCP_HTTP_MAX_BODY   = 1024 * 1024,  /* 1 MB max request body      */
    MCP_HTTP_MAX_SESS   = 32,           /* max concurrent sessions    */
    MCP_HTTP_ID_LEN     = 24,           /* session-id hex chars       */
    MCP_HTTP_HEARTBEAT  = 15000,        /* SSE ping interval (ms)     */
    MCP_HTTP_POLL_MS    = 200,          /* Mongoose poll interval     */
    MCP_HTTP_PATH_MAX   = 64,           /* max base_path length       */
};

/* ── Tools blocked on the HTTP transport ──────────────────────── */

static const char *const k_blocked_tools[] = {
    "index_repository",
    "delete_project",
    "index_status",
    "ingest_traces",
    NULL,
};

static bool tool_is_blocked(const char *name) {
    if (!name) return false;
    for (int i = 0; k_blocked_tools[i]; i++) {
        if (strcmp(k_blocked_tools[i], name) == 0) return true;
    }
    return false;
}

/* ── Session table ────────────────────────────────────────────── */

typedef struct {
    char                  id[MCP_HTTP_ID_LEN + 1];
    struct mg_connection *sse_conn;      /* open GET connection (SSE) */
    bool                  active;
    uint64_t              next_ping_ms;
} mcp_session_t;

static mcp_session_t g_sess[MCP_HTTP_MAX_SESS];

/* ── Server struct ────────────────────────────────────────────── */

struct cbm_mcp_http_server {
    struct mg_mgr        mgr;
    cbm_mcp_server_t    *mcp;
    atomic_int           stop_flag;
    int                  port;
    bool                 local_only;
    bool                 listener_ok;
    char                 base_path[MCP_HTTP_PATH_MAX];      /* e.g. "/mcp"  */
    char                 health_path[MCP_HTTP_PATH_MAX + 8];/* base + /health */
    char                 health_wc[MCP_HTTP_PATH_MAX + 8];  /* base + /health* */
    char                 base_wc[MCP_HTTP_PATH_MAX + 2];    /* base + *     */
};

/* ── CORS helpers ─────────────────────────────────────────────── */

/*
 * Per-request CORS buffers.  Updated at the start of each handler via
 * update_cors().  Safe because the Mongoose event loop is single-threaded.
 */
static char g_cors[256];
static char g_cors_json[512];

static void update_cors(struct mg_http_message *hm) {
    struct mg_str *origin = mg_http_get_header(hm, "Origin");
    if (origin && origin->len > 0) {
        snprintf(g_cors, sizeof(g_cors),
                 "Access-Control-Allow-Origin: %.*s\r\n"
                 "Access-Control-Allow-Methods: POST, GET, OPTIONS\r\n"
                 "Access-Control-Allow-Headers: "
                     "Content-Type, Mcp-Session-Id, Authorization\r\n"
                 "Access-Control-Expose-Headers: Mcp-Session-Id\r\n",
                 (int)origin->len, origin->buf);
    } else {
        snprintf(g_cors, sizeof(g_cors),
                 "Access-Control-Allow-Methods: POST, GET, OPTIONS\r\n"
                 "Access-Control-Allow-Headers: "
                     "Content-Type, Mcp-Session-Id, Authorization\r\n"
                 "Access-Control-Expose-Headers: Mcp-Session-Id\r\n");
    }
    snprintf(g_cors_json, sizeof(g_cors_json),
             "%sContent-Type: application/json\r\n", g_cors);
}

/* ── Monotonic millisecond clock ──────────────────────────────── */

static uint64_t now_ms(void) {
    struct timespec ts;
#ifdef CLOCK_MONOTONIC
    clock_gettime(CLOCK_MONOTONIC, &ts);
#else
    clock_gettime(CLOCK_REALTIME, &ts);
#endif
    return (uint64_t)ts.tv_sec * CBM_MSEC_PER_SEC
         + (uint64_t)ts.tv_nsec / CBM_NSEC_PER_MSEC;
}

/* ── Session management ───────────────────────────────────────── */

static void gen_session_id(char *out) {
    static atomic_uint_fast32_t counter = 0;
    unsigned long long t = (unsigned long long)time(NULL);
    unsigned int n = (unsigned int)atomic_fetch_add(&counter, 1u);
    snprintf(out, MCP_HTTP_ID_LEN + 1, "%016llx%08x", t, n);
}

static mcp_session_t *sess_find(const char *id) {
    if (!id || !id[0]) return NULL;
    for (int i = 0; i < MCP_HTTP_MAX_SESS; i++) {
        if (g_sess[i].active && strcmp(g_sess[i].id, id) == 0)
            return &g_sess[i];
    }
    return NULL;
}

static mcp_session_t *sess_new(void) {
    for (int i = 0; i < MCP_HTTP_MAX_SESS; i++) {
        if (!g_sess[i].active) {
            memset(&g_sess[i], 0, sizeof(g_sess[i]));
            gen_session_id(g_sess[i].id);
            g_sess[i].active = true;
            g_sess[i].next_ping_ms = now_ms() + MCP_HTTP_HEARTBEAT;
            return &g_sess[i];
        }
    }
    return NULL;
}

static void sess_close_sse(mcp_session_t *s) {
    if (s && s->sse_conn) {
        s->sse_conn->is_draining = 1;
        s->sse_conn = NULL;
    }
}

/* ── Tools-list response filter ──────────────────────────────── */

/*
 * Remove blocked tools from a tools/list JSON-RPC response.
 * Input:  full JSON-RPC response string from cbm_mcp_server_handle.
 * Output: heap-allocated filtered copy (caller must free), or the
 *         original pointer if filtering is not needed / fails.
 */
static char *filter_tools_list(char *response) {
    if (!response) return response;

    yyjson_doc *doc = yyjson_read(response, strlen(response), 0);
    if (!doc) return response;

    yyjson_val *root   = yyjson_doc_get_root(doc);
    yyjson_val *result = yyjson_obj_get(root, "result");
    yyjson_val *tools  = result ? yyjson_obj_get(result, "tools") : NULL;

    if (!yyjson_is_arr(tools)) {
        yyjson_doc_free(doc);
        return response;
    }

    yyjson_mut_doc *mdoc  = yyjson_doc_mut_copy(doc, NULL);
    yyjson_doc_free(doc);
    if (!mdoc) return response;

    yyjson_mut_val *mroot   = yyjson_mut_doc_get_root(mdoc);
    yyjson_mut_val *mresult = yyjson_mut_obj_get(mroot, "result");
    yyjson_mut_val *mtools  = mresult ? yyjson_mut_obj_get(mresult, "tools") : NULL;

    if (!mtools) {
        yyjson_mut_doc_free(mdoc);
        return response;
    }

    /* Build a new array without blocked tools.
     * Two-pass approach: collect allowed tool pointers first (no next-pointer
     * mutation during iteration), then append them.  A single-pass
     * yyjson_mut_arr_append(filtered, tool) inside foreach corrupts the
     * iterator because append overwrites tool->next, causing the loop to
     * revisit the same element on every subsequent step. */
    yyjson_mut_val *allowed[32];
    int allowed_n = 0;
    {
        size_t idx = 0, max = yyjson_mut_arr_size(mtools);
        yyjson_mut_val *tool;
        yyjson_mut_arr_foreach(mtools, idx, max, tool) {
            yyjson_mut_val *v_name = yyjson_mut_obj_get(tool, "name");
            if (!v_name) continue;
            const char *name = yyjson_mut_get_str(v_name);
            if (!tool_is_blocked(name) && allowed_n < (int)(sizeof(allowed) / sizeof(allowed[0]))) {
                allowed[allowed_n++] = tool;
            }
        }
    }
    yyjson_mut_val *filtered = yyjson_mut_arr(mdoc);
    for (int i = 0; i < allowed_n; i++) {
        yyjson_mut_arr_append(filtered, allowed[i]);
    }
    yyjson_mut_obj_put(mresult, yyjson_mut_strcpy(mdoc, "tools"), filtered);

    size_t len = 0;
    char *out = yyjson_mut_write(mdoc, 0, &len);
    yyjson_mut_doc_free(mdoc);

    if (!out) return response;

    free(response);
    return out;
}

/* ── GET <base_path> — SSE stream ────────────────────────────── */

static void handle_sse(struct mg_connection *c, struct mg_http_message *hm,
                       const char *session_id,
                       const cbm_mcp_http_server_t *srv) {
    mcp_session_t *s = sess_find(session_id);

    if (s && s->sse_conn) {
        sess_close_sse(s);
    }

    char hdrs[512];
    snprintf(hdrs, sizeof(hdrs),
             "HTTP/1.1 200 OK\r\n"
             "Content-Type: text/event-stream\r\n"
             "Cache-Control: no-cache\r\n"
             "Connection: keep-alive\r\n"
             "%s"
             "\r\n",
             g_cors);
    mg_printf(c, "%s", hdrs);

    c->data[0] = 'S'; /* mark as SSE */

    if (s) {
        s->sse_conn = c;
        memcpy(c->data + 1, &s, sizeof(s));
        s->next_ping_ms = now_ms() + MCP_HTTP_HEARTBEAT;
    }

    /* Announce the POST endpoint so clients know where to send requests */
    mg_printf(c, "event: endpoint\ndata: %s\n\n", srv->base_path);

    (void)hm;
}

/* ── POST <base_path> — JSON-RPC dispatch ────────────────────── */

static void handle_post(struct mg_connection *c, struct mg_http_message *hm,
                        cbm_mcp_server_t *mcp, const char *session_id) {
    if (hm->body.len == 0 || hm->body.len > (size_t)MCP_HTTP_MAX_BODY) {
        mg_http_reply(c, 400, g_cors_json,
                      "{\"jsonrpc\":\"2.0\",\"error\":{\"code\":-32600,"
                      "\"message\":\"invalid request size\"},\"id\":null}");
        return;
    }

    char *body = malloc(hm->body.len + 1);
    if (!body) {
        mg_http_reply(c, 500, g_cors, "out of memory");
        return;
    }
    memcpy(body, hm->body.buf, hm->body.len);
    body[hm->body.len] = '\0';

    /* Parse enough to determine method, id, and tool name */
    const char *method    = NULL;
    const char *tool_name = NULL;
    bool        has_id    = false;
    bool        is_init   = false;
    bool        is_tools_list = false;

    yyjson_doc *peek = yyjson_read(body, hm->body.len, 0);
    if (peek) {
        yyjson_val *root     = yyjson_doc_get_root(peek);
        yyjson_val *v_id     = yyjson_obj_get(root, "id");
        yyjson_val *v_method = yyjson_obj_get(root, "method");
        yyjson_val *v_params = yyjson_obj_get(root, "params");

        has_id = v_id && !yyjson_is_null(v_id);
        if (yyjson_is_str(v_method)) {
            method = yyjson_get_str(v_method);
        }

        if (method) {
            is_init       = (strcmp(method, "initialize") == 0);
            is_tools_list = (strcmp(method, "tools/list") == 0);

            if (strcmp(method, "tools/call") == 0 && yyjson_is_obj(v_params)) {
                yyjson_val *v_name = yyjson_obj_get(v_params, "name");
                if (yyjson_is_str(v_name)) {
                    tool_name = yyjson_get_str(v_name);
                }
            }
        }
        yyjson_doc_free(peek);
    }

    /* Block write/indexing tools */
    if (tool_name && tool_is_blocked(tool_name)) {
        free(body);
        mg_http_reply(c, 403, g_cors_json,
                      "{\"jsonrpc\":\"2.0\",\"error\":{\"code\":-32601,"
                      "\"message\":\"tool not available on HTTP transport\"},"
                      "\"id\":null}");
        return;
    }

    /* Notifications (no id) → 202 Accepted */
    if (!has_id) {
        cbm_mcp_server_handle(mcp, body); /* process side-effects, ignore result */
        free(body);
        mg_http_reply(c, 202, g_cors, "");
        return;
    }

    char *response = cbm_mcp_server_handle(mcp, body);
    free(body);

    if (!response) {
        mg_http_reply(c, 204, g_cors, "");
        return;
    }

    /* Filter tools/list to remove blocked tools */
    if (is_tools_list) {
        response = filter_tools_list(response);
    }

    char resp_hdrs[768];
    if (is_init) {
        mcp_session_t *s = sess_new();
        if (s) {
            snprintf(resp_hdrs, sizeof(resp_hdrs),
                     "%sMcp-Session-Id: %s\r\n", g_cors_json, s->id);
            cbm_log_info("mcp_http.session.new", "id", s->id);
        } else {
            snprintf(resp_hdrs, sizeof(resp_hdrs), "%s", g_cors_json);
            cbm_log_warn("mcp_http.session.full", "reason", "all slots occupied");
        }
    } else {
        if (session_id && session_id[0] && !sess_find(session_id)) {
            cbm_log_warn("mcp_http.session.unknown", "id", session_id);
        }
        snprintf(resp_hdrs, sizeof(resp_hdrs), "%s", g_cors_json);
    }

    mg_http_reply(c, 200, resp_hdrs, "%s", response);
    free(response);
}

/* ── GET <base_path>/health ───────────────────────────────────── */

static void handle_health(struct mg_connection *c) {
    int active = 0;
    for (int i = 0; i < MCP_HTTP_MAX_SESS; i++) {
        if (g_sess[i].active) active++;
    }
    mg_http_reply(c, 200, g_cors_json,
                  "{\"status\":\"ok\",\"transport\":\"streamable-http\","
                  "\"sessions\":%d}", active);
}

/* ── Extract Mcp-Session-Id header ───────────────────────────── */

static void get_session_id(struct mg_http_message *hm, char *out, int outsz) {
    out[0] = '\0';
    struct mg_str *h = mg_http_get_header(hm, "Mcp-Session-Id");
    if (h && h->len > 0 && (int)h->len < outsz) {
        memcpy(out, h->buf, h->len);
        out[h->len] = '\0';
    }
}

/* ── SSE heartbeat pass ───────────────────────────────────────── */

static void send_heartbeats(void) {
    uint64_t ms = now_ms();
    for (int i = 0; i < MCP_HTTP_MAX_SESS; i++) {
        mcp_session_t *s = &g_sess[i];
        if (!s->active || !s->sse_conn) continue;
        if (ms >= s->next_ping_ms) {
            mg_printf(s->sse_conn, "event: ping\ndata: {}\n\n");
            s->next_ping_ms = ms + MCP_HTTP_HEARTBEAT;
        }
    }
}

/* ── HTTP event handler ───────────────────────────────────────── */

static void mcp_http_handler(struct mg_connection *c, int ev, void *ev_data) {
    if (ev == MG_EV_CLOSE) {
        if (c->data[0] == 'S') {
            mcp_session_t *s = NULL;
            memcpy(&s, c->data + 1, sizeof(s));
            if (s && s->sse_conn == c) s->sse_conn = NULL;
        }
        return;
    }

    if (ev == MG_EV_POLL) {
        send_heartbeats();
        return;
    }

    if (ev != MG_EV_HTTP_MSG) return;

    struct mg_http_message  *hm  = ev_data;
    cbm_mcp_http_server_t   *srv = c->fn_data;

    update_cors(hm);

    /* CORS preflight */
    if (mg_strcmp(hm->method, mg_str("OPTIONS")) == 0) {
        char opt[512];
        snprintf(opt, sizeof(opt), "%sContent-Length: 0\r\n", g_cors);
        mg_http_reply(c, 204, opt, "");
        return;
    }

    /* GET <base_path>/health */
    if (mg_strcmp(hm->method, mg_str("GET")) == 0 &&
        mg_match(hm->uri, mg_str(srv->health_wc), NULL)) {
        handle_health(c);
        return;
    }

    char sid[MCP_HTTP_ID_LEN + 1];
    get_session_id(hm, sid, (int)sizeof(sid));

    /* GET <base_path> → SSE */
    if (mg_strcmp(hm->method, mg_str("GET")) == 0 &&
        mg_match(hm->uri, mg_str(srv->base_path), NULL)) {
        handle_sse(c, hm, sid, srv);
        return;
    }

    /* POST <base_path> → JSON-RPC */
    if (mg_strcmp(hm->method, mg_str("POST")) == 0 &&
        mg_match(hm->uri, mg_str(srv->base_path), NULL)) {
        handle_post(c, hm, srv->mcp, sid);
        return;
    }

    mg_http_reply(c, 404, g_cors_json,
                  "{\"error\":\"not found\","
                  "\"hint\":\"POST %s for MCP JSON-RPC\"}", srv->base_path);
}

/* ── Public API ───────────────────────────────────────────────── */

cbm_mcp_http_server_t *cbm_mcp_http_server_new(int port, bool local_only,
                                                const char *base_path) {
    cbm_mcp_http_server_t *srv = calloc(1, sizeof(*srv));
    if (!srv) return NULL;

    srv->port       = port;
    srv->local_only = local_only;
    atomic_store(&srv->stop_flag, 0);

    /* Normalise base_path */
    const char *bp = (base_path && base_path[0]) ? base_path : "/mcp";
    snprintf(srv->base_path,    sizeof(srv->base_path),    "%s", bp);
    snprintf(srv->health_path,  sizeof(srv->health_path),  "%s/health", bp);
    snprintf(srv->health_wc,    sizeof(srv->health_wc),    "%s/health*", bp);
    snprintf(srv->base_wc,      sizeof(srv->base_wc),      "%s*", bp);

    srv->mcp = cbm_mcp_server_new(NULL);
    if (!srv->mcp) {
        cbm_log_error("mcp_http.init_fail", "reason", "cannot create MCP instance");
        free(srv);
        return NULL;
    }

    mg_mgr_init(&srv->mgr);
    srv->mgr.userdata = srv;

    char url[64];
    snprintf(url, sizeof(url), "http://%s:%d",
             local_only ? "127.0.0.1" : "0.0.0.0", port);

    struct mg_connection *listener =
        mg_http_listen(&srv->mgr, url, mcp_http_handler, srv);
    if (!listener) {
        char port_str[16];
        snprintf(port_str, sizeof(port_str), "%d", port);
        cbm_log_warn("mcp_http.unavailable", "port", port_str,
                     "reason", "in_use",
                     "hint", "use --mcp-http-port=N to override");
        cbm_mcp_server_free(srv->mcp);
        mg_mgr_free(&srv->mgr);
        free(srv);
        return NULL;
    }

    srv->listener_ok = true;

    char full_url[128];
    snprintf(full_url, sizeof(full_url), "%s%s", url, srv->base_path);
    cbm_log_info("mcp_http.serving", "url", full_url, "path", srv->base_path);

    return srv;
}

void cbm_mcp_http_server_free(cbm_mcp_http_server_t *srv) {
    if (!srv) return;
    mg_mgr_free(&srv->mgr);
    cbm_mcp_server_free(srv->mcp);
    free(srv);
}

void cbm_mcp_http_server_stop(cbm_mcp_http_server_t *srv) {
    if (srv) atomic_store(&srv->stop_flag, 1);
}

void cbm_mcp_http_server_run(cbm_mcp_http_server_t *srv) {
    if (!srv || !srv->listener_ok) return;
    while (!atomic_load(&srv->stop_flag)) {
        mg_mgr_poll(&srv->mgr, MCP_HTTP_POLL_MS);
    }
    for (int i = 0; i < MCP_HTTP_MAX_SESS; i++) {
        sess_close_sse(&g_sess[i]);
    }
}

bool cbm_mcp_http_server_is_running(const cbm_mcp_http_server_t *srv) {
    return srv && srv->listener_ok;
}
