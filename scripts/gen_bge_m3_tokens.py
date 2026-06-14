"""Generate vendored/bge_m3/ files from tokenizer only (no model needed).

Run from project root:
    python3 scripts/gen_bge_m3_tokens.py
"""
import re
import sys
import struct
import shutil
from pathlib import Path


def is_code_relevant(token_str):
    s = token_str.strip()
    if not s:
        return False
    clean = s.lstrip("Ġ▁")
    if not clean:
        return False
    if clean.startswith("<") and clean.endswith(">"):
        return False
    if clean.startswith("[") and clean.endswith("]"):
        return False
    inner = clean.strip("_")
    if not inner:
        return False
    is_latin_ident = bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", inner))
    is_multiling = bool(re.match(r"^[^\x00-\x7F]+$", inner))
    if not is_latin_ident and not is_multiling:
        return False
    if len(inner) < 2:
        return False
    return True


def clean_token(token_str):
    s = token_str.strip()
    s = s.lstrip("Ġ▁")
    s = s.strip("_")
    if re.match(r"^[a-zA-Z0-9_]+$", s):
        s = s.lower()
    return s


def main():
    out_dir = Path("vendored/bge_m3")
    out_dir.mkdir(parents=True, exist_ok=True)

    print("Loading BAAI/bge-m3 tokenizer (no model)...")
    sys.stdout.flush()

    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3", trust_remote_code=True)
    print(f"Tokenizer vocab size: {tokenizer.vocab_size}")

    vocab = tokenizer.get_vocab()
    print(f"Raw vocabulary: {len(vocab)} tokens")

    seen = set()
    filtered_tokens = []
    for tok_str, tok_id in sorted(vocab.items(), key=lambda x: x[1]):
        if not is_code_relevant(tok_str):
            continue
        clean = clean_token(tok_str)
        if not clean or clean in seen:
            continue
        if len(clean) < 2:
            continue
        seen.add(clean)
        filtered_tokens.append(clean)

    filtered_tokens.sort()
    print(f"Code-relevant tokens: {len(filtered_tokens)}")

    src_bin = Path("vendored/bge_m3_real/code_vectors.bin")
    with open(src_bin, "rb") as f:
        count, dim = struct.unpack("<ii", f.read(8))
    print(f"code_vectors.bin: count={count} dim={dim}")

    if len(filtered_tokens) != count:
        print(f"WARNING: token count mismatch! tokens={len(filtered_tokens)} vs bin={count}")
    else:
        print("Token count matches bin header - OK")

    with open(out_dir / "code_tokens.txt", "w") as f:
        for t in filtered_tokens:
            f.write(t + "\n")
    print("Written: code_tokens.txt")

    with open(out_dir / "code_tokens.h", "w") as f:
        f.write(f"/* BAAI/bge-m3 token vocabulary — {len(filtered_tokens)} tokens. */\n")
        f.write("#ifndef CBM_NOMIC_TOKENS_H\n")
        f.write("#define CBM_NOMIC_TOKENS_H\n\n")
        f.write(f"static const char *PRETRAINED_TOKENS[{len(filtered_tokens)}] = {{\n")
        for t in filtered_tokens:
            escaped = t.replace("\\", "\\\\").replace('"', '\\"')
            f.write(f'"{escaped}",\n')
        f.write("};\n\n")
        f.write("#endif /* CBM_NOMIC_TOKENS_H */\n")
    print("Written: code_tokens.h")

    incbin_path = "vendored/bge_m3/code_vectors.bin"
    with open(out_dir / "code_vectors.h", "w") as f:
        f.write(f"""/* BAAI/bge-m3 token embeddings.
 * {len(filtered_tokens)} tokens x {dim}d int8-quantized unit vectors.
 *
 * Vector blob embedded via code_vectors_blob.S (assembler .incbin).
 * Token strings are in this header as a static array.
 *
 * Source: https://huggingface.co/BAAI/bge-m3
 * License: Apache 2.0
 */
#ifndef CBM_NOMIC_VECTORS_H
#define CBM_NOMIC_VECTORS_H

#include <stdint.h>

#define PRETRAINED_TOKEN_COUNT {len(filtered_tokens)}
#define PRETRAINED_DIM {dim}

/* Raw vector blob: first 8 bytes = [int32 count][int32 dim],
 * then count x dim int8 values (unit-normalized, x127 scaled). */
extern const unsigned char PRETRAINED_VECTOR_BLOB[];
extern const unsigned int PRETRAINED_VECTOR_BLOB_LEN;

/* Access the int8 vector for token index i. */
static inline const int8_t *pretrained_vec_at(int i) {{
    return (const int8_t *)(PRETRAINED_VECTOR_BLOB + 8 + (size_t)i * PRETRAINED_DIM);
}}

/* Token strings (separate header to keep this file clean). */
#include "code_tokens.h"

#endif /* CBM_NOMIC_VECTORS_H */
""")
    print("Written: code_vectors.h")

    blob_content = f"""/* BAAI/bge-m3 vector blob embedded via assembler.
 * Cross-platform: macOS (Mach-O) vs Linux (ELF) vs Windows (COFF). */

#if defined(__APPLE__)
    .section __DATA,__const
    .globl _PRETRAINED_VECTOR_BLOB
    .globl _PRETRAINED_VECTOR_BLOB_LEN
    .p2align 4
_PRETRAINED_VECTOR_BLOB:
    .incbin "{incbin_path}"
_PRETRAINED_VECTOR_BLOB_END:

    .section __DATA,__const
    .p2align 2
_PRETRAINED_VECTOR_BLOB_LEN:
    .long _PRETRAINED_VECTOR_BLOB_END - _PRETRAINED_VECTOR_BLOB

#elif defined(_WIN32) || defined(__CYGWIN__) || defined(__MINGW32__)
    .section .rdata,"dr"
    .globl PRETRAINED_VECTOR_BLOB
    .globl PRETRAINED_VECTOR_BLOB_LEN
    .p2align 4
PRETRAINED_VECTOR_BLOB:
    .incbin "{incbin_path}"
PRETRAINED_VECTOR_BLOB_END:

    .section .rdata,"dr"
    .p2align 2
PRETRAINED_VECTOR_BLOB_LEN:
    .long PRETRAINED_VECTOR_BLOB_END - PRETRAINED_VECTOR_BLOB

#else
    .section .rodata,"a",@progbits
    .globl PRETRAINED_VECTOR_BLOB
    .globl PRETRAINED_VECTOR_BLOB_LEN
    .p2align 4
PRETRAINED_VECTOR_BLOB:
    .incbin "{incbin_path}"
PRETRAINED_VECTOR_BLOB_END:

    .section .rodata,"a",@progbits
    .p2align 2
PRETRAINED_VECTOR_BLOB_LEN:
    .long PRETRAINED_VECTOR_BLOB_END - PRETRAINED_VECTOR_BLOB
#endif
"""
    with open(out_dir / "code_vectors_blob.S", "w") as f:
        f.write(blob_content)
    print("Written: code_vectors_blob.S")

    dst_bin = out_dir / "code_vectors.bin"
    if not dst_bin.exists():
        shutil.copy2(str(src_bin), str(dst_bin))
        print(f"Copied: code_vectors.bin ({dst_bin.stat().st_size // 1024 // 1024} MB)")
    else:
        print("code_vectors.bin already exists")

    print("Done!")


if __name__ == "__main__":
    main()
