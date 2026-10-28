# 요구사항·업무 질문·검증 기록 (선택 기능)

이 문서는 **허용된 과제 수행 단계**의 로컬 기록 사용법이다. 공식 문제와 과제 README가 항상 우선한다. 필요한 경우에만 사용하고 기록 작업에 시간을 과도하게 쓰지 않는다. AI 사용 금지 단계에서는 사용하지 않는다.

- 모든 상태는 `<TASK>/.ai-task-kit/worklog.json`에만 저장한다. 외부 전송·Git Push·테스트 명령 실행·자동 제출을 하지 않는다.
- 사용자가 실제로 확인한 답변과 실행 결과만 기록한다. `PASS`는 **사용자가 입력한 검증 결과 기록**이지 도구가 명령을 실행해서 확인한 PASS가 아니다.
- `<SCRIPT>`는 `.agents/skills/ai-task-kit/scripts/taskkit.py`의 실제 경로로 바꾼다. `<TASK>`는 실제 과제 폴더다. 아래 파일명과 업무 조건은 설명용 가상 예시다.

## 1. 먼저 요구사항과 연결될 파일 지정

`@bash
python3 "<SCRIPT>" worklog requirement --root "<TASK>" --id r-sales --text "판매 합계 계산" --file output.csv
`@

산출물 파일이 아직 없어도 요구사항을 추가할 수 있다. 이후 `evidence`는 해당 요구사항에 등록한 파일만 기록할 수 있다. 요구사항에 파일이 없으면 완료 증거를 자동 판정하지 않는다.

## 2. 모호한 업무 조건을 질문하고 받은 답변 기록

`@bash
python3 "<SCRIPT>" worklog ask --root "<TASK>" --id q-cancel --requirement r-sales --text "취소 주문은 합계에서 제외하나요?"
python3 "<SCRIPT>" worklog answer --root "<TASK>" --id q-cancel --text "취소 주문 제외" --source "업무 담당자에게 직접 확인"
`@

`ask`는 질문을 **기록만** 한다. 업무 메신저를 자동으로 조작하거나 질문을 전송하지 않는다. 실제 답변을 받은 뒤 `answer`를 입력한다. 답변을 코드에 반영한 뒤 실제 파일을 지정해 기록한다.

`@bash
python3 "<SCRIPT>" worklog apply --root "<TASK>" --id q-cancel --file output.csv
`@

`apply`는 그 순간 파일의 SHA-256 값을 기록한다. 이후 파일이 바뀌면 반영 확인을 다시 해야 한다. 적용했음을 **입력한 사실**과 실제 요구조건을 올바르게 구현했는지는 다르다.

## 3. 중요한 판단과 실제 검증 기록

`@bash
python3 "<SCRIPT>" worklog decision --root "<TASK>" --id d-cancel --requirement r-sales --text "취소 주문은 별도 집계" --reason "담당자가 합계 제외를 요청" --source "업무 담당자 답변 q-cancel"
python3 "<SCRIPT>" worklog evidence --root "<TASK>" --id e-sales --requirement r-sales --file output.csv --command "python3 check_result.py" --outcome PASS --note "실제로 실행한 출력과 예시 데이터의 합계가 일치함"
`@

검사는 **먼저** 플랫폼에서 실제로 실행한 뒤 그 사실만 입력한다. `--command`는 명령 문구를 기록할 뿐 실행하지 않는다. 명령 실패라면 `--outcome FAIL`로 기록한다. 이후 PASS가 기록되어도 파일을 바꾸면 증거는 오래된 것으로 처리한다.

## 4. 현재 기록과 제출 전 로컬 점검

`@bash
python3 "<SCRIPT>" worklog status --root "<TASK>" --json
python3 "<SCRIPT>" preflight --root "<TASK>" --require output.csv --require report.md --json
`@

`status`에서는 `UNANSWERED`(미답변), `ANSWERED_NOT_APPLIED`(반영 확인 전), `APPLIED_FILE_CHANGED`(반영 파일 변경), `EVIDENCE_STALE`(검증 파일 변경), `PASS_RECORDED_ONLY`(사용자 PASS 기록·실행 재검증 아님) 등을 구분한다.

`preflight`는 필수 파일 존재·자료 형식, 최근 증거, 검토 후보 파일을 모아 **확인용 목록**을 만든다. `UNVERIFIED`는 정상 설계다. 실제 앱 동작·에디터의 저장됨 표시·숨김 파일이 포함된 실제 제출 대상·플랫폼 제출 완료를 판정하지 않는다. 사용자가 화면에서 최종 확인한다.

## 데이터·보안 제약

파일 읽기는 각 8 MiB 한도, 기록 파일은 128 KiB 한도다. 외부 파이썬 패키지나 별도 네트워크가 필요하지 않다. 시크릿·신분증·비공개 시험 원문 등 민감한 내용을 기록하지 않는다. 한 번 등록한 ID는 조용히 덮어쓰지 않으며, 기록을 지우지 않고 수정할 때는 새 ID로 정정 내역을 남긴다. 동시에 여러 프로세스가 기록하면 충돌할 수 있으므로 한 작업자가 사용한다. 기록 폴더를 제출에 포함할지 여부를 도구가 결정하지 않는다.
