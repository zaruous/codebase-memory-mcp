# BGE-M3 임베딩 모델 세팅 가이드

nomic-embed-code에서 BAAI/bge-m3로 교체하여 **다국어 docstring 임베딩**을 활성화하는 전체 절차입니다.

---

## 개요

```
[1단계] BGE-M3 벡터 추출 (Python, 1회성)
          └─ vendored/bge_m3/ 생성
              │
[2단계] C 바이너리 빌드
          └─ build/codebase-memory-mcp 생성
              │
[3단계] 테스트
          ├─ 자동화 테스트 (make test)
          └─ 런타임 수동 테스트 (CBM_SEMANTIC_ENABLED=1)
```

---

## 1단계 — BGE-M3 벡터 추출

### 요구 사항

| 항목 | 최소 사양 | 권장 |
|------|---------|------|
| Python | 3.9+ | 3.11+ |
| RAM | 4GB | 8GB |
| 저장 공간 | 3GB (모델 + 출력) | 5GB |
| GPU | 없어도 가능 | CUDA 또는 MPS |
| 예상 시간 | CPU ~2-3시간 | GPU ~30분 |

> BGE-M3는 ~570M 파라미터 (XLM-RoBERTa-large 기반)로 nomic의 7B 대비 훨씬 가볍습니다.

### 패키지 설치

```bash
pip install torch transformers
```

GPU 사용 시 (CUDA):
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu121
pip install transformers
```

### 추출 실행

```bash
# 기본 실행 (vendored/bge_m3/ 에 출력)
python3 scripts/extract_nomic_vectors.py

# 출력 디렉토리 명시
python3 scripts/extract_nomic_vectors.py --output-dir vendored/bge_m3

# GPU 강제 지정
python3 scripts/extract_nomic_vectors.py --device cuda

# Apple Silicon (MPS) — 32GB 이상 권장
python3 scripts/extract_nomic_vectors.py --device mps

# 시뮬레이션 어텐션 생략 (빠르지만 품질 낮음)
python3 scripts/extract_nomic_vectors.py --skip-attention

# 중단 후 재개 (체크포인트 자동 사용)
python3 scripts/extract_nomic_vectors.py --checkpoint vendored/bge_m3/checkpoint.npz
```

### 추출 완료 확인

```bash
ls -lh vendored/bge_m3/
```

아래 5개 파일이 생성되어야 합니다:

```
code_vectors.bin      # 메인 벡터 블롭 (int8, ~40-80MB 예상)
code_tokens.txt       # 토큰 목록 (한 줄에 하나)
code_tokens.h         # C 헤더 — PRETRAINED_TOKENS[]
code_vectors.h        # C 헤더 — pretrained_vec_at() accessor
code_vectors_blob.S   # 어셈블러 .incbin 지시자
```

---

## 2단계 — C 바이너리 빌드

### 요구 사항

```bash
# macOS
xcode-select --install

# Ubuntu / Debian
sudo apt install build-essential
```

### 빌드

```bash
# 기존 빌드 캐시 제거 후 재빌드 (벡터 블롭 변경 시 필수)
make -f Makefile.cbm clean-c
make -f Makefile.cbm cbm
```

Apple Silicon macOS:
```bash
arch -arm64 make -f Makefile.cbm clean-c
arch -arm64 make -f Makefile.cbm cbm -j$(sysctl -n hw.logicalcpu)
```

Linux (멀티코어):
```bash
make -f Makefile.cbm clean-c
make -f Makefile.cbm cbm -j$(nproc)
```

빌드 성공 시:
```
Built: build/codebase-memory-mcp
```

---

## 3단계 — 테스트

### 자동화 테스트 (전체)

```bash
make -f Makefile.cbm test
```

ASan + UBSan 포함한 전체 테스트 스위트를 실행합니다.
docstring 관련 테스트 케이스:
- `pipeline_docstring_go_function`
- `pipeline_docstring_python_function`
- `pipeline_docstring_java_method`
- `pipeline_docstring_kotlin_function`
- `python_docstring`

빠른 빌드 확인만 필요할 때 (의존성 적음):
```bash
make -f Makefile.cbm test-foundation
```

### 런타임 수동 테스트

시맨틱 임베딩은 **opt-in**입니다. 반드시 환경변수를 설정해야 활성화됩니다.

```bash
# 시맨틱 기능 활성화 후 실행
CBM_SEMANTIC_ENABLED=1 ./build/codebase-memory-mcp /path/to/your/project
```

#### 다국어 docstring 효과 확인

한국어 주석이 포함된 테스트용 Python 파일 작성:

```python
# test_korean.py
def get_user(user_id: int):
    """사용자 ID로 사용자를 조회합니다. 존재하지 않으면 None을 반환합니다."""
    pass

def find_account(account_id: int):
    """계정 ID로 계정 정보를 검색합니다. 사용자와 연관된 계정을 반환합니다."""
    pass
```

실행 후 `SEMANTICALLY_RELATED` 엣지가 두 함수 사이에 생성되는지 확인합니다 ("사용자", "조회", "반환" 등 공통 어휘가 유사도에 기여).

#### 유사도 임계값 조정

기본값 0.75가 너무 엄격하거나 너무 느슨하다면:

```bash
# 더 많은 엣지 (낮은 임계값)
CBM_SEMANTIC_ENABLED=1 CBM_SEMANTIC_THRESHOLD=0.65 ./build/codebase-memory-mcp /path/to/project

# 더 적은 엣지 (높은 임계값)
CBM_SEMANTIC_ENABLED=1 CBM_SEMANTIC_THRESHOLD=0.85 ./build/codebase-memory-mcp /path/to/project
```

---

## 트러블슈팅

### 벡터 파일 없음 오류

```
fatal error: bge_m3/code_vectors.h: No such file or directory
```

→ 1단계 추출이 완료되지 않은 것. `ls vendored/bge_m3/` 확인.

### 빌드 링크 오류 (차원 불일치)

기존 nomic 벡터(`vendored/nomic/`)가 링크되고 있을 수 있습니다.

```bash
make -f Makefile.cbm clean-c   # 반드시 clean 후 재빌드
make -f Makefile.cbm cbm
```

### 추출 중 OOM (메모리 부족)

```bash
# 배치 크기 줄이기 (기본 32 → 8)
python3 scripts/extract_nomic_vectors.py --batch-size 8

# 시뮬레이션 어텐션 생략 (메모리 사용량 대폭 감소)
python3 scripts/extract_nomic_vectors.py --skip-attention
```

### 한국어 토큰이 여전히 임베딩에 반영 안 됨

BGE-M3 어휘(`code_tokens.txt`)에 실제로 한국어 토큰이 포함되어 있는지 확인:

```bash
grep -P '[^\x00-\x7F]' vendored/bge_m3/code_tokens.txt | head -20
```

출력이 없다면 추출 스크립트의 `is_code_relevant()` 필터 확인.
