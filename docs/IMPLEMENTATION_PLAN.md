# AI Task Kit Implementation Plan

> 실행 방식: 승인된 대화 설계를 현재 세션에서 순차 구현한다. 별도 실행 에이전트가 없으므로 작성자가 구현·자가 리뷰한다.

**Goal:** 짧은 과제 수행을 지원하는 한국어 Skill과 안전한 로컬 검사 도구를 제공한다.
**Architecture:** 단일 Skill 패키지에 독립 Python CLI를 넣고 루트 래퍼가 이를 실행한다.
**Tech Stack:** Python 3.10+ 표준 라이브러리, Markdown, unittest.
**Spec:** `docs/SPEC.md`

## Global Constraints
외부 의존성/네트워크/임의 명령 실행 없음. 원본 보호. 시험 지침 우선. 서술형 답변 생성 제외. 파일 8 MiB/표 100,000행. 무제한 재시도와 자동 설치 금지.

## Review Focus
- 경로 이탈·심볼릭 링크·특수 파일을 읽거나 수정하지 않는가?
- 미검증·부분 검사와 성공을 혼동하지 않는가?
- 결측/중복/비유한 수치를 조용히 정상값으로 바꾸지 않는가?
- 자체 타이머와 사용자 시간 입력을 제거했는가? 오류 재시도 기록이 독립적으로 작동하며 기존 `session.json`을 보존하는가?
- Skill 복사본·루트 실행·한글/공백 경로에서 동일하게 작동하는가?

## Task 1: 검사 CLI
**Files:** `kit.py`, `.agents/skills/ai-task-kit/scripts/taskkit.py`, `tests/test_kit.py`
**Interface:** `python3 kit.py <doctor|inspect|audit|verify|explain|retry|worklog|preflight> ... [--json]`; 결과 status/scope/summary/details, 종료 코드 0/1/2.
- [ ] 경로/입력/상태 구분 회귀 테스트를 먼저 작성하고 실패 확인.
- [ ] 읽기 전용 검사, 수치 검산, 안전한 세션 상태 저장 구현.
- [ ] 전체 unittest 및 CLI 스모크 테스트 통과 확인.

## Task 2: Skill·사용자 안내
**Files:** `BOOTSTRAP.md`, `.agents/skills/ai-task-kit/SKILL.md`, 해당 `references/`, `README.md`
**Interface:** 과제 루트와 도구 루트를 구별하고 초기 지침을 직접 읽어서도 사용 가능.
- [ ] 문서 계약 검사를 먼저 작성해 실패 확인.
- [ ] 작업 권한/위험 판단/짧은 보고/시간 상한/실제 검증 절차 명시.
- [ ] 상대 링크·정적 계약·독립 Skill 실행 확인.

## Task 3: 개발 인계·배포
**Files:** `docs/CODEX_WORK_ORDER.md`, `docs/VALIDATION.md`, `evals/SCENARIOS.md`, `LICENSE`, `THIRD_PARTY_NOTICES.md`
- [ ] 기능 결과와 모델 성능 평가를 분리한 검증표 작성.
- [ ] 작성자 자가 리뷰, 중요 결함 회귀 테스트 추가.
- [ ] ZIP 및 SHA256 manifest 생성, 압축 해제 복사본 전체 테스트.
- [ ] 비어 있는 사용자 저장소에 초기 구현 반영 후 파일 해시 재확인.

## Task 4: 공식 매뉴얼 기반 보강 (2026-10-29)

**범위:** 요구사항·업무 질문·답변 반영 상태, 판단·검증 기록, 로컬 제출 점검, Cofa 웹 실행 안내.
- [x] 기존 검사 기능을 활용한 선택형 로컬 기록·해시 비교.
- [x] 요구사항·질문·답변·결정·검증 기록 및 상태 출력.
- [x] 필수 제출 파일과 도구 파일·임시 파일 검토 후보 확인.
- [x] Cofa Browser 실행/오류 대응 참고 문서 및 한국어 오류 힌트.
- [x] 합성 데이터 기반 자동 테스트·CI 구성.
- [ ] 실제 Cofa 접속 및 AI 모델 과제 성능 확인 (별도 환경 필요).

## Task 5: 공식 타이머와 중복되는 시간 기능 제거 (2026-10-29)
**범위:** `session start/status`, 로컬 남은 분 계산·제출 여유 분 계산 제거. 오류 재시도 명령을 `retry attempt/status`로 독립.
- [x] 오류 재시도 로컬 기록 구조 `.ai-task-kit/retries.json`에 분리.
- [x] 자체 타이머 시작·남은 시간 입력 경로 제거.
- [x] 기존 `session.json`을 그대로 보존하고 자동 이관하지 않음.
- [x] 관련 회귀 테스트·사용 설명·Skill 지침 변경.
- [ ] 새 버전 자동 테스트와 플랫폼 실제 사용 검증은 별도 검증 기록 확인.

## Task 6: 180분 제약 대응 Lite Mode·필수 구현 우선 (2026-10-29)

**범위:** 문서 선택·Codex 행동 원칙만 변경하며 Python 검사 CLI API는 유지.
- [x] 12가지 상세 지침을 `docs/prompts/P01.md`~`P12.md`로 분리하고 색인을 간결화.
- [x] `BOOTSTRAP.md`에서 실제 과제 README·최소 지침으로 시작해 필요한 상세 파일만 읽도록 안내.
- [x] 필수 요구사항/확인 필요 조건/선택 기능 분류와 최초 실행 경로 우선 구현.
- [x] 빠른 관련 테스트와 주요 단계·제출 전 종합 검증을 분리. `UNVERIFIED`를 동일 검사 재시도 이유로 오해하지 않도록 안내.
- [x] 같은 문제 반복 시 전략 전환, 선택적 `worklog/retry/audit`, 짧은 두 줄 보고 유지.
- [ ] 실제 Codex 수행 시간·Cofa 플랫폼 효과는 별도 검증 필요. 정적 테스트 통과로 성능 향상을 주장하지 않음.

## 승인과 한계
사용자의 최신 요청은 이 설계의 구현 승인이다. 별도 PR/릴리스나 제3자 저장소 변경은 하지 않는다. 신규 빈 저장소 초기 버전만 반영한다. 실제 Cofa 접근과 모델 A/B 평가는 제공되지 않아 완료를 주장하지 않는다.
