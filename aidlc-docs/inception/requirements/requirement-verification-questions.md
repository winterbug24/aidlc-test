# 요구사항 확인 질문

Flask To-Do 관리 REST API의 요구사항을 명확히 하기 위한 질문입니다.
각 질문의 `[Answer]:` 뒤에 선택지의 알파벳을 적어 주세요.
맞는 선택지가 없으면 마지막 선택지(Other)를 고르고 `[Answer]:` 뒤에 내용을 직접 적어 주세요.

---

## Question 1
할 일(To-Do) 항목에 어떤 정보를 저장할까요? (id, 완료 여부, 생성 시각은 기본 포함)

A) 제목(title)만

B) 제목(title) + 상세 설명(description, 선택 입력)

C) 제목 + 상세 설명 + 마감일(due date)

D) 제목 + 상세 설명 + 마감일 + 우선순위(priority)

E) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
"완료처리"는 어떻게 동작해야 할까요?

A) 완료로만 변경 (한 번 완료하면 되돌릴 수 없음)

B) 완료/미완료 양방향 변경 가능 (완료 취소 허용)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3
"조회" 기능의 범위는 어디까지일까요?

A) 전체 목록 조회만

B) 전체 목록 조회 + 단건 조회(id 기준)

C) 전체 목록 조회 + 단건 조회 + 완료 여부 필터(예: `?completed=true`)

D) 위 C에 더해 페이지네이션(limit/offset)까지

E) Other (please describe after [Answer]: tag below)

[Answer]: C

## Question 4
"삭제"는 어떤 방식으로 처리할까요?

A) 물리 삭제 (DB에서 행을 실제로 제거)

B) 논리 삭제 (삭제 표시만 하고 데이터는 보존)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5
API 인증/사용자 구분이 필요할까요?

A) 필요 없음 (인증 없이 누구나 호출, 단일 사용자용/로컬 학습용)

B) 간단한 API 키 헤더 인증

C) 사용자 계정별로 할 일을 구분 (로그인/토큰 인증)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
SQLite 접근 방식은 무엇을 사용할까요?

A) 파이썬 표준 라이브러리 `sqlite3` 직접 사용 (추가 의존성 없음)

B) Flask-SQLAlchemy ORM 사용

C) Other (please describe after [Answer]: tag below)

[Answer]: AA

## Question 7
프로젝트 코드 구조는 어느 수준으로 할까요?

A) 단일 파일 (`app.py` 하나에 모두 작성, 가장 단순)

B) 소규모 패키지 구조 (앱 팩토리 + 라우트/DB 모듈 분리)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 8
자동화 테스트는 어느 범위까지 포함할까요?

A) pytest 기반 API 테스트 포함 (각 엔드포인트의 정상/오류 케이스)

B) 테스트 코드 없이 수동 확인용 curl 예시만 제공

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

# 확장(Extension) 적용 여부

아래 3개 질문은 AI-DLC 확장 규칙의 적용 여부를 결정합니다.

## Question 9: 보안 확장 (Security Extensions)
이 프로젝트에 보안 확장 규칙을 강제 적용할까요?

A) 예 — 모든 SECURITY 규칙을 차단(blocking) 제약으로 강제 적용 (프로덕션 수준 애플리케이션에 권장)

B) 아니오 — 모든 SECURITY 규칙을 건너뜀 (PoC, 프로토타입, 실험용 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10: 복원력 확장 (Resiliency Extensions)
이 프로젝트에 복원력 기준(resiliency baseline)을 적용할까요?

**이 확장이 하는 일.** 활성화하면 **AWS Well-Architected Framework(안정성 원칙)** 및 복원력 검토 지침에서 도출한 **방향 제시형 설계 단계 모범 사례**가 적용됩니다. 요구사항·설계·코드를 장애 허용, 고가용성, 관측 가능성, 복구 가능성 쪽으로 이끌며, 비즈니스 목표, 변경 관리, 관측 가능성, 고가용성, 재해 복구, 지속적 개선에 걸친 15개 실천 영역을 다룹니다.

**이 확장이 하지 않는 일.** 활성화한다고 해서 워크로드가 프로덕션 준비 상태가 되는 것은 **아니며**, 특정 가용성·RTO·RPO 목표를 인증하거나 보장하지도 않습니다. 초기에 좋은 복원력 결정을 내리도록 돕는 **출발점**일 뿐, 구축된 시스템에 대한 공식 **AWS Well-Architected Review**를 대체하지 않습니다.

결과물은 검증하고 발전시켜 나갈 **복원력 태세의 근거 있는 초안**으로 취급해 주세요. 프로덕션 인증이 끝난 완성본이 아닙니다.

A) 예 — 복원력 기준을 방향 제시형 모범 사례 및 설계 단계 지침으로 적용 (비즈니스 핵심 워크로드에 권장, 출시 전 검증·강화할 수 있는 출발점)

B) 아니오 — 복원력 기준을 건너뜀 (안정성보다 빠른 반복이 중요한 PoC, 프로토타입, 실험용 프로젝트에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11: 속성 기반 테스트 확장 (Property-Based Testing Extension)
이 프로젝트에 속성 기반 테스트(PBT) 규칙을 강제 적용할까요?

A) 예 — 모든 PBT 규칙을 차단(blocking) 제약으로 강제 적용 (비즈니스 로직, 데이터 변환, 직렬화, 상태 저장 컴포넌트가 있는 프로젝트에 권장)

B) 부분 적용 — 순수 함수와 직렬화 왕복(round-trip)에만 PBT 규칙 적용 (알고리즘 복잡도가 제한적인 프로젝트에 적합)

C) 아니오 — 모든 PBT 규칙을 건너뜀 (단순 CRUD 애플리케이션, UI 전용 프로젝트, 비즈니스 로직이 거의 없는 얇은 통합 계층에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
