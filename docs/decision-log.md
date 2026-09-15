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

## DL-007 — 파이프라인 우선, 법령 corpus는 어댑터로

**배경:** ADOMS는 실제 법령을 만나며 5년간 스키마를 재설계했다.
jungche는 v0.2/v0.3 설계안에 그 시행착오의 결론이 이미 압축되어 있다.

**결정:** 순서를 뒤집는다.
- ADOMS: 법령 → 시행착오 → 설계
- jungche: 설계 → 파이프라인 → 법령 (어댑터로)

**이유:**
- Phase 6 (Assessment)은 법령 없이도 T01~T09로 검증 가능
- 엔진 계층이 굳어야 law adapter가 뭘 넣어야 하는지 명확해짐
- ADOMS corpus는 adapter로 가져옴 (v0.3 §0-A2)

**감수하는 리스크:**
- 법령 원문 자체의 지저분함(별표, "다만 ~ 제외")이
  설계에 반영 안 됐을 수 있음
- → 어댑터 붙일 때 드러남. 그때 DL로 기록.

**대가:** ADOMS가 겪은 중간 단계를 우리는 건너뛴다.
장점: 그 5년을 안 산다. 단점: 그 5년이 준 직관을 놓친다.

**검증 상태 (2026-09-15):**
- Assessment engine 완성
- T01~T09 integration 100% PASS
- residual 생성 경로 검증 (MISSING_FACT, RULE_COVERAGE)
- pytest 총 154 passed

---

## DL-008 — Residual signature 설계

**문제:** 같은 원인의 residual이 매번 새 row가 되면 클러스터링 불가.
`occurrence_count` 누적이 안 됨.

**현재 구현 (013d):**
- `signature = f"scope:{scope_key}:{reason}"` — 결정적 문자열
- 매번 새 row INSERT (누적 로직 아직 없음)

**다음 (013e):**
- signature 기반 UPSERT — 같은 signature면 `occurrence_count += 1`, `last_seen_at` 갱신
- `pg_trgm similarity`로 유사 signature 클러스터링
- `candidate_min_occurrence = 3` config (v0.2 §14.2)

**대가:** signature 생성 규칙이 residual_type별로 달라야 함.
지금은 scope 실패만. MISSING_FACT/PARSER 등은 별도 규칙 필요.


## DL-009 — Ontology는 residual 뒤에만 존재할 수 있다 (DB 강제)

**배경:** v0.2 §13.4, §0-B2는 "AI가 법률을 만들지 않는다",
"Ontology를 hot path에 넣지 않는다"를 문서 원칙으로 적었다.
원칙만으로는 코드가 어길 수 있다.

**결정:** `review.ontology_candidate` 스키마 제약으로 강제.
- `residual_id uuid NOT NULL REFERENCES review.residual_item`
  → 정상 판정 경로에서는 candidate 생성 불가 (DB가 거부)
- `candidate_type CHECK IN ('ALIAS','CLASS','MAPPING','SCOPE')`
  → 자유텍스트 증식 방지
- `status CHECK IN ('PENDING','APPROVED','REJECTED','DEFERRED')`
  → 4상태 외 없음

**결과:**


## DL-010 — RULE_COVERAGE 승격은 한 단계 더 검증 필요 (해결: 013i, 2026-09-16)


**상태:** 이번 티켓(013g)에서는 v0.2 §12.3 그대로 구현. 정교화는 별도 티켓으로 미룸.

**GPT Project 지적 (2026-09-15):**
> RULE_COVERAGE는 UNMAPPED_SOURCE_TYPE보다 조심해야 한다.
> 이것도 무조건 승격이 아니라:
> ```
> RULE_COVERAGE 발생
>   ↓
> source/parser/version 문제 아님 확인
>   ↓
> 같은 패턴 반복
>   ↓
> 기존 scope/rule로 설명 불가
>   ↓
> candidate
> ```
> 여기까지 가야 한다.

**문제:** 현재 `promote_residuals`는 `RULE_COVERAGE`와 `UNMAPPED_SOURCE_TYPE`을 동등 취급.
- `residual_type = RULE_COVERAGE`
- `occurrence_count >= 3`
- `status = ACCUMULATING`
- 미승격

이 4개 조건만 만족하면 무조건 candidate 생성.

**왜 위험한가:**
- `RULE_COVERAGE`가 실제로는 **source/parser/version 문제** 때문에 생겼을 수 있음
- 그걸 ontology candidate로 승격하면 → **DB 스키마 문제를 ontology 문제로 오진**
- v0.2 §12.3 원문도 "**RULE_COVERAGE 중에서도 반복 패턴이 확인된 것만**" 이라고 조건을 달아놨음
- 지금 코드는 "반복"만 보고 "패턴 확인"은 안 함

**미래 티켓 (013h or later) 스코프:**
1. `RULE_COVERAGE` 발생 시 같은 scope/source에 대해:
   - `LAW_VERSION_CONFLICT` 동시 발생 여부 확인
   - `PARSER` residual 동시 발생 여부 확인
   - 해당 scope의 `source_block_id` 파싱 실패 이력 확인
2. 위 셋 다 아니고 **순수 coverage 부족**일 때만 승격
3. 이를 위한 별도 residual 컬럼 또는 조회 함수

**당장의 대응:**
- 지금은 DL-010을 남기고 진행
- 실제로 `RULE_COVERAGE`가 반복되는 케이스가 나오면 그때 013h로 처리
- 그때까지는 "일단 다 승격"이 정책

**대가:**
- 정책이 v0.2 §12.3보다 느슨함
- 하지만 현재 시드 데이터에 `RULE_COVERAGE`가 반복될 만한 케이스가 없음
- 실제 데이터로 드러나면 그때 조임

**기억 장치:**
- 이 DL이 저장소에 있으므로 다음 세션에서도 참조 가능
- 관련: v0.2 §12.3, DL-009 (ontology는 residual 뒤에만)
- 다음 티켓 후보: 013h (RULE_COVERAGE 정교화), 또는 실제 데이터 들어온 뒤



**해결 (Ticket 013i, 2026-09-16):**
`promote_residuals`에 gate 추가:
- `_has_conflicting_residual(conn, facility_id, conflict_types=...)` 헬퍼
- `RULE_COVERAGE` 승격 전 같은 facility에 대해 확인:
  - `PARSER` / `LAW_VERSION_CONFLICT` / `SOURCE_CONFLICT`
- 위 중 하나라도 `ACCUMULATING` 상태면 승격 skip
- `UNMAPPED_SOURCE_TYPE`은 gate 없음
- 회귀 테스트 4개 (`TestRuleCoverageGate`)
---

## DL-011: Ollama 연동 스코프 & 모델 선택 (Phase 9 진입)

**Date**: 2026-09-16
**Status**: Accepted
**Context**: v0.2 §24 Phase 9. residual cluster 자동 분류를 위해
로컬 LLM 필요. Phase 2/3(Law Adapter)은 DL-007에 따라 defer.

**Decisions**:
1. 모델: `qwen3:8b` (로컬 확인, 5.2GB, ollama 0.34.0)
2. API: `/api/chat` (system/user 역할 분리)
3. 출력: JSON 강제 (`format: "json"`)
4. **thinking mode 비활성화**: `think: false`
   — Qwen3 기본 thinking이 JSON 파싱 방해
5. 클라이언트: httpx sync
6. 타임아웃 60s, 재시도 1회
7. 후보는 DB 직행 금지 — 사람 검수 큐 경유 (v0.2 §13.4)
8. 판정 엔진 import 금지 — Ollama 죽어도 판정 무영향 (v0.2 §15)

**Consequences**:
- 013j: client.py 골격 + 단일 호출 성공
- 013k: cluster → prompt → candidate 저장
- 013l: 실패 격리 테스트

**Related**: DL-007, v0.2 §13.4, §15, §24

## DL-012: Branch Diagnosis & Growth Origin

**Date**: 2026-09-16
**Status**: Accepted
**Context**: Phase 9 후속. `promotion.py`가 residual_type →
candidate_type을 자동 확정 (UNMAPPED_SOURCE_TYPE→CLASS,
RULE_COVERAGE→SCOPE)하여 클래스 폭발 위험. 네 통찰:
조문 성장은 위/아래층에서 원인이 다름.

**Decisions**:
1. residual_type은 "증상", candidate_type은 "진단".
   자동 확정 금지.
2. candidate_type = {ALIAS, MAPPING, CLASS, SCOPE, NONE}
   — 비용 순서대로 ALIAS < MAPPING < CLASS < SCOPE.
   싼 것으로 해결 가능하면 비싼 것으로 승격 금지.
3. `NO_ONTOLOGY_CHANGE` 공식 허용. AI가 "새로 만들지 마"
   라고 답할 권리를 프롬프트 스키마에 명시.
4. 승격 gate = 반복성 + 판정 가치(decision_gain).
   - 분리 시 다른 rule set / EXCLUDE / threshold / scope 적용?
   - 전부 NO면 alias/mapping으로 종결.
5. growth_origin = {TOP_DOWN, BOTTOM_UP}.
   - BOTTOM_UP: residual 경로 (현장·사고·집행)
   - TOP_DOWN: 법령 개정 diff 경로 (Phase 2/3 이후)
6. 92-class 선제 확정 금지. backbone + 자가확장.

**Consequences**:
- 013L: Branch Diagnosis 구현 (아래 스코프)
- Phase 2/3 Law Adapter: law diff → TOP_DOWN 후보 경로 신설
- promotion.py 자동 확정 로직 제거

**Related**: DL-007, DL-011, v0.2 §13.4, §14, §24

## DL-012: Branch Diagnosis & Growth Origin

**Date**: 2026-09-16
**Status**: Accepted
**Context**: 013k 이후. `promotion.py`가 residual_type →
candidate_type을 자동 확정 (`UNMAPPED_SOURCE_TYPE→CLASS`,
`RULE_COVERAGE→SCOPE`)하여 클래스 폭발 위험. 조문 성장은
위층(정책·입법 목적, 축 개설)과 아래층(사고·집행·현장 예외,
항·호·목·단서·별표)에서 원인이 다름.

**Decisions**:
1. residual_type은 "증상", candidate_type은 "진단".
   자동 확정 금지.
2. candidate_type = {ALIAS, MAPPING, CLASS, SCOPE, NONE}.
   비용 순서: ALIAS < MAPPING < CLASS < SCOPE.
   싼 것으로 해결 가능하면 비싼 것으로 승격 금지.
3. `NO_ONTOLOGY_CHANGE` 공식 허용. AI가 "새로 만들지 마"
   라고 답할 권리를 프롬프트 스키마에 명시 (013k 후속).
4. 승격 gate = 반복성 + 판정 가치(decision_gain).
   - 분리 시 다른 rule set / EXCLUDE / threshold / scope?
   - 전부 NO면 alias/mapping으로 종결.
5. growth_origin = {TOP_DOWN, BOTTOM_UP}.
   - BOTTOM_UP: residual 경로 (현장·사고·집행)
   - TOP_DOWN: 법령 개정 diff 경로 (Phase 2/3 이후)
6. 92-class 선제 확정 금지. backbone + 자가확장.
7. 자동 승격 금지 원칙(v0.2 §13.4) 재확인.

**Consequences**:
- 013L: Branch Diagnosis 구현
- promotion.py `_CANDIDATE_TYPE_MAP` 제거
- Phase 2/3 Law Adapter: law diff → TOP_DOWN 경로 신설

**Related**: DL-007, DL-010, DL-011, v0.2 §13.4, §14, §24