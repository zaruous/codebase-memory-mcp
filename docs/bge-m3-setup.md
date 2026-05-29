# BGE-M3 임베딩 모델 세팅 가이드

nomic-embed-code에서 BAAI/bge-m3로 교체하여 **다국어 docstring 임베딩**을 활성화하는 전체 절차입니다.

---

## 개요

```
[1단계] BGE-M3 벡터 추출 (Python 또는 TEI Docker, 1회성)
          └─ vendored/bge_m3_real/ 생성
              │
[2단계] 소스 수정
          ├─ semantic.h: CBM_SEM_DIM 768 → 1024
          ├─ semantic.c: #include 경로 수정
          └─ Makefile.cbm: blob 경로 수정
              │
[3단계] C 바이너리 빌드
          └─ build/codebase-memory-mcp(.exe) 생성
              │
[4단계] 테스트
          ├─ 자동화 테스트 (make test)
          └─ 런타임 수동 테스트 (CBM_SEMANTIC_ENABLED=1)
```

---

## 1단계 — BGE-M3 벡터 추출

### 방법 A — HuggingFace TEI Docker (권장, 빠름)

RTX 3070 기준 약 50분 (추출 ~30분 + simulated attention ~20분).

#### 요구 사항

- Docker Desktop (GPU 지원)
- 이미지: `ghcr.io/huggingface/text-embeddings-inference:86-1.9` (SM 8.6 = RTX 30xx)
  - SM 8.9 (RTX 40xx): `:89-1.9`
  - SM 7.5 (RTX 20xx/T4): `:75-1.9`
- Python 패키지: `pip install transformers numpy requests`

#### TEI 컨테이너 시작

```bash
docker run -d --name tei-bge-m3 --gpus all -p 8080:80 \
  ghcr.io/huggingface/text-embeddings-inference:86-1.9 \
  --model-id BAAI/bge-m3 \
  --pooling cls \
  --dtype float16
```

서버 준비 확인 (`Ready` 로그 대기):
```bash
docker logs -f tei-bge-m3 2>&1 | grep -m1 "Ready"
```

#### 벡터 추출

```bash
python3 scripts/extract_nomic_vectors.py \
  --output-dir vendored/bge_m3_real \
  --tei-url http://localhost:8080
```

완료 후 컨테이너 정리:
```bash
docker stop tei-bge-m3 && docker rm tei-bge-m3
```

---

### 방법 B — 직접 Python 추론 (TEI 없이)

#### 요구 사항

| 항목 | 최소 사양 | 권장 |
|------|---------|------|
| Python | 3.9+ | 3.11+ |
| RAM | 4GB | 8GB |
| 저장 공간 | 3GB (모델 + 출력) | 5GB |
| GPU | 없어도 가능 | CUDA 또는 MPS |
| 예상 시간 | CPU ~2-3시간 | GPU ~30분 |

```bash
pip install torch transformers numpy
```

```bash
python3 scripts/extract_nomic_vectors.py \
  --output-dir vendored/bge_m3_real \
  --device cuda   # 또는 cpu / mps
```

---

### 추출 완료 확인

```bash
ls -lh vendored/bge_m3_real/
```

아래 5개 파일이 생성되어야 합니다:

```
code_vectors.bin      # 메인 벡터 블롭 (int8, ~170MB — 174K tokens × 1024d)
code_tokens.txt       # 토큰 목록 (한 줄에 하나, UTF-8)
code_tokens.h         # C 헤더 — PRETRAINED_TOKENS[]
code_vectors.h        # C 헤더 — pretrained_vec_at() accessor
code_vectors_blob.S   # 어셈블러 .incbin 지시자
```

한국어 토큰 포함 여부 확인:
```bash
grep -P '[^\x00-\x7F]' vendored/bge_m3_real/code_tokens.txt | head -20
```

---

## 2단계 — 소스 수정

### `src/semantic/semantic.h`

```c
// 변경 전
enum { CBM_SEM_DIM = 768 };

// 변경 후
enum { CBM_SEM_DIM = 1024 };
```

### `src/semantic/semantic.c`

```c
// 변경 전
#include "bge_m3/code_vectors.h"

// 변경 후
#include "bge_m3_real/code_vectors.h"
```

### `Makefile.cbm`

```makefile
# 변경 전
UNIXCODER_BLOB_SRC = vendored/nomic/code_vectors_blob.S
$(UNIXCODER_OBJ): $(UNIXCODER_BLOB_SRC) vendored/nomic/code_vectors.bin | $(BUILD_DIR)

# 변경 후
UNIXCODER_BLOB_SRC = vendored/bge_m3_real/code_vectors_blob.S
$(UNIXCODER_OBJ): $(UNIXCODER_BLOB_SRC) vendored/bge_m3_real/code_vectors.bin | $(BUILD_DIR)
```

---

## 3단계 — C 바이너리 빌드

### macOS / Linux

```bash
make -f Makefile.cbm clean-c
make -f Makefile.cbm cbm -j$(nproc)
```

Apple Silicon:
```bash
arch -arm64 make -f Makefile.cbm clean-c
arch -arm64 make -f Makefile.cbm cbm -j$(sysctl -n hw.logicalcpu)
```

### Windows (Docker + MinGW 크로스컴파일)

```powershell
# 1. 프로젝트 복사 (C: 드라이브로, Docker 공유 드라이브)
robocopy "D:\git\python\codebase-memory-mcp" "C:\Temp\cbm-build" /MIR /XD .git

# 2. Docker 크로스컴파일
docker run --rm -v "//c/Temp/cbm-build:/src" `
  test-infrastructure-build-windows:latest `
  "cd /src && cd vendored && rm -f bge_m3 && ln -sf nomic bge_m3 && cd .. && \
   make -j4 -f Makefile.cbm clean-c && \
   make -j4 -f Makefile.cbm cbm \
     CC=x86_64-w64-mingw32-clang \
     CXX=x86_64-w64-mingw32-clang++"

# 3. 결과물 복사
Copy-Item "C:\Temp\cbm-build\build\c\codebase-memory-mcp.exe" `
          "D:\git\python\codebase-memory-mcp\build\c\codebase-memory-mcp.exe" -Force
```

빌드 성공 시:
```
Built: build/c/codebase-memory-mcp(.exe)
```

---

## 4단계 — 테스트

### 자동화 테스트

```bash
make -f Makefile.cbm test
```

### 런타임 수동 테스트

시맨틱 임베딩은 **opt-in**입니다. 환경변수로 활성화합니다.

```bash
CBM_SEMANTIC_ENABLED=1 ./build/c/codebase-memory-mcp /path/to/your/project
```

#### 한국어 다국어 효과 확인

```python
# test_korean.py
def get_user(user_id: int):
    """사용자 ID로 사용자를 조회합니다. 존재하지 않으면 None을 반환합니다."""
    pass

def find_account(account_id: int):
    """계정 ID로 계정 정보를 검색합니다. 사용자와 연관된 계정을 반환합니다."""
    pass
```

인덱싱 후 `SEMANTICALLY_RELATED` 엣지가 두 함수 사이에 생성되는지 확인합니다.

#### 유사도 임계값 조정

```bash
# 기본값 0.75 (Linux 커널 기준 ~95% 정밀도)
CBM_SEMANTIC_ENABLED=1 ./build/c/codebase-memory-mcp /path/to/project

# 더 많은 엣지 (낮은 임계값)
CBM_SEMANTIC_ENABLED=1 CBM_SEMANTIC_THRESHOLD=0.65 ./build/c/codebase-memory-mcp /path/to/project

# 더 적은 엣지 (높은 임계값)
CBM_SEMANTIC_ENABLED=1 CBM_SEMANTIC_THRESHOLD=0.85 ./build/c/codebase-memory-mcp /path/to/project
```

---

## 벡터 사양 비교

| 항목 | nomic-embed-code (구) | BAAI/bge-m3 (현재) |
|------|----------------------|-------------------|
| 차원 | 768d | **1024d** |
| 토큰 수 | 40,856 | **173,966** |
| 언어 | ASCII 전용 | **다국어 (한/일/중/아랍/등)** |
| 블롭 크기 | ~30MB | **~170MB** |
| 한국어 recall | ~5% | **~80%** |
| 모델 기반 | nomic 7B distill | XLM-RoBERTa-large |

---

## 트러블슈팅

### 헤더 파일 없음 오류

```
fatal error: bge_m3_real/code_vectors.h: No such file or directory
```

→ 1단계 추출이 완료되지 않은 것. `ls vendored/bge_m3_real/` 확인.

### 빌드 링크 오류 (차원 불일치)

```bash
make -f Makefile.cbm clean-c   # 반드시 clean 후 재빌드
make -f Makefile.cbm cbm
```

### Windows: 체크포인트 파일 잠김 (PermissionError)

다른 Python 프로세스가 checkpoint.npz를 열어 둔 경우. `--checkpoint` 로 다른 경로 지정:

```bash
python3 scripts/extract_nomic_vectors.py \
  --output-dir vendored/bge_m3_real \
  --tei-url http://localhost:8080 \
  --checkpoint vendored/bge_m3_real/ckpt_new.npz
```

### Windows: code_tokens.txt 인코딩 오류 (UnicodeEncodeError cp949)

추출 스크립트가 중단된 경우 `scripts/write_headers.py`로 헤더 파일만 재생성:

```bash
python3 scripts/write_headers.py
# vendored/bge_m3_real/code_vectors.bin 이 있으면 나머지 파일을 UTF-8로 생성
```

### 추출 중 OOM (메모리 부족)

```bash
# 배치 크기 줄이기 (TEI: 기본 32, 직접 추론: 기본 32)
python3 scripts/extract_nomic_vectors.py --batch-size 8

# 시뮬레이션 어텐션 생략 (메모리 사용량 대폭 감소, 품질 소폭 저하)
python3 scripts/extract_nomic_vectors.py --skip-attention
```
