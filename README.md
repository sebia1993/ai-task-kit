# AI Task Kit — Exam Edition

**개발을 잘 모르는 응시자와, 허용된 과제 환경의 Codex를 위한 작은 작업 지침 + 로컬 검사 도구.**

별도 AI 모델, 정답 모음, GUI, 자동 제출 프로그램이 아닙니다. Superpowers 전체를 설치하지 않고 계획·원인 조사·완료 전 검증 원칙을 독자적으로 재구성했습니다. 외부 Python 패키지 없이 Python 3.10 이상에서 실행합니다.

> 시험 규정과 실제 문제 지침이 항상 우선합니다. 공개 저장소라고 모든 사용이 허용되는 것은 아닙니다. 후속 서술형 등 AI 금지 단계에는 사용하지 않습니다. **Cofa 실환경 호환성과 Codex 성능 개선은 아직 검증하지 않았습니다.**

## 가장 쉬운 사용법

### 1. 공개 도구 사용이 허용된 터미널에서 가져오기

아래 명령은 **일반 터미널**에서 입력합니다. 현재 폴더에 `ai-task-kit` 폴더가 없어야 합니다. 기존 폴더를 지우지 마세요. 실제 시험에서는 사전에 검증한 커밋을 고정해서 사용하는 것이 좋습니다.

```bash
git clone --depth 1 https://github.com/sebia1993/ai-task-kit.git ai-task-kit
```

clone이 막히면 우회하지 않습니다. 도구 설치가 3분 이상 걸리면 기본 Codex로 진행합니다. 과제 파일을 이 저장소로 옮기거나 시험 중 Git Push하지 않습니다.

### 2. 플랫폼에서 제공하는 Codex에 한국어로 요청

아래는 **Codex 대화 입력란에 넣는 문장**이지 터미널 명령어가 아닙니다. 경로가 다르면 실제 위치를 알려주세요.

```text
ai-task-kit/BOOTSTRAP.md를 읽고 이번 과제에 적용해줘.
도구 폴더와 실제 과제 폴더를 구분하고, 과제 README와 필수 제출물을 먼저 확인해줘.
기술 작업은 직접 진행하되, 업무 결과를 바꾸는 중요한 결정만 쉬운 한국어로 설명해줘.
실제로 검증하지 않은 것은 완료로 보고하지 마. 최종 제출은 내가 할게.
```

Skill 자동 인식은 필수가 아닙니다. 파일을 직접 읽는 대체 경로가 있습니다. 플랫폼이 파일 읽기 자체를 금지하면 그 경로도 사용하지 않습니다. 맥북을 쓰더라도 원격 과제 환경이 macOS라고 가정하지 않습니다.

### 3. 사용자는 이 네 가지를 확인

“무엇을 만들었는지”, “실제로 어떤 검사를 했는지”, “어떤 결과가 아직 미검증인지”, “내가 결정해야 할 업무 조건은 무엇인지”를 확인합니다. Python·SQL 문법을 외울 필요는 없습니다. 터미널 명령 승인과 최종 제출은 직접 수행합니다.

## 포함 기능

| 구성 | 역할 |
|---|---|
| 핵심 Skill | 요구 분석, 작은 작업으로 구현, 실패 원인 조사, 실제 검증 |
| 한국어 판단 안내 | 상황·영향·권장 조치·필요한 한 가지 질문 |
| doctor / inspect | 환경과 파일 목록 확인, 과제 유형 후보 |
| audit | CSV/JSON 결측·중복·열·합계·고유값·날짜 검사 |
| verify | 필수 파일·비어 있음·Python 문법·자료 형식 확인 |
| explain | 오류를 확정하지 않고 한국어 조사 방향 제공 |
| session | 공식 시간을 보조하는 로컬 시간 추정과 재시도 기록 |
| worklog | 업무 질문·답변 반영, 중요한 판단과 검증 주장 기록, 파일 변경 감지 |
| preflight | 필수 파일·검토 후보·작업 기록 종합 점검 |
| Cofa 웹 참고 | 기존 서버의 포트·바인딩·미리보기 점검 안내 |

도구는 코드를 대신 생성하거나 테스트를 대신 실행하지 않습니다. 생성·실행·수정은 **플랫폼의 Codex**가 담당합니다. 검증 명령의 `PASS`는 해당 검사 범위에 한정됩니다. `verify`는 파일 형식이 모두 맞아도 기능 동작을 증명하지 못하므로 `UNVERIFIED`를 반환합니다. `worklog`의 PASS 역시 실제 명령을 실행해 확인한 결과가 아닌 **사용자가 입력한 검증 기록**입니다. `preflight`가 정상이어도 실제 제출 상태는 `UNVERIFIED`입니다.

## 개발자용 명령

`--root`는 실제 과제 폴더이며 검사 파일은 그 안의 상대 경로입니다.

```bash
python3 kit.py doctor --root /실제/과제/폴더
python3 kit.py inspect --root /실제/과제/폴더 --json
python3 kit.py audit --root /실제/과제/폴더 --file data/input.csv
python3 kit.py verify --root /실제/과제/폴더 --require main.py --require report.md
python3 kit.py worklog status --root /실제/과제/폴더 --json
python3 kit.py preflight --root /실제/과제/폴더 --require main.py --require report.md
python3 -m unittest discover -s tests -v
```

정확한 옵션과 검사 한도는 [도구 설명](.agents/skills/ai-task-kit/references/TOOLS.md)을 참고합니다. 코드 실행 실패를 숨기기 위해 입력·공식 테스트를 바꾸지 않습니다. 지원하지 않는 자료를 억지로 읽지 않습니다.

기록 기능을 쓸 때는 [요구사항·업무 질문·검증 기록 안내](.agents/skills/ai-task-kit/references/WORKFLOW.md)를, 웹 서비스 과제에서는 [Cofa 웹 실행 안내](.agents/skills/ai-task-kit/references/COFA_WEB.md)를 읽으세요. 둘 다 **필요한 상황에서만 사용하는 선택 기능**입니다. 과제 원문·비공개 파일·결과를 공개 GitHub에 올리지 않습니다. 로컬 `.ai-task-kit` 상태 폴더는 제출 산출물과 구분합니다.

## 문서와 검증 상태

- [설계 확정안](docs/SPEC.md) / [구현 계획서](docs/IMPLEMENTATION_PLAN.md)
- [코덱스 개발 작업지시서](docs/CODEX_WORK_ORDER.md)
- [검증 결과와 실사용 전 확인사항](docs/VALIDATION.md)
- [모델·플랫폼 비교 시나리오](evals/SCENARIOS.md)

검사 프로그램의 자동 테스트와 실제 AI의 작업 성능은 다릅니다. 모델 A/B 실험·Cofa 사전 체험이 끝나기 전에는 합격률 개선이나 현장 작동을 주장하지 않습니다. 사전 체험 설정이 본시험에 유지되는지도 별도로 확인해야 합니다.

## 출처·라이선스

MIT. 이 저장소의 문서·코드는 독자 작성했습니다. 방법론 참고: [obra/superpowers](https://github.com/obra/superpowers). Skill 구조 참고: [OpenAI Skill 문서](https://developers.openai.com/codex/skills/). 자세한 구분은 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)에 있습니다. 특정 대회·플랫폼·OpenAI가 공식 승인한 프로젝트가 아닙니다.
