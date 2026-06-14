/* BAAI/bge-m3 token embeddings.
 * 173966 tokens x 1024d int8-quantized unit vectors.
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

#define PRETRAINED_TOKEN_COUNT 173966
#define PRETRAINED_DIM 1024

/* Raw vector blob: first 8 bytes = [int32 count][int32 dim],
 * then count x dim int8 values (unit-normalized, x127 scaled). */
extern const unsigned char PRETRAINED_VECTOR_BLOB[];
extern const unsigned int PRETRAINED_VECTOR_BLOB_LEN;

/* Access the int8 vector for token index i. */
static inline const int8_t *pretrained_vec_at(int i) {
    return (const int8_t *)(PRETRAINED_VECTOR_BLOB + 8 + (size_t)i * PRETRAINED_DIM);
}

/* Token strings (separate header to keep this file clean). */
#include "code_tokens.h"

#endif /* CBM_NOMIC_VECTORS_H */
