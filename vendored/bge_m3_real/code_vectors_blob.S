/* bge-m3 vector blob — assembler incbin (ELF / MinGW) */
    .section .rodata
    .globl PRETRAINED_VECTOR_BLOB
    .globl PRETRAINED_VECTOR_BLOB_LEN
    .p2align 4
PRETRAINED_VECTOR_BLOB:
    .incbin "vendored/bge_m3_real/code_vectors.bin"
PRETRAINED_VECTOR_BLOB_END:

    .section .rodata
    .p2align 2
PRETRAINED_VECTOR_BLOB_LEN:
    .long PRETRAINED_VECTOR_BLOB_END - PRETRAINED_VECTOR_BLOB
