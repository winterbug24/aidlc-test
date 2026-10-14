# 요구사항 확인 질문: 등록 일자와 완료 일자 표시 (4차 워크플로)

각 질문의 `[Answer]:` 뒤에 고른 글자를 적어 주세요. 맞는 선택지가 없으면 마지막 "기타"를 고르고 내용을 적어 주세요.
"(권장)"은 AI의 제안이며 그대로 따르지 않아도 됩니다.

## 알아 두실 점

- **등록 일자**는 이미 저장되어 있습니다. DB의 `created_at` 열에 UTC 시각으로 들어 있고, API 응답에도 포함됩니다.
- **완료 일자**는 지금 어디에도 저장되지 않습니다. 완료 여부(`completed`, 0 또는 1)만 저장합니다.
  그래서 완료 일자를 보이려면 DB에 완료 시각 열(`completed_at`)을 추가해야 합니다. 이미 쓰고 있는 DB 파일(`instance/todo.db`)에도 서버가 시작될 때 이 열을 자동으로 추가하도록 만들어야 합니다.
- 이 변경 전에 이미 완료한 할 일은 언제 완료했는지 기록이 없습니다.

## Question 1
변경 전에 이미 완료 상태였던 할 일의 완료 일자는 어떻게 표시할까요?

A) 완료 일자를 비워 두고 "완료 -"처럼 알 수 없음으로 표시한다 (권장: 사실이 아닌 날짜를 만들지 않음)

B) 서버가 열을 추가하는 시점의 날짜를 완료 일자로 채운다

C) 등록 일자와 같은 날짜로 채운다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
완료 체크를 해제하면 완료 일자는 어떻게 될까요?

A) 완료 일자를 지운다. 다시 체크하면 그때 날짜로 새로 기록한다 (권장)

B) 마지막 완료 일자를 남겨 두고 해제 상태에서는 흐리게 보여 준다. 다시 체크하면 그때 날짜로 바꾼다

C) 처음 완료한 날짜를 계속 유지한다 (해제 후 다시 체크해도 바뀌지 않음)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
날짜는 어느 시간대를 기준으로 표시할까요? (저장은 지금처럼 UTC로 합니다)

A) 브라우저(Windows)의 시간대. 한국이면 한국 시간 기준 (권장: 밤 9시 이후에 등록한 할 일이 다음 날로 보이는 문제를 막음)

B) UTC 그대로

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
아직 완료하지 않은 할 일에는 완료 일자 자리를 어떻게 보일까요?

A) 등록 일자만 보이고 완료 일자 자리는 비운다

B) "완료 -"처럼 자리를 표시해 줄 맞춤을 유지한다 (권장: 목록에서 날짜 열이 가지런히 보임)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
날짜를 어디에, 어떤 모양으로 배치할까요? (`[ ]`는 체크 상자)

A) 체크 상자와 제목 사이에 한 줄로: `[ ] 등록 2026/10/14 · 완료 2026/10/16  장보기   [삭제]`

B) 체크 상자 옆 제목 아래 작은 글씨로 둘째 줄에: 첫 줄 `[ ] 장보기  [삭제]`, 둘째 줄 `등록 2026/10/14 · 완료 2026/10/16` (권장: 제목이 길어도 날짜가 밀리지 않고 화면이 좁아도 읽기 쉬움)

C) 행 오른쪽, 삭제 버튼 앞에: `[ ] 장보기   등록 2026/10/14 · 완료 2026/10/16  [삭제]`

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
API 응답(`GET /todos` 등)에 완료 시각 `completed_at`을 추가해도 될까요?

A) 추가한다. 미완료면 `null`. 기존 필드는 그대로 두므로 curl 등 기존 사용 방식은 깨지지 않는다 (권장: 화면이 API에서 받은 값으로 표시하므로 필요함)

B) 추가하지 않는다 (이 경우 화면에 완료 일자를 보일 방법이 없으므로 요청 범위를 줄여야 함)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
확장 규칙 설정을 이전 워크플로와 같이 유지할까요?
(현재: Security Baseline 적용, Resiliency Baseline 적용, Property-Based Testing 부분 적용(PBT-02, 03, 07, 08, 09만 강제))

A) 그대로 유지한다 (권장: 같은 프로젝트의 기존 기준과 일관됨)

B) 이번 워크플로에서 바꾼다 (아래 기타 칸에 바꿀 내용을 적어 주세요)

X) Other (please describe after [Answer]: tag below)

[Answer]: A
