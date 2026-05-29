/*
 * mcp_http.h — MCP Streamable HTTP transport (2025-03-26 spec).
 *
 * Implements JSON-RPC 2.0 over HTTP alongside the stdio transport.
 * Runs on a separate port so agents that support HTTP-based MCP
 * can connect without spawning a subprocess.
 *
 * Endpoints:
 *   POST /mcp    → JSON-RPC request/response (application/json)
 *   GET  /mcp    → Server-Sent Events stream for notifications
 *   OPTIONS /mcp → CORS preflight
 *
 * Session lifecycle:
 *   1. Client POST initialize (no Mcp-Session-Id)
 *   2. Server responds 200 with Mcp-Session-Id header
 *   3. Client POST initialized (Mcp-Session-Id required)
 *   4. Subsequent calls include Mcp-Session-Id
 */
#ifndef CBM_MCP_HTTP_H
#define CBM_MCP_HTTP_H

#include <stdbool.h>

typedef struct cbm_mcp_http_server cbm_mcp_http_server_t;

/* Create an MCP HTTP transport server.
 *
 *   port        — TCP port to listen on (e.g. 9748)
 *   local_only  — true: bind 127.0.0.1, false: bind 0.0.0.0
 *   base_path   — context path prefix, e.g. "/mcp" or "/api/mcp"
 *                 Must start with '/'. NULL or empty → defaults to "/mcp".
 *
 * Only code-search/query tools are exposed (index_repository, delete_project,
 * index_status, and ingest_traces are intentionally excluded).
 *
 * Returns NULL on failure (e.g. port already in use). */
cbm_mcp_http_server_t *cbm_mcp_http_server_new(int port, bool local_only,
                                                const char *base_path);

/* Free the server. Must be called after the background thread is joined. */
void cbm_mcp_http_server_free(cbm_mcp_http_server_t *srv);

/* Signal the server to stop (safe to call from any thread or signal handler). */
void cbm_mcp_http_server_stop(cbm_mcp_http_server_t *srv);

/* Run the event loop. Blocks until cbm_mcp_http_server_stop() is called.
 * Call from a dedicated background thread. */
void cbm_mcp_http_server_run(cbm_mcp_http_server_t *srv);

/* Returns true if the listener socket bound successfully. */
bool cbm_mcp_http_server_is_running(const cbm_mcp_http_server_t *srv);

#endif /* CBM_MCP_HTTP_H */
