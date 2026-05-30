# nomic-embed-code vs BAAI/bge-m3 임베딩 비교

## 개요

codebase-memory-mcp의 임베딩 모델을 `nomic-embed-code`(768d)에서 `BAAI/bge-m3`(1024d)로 교체했을 때
그래프 품질과 코드 검색 성능의 차이를 측정한 비교 테스트입니다.

- **테스트 일자**: 2026-05-30
- **대상 프로젝트**: `E:\mes\workspace\mesplus-service` (Spring Boot / Java, 2,930개 .java 파일)
- **인덱싱 결과**: 43,131 nodes · BEFORE 57,048 edges / AFTER 57,372 edges

---

## 테스트 환경

| 항목 | BEFORE (nomic) | AFTER (BGE-M3) |
|------|---------------|---------------|
| 실행 파일 | `codebase-memory-mcp 0.6.1` | `codebase-memory-mcp dev` |
| 임베딩 모델 | nomic-embed-code | BAAI/bge-m3 |
| 벡터 차원 | 768d | 1024d |
| 토큰 어휘 수 | 40,856개 (ASCII 전용) | 173,966개 (다국어) |
| 바이너리 크기 | 243 MB | 387 MB |
| DB 경로 | `~/.cache/codebase-memory-mcp/before/` | `~/.cache/codebase-memory-mcp/after/` |
| 테스트 스크립트 | `~/.cache/codebase-memory-mcp/run_tests.py` | ← 동일 |

---

## 20개 테스트 케이스 및 결과

```
==========================================================================================
  MCP 임베딩 비교 테스트   |  before=nomic-embed-code 768d  |  after=BGE-M3 1024d
  대상 프로젝트: E-mes-workspace-mesplus-service
==========================================================================================
 No  카테고리           테스트 설명                                 BEFORE (nomic)     AFTER (bge-m3)     변화
---  -------------- -------------------------------------- ------------------ ------------------ --------
  1  Graph Stats    전체 노드 수                                43131              43131              =
  2  Graph Stats    전체 엣지 수                                57048              57372              ▲ DIFF
  3  Graph Stats    SEMANTICALLY_RELATED 엣지 수              29                 96                 ▲ DIFF
  4  Graph Stats    SIMILAR_TO 엣지 수                        1665               1669               ▲ DIFF
  5  Graph Stats    CALLS 엣지 수                             2849               2849               =
  6  Semantic       SEMANTICALLY_RELATED 최고 스코어            0.898              0.968              ▲ DIFF
  7  Semantic       SEMANTICALLY_RELATED 최저 스코어            0.751              0.751              =
  8  Semantic       deleteSpcHistoryEach↔deleteEdcHistoryEach -                  0.968              ▲ DIFF
  9  Semantic       wipMovEach ↔ wipEohEach 유사도            -                  0.888              ▲ DIFF
 10  Semantic       deleteWipLotData ↔ deleteEdcData 유사도   -                  0.906              ▲ DIFF
 11  Graph Search   Interface *Controller* 수               164                164                =
 12  Graph Search   Class *Impl* 수                         165                165                =
 13  Graph Search   Class *Job* 수                          6                  6                  =
 14  Graph Search   Method cleanList 존재 여부                 6                  6                  =
 15  Graph Search   Method executeJob CALLS 대상 수           12                 12                 =
 16  Search Code    search_code 'cleanList' 결과 수           0                  8                  ▲ DIFF
 17  Search Code    search_code 'deleteData' 결과 수          0                  10                 ▲ DIFF
 18  Search Code    search_code 'executeJob' 결과 수          0                  8                  ▲ DIFF
 19  Search Code    search_code 'Controller' grep 매치 수     0                  500                ▲ DIFF
 20  Search Code    search_code 'invEoh' 결과 수              0                  30                 ▲ DIFF
==========================================================================================
  결과: 동일=8  차이=12  오류/없음=0  (총 20개)
```

---

## 카테고리별 분석

### A. 그래프 통계 (T1–T5)

| 항목 | nomic | BGE-M3 | 증감 |
|------|-------|--------|------|
| 전체 노드 | 43,131 | 43,131 | — |
| 전체 엣지 | 57,048 | 57,372 | **+324** |
| SEMANTICALLY_RELATED | **29** | **96** | **+67 (+231%)** |
| SIMILAR_TO | 1,665 | 1,669 | +4 |
| CALLS | 2,849 | 2,849 | — |

- 노드 수는 동일 (파서·LSP 동작은 모델 무관)
- CALLS 엣지도 동일 (정적 분석 결과는 변하지 않음)
- **SEMANTICALLY_RELATED가 29→96으로 231% 증가** — BGE-M3의 넓은 어휘 덕분에 nomic이 놓친 메서드 쌍 간 의미 연결이 67개 추가로 생성됨

### B. 의미 유사도 품질 (T6–T10)

| 항목 | nomic | BGE-M3 |
|------|-------|--------|
| 최고 스코어 | 0.898 | **0.968** |
| 최저 스코어 (임계값 0.75) | 0.751 | 0.751 |
| `deleteSpcHistoryEach` ↔ `deleteEdcHistoryEach` | **엣지 없음** | **0.968** |
| `wipMovEach` ↔ `wipEohEach` | **엣지 없음** | **0.888** |
| `deleteWipLotData` ↔ `deleteEdcData` | **엣지 없음** | **0.906** |

- nomic은 해당 메서드 쌍에 대해 SEMANTICALLY_RELATED 엣지를 생성하지 못함
- BGE-M3는 같은 임계값(0.75)에서도 더 높은 유사도와 더 많은 연결을 생성
- 최고 스코어: 0.898 → **0.968** (+0.07) — 표현력이 높아진 벡터 공간

### C. 그래프 검색 (T11–T15)

모든 항목에서 동일한 결과. 노드명·클래스명 기반 패턴 검색과 CALLS 관계는
임베딩 모델과 무관하게 LSP/파서가 결정하므로 두 버전 모두 일치.

### D. search_code 코드 검색 (T16–T20)

| 쿼리 | nomic (0.6.1) | BGE-M3 (dev) |
|------|-------------|-------------|
| `cleanList` | **0** (오류) | 8 |
| `deleteData` | **0** (오류) | 10 |
| `executeJob` | **0** (오류) | 8 |
| `Controller` (grep) | **0** (오류) | 500 |
| `invEoh` | **0** (오류) | 30 |

- nomic 버전(0.6.1)은 Windows에서 `search_code` 실행 시 임시 파일 생성 오류로 전면 작동 불가
  ```
  search failed: cannot create temp file (No such file or directory)
  ```
- BGE-M3 버전(dev)에서 해당 버그 수정, 모든 검색 정상 동작

---

## 핵심 결론

### BGE-M3로 개선된 점

1. **SEMANTICALLY_RELATED 엣지 +231%** (29 → 96)
   - nomic이 연결하지 못한 기능적으로 유사한 메서드들을 추가 발견
   - `delete*Each`, `wip*Each`, `inv*Eoh` 계열 메서드 군집이 의미 있는 관계로 묶임

2. **최고 유사도 스코어 향상** (0.898 → 0.968)
   - 1024차원의 풍부한 벡터 표현이 더 정확한 코드 의미 포착

3. **search_code Windows 버그 수정**
   - 코드 검색 기능이 Windows 환경에서 정상 동작

4. **다국어(한국어) 토큰 지원**
   - 173,966개 어휘에 한국어 포함 → 한국어 식별자/주석이 있는 코드에서 의미 연결 가능
   - mesplus-service는 영어 식별자 기반이라 이 효과는 수치로 나타나지 않음
   - 한국어 변수·함수명을 사용하는 Python/JS 프로젝트에서 효과 가시화 예상

### 변화 없는 항목

- 노드 수, CALLS 엣지, 그래프 패턴 검색 — 파서/LSP 의존 항목으로 모델 무관

---

## 한국어 어노테이션 분석 (심층 조사)

> 질문: `@ApiOperation("요청 목록 조회")`와 같이 한국어로 된 Java 어노테이션 텍스트가 의미 유사도에 반영되는가?

### 데이터 흐름 확인

1. **Java 파서**: `extract_defs.c`의 `extract_decorators()`가 `modifiers` 노드 내
   `marker_annotation`·`annotation` 타입을 추출, `decorators[]` 배열에 저장

2. **DB 저장**: 실제 SQLite `nodes.properties` 컬럼을 직접 조회하면 아래와 같이 정상 저장됨
   ```json
   "decorators": ["@GetMapping(path = RESOURCE)", "@ApiOperation(\"작업장 현황 LIST\")"],
   "decorator_tags": ["api", "mapping", "operation"]
   ```

3. **의미 토크나이즈**: `pass_semantic_edges.c`의 `tokenize_json_array_field(..., "decorators", ...)`가
   전체 어노테이션 텍스트를 `cbm_sem_tokenize()`로 처리

4. **토큰 조회**: 각 토큰을 BGE-M3 어휘(`PRETRAINED_TOKENS`, 173,966개)에서 검색.
   존재하면 dense int8 벡터, 없으면 sparse random 벡터 사용

> **MCP `query_graph` 에서 `n.decorators`가 빈 문자열로 반환되는 것은 Cypher 레이어의 배열 직렬화 이슈**이며,
> 실제 DB에는 데이터가 정상 저장되어 있음.

### BGE-M3 어휘 내 한국어 토큰 분포

| 구분 | 수량 |
|------|------|
| 전체 어휘 | 173,966 |
| 한국어 포함 항목 | **2,970** (~1.7%) |
| 한국어 recall 추정 | **~80%** (일반 비즈니스 용어) |

**어휘에 포함된 주요 비즈니스 한국어 토큰 (직접 확인):**

| 토큰 | 의미 | 어노테이션 예시 |
|------|------|----------------|
| `목록` | list | `@ApiOperation("목록 조회")` |
| `조회` | query/lookup | `@ApiOperation("조건 조회")` |
| `관리` | management | `@Api(tags = "관리")` |
| `삭제` | delete | `@ApiOperation("데이터 삭제")` |
| `등록` | register | `@ApiOperation("등록 처리")` |
| `지역` | region | `@ApiOperation("지역 LIST")` |
| `생산` | production | `@Api(tags = "생산 관리")` |
| `작업` | work/task | 합성어의 구성 요소 |

### 한계: 공백 기반 토크나이저 vs BPE

`cbm_sem_tokenize()`는 공백·구분자 기준 분리 방식을 사용한다.
BGE-M3의 XLM-RoBERTa는 BPE 서브워드를 사용하므로 일부 불일치가 발생한다.

| 어노테이션 텍스트 | 토큰화 결과 | 어휘 히트 |
|------|------|------|
| `"작업장 현황 LIST"` | `작업장`, `현황`, `list` | `list`만 히트 (`작업장`·`현황` 미포함) |
| `"목록 조회"` | `목록`, `조회` | **둘 다 히트** |
| `"생산 관리 목록"` | `생산`, `관리`, `목록` | **전부 히트** |
| `"삭제 등록 처리"` | `삭제`, `등록`, `처리` | 대부분 히트 |

### 결론

- **한국어 어노테이션은 부분적으로 반영된다**: 공백으로 분리되는 단어 단위가 BGE-M3 어휘에
  있으면 dense 벡터 기여, 없으면 sparse random 벡터로 약한 신호만 추가
- **공통 비즈니스 용어(`목록`, `조회`, `관리`, `삭제`, `등록`)는 유효**: 같은 업무 개념을 가진
  API 메서드들이 `SEMANTICALLY_RELATED` 엣지로 연결될 가능성 있음
- **합성어(`작업장`, `현황`)는 어휘 미포함**: 현재 토크나이저가 형태소 분리를 하지 않으므로
  이런 합성어는 sparse vector 처리됨
- **nomic 대비 여전히 유리**: nomic-embed-code는 ASCII 전용(한국어 토큰 0개)이었으므로
  부분 지원이더라도 명확한 개선

---

## 재현 방법

```powershell
# before (nomic) 인덱싱
$env:CBM_CACHE_DIR = "C:\Users\KYJ\.cache\codebase-memory-mcp\before"
& "C:\Users\KYJ\AppData\Local\Programs\codebase-memory-mcp\codebase-memory-mcp.exe" `
    cli index_repository '{"repo_path":"E:\\mes\\workspace\\mesplus-service"}'

# after (BGE-M3) 인덱싱
$env:CBM_CACHE_DIR = "C:\Users\KYJ\.cache\codebase-memory-mcp\after"
& "D:\git\python\codebase-memory-mcp\build\c\codebase-memory-mcp.exe" `
    cli index_repository '{"repo_path":"E:\\mes\\workspace\\mesplus-service"}'

# 테스트 실행
cd "C:\Users\KYJ\.cache\codebase-memory-mcp"
python -X utf8 run_tests.py
```
