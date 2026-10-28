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
- 세션 재시작으로 시간이 초기화되거나 타이머가 연장되지 않는가?
- Skill 복사본·루트 실행·한글/공백 경로에서 동일하게 작동하는가?

## Task 1: 검사 CLI
**Files:** `kit.py`, `.agents/skills/ai-task-kit/scripts/taskkit.py`, `tests/test_kit.py`
**Interface:** `python3 kit.py <doctor|inspect|audit|verify|explain|session> ... [--json]`; 결과 status/scope/summary/details, 종료 코드 0/1/2.
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

## 승인과 한계
사용자의 최신 요청은 이 설계의 구현 승인이다. 별도 PR/릴리스나 제3자 저장소 변경은 하지 않는다. 신규 빈 저장소 초기 버전만 반영한다. 실제 Cofa 접근과 모델 A/B 평가는 제공되지 않아 완료를 주장하지 않는다.
