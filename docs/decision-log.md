# Decision Log — jungche-artisan

프로젝트 설계 결정 기록. 각 DL은 "무엇을 정했고, 왜, 무엇을 포기했는가"를 남긴다.

---

## DL-001 — final_verdict coverage guard (v0.2 12.1)

**문제:** `rule_results == []`가 두 원인을 구분 못 함.
- A. 스코프 확정 + 매칭 0 → NOT_APPLICABLE
- B. rule 로딩 실패/누락 → NOT_APPLICABLE로 보내면 최악의 false negative

**결정:** `final_verdict(rule_results, *, candidate_scope_resolved)` 필수 인자.
- `False` → 무조건 INDETERMINATE + 호출자가 `RULE_COVERAGE` residual 기록
- `True` → v0.2 10장 4-state 알고리즘

**근거:** 법률 시스템에서 "적용 대상인데 안전하다고 확신"이 가장 위험.
불확실 시 사람 검토로 유보.

**스코프 판정 주체:** Assessment Engine.
`law.reference_edge` 순회 + `rule.rule` 로딩이 완결됐는지 여부.
→ Ticket 013a에서 `rule.scope.coverage_status = COMPLETE`로 구현.

**추가 결정 (2026-09-15):**
scope unresolved 시 EXCLUDE=TRUE도 INDETERMINATE.
이유: 스코프 불확실하면 어떤 rule도 신뢰 불가.
법률 안전 기본값은 사람 검토.

---

## DL-002 — psycopg3는 jsonb 컬럼에 Jsonb() 래퍼 필수

**문제:** psycopg3는 Python str/int를 jsonb 컬럼에 자동 어댑트하지 않는다.
`"OFFICE"`를 그대로 넘기면 PostgreSQL이 JSON 파싱 시도 → `Token "OFFICE" is invalid`.

**발견 경로:** Ticket 013c 첫 integration 실행.

**결정:** jsonb 컬럼 INSERT 파라미터는 항상 `Jsonb()` 래핑.
- `Jsonb("OFFICE")` → `'"OFFICE"'`
- `Jsonb(3000)` → `'3000'`
- `Jsonb(None)` → `'null'`
- `Jsonb({"a": 1})` → `'{"a": 1}'`

**대가:** 매 INSERT마다 명시 래핑 필요. 잊으면 런타임 에러.
초기 `_json()` no-op 헬퍼는 오판이었음 — 명시 래퍼로 교체.

**참고:** fake-conn 유닛 테스트는 타입 어댑테이션을 거치지 않으므로
이 문제를 절대 못 잡는다. integration test가 유일한 방어선.

---

## DL-003 — final_verdict: INCLUDE FALSE dominates EXCLUDE

**문제:** v0.2 §10 알고리즘이 "EXCLUDE 우선"을 잘못 구현.
INCLUDE가 모두 FALSE인데 EXCLUDE UNKNOWN이 INDETERMINATE를 만들었음.

**발견 경로:** Ticket 013c 통합테스트 T03.
- T03: OFFICE scope, `area=2000` (INCLUDE FALSE), officetel 정보 없음 (EXCLUDE UNKNOWN)
- 기존: INDETERMINATE (잘못)
- 정정: NOT_APPLICABLE

**정정된 알고리즘:**

**근거:** EXCLUDE는 "적용 대상일 때 제외"라는 의미.
INCLUDE가 FALSE면 시설은 적용 대상 아님 → EXCLUDE 평가 무의미.

**대가:** v0.2 §10 문서 알고리즘과 다름. v0.3 문서에 반영 필요.

**부수 관찰:** integration seed에서 `use_type`/`subtype`을 명시 안 하면
EXCLUDE rule이 UNKNOWN이 되어 T01/T08이 INDETERMINATE로 나옴.
이는 정정된 로직의 정상 동작 — "제외 여부 미확정 → 확정 불가".
→ seed fixture는 시설 유형을 명시적으로 기록해야 함.

---

## DL-004 — Grok 반증감사 처분 (Ticket 012c)

**배경:** expression tree trace 로직에 대해 Grok이 FP 5개 / FN 5개 제시.

**수용:**
- FP-2: `None` 값은 `NULL_VALUE` reason으로 분리 (MISSING_FACT와 다름)
- FP-4: `fact_meta`가 dict가 아니면 조용히 버림 (crash 방지)
- FP-5: bool ↔ number 혼용은 UNKNOWN (TypeError 방지)
- FN-3: UNKNOWN 이유 3분화 (`MISSING_FACT` / `NULL_VALUE` / `TYPE_MISMATCH`)
- FN-5: `sort_order` 동률은 `(sort_order, expr_id)` tie-break
- X-1: `fact_meta` 타입 가드

**거부:**
- FP-1: Kleene OR + 결측 = TRUE는 v0.2 §9 정상. 회귀 테스트로 명시적 고정.
- FN-1/X-2: unknown operator는 여전히 `ValueError`. fail-fast 유지.
  이유: programmer/config error를 조용히 UNKNOWN으로 넘기면
  법률 시스템의 seed 검증 실패를 감춤.
- FN-2: 내부 AND/OR/NOT 노드 trace는 v0.2 §11.3 계약상 leaf만.
- FN-4: `fact_meta` 키를 `expr_id`로 주는 건 잘못된 사용.

**추가 수정 (Grok #4):** loader와 eval의 children 정렬 키가 달랐음.
loader는 `sort_order`만, eval은 `(sort_order, expr_id)`.
→ loader도 동일 키로 통일. `test_loader_tiebreak.py`로 고정.

**대가:** `evaluate_tree` API는 그대로. `evaluate_tree_with_trace`가 실제 구현.
회귀 테스트 14개 + tie-break 2개가 계약을 지킴.

---

## DL-005 — ADOMS는 Knowledge Provider, 본 시스템은 Canonical Engine

**배경:** v0.3 §0-A/B/C. ADOMS(10M 트리플 GraphDB)는 폐기 대상이 아니라
상위 지식공급자 + 교차검증 자산으로 둔다.

**결정:**
- ADOMS = Knowledge Provider (읽기 전용 참조)
- PostgreSQL = Canonical Decision Engine (판정 정본)
- 둘 사이에 adapter를 두고, GraphDB 내부 구조(IRI, named graph)는
  서비스 판정 엔진에 노출하지 않는다.

**가져온 패턴 (v0.3 §0-A):**
- A1 사실층/판단층 분리 → schema 분리
- A2 관계에 provenance → `reference_edge` metadata 확장 (예정)
- A3 역방향 edge 저장 X → `from/to` 한 방향만
- A4 위임 전이성 X → Recursive CTE로 경로
- A6 불투명 PK + 사람 경로 → `uuid` + `ltree path`/`fact_key`
- A8 "0건 ≠ 없음" → DL-001로 구현
- A10 append 아닌 version → `effective_from/to`
- A11 파싱 실패는 review queue → `residual_item`

**가져오지 않은 것 (v0.3 §0-B):**
- B1 10M 트리플 복제
- B2 Ontology를 hot path에
- B3 GraphDB 내부 구조 API 노출
- B4 GraphDB를 SoT + Engine 동시

**대가:** ADOMS와의 동기화 지점이 별도 작업이 됨.
교차검증은 나중에 별도 티켓으로.

---

## DL-006 — Phase 6 완료 조건 (2026-09-15)

**완료:**
- [x] 3-valued logic (TRUE/FALSE/UNKNOWN)
- [x] AND/OR/NOT/PREDICATE 트리 재귀 평가
- [x] Predicate trace (expr_id, fact_id, reason)
- [x] 4-state verdict (APPLICABLE/NOT_APPLICABLE/EXCLUDED/INDETERMINATE)
- [x] Coverage guard (candidate_scope_resolved)
- [x] scope registry + coverage resolution
- [x] Assessment engine (실 DB INSERT)
- [x] T01~T09 integration 100% PASS
- [x] Grok 반증감사 1회 + 회귀 테스트 14개
- [x] pytest 총 **151 passed**

**다음:** Phase 7 — Residual 파이프라인.