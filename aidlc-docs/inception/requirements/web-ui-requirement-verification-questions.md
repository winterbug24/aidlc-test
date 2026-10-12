# 요구사항 확인 질문 - 웹 화면 추가 (2차 워크플로)

To-Do API를 사용하는 웹 화면의 요구사항을 정하기 위한 질문입니다.
각 질문의 `[Answer]:` 뒤에 선택지의 알파벳을 적어 주세요.
맞는 선택지가 없으면 마지막 선택지(Other)를 고르고 내용을 직접 적어 주세요.

참고: 1차 워크플로의 질문 파일(`requirement-verification-questions.md`)은 그대로 보존하고, 이번 워크플로의 문서는 `web-ui-` 접두어를 붙여 구분합니다.

---

## 인증과 구조

## Question 1
화면에서 API 키를 어떻게 다룰까요? (API는 `X-API-Key` 헤더가 있어야 동작합니다. 가장 중요한 결정입니다.)

A) 화면에 처음 들어올 때 키를 입력받고, 브라우저 탭이 열려 있는 동안만 기억 (탭이나 브라우저를 닫으면 다시 입력. 키가 디스크에 남지 않음)

B) 한 번 입력하면 브라우저에 계속 저장 (다음부터 입력 불필요. 편하지만 키가 브라우저 저장소에 평문으로 남음. 화면에서 "키 지우기" 제공)

C) 서버 로그인 방식 - 키를 한 번 입력하면 서버가 로그인 쿠키를 발급 (스크립트가 키를 다루지 않아 가장 안전하지만, API에 쿠키 인증과 요청 위조 방지를 추가해야 해서 변경 범위가 큼)

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 2
화면은 어떤 기술로 만들까요?

A) 빌드 도구 없는 순수 HTML, CSS, JavaScript - 기존 Flask 서버가 파일을 그대로 제공 (Node.js 불필요, 의존성 추가 없음, 가장 단순)

B) 서버가 HTML을 만들어 주는 방식(Flask 템플릿) + 소량의 JavaScript (동작마다 페이지를 다시 불러오는 전통적인 방식)

C) React, Vue 같은 프레임워크 + 빌드 도구 (Node.js 설치와 빌드 단계 필요. 이 규모에는 과할 수 있음)

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
화면 주소는 어디로 할까요?

A) `http://127.0.0.1:8000/` (서버 주소만 열면 바로 화면)

B) `http://127.0.0.1:8000/app` (루트는 비워 둠)

C) Other (please describe after [Answer]: tag below)

[Answer]: B : http://127.0.0.1:8000/api_test  로 하고, port는 상황 다른데서 사용하고 있으면, 변경해줘

## 기능

## Question 4
화면에서 어떤 기능을 제공할까요?

A) API의 모든 기능 + 필터: 추가, 목록 보기, 완료 체크/해제, 삭제, 그리고 전체/미완료/완료 필터

B) 필터 없이 기본 기능만: 추가, 목록 보기, 완료 체크/해제, 삭제

C) 위 A에 더해 남은 할 일 개수 표시 (예: "미완료 3개")

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
삭제 버튼을 누르면 어떻게 동작할까요? (삭제한 할 일은 복구할 수 없습니다.)

A) 확인을 한 번 거친 뒤 삭제

B) 확인 없이 즉시 삭제

C) 즉시 삭제하되 몇 초 동안 "실행 취소"를 보여 주고, 그동안은 실제 삭제 요청을 보내지 않음

D) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
목록은 언제 새로 불러올까요? (API에는 분당 60회 요청 제한이 있습니다.)

A) 화면을 열 때와 내가 추가/변경/삭제를 한 직후에만. 필요하면 "새로고침" 버튼으로 수동 갱신

B) 위 A에 더해 주기적으로 자동 갱신 (예: 30초마다. 다른 도구로 바꾼 내용이 자동 반영됨)

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## 디자인과 환경

## Question 7
색상 테마는 어떻게 할까요?

A) 밝은 테마 하나만

B) Windows 설정(밝게/어둡게)을 따라 자동 전환

C) 위 B에 더해 화면에서 직접 바꾸는 버튼 제공

D) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 8
"윈도우 환경에서 잘 표현"의 범위를 확인합니다. 어떤 환경을 기준으로 할까요?

A) Windows의 Edge와 Chrome 최신 버전, 데스크톱 창 기준. Windows 기본 글꼴(맑은 고딕, Segoe UI) 사용, 창을 좁혀도 깨지지 않게 구성

B) 위 A에 더해 휴대폰 폭의 화면까지 대응 (단, 서버가 127.0.0.1에만 열려 있어 다른 기기에서는 접속할 수 없음)

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9
Windows에서 쉽게 시작할 수 있는 실행 파일이 필요할까요? (서버는 WSL에서 실행됩니다.)

A) 필요 - 더블클릭하면 WSL에서 서버를 시작하고 브라우저로 화면을 여는 배치 파일(`.bat`) 제공

B) 필요 없음 - 지금처럼 WSL 터미널에서 서버를 실행하고 브라우저에 주소를 직접 입력

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
화면의 문구는 어떤 언어로 할까요?

A) 한국어

B) 영어

C) Other (please describe after [Answer]: tag below)

[Answer]: A

## 품질

## Question 11
화면에 대한 테스트는 어느 범위까지 할까요?

A) 서버 쪽 자동 테스트(화면 파일 제공, 보안 헤더, 기존 API 회귀) + 화면 동작은 수동 확인 체크리스트 제공 (추가 의존성 없음)

B) 위 A에 더해 실제 브라우저를 띄우는 자동화 테스트(Playwright) 추가 (화면 동작까지 자동 검증. 브라우저 설치가 필요하고 의존성과 CI 시간이 늘어남)

C) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 12: 확장 설정
1차 워크플로에서 정한 확장 설정(보안: 적용, 복원력: 적용, 속성 기반 테스트: 부분 적용)을 이번에도 그대로 유지할까요?
보안 확장을 유지하면 화면에 엄격한 콘텐츠 보안 정책(CSP)이 적용되어 인라인 스크립트와 외부 CDN을 쓰지 않는 방식으로 만들게 됩니다.

A) 그대로 유지

B) 변경 - `[Answer]:` 뒤에 바꿀 내용을 적어 주세요 (예: 복원력 확장 해제)

X) Other (please describe after [Answer]: tag below)

[Answer]: A
