# NFR Requirements 계획 - web-ui

## 유닛 컨텍스트
- **유닛**: `web-ui`
- **입력 문서**: `aidlc-docs/inception/requirements/web-ui-requirements.md` 4장, `aidlc-docs/construction/web-ui/functional-design/`, 1차의 `aidlc-docs/construction/todo-api/nfr-requirements/`
- **확인한 환경 (2026-10-12)**:
  - PyPI 최신 버전: playwright 1.63.0, pytest-playwright 0.10.0 (둘 다 Python 3.12 지원)
  - WSL에 Chromium 실행에 필요한 시스템 라이브러리 일부가 없음: `libnss3`, `libnspr4`, `libasound2`
  - `sudo`는 비밀번호가 필요해 AI가 대신 설치할 수 없음
  - 디스크 여유 공간은 충분함 (Chromium 내려받기 약 수백 MB)

## 실행 단계
- [x] 1. 기능 설계 분석
- [x] 2. NFR 질문 작성 (아래 질문 1~2)
- [x] 3. 사용자 답변 수집 및 모호함 분석
- [x] 4. `nfr-requirements.md` 작성 - 보안 헤더 값, 제한 시간, 표시 기준, 테스트 환경, 성능 기준을 수치로 확정
- [x] 5. `tech-stack-decisions.md` 작성 - 화면 기술, 테스트 의존성과 버전, CI 구성
- [x] 6. 확장 규칙 준수 점검 (Security, Resiliency, PBT 부분 적용)
- [x] 7. 완료 메시지 제시 및 승인 요청

## 질문 평가 결과

| 범주 | 판단 |
|---|---|
| 확장성 | 질문 없음 - 1차와 같은 단일 사용자, 단일 프로세스 전제 |
| 성능 | 질문 없음 - 요구사항(첫 화면 요청 5회 이내, 동작당 2회 이내)과 기능 설계(4회, 1회)로 확정됨 |
| 가용성 | 질문 없음 - 1차의 결정(RTO/RPO, 백업/복원)을 그대로 따름. 새 데이터 저장소 없음 |
| 보안 | 질문 없음 - 키 처리 방식과 헤더 종류는 요구사항에서 확정됨. 헤더의 구체 값은 아래 "질문 없이 정하는 항목" |
| 기술 스택 | 질문 1, 2 - 브라우저 자동화 테스트의 실행 환경과 대상 브라우저 |
| 신뢰성 | 질문 없음 - 제한 시간 값은 서버 동작에서 도출됨 |
| 유지보수성 | 질문 1 - 로컬에서 브라우저 테스트를 돌릴 수 있는지가 유지보수에 영향 |
| 사용성 | 질문 없음 - 표시 기준은 요구사항에서 확정됨 |
| 복원력 확장의 사용자 결정 항목 | 질문 없음 - CI/CD, 롤백, 배포 방식, 장애 대응, 복원력 테스트 방식 모두 1차의 답을 그대로 적용 (요구사항 WNFR-RES-04에서 승인됨) |

질문 없이 정하는 항목과 근거:
- **API 호출 제한 시간 15초**: 서버가 DB 잠금 때 최대 약 10초(5초 대기 + 1회 재시도) 걸릴 수 있어 그보다 길어야 한다
- **실행 파일의 서버 응답 대기 20초**: 서버 기동은 보통 1~2초이고, 느린 디스크를 고려한 여유
- **콘텐츠 보안 정책**: 기본은 모두 차단하고 같은 출처의 스크립트, 스타일, API 호출만 허용. 인라인과 `eval` 불허, 프레임 삽입 금지
- **화면 파일 캐시**: 지금처럼 `no-store` 유지. 로컬이라 속도 차이가 없고, 화면을 고친 뒤 옛 파일이 보이는 문제를 피한다
- **글자 대비 기준**: 본문 4.5:1 이상 (WCAG AA)
- **JavaScript 수준**: 최신 Edge와 Chrome이 지원하는 표준 문법만 사용. 변환 도구 없음

---

# NFR 질문

각 질문의 `[Answer]:` 뒤에 선택지의 알파벳을 적어 주세요.

## Question 1
브라우저 자동화 테스트(Playwright)를 어디에서 실행할까요?
현재 WSL에는 Chromium 실행에 필요한 시스템 라이브러리 3개가 없고, 설치에는 `sudo` 비밀번호가 필요해 직접 실행해 주셔야 합니다.

A) 로컬과 CI 모두 - 아래 명령을 WSL 터미널에서 한 번 실행해 주시면, 이후 로컬에서도 브라우저 테스트를 돌려 결과를 확인합니다
   `sudo apt install -y libnss3 libnspr4 libasound2t64`
   (이 선택지를 고르면 Code Generation 전에 설치를 부탁드립니다)

B) CI에서만 - 시스템에 아무것도 설치하지 않음. 로컬에서는 브라우저를 띄울 수 없으면 브라우저 테스트를 자동으로 건너뛰고, GitHub Actions에서만 실행. 이 경우 화면 동작의 자동 검증 결과는 푸시한 뒤에야 확인할 수 있고, 그 전까지는 수동 확인에 의존함

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
브라우저 자동화 테스트는 어떤 브라우저로 돌릴까요? (Edge와 Chrome은 둘 다 Chromium 엔진을 씁니다.)

A) Playwright의 Chromium 하나 - Edge와 Chrome의 공통 엔진으로 검증 (설치와 실행이 가장 가볍고, 엔진이 같아 동작 차이가 거의 없음)

B) 실제 Chrome과 실제 Edge 두 가지 - CI에 두 브라우저를 설치해 각각 실행 (실제 제품으로 검증하지만 설치 용량과 실행 시간이 약 두 배. WSL 로컬에는 두 브라우저의 Linux 버전을 따로 설치해야 함)

C) Other (please describe after [Answer]: tag below)

[Answer]: A
