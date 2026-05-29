/* BAAI/bge-m3 token embeddings. 173966 tokens x 1024d int8-quantized.
 * Source: https://huggingface.co/BAAI/bge-m3  License: MIT
 */
#ifndef CBM_NOMIC_VECTORS_H
#define CBM_NOMIC_VECTORS_H

#include <stdint.h>

#define PRETRAINED_TOKEN_COUNT 173966
#define PRETRAINED_DIM 1024

extern const unsigned char PRETRAINED_VECTOR_BLOB[];
extern const unsigned int PRETRAINED_VECTOR_BLOB_LEN;

static inline const int8_t *pretrained_vec_at(int i) {
    return (const int8_t *)(PRETRAINED_VECTOR_BLOB + 8 + (size_t)i * PRETRAINED_DIM);
}

#include "code_tokens.h"

#endif /* CBM_NOMIC_VECTORS_H */
