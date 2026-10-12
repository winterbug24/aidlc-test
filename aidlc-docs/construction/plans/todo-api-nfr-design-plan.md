# NFR Design 계획 - todo-api

## 유닛 컨텍스트
- **유닛**: `todo-api`
- **입력 문서**: `aidlc-docs/construction/todo-api/nfr-requirements/` (nfr-requirements.md, tech-stack-decisions.md), `aidlc-docs/construction/todo-api/functional-design/`

## 실행 단계
- [x] 1. NFR 요구사항 분석
- [x] 2. 설계 질문 작성 (아래 질문 1~4)
- [x] 3. 사용자 답변 수집 및 모호함 분석
- [x] 4. `nfr-design-patterns.md` 작성 - 보안, 복원력, 관측 가능성, 성능, 테스트 용이성 패턴과 복원력 테스트 시나리오
- [x] 5. `logical-components.md` 작성 - 논리 컴포넌트, 책임, 의존 관계, 요청 처리 파이프라인, 설정 항목
- [x] 6. 확장 규칙 준수 점검 (Security, Resiliency, PBT 부분 적용)
- [x] 7. 완료 메시지 제시 및 승인 요청

## 질문 범주 평가 결과

| 범주 | 판단 | 근거 |
|---|---|---|
| Resilience Patterns | 질문 3개 (Q1, Q3, Q4) | 복원력 테스트 방식은 확장 규칙이 사용자에게 묻도록 정함. SQLite 저널 방식과 잠금 시 동작은 설계 결과가 달라짐 |
| Scalability Patterns | 질문 없음 | 단일 프로세스, 수평 확장 미요구로 확정됨 (SCAL-01) |
| Performance Patterns | 질문 없음 | 목표와 수단(인덱스)이 확정됨 (PERF-01, 02). 캐시는 규모상 불필요 |
| Security Patterns | 질문 1개 (Q2) | 인증, 검증, 요청 제한 방식과 수치는 확정됨. API 키 전달 헤더만 미정 |
| Logical Components | 질문 없음 | 큐, 캐시, 서킷 브레이커는 외부 의존성이 없어 불필요. 요청 제한 저장소는 메모리로 확정됨 |

질문 없이 설계에서 정하는 항목: 요청 제한의 클라이언트 식별은 직접 연결된 원격 주소만 사용(프록시 헤더 신뢰 안 함), 요청 제한 초과 응답에 `Retry-After` 헤더 포함.

---

# 설계 질문

각 질문의 `[Answer]:` 뒤에 선택지의 알파벳을 적어 주세요.

## Question 1: 복원력 테스트 접근 방식 (RESILIENCY-14)
복원력 메커니즘(장애 조치, 복구)은 어떻게 검증할까요? 이 프로젝트에서는 백업/복원과 DB 접근 실패 시 동작이 대상입니다.

A) 기존 DR 테스트/게임 데이/카오스 엔지니어링 관행 사용 - `[Answer]:` 뒤에 참조를 함께 적어 주세요

B) 관행 없음 - AI-DLC가 테스트 일정과 실험 계획을 제안 (예: 백업 후 복원 검증 절차와 주기, DB 파일 잠금/손상/삭제 상황의 자동화 테스트)

C) Operations 단계로 미룸 - 테스트 시나리오만 지금 기록하고 실행은 Operations 단계에서

X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2
API 키는 어떤 HTTP 헤더로 전달할까요?

A) `X-API-Key: <키>` (API 키 방식에서 널리 쓰이는 전용 헤더, curl 예시가 단순함)

B) `Authorization: Bearer <키>` (표준 인증 헤더, 나중에 토큰 방식으로 바꾸기 쉬움)

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
SQLite 저널 방식은 무엇을 사용할까요?

A) WAL 모드 - 읽기와 쓰기가 서로 막지 않아 다중 스레드 서버에 유리하고 비정상 종료에 강함. DB 파일 옆에 `-wal`, `-shm` 보조 파일이 생기므로 파일을 직접 복사하지 말고 제공되는 백업 스크립트를 써야 함

B) 기본 모드(DELETE 저널) - DB 파일 하나로 관리되어 단순함. 쓰기 중에는 읽기가 잠시 대기

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
DB가 잠겨 있어 타임아웃(5초) 안에 작업하지 못하면 어떻게 응답할까요?

A) 재시도 없이 즉시 503 `service_unavailable` 반환, `Retry-After` 헤더 포함 (단순하고 예측 가능. 재시도는 클라이언트 몫)

B) 서버가 한 번 더 시도한 뒤에도 실패하면 503 반환 (일시적 잠금에 더 관대하지만 최악의 경우 응답이 약 10초 걸림)

C) Other (please describe after [Answer]: tag below)

[Answer]: B
