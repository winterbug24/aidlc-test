# 요구사항 추가 확인 질문 (Clarification)

답변을 분석한 결과, 요구사항 문서를 작성하기 전에 해결해야 할 항목이 있습니다.
각 질문의 `[Answer]:` 뒤에 선택지의 알파벳을 적어 주세요.

---

## 유효하지 않은 답변 1: SQLite 접근 방식 (Q6)
Q6의 답변이 "AA"로 입력되어 있어 유효한 선택지가 아닙니다. 오타로 보이지만 추측하지 않고 확인합니다.

### Clarification Question 1
SQLite 접근 방식은 무엇을 사용할까요?

A) 파이썬 표준 라이브러리 `sqlite3` 직접 사용 (추가 의존성 없음)

B) Flask-SQLAlchemy ORM 사용

C) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 모순 1: 인증 없음(Q5:A) vs 보안 확장 강제 적용(Q9:A)
Q5에서 "인증 필요 없음"을 선택했지만, Q9에서 보안 확장 규칙 전체를 차단 제약으로 강제 적용하도록 선택했습니다.
보안 규칙 SECURITY-08은 "모든 엔드포인트는 명시적으로 공개(public)로 표시하지 않는 한 인증을 요구해야 한다"고 규정하므로 두 답변이 충돌합니다.

### Clarification Question 2
인증과 보안 확장을 어떻게 조정할까요?

A) 보안 확장 유지 + 간단한 API 키 헤더 인증 추가 (키는 환경 변수로 주입, 모든 할 일 엔드포인트에 적용)

B) 보안 확장 유지 + 인증 없음 — 모든 엔드포인트를 "의도적 공개"로 명시하고 근거(로컬 단일 사용자용)를 문서화. 입력 검증, 요청 제한(rate limiting), 로깅, 오류 처리 등 나머지 보안 규칙은 그대로 적용

C) 보안 확장 비활성화 + 인증 없음 (학습/프로토타입 용도로 단순하게)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## 모호함 1: 논리 삭제된 항목의 취급 (Q4:B)
논리 삭제를 선택하셨는데, 삭제된 항목을 이후에 어떻게 다룰지가 정해지지 않았습니다.
(요청하신 기능은 "추가/조회/완료처리/삭제만"이었습니다.)

### Clarification Question 3
논리 삭제된 할 일은 어떻게 취급할까요?

A) 모든 조회에서 제외하고 복구 기능도 없음 (API에서는 삭제된 것처럼 보이고, DB에만 기록이 남음)

B) 기본 조회에서는 제외하되 `?include_deleted=true`로 삭제된 항목도 조회 가능 (복구 기능 없음)

C) 기본 조회에서 제외 + 삭제 항목 조회 + 복구(restore) 엔드포인트 추가

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

# 복원력 확장 필수 질문

복원력 확장(Q10:A)을 활성화하셨기 때문에, 확장 규칙이 요구사항 단계에서 반드시 사용자에게 묻도록 정한 질문입니다.
(CI/CD, 롤백, 배포 방식, 장애 대응, 복원력 테스트 관련 질문은 이후 NFR 단계에서 이어집니다.)

## Clarification Question 4: 배포 대상
이 API는 어디에서 실행될 예정인가요? (복원력 규칙 중 다중 가용 영역, 오토스케일링 등의 적용 여부가 여기에 따라 결정됩니다.)

A) 로컬 PC에서만 실행 (학습/개인용, 배포 없음) — 인프라 관련 복원력 규칙 대부분은 N/A 처리

B) 단일 서버/VM 또는 단일 컨테이너에 배포

C) 클라우드에 프로덕션 수준으로 배포 (다중 가용 영역, 로드 밸런서 등) — 참고: 파일 기반 SQLite는 다중 인스턴스 구성과 맞지 않아 저장소 재검토가 필요할 수 있음

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification Question 5: RTO/RPO 목표 및 재해 복구 전략 (RESILIENCY-02)
복구 시간 목표(RTO)와 복구 시점 목표(RPO)는 어느 수준인가요? 재해 복구(DR) 전략과 인프라 이중화 수준을 결정합니다.

A) RPO/RTO: 수 시간 — 백업 및 복원(Backup & Restore) 전략. 최저 비용. 데이터만 백업하고, 장애 시 재배포 후 백업에서 복원. 비핵심 워크로드에 적합

B) RPO/RTO: 수십 분 — 파일럿 라이트(Pilot Light) 전략. 데이터는 실시간 유지, 서비스는 대기 상태. 중요 워크로드에 적합

C) RPO/RTO: 수 분 — 웜 스탠바이(Warm Standby) 전략. 데이터 실시간 유지, 서비스는 축소 용량으로 가동. 비즈니스 핵심 애플리케이션에 적합

D) RPO/RTO: 거의 실시간 — 다중 사이트 액티브/액티브 전략. 최고 비용. 여러 리전에서 동시 가동. 무중단이 필요한 미션 크리티컬 워크로드에 적합

E) 해당 없음 — 단일 리전(또는 로컬) 실행으로 충분하며 리전 간 DR 불필요

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Clarification Question 6: 변경 관리 프로세스 (RESILIENCY-03)
이 워크로드의 프로덕션 변경은 어떻게 관리되어야 하나요?

A) 기존 조직의 변경 관리 프로세스 사용 — `[Answer]:` 뒤에 이름/도구를 함께 적어 주세요 (예: ServiceNow, Jira Change, 내부 CAB)

B) 공식 프로세스가 아직 없음 — AI-DLC가 가벼운 변경 관리 프로세스(변경 기록 + 승인 + 롤백 메모)를 제안

C) 해당 없음 — 공식 변경 관리 대상이 아님 (예: 개인/내부 도구). 면제 사유를 문서화

X) Other (please describe after [Answer]: tag below)

[Answer]: C
