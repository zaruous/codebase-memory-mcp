"""One-shot: regenerate missing header/text files from existing code_vectors.bin."""
import re
import struct
from pathlib import Path

from transformers import AutoTokenizer

MODEL_NAME = "BAAI/bge-m3"
out_dir = Path("vendored/bge_m3_real")
incbin_path = "vendored/bge_m3_real/code_vectors.bin"


def is_code_relevant(s):
    s = s.strip()
    if not s:
        return False
    clean = s.lstrip("Ġ▁")
    if not clean:
        return False
    if (clean.startswith("<") and clean.endswith(">")) or (
        clean.startswith("[") and clean.endswith("]")
    ):
        return False
    inner = clean.strip("_")
    if not inner or len(inner) < 2:
        return False
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", inner)) or bool(
        re.match(r"^[^\x00-\x7F]+$", inner)
    )


def clean_token(s):
    s = s.strip().lstrip("Ġ▁").strip("_")
    if re.match(r"^[a-zA-Z0-9_]+$", s):
        s = s.lower()
    return s


print("loading tokenizer...")
tok = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
vocab = tok.get_vocab()
seen, tokens = set(), []
for ts, _ in sorted(vocab.items(), key=lambda x: x[1]):
    if not is_code_relevant(ts):
        continue
    c = clean_token(ts)
    if not c or c in seen or len(c) < 2:
        continue
    seen.add(c)
    tokens.append(c)
tokens.sort()
print(f"  {len(tokens)} tokens")

with open(out_dir / "code_vectors.bin", "rb") as f:
    count, dim = struct.unpack("<ii", f.read(8))
print(f"  bin: {count} vectors x {dim}d")

# code_tokens.txt
with open(out_dir / "code_tokens.txt", "w", encoding="utf-8") as f:
    for t in tokens:
        f.write(t + "\n")
print("  wrote code_tokens.txt")

# code_tokens.h
with open(out_dir / "code_tokens.h", "w", encoding="utf-8") as f:
    f.write(f"/* bge-m3 token vocabulary — {len(tokens)} tokens. */\n")
    f.write("#ifndef CBM_NOMIC_TOKENS_H\n#define CBM_NOMIC_TOKENS_H\n\n")
    f.write(f"static const char *PRETRAINED_TOKENS[{len(tokens)}] = {{\n")
    for t in tokens:
        escaped = t.replace("\\", "\\\\").replace('"', '\\"')
        f.write(f'"{escaped}",\n')
    f.write("};\n\n#endif /* CBM_NOMIC_TOKENS_H */\n")
print("  wrote code_tokens.h")

# code_vectors.h
with open(out_dir / "code_vectors.h", "w", encoding="utf-8") as f:
    f.write(
        f"""/* BAAI/bge-m3 token embeddings. {len(tokens)} tokens x {dim}d int8-quantized.
 * Source: https://huggingface.co/BAAI/bge-m3  License: MIT
 */
#ifndef CBM_NOMIC_VECTORS_H
#define CBM_NOMIC_VECTORS_H

#include <stdint.h>

#define PRETRAINED_TOKEN_COUNT {len(tokens)}
#define PRETRAINED_DIM {dim}

extern const unsigned char PRETRAINED_VECTOR_BLOB[];
extern const unsigned int PRETRAINED_VECTOR_BLOB_LEN;

static inline const int8_t *pretrained_vec_at(int i) {{
    return (const int8_t *)(PRETRAINED_VECTOR_BLOB + 8 + (size_t)i * PRETRAINED_DIM);
}}

#include "code_tokens.h"

#endif /* CBM_NOMIC_VECTORS_H */
"""
    )
print("  wrote code_vectors.h")

# code_vectors_blob.S  — ELF / MinGW syntax (no leading underscore, .rodata section)
with open(out_dir / "code_vectors_blob.S", "w", encoding="utf-8") as f:
    f.write(
        f"""/* bge-m3 vector blob — assembler incbin (ELF / MinGW) */
    .section .rodata
    .globl PRETRAINED_VECTOR_BLOB
    .globl PRETRAINED_VECTOR_BLOB_LEN
    .p2align 4
PRETRAINED_VECTOR_BLOB:
    .incbin "{incbin_path}"
PRETRAINED_VECTOR_BLOB_END:

    .section .rodata
    .p2align 2
PRETRAINED_VECTOR_BLOB_LEN:
    .long PRETRAINED_VECTOR_BLOB_END - PRETRAINED_VECTOR_BLOB
"""
    )
print("  wrote code_vectors_blob.S")
print("done.")
