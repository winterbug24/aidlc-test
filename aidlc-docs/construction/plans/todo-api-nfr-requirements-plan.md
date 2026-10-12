# NFR Requirements 계획 - todo-api

## 유닛 컨텍스트
- **유닛**: `todo-api`
- **입력 문서**: `aidlc-docs/inception/requirements/requirements.md` 4장, `aidlc-docs/construction/todo-api/functional-design/`
- **실행 환경**: 로컬 PC 전용. 확인된 환경: WSL Ubuntu, Python 3.12.3 설치됨, `pip` 명령은 없음(가상 환경 구성 필요)

## 실행 단계
- [x] 1. 기능 설계 분석
- [x] 2. NFR 질문 작성 (아래 질문 1~12)
- [x] 3. 사용자 답변 수집 및 모호함 분석
- [x] 4. `nfr-requirements.md` 작성 - 성능/확장성 가정, 가용성, 보안, 신뢰성, 유지보수성 요구사항과 측정 기준
- [x] 5. `tech-stack-decisions.md` 작성 - 런타임, 프레임워크, 라이브러리, 버전 고정 방식, PBT 프레임워크(PBT-09)
- [x] 6. 확장 규칙 준수 점검 (Security, Resiliency, PBT 부분 적용)
- [x] 7. 완료 메시지 제시 및 승인 요청

## 질문 평가 결과
- **질문하지 않는 항목**: 인증 방식, RTO/RPO, 변경 관리, DB 접근 방식, 테스트 프레임워크(pytest, Hypothesis)는 이미 확정됨
- **가정으로 기록할 항목**: 확장성과 성능은 로컬 단일 사용자 기준(동시 사용자 1명, 항목 수천 건 이하)으로 가정하며 별도 목표 수치를 묻지 않음. 가정이 맞지 않으면 승인 단계에서 알려 주세요
- **해당 없는 범주**: 사용성/접근성(화면 없음)

---

# NFR 질문

각 질문의 `[Answer]:` 뒤에 선택지의 알파벳을 적어 주세요.

## 기술 스택

## Question 1
Python 버전은 무엇을 기준으로 할까요?

A) Python 3.12 (현재 WSL에 설치된 버전, 추가 설치 불필요)

B) Python 3.13 이상 (별도 설치 필요)

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
의존성 버전 고정은 어떤 방식으로 할까요? (보안 규칙 SECURITY-10은 정확한 버전 고정 또는 잠금 파일을 요구합니다.)

A) `requirements.txt`와 `requirements-dev.txt`에 직접 의존성과 하위 의존성을 모두 정확한 버전(`==`)으로 고정 (도구 추가 없음)

B) pip-tools 사용 - `requirements.in`에서 해시가 포함된 `requirements.txt`를 생성 (무결성 검증 강화, 도구 1개 추가)

C) uv 또는 Poetry 같은 프로젝트 관리 도구와 그 잠금 파일 사용

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
입력 검증은 어떻게 구현할까요? (보안 규칙 SECURITY-05는 모든 API 핸들러가 검증 라이브러리 또는 스키마를 사용하도록 요구합니다.)

A) 자체 스키마 검증 모듈 작성 - 필드별 타입/길이/허용 필드를 선언한 스키마와 검증 함수 (추가 의존성 없음, 규칙이 단순해 충분함)

B) pydantic 사용 (선언적 모델, 의존성 추가)

C) marshmallow 사용 (선언적 스키마, 의존성 추가)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
요청 제한(rate limiting)은 어떻게 구현할까요?

A) Flask-Limiter 라이브러리 사용, 메모리 저장소 (검증된 구현, 의존성 추가. 서버를 재시작하면 카운터 초기화)

B) 자체 구현 - 메모리 기반의 간단한 고정 창 카운터 (추가 의존성 없음, 직접 유지보수)

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
요청 제한 한도는 어느 수준으로 할까요? (클라이언트 IP 기준)

A) 분당 60회, 인증 실패는 분당 10회로 더 엄격하게

B) 분당 120회, 인증 실패는 분당 10회로 더 엄격하게

C) 분당 600회, 인증 실패는 분당 20회 (자동화 스크립트로 많이 호출할 예정인 경우)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
애플리케이션은 어떤 서버로 실행할까요?

A) Flask 내장 개발 서버 (`flask run`, 디버그 모드 끔, 127.0.0.1 바인딩) - 가장 단순하지만 Flask가 프로덕션 용도로는 권장하지 않음

B) Waitress WSGI 서버 (순수 파이썬, Windows와 Linux 모두 동작, 의존성 추가)

C) Gunicorn WSGI 서버 (Linux/WSL 전용, 의존성 추가)

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## 운영

## Question 7
로그는 어디에 남길까요? (형식은 JSON 구조화 로그로 확정되어 있습니다.)

A) 표준 출력(stdout)에만 출력

B) 표준 출력 + 로컬 로그 파일 (크기 기준 순환, 최근 파일 몇 개만 보관)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 8
DB 백업은 어떤 형태로 제공할까요? (RTO/RPO 수 시간, 백업 및 복원 전략으로 확정되어 있습니다.)

A) 백업/복원 스크립트 제공 - 수동 실행. SQLite 온라인 백업 기능으로 타임스탬프가 붙은 사본을 만들고 무결성 검사 수행, 최근 N개만 보관

B) 위 A에 더해 주기적 실행 방법(cron 등 예시)을 README에 안내

C) 스크립트 없이 README에 수동 복사 절차만 문서화

D) Other (please describe after [Answer]: tag below)

[Answer]: A

---

# 복원력 확장 필수 질문

복원력 확장 규칙이 사용자에게 직접 묻도록 정한 질문입니다. 로컬 전용 프로젝트라는 점을 고려해 해당 없음에 가까운 선택지도 표시했습니다.

## Question 9: CI/CD 및 배포 도구 (RESILIENCY-04)
이 워크로드는 어떤 CI/CD 도구와 배포 프로세스를 사용할까요?

A) 기존 CI/CD 파이프라인 사용 - `[Answer]:` 뒤에 도구 이름을 함께 적어 주세요 (예: GitHub Actions, GitLab CI, Jenkins)

B) 파이프라인 없음 - AI-DLC가 CI 파이프라인 정의를 제안 (예: 테스트와 취약점 스캔을 실행하는 GitHub Actions 워크플로 파일 생성)

C) 파이프라인 없음 - 만들지 않음. 로컬에서 수동으로 테스트와 취약점 스캔을 실행하고 절차만 문서화 (규칙의 기본 선택지에는 없는 항목으로, Other에 해당하는 답변으로 기록됩니다)

X) Other (please describe after [Answer]: tag below)

[Answer]: A : GitHub Actions

## Question 10: 롤백 방식 (RESILIENCY-04)
변경 후 문제가 생기면 어떻게 되돌릴까요?

A) 이전 버전을 다시 배포 (버전 고정 롤백) - 로컬에서는 git으로 이전 커밋/태그로 되돌리고 재시작하는 방식

B) 블루/그린 전환으로 이전 환경 복귀

C) 카나리 자동 롤백 (상태/지표 악화 시)

D) DB 인식 롤백 필요 (스키마/데이터 마이그레이션 되돌리기) - 별도 설계 대상

E) 기존 조직의 롤백 절차 사용 - `[Answer]:` 뒤에 참조를 함께 적어 주세요

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11: 배포 방식 (RESILIENCY-04)
이 워크로드의 위험 수준에서 허용되는 배포 전략은 무엇인가요?

A) 직접/제자리 교체 (최저 비용, 영향 범위 최대) - 비핵심 워크로드에 적합. 로컬에서는 프로세스를 멈추고 새 코드로 다시 시작하는 방식

B) 롤링 (인스턴스를 점진적으로 교체)

C) 블루/그린 (무중단 전환, 비용 높음)

D) 카나리 (점진적 트래픽 이동과 자동 롤백)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 12: 장애 대응 프로세스 (RESILIENCY-15)
이 워크로드의 장애는 어떻게 처리되나요?

A) 기존 장애 대응 프로세스 사용 - `[Answer]:` 뒤에 참조를 함께 적어 주세요 (예: PagerDuty 런북, 내부 온콜 절차)

B) 공식 프로세스 없음 - AI-DLC가 가벼운 장애 대응 및 사후 분석(COE) 절차를 제안 (README에 문제 해결 절차와 간단한 사후 기록 양식 포함)

X) Other (please describe after [Answer]: tag below)

[Answer]: B
