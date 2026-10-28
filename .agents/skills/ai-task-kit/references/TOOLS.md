# 검사 도구 사용법

Python 3.10+ 표준 라이브러리만 사용한다. 아래 `<TASK>`는 실제 과제 폴더다. 모든 입력 파일 경로는 그 폴더 기준 상대 경로이며 링크·상위 경로를 거부한다. `<SCRIPT>`는 이 Skill의 `scripts/taskkit.py` 절대 경로다. 저장소 전체를 가져왔다면 `kit.py`도 같은 도구다.

```bash
python3 "<SCRIPT>" doctor --root "<TASK>"
python3 "<SCRIPT>" inspect --root "<TASK>"
python3 "<SCRIPT>" audit --root "<TASK>" --file data/orders.csv
python3 "<SCRIPT>" audit --root "<TASK>" --file data/orders.csv --column amount --expect-sum 123.45 --unique id
python3 "<SCRIPT>" audit --root "<TASK>" --file data/orders.csv --require-column date --date-column date
python3 "<SCRIPT>" verify --root "<TASK>" --require main.py --require report.md
python3 "<SCRIPT>" explain --root "<TASK>" --file local-error.log
python3 "<SCRIPT>" session start --root "<TASK>" --minutes 180 --reserve 15
python3 "<SCRIPT>" session status --root "<TASK>"
python3 "<SCRIPT>" session attempt --root "<TASK>" --issue input-schema
python3 "<SCRIPT>" worklog status --root "<TASK>"
python3 "<SCRIPT>" preflight --root "<TASK>" --require main.py --require report.md
```

각 명령 끝에 `--json`을 붙이면 구조화된 결과가 나온다. 예시 파일명과 합계는 예시일 뿐이다. 실제 과제 지침에서 경로·기대값을 가져와야 한다. `--minutes`는 도구 시작 시점의 공식 남은 분으로 지정하며 180분을 무조건 복사하지 않는다.

| 명령 | 의미 | 하지 않는 일 |
|---|---|---|
| doctor | Python·명령·선택 패키지 존재 | 설치, Codex 로그인, Cofa 호환 판정 |
| inspect | 파일 목록과 확장자 기반 유형 후보 | 의미 기반 요구사항 확정, 원문 자동 지시 실행 |
| audit | CSV/JSON 구조·결측·중복·명시한 조건 | 자동 결측 제거, 0 채움, 인코딩 추측, DB 접속 |
| verify | 존재·내용·Python 문법·JSON/CSV 구조 | 앱 실행, 테스트 실행, 정답/점수 판정, 자동 제출 |
| explain | 오류 유형별 한국어 조사 힌트 | 원인 확정, 로그 원문 재출력, 자동 패키지 설치 |
| session | 로컬 시간 추정·같은 오류 재시도 횟수 | 공식 타이머 읽기, 백그라운드 알림, 실행 강제 중단 |
| worklog | 요구사항·업무 질문·답변·판단·검증 주장 기록 | 담당자 메시지 자동 전송, 검증 명령 실행 |
| preflight | 필수 파일·검토 후보·작업 기록 종합 점검 | 에디터 저장 상태 판정, 자동 제출 |

## 결과를 정확하게 해석하기
- `PASS`(종료 0): **scope에 표시된 검사만** 통과했다.
- `FAIL`(종료 1): 지정한 검사에서 실패를 확인했다.
- `UNVERIFIED`(종료 2): 검사 한도·빈 자료·미검증 등이 있다. `verify`는 모든 파일 형식이 맞아도 기능을 실행하지 않으므로 이 상태를 반환한다. 이를 크래시로 오해하거나 0으로 덮어쓰지 않는다.

## 추가 기능
- [요구사항·질문·판단·검증 기록 사용법](WORKFLOW.md)에서는 `worklog requirement` → `ask/answer/apply` → `decision` → `evidence` → `status` 순서로 기록한다. 모두 선택 기능이다.
- [Cofa 웹 실행 참고](COFA_WEB.md)는 웹 프로젝트에서만 사용한다. 기존 서버 실행 방법·포트·경로를 확인한다.
- `preflight --require`에는 과제에서 실제 요구한 파일을 입력한다. 검토 후보는 자동 삭제 대상이 아니다.
- `PASS_RECORDED_ONLY`는 **사람이 PASS라고 입력한 기록**일 뿐 도구가 실행한 검증이 아니다. `preflight`는 파일 검사에 성공해도 `UNVERIFIED`로 남는다.

## 자료 규칙
기본 UTF-8(BOM 허용). 다른 형식이 확인됐을 때만 `--encoding cp949` 또는 `--encoding utf-16`을 사용한다. CSV 기본 구분자는 쉼표이며 `--delimiter ';'` 등으로 명시한다. `verify`의 CSV 검사는 기본 UTF-8/쉼표로 한정되므로 다른 형식은 `audit`의 명시 옵션으로 검사하고 제한을 기록한다.

합계는 `--column`, 기대값 비교는 `--expect-sum`이다. 쉼표/통화 단위/비유한 숫자를 추측해서 바꾸지 않는다. 누락값이 있으면 실패하며 업무상 제외가 허용될 때만 `--allow-missing`을 선택한다. 제외 건수는 출력에 남는다. 날짜 검사는 `YYYY-MM-DD` 날짜만 지원한다. 시간대·시각 검사는 별도로 수행한다.

파일 8 MiB, 표 100,000행·1,024열·행×열 2,000,000, 파일 목록 500개/탐색 항목 2,000개/깊이 12 제한이 있다. 한도를 넘으면 전체 검사가 완료됐다고 하지 않는다. 대규모 자료는 Codex가 별도 스트리밍 구현을 만들되 샘플 결과를 전체 결과로 포장하지 않는다.

## 안전 범위
읽기 명령은 입력 파일을 수정하지 않는다. `session start/attempt`는 `.ai-task-kit/session.json`, 명시적인 `worklog` 기록 명령만 `.ai-task-kit/worklog.json`을 저장한다. `preflight`와 `worklog status`는 파일을 수정하지 않는다. 동시 다중 기록은 지원하지 않으며 한 에이전트가 사용한다. 원본과 다른 프로세스가 동시에 경로를 바꾸는 적대적 상황을 막는 OS 샌드박스가 아니다. 도구 자체에 네트워크·프로세스 실행 코드는 없지만 Codex와 다른 도구의 통신까지 차단하지는 않는다.
