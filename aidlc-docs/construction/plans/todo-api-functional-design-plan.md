# Functional Design 계획 - todo-api

## 유닛 컨텍스트
- **유닛**: `todo-api` (단일 유닛. Application Design과 Units Generation은 건너뛰었으므로 `aidlc-docs/inception/requirements/requirements.md`를 기준 문서로 사용)
- **책임**: 할 일 추가, 목록/단건 조회, 완료 상태 변경, 논리 삭제, 상태 확인
- **경계**: 외부 시스템 연동 없음. 영속 저장은 로컬 SQLite 파일 하나

## 실행 단계
- [x] 1. 유닛 컨텍스트 분석 (요구사항 문서 기준)
- [x] 2. 설계 질문 작성 (아래 질문 1~4)
- [x] 3. 사용자 답변 수집 및 모호함 분석
- [x] 4. `domain-entities.md` 작성 - Todo 엔티티, 필드 제약, 상태
- [x] 5. `business-rules.md` 작성 - 입력 검증 규칙, 완료 상태 전환 규칙, 논리 삭제 규칙, 오류 규칙
- [x] 6. `business-logic-model.md` 작성 - 기능별 처리 흐름, API 계약, 오류 응답 형식, 오용 시나리오(SECURITY-11), 테스트 가능한 속성(PBT-01 권고)
- [x] 7. 확장 규칙 준수 점검 (Security, Resiliency, PBT 부분 적용)
- [x] 8. 완료 메시지 제시 및 승인 요청

## 질문 평가 결과
요구사항 단계에서 이미 확정되어 질문하지 않는 항목: 엔티티 필드, 완료 상태 전환(양방향, 멱등), 논리 삭제 항목 취급, 필터 값 검증, 인증 방식.
해당 없는 범주: 외부 연동(없음), 프런트엔드 컴포넌트(없음).
아래 4개는 설계 결과가 달라지는 미정 사항입니다.

---

# 설계 질문

각 질문의 `[Answer]:` 뒤에 선택지의 알파벳을 적어 주세요.

## Question 1
같은 제목의 할 일을 여러 개 등록할 수 있게 할까요?

A) 허용 (제목 중복 검사 없음)

B) 금지 - 삭제되지 않은 항목 중 같은 제목이 있으면 거부 (HTTP 409)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2
목록 조회 결과의 정렬 순서는 어떻게 할까요?

A) 생성 순 (오래된 항목이 먼저)

B) 최신 순 (새로 만든 항목이 먼저)

C) 미완료 항목 먼저, 그 안에서는 최신 순

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3
제목에 HTML/스크립트로 해석될 수 있는 문자(`<`, `>` 등)가 들어오면 어떻게 처리할까요?
(보안 규칙 SECURITY-05는 사용자 입력 문자열의 HTML/스크립트 내용을 이스케이프하거나 거부하도록 요구합니다. 이 API는 HTML을 제공하지 않고 JSON만 반환합니다.)

A) 거부 - `<` 또는 `>`가 포함된 제목은 HTTP 400 (가장 단순하고 엄격함. "a < b" 같은 제목은 등록 불가)

B) 이스케이프하여 저장 - `<`는 `&lt;` 등으로 변환해 저장하고 그대로 반환 (등록은 되지만 조회 값이 입력과 달라짐)

C) 원문 그대로 저장하고 JSON으로만 반환 - 응답은 항상 `application/json`이며 JSON 직렬화가 이스케이프 역할을 함. 제어 문자만 거부 (입력과 조회 값이 항상 같음)

D) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4
요청 본문에 정의되지 않은 필드가 포함되어 있으면 어떻게 처리할까요? (예: 추가 요청에 `title` 외에 `priority`가 함께 온 경우)

A) 거부 - HTTP 400 (엄격한 검증, 클라이언트 실수를 바로 알 수 있음)

B) 무시 - 정의된 필드만 사용하고 나머지는 버림

C) Other (please describe after [Answer]: tag below)

[Answer]: C : 경고창을 통해서 안내
