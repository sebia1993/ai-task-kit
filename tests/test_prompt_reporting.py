"""Static guardrails for situational prompt selection and honest reporting.

These tests validate documentation only, NOT actual Codex behavior,
platform permissions, genuine reads, or independent execution evidence.
"""
from pathlib import Path
import re
import unittest

REPO = Path(__file__).resolve().parents[1]
BOOTSTRAP = REPO / "BOOTSTRAP.md"
SKILL = REPO / ".agents/skills/ai-task-kit/SKILL.md"
PLAYBOOK = REPO / "docs/EXAM_PROMPT_PLAYBOOK.md"
README = REPO / "README.md"
EVALS = REPO / "evals/SCENARIOS.md"


class PromptReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.playbook = PLAYBOOK.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")
        cls.evals = EVALS.read_text(encoding="utf-8")

    def test_all_prompt_ids_exist_once_in_order(self):
        ids = re.findall(r"^### (P\d{2})\.", self.playbook, flags=re.M)
        self.assertEqual(ids, [f"P{i:02}" for i in range(1, 13)])

    def test_bootstrap_requires_actual_playbook_read(self):
        self.assertIn(".agents/skills/ai-task-kit/SKILL.md", self.bootstrap)
        self.assertIn("docs/EXAM_PROMPT_PLAYBOOK.md", self.bootstrap)
        self.assertIn("실제로 열어 읽는다", self.bootstrap)

    def test_user_does_not_have_to_supply_prompt_ids(self):
        self.assertIn("매번 번호를 지시하게 하지 않는다", self.skill)
        self.assertIn("P번호를 기억", self.playbook)
        self.assertIn("P01~P12 지침을 스스로 선택", self.readme)

    def test_selection_by_real_situation_only(self):
        self.assertIn("복합 작업에서 최대 3개", self.skill)
        self.assertIn("상황이 바뀌면", self.playbook)
        self.assertIn("읽기만 해 놓고 수행하지 않은 지침", self.skill)

    def test_two_line_reporting_contract(self):
        for document in (self.skill, self.playbook):
            self.assertIn("적용 지침:", document)
            self.assertIn("플레이북:", document)
            self.assertIn("수행 근거:", document)
            self.assertIn("검증:", document)
        self.assertIn("매 응답의 마지막", self.skill)

    def test_load_failure_is_reported_as_not_applied(self):
        self.assertIn("로드 실패 · 적용 지침 없음", self.bootstrap)
        self.assertIn("적용 지침: 없음", self.skill)
        self.assertIn("적용 지침: 없음", self.playbook)
        self.assertIn("읽기 미확인", self.skill)
        self.assertIn("P12를 읽지 않았는데 P12를 적용했다고", self.skill)

    def test_actual_evidence_not_inferred_from_prompt_read(self):
        for document in (self.skill, self.playbook):
            self.assertIn("UNVERIFIED", document)
            self.assertIn("자기 보고", document)
            self.assertIn("실제", document)
        self.assertIn("독립적인", self.readme)
        self.assertIn("기능 성공을 주장하지 않음", self.evals)

    def test_exam_boundary_remains(self):
        for word in ("클립보드", "외부 메모", "2차 예선 결과", "Git Push", "서술형"):
            self.assertIn(word, self.playbook)
        for word in ("외부 AI", "후속 서술형", "자동 제출", "공식 타이머", "Computer Use"):
            self.assertIn(word, self.skill)

    def test_toolkit_is_separate_from_task_submission(self):
        self.assertIn("과제 폴더 바깥", self.readme)
        self.assertIn("과제 폴더 바깥", self.bootstrap)
        self.assertIn("KIT가 TASK 안에 있으면", self.playbook)
        self.assertIn("자동 이동·삭제하지 않는다", self.bootstrap)
        self.assertIn("제출 대상", self.readme)
        self.assertIn("제출 대상", self.skill)

    def test_bootstrap_is_single_entrypoint(self):
        self.assertIn("ai-task-kit/BOOTSTRAP.md를 실제로 읽고", self.readme)
        self.assertNotIn("ai-task-kit/BOOTSTRAP.md와 ai-task-kit/docs/EXAM_PROMPT_PLAYBOOK.md", self.readme)
        self.assertIn("단일 시작점", self.bootstrap)
        self.assertIn("단일 시작점", self.skill)
        self.assertIn("BOOTSTRAP.md 하나를 시작점", self.playbook)

    def test_p01_does_not_require_repeated_bootstrap_and_skill(self):
        p01 = self.playbook.split("### P01.", 1)[1].split("### P02.", 1)[0]
        self.assertNotIn("ai-task-kit/BOOTSTRAP.md와 Skill을 확인해줘", p01)
        self.assertIn("이미 읽었다면 다시 읽지 말고", p01)
        self.assertIn("P01을 선택한 뒤 BOOTSTRAP과 Skill을 반복해서 읽지 않는다", self.bootstrap)
        self.assertIn("P01을 적용한다는 이유만으로", self.skill)

    def test_provenance_uses_verified_local_git_read_only_commands(self):
        rev = 'git -C "<KIT>" rev-parse --verify HEAD'
        status = 'git -C "<KIT>" status --porcelain -- BOOTSTRAP.md .agents/skills/ai-task-kit/SKILL.md docs/EXAM_PROMPT_PLAYBOOK.md'
        for doc in (self.bootstrap, self.playbook, self.skill):
            self.assertIn(rev, doc)
            self.assertIn(status, doc)
            self.assertIn("미확인", doc)
        self.assertIn("첫 명령이", self.bootstrap)
        self.assertIn("지침 파일 변경", self.playbook)
        self.assertIn("커밋", self.readme)

    def test_initial_provenance_report_is_not_per_response(self):
        self.assertIn("최초 로드에 한 번만 보고", self.playbook)
        self.assertIn("매 응답", self.skill)
        self.assertIn("초기 로드:", self.bootstrap)
        self.assertIn("수행 근거:", self.skill)
        self.assertIn("검증:", self.skill)

    def test_provenance_not_an_actual_content_or_test_guarantee(self):
        self.assertIn("파일 읽기와 Git 버전 확인은 별개", self.bootstrap)
        self.assertIn("Git HEAD와 다르다면", self.skill)
        self.assertIn("실제 파일 읽기는 별개", self.playbook)
        self.assertIn("독립적인", self.readme)
        self.assertIn("제출 대상", self.readme)

    def test_markdown_fences_balanced(self):
        self.assertEqual(self.playbook.count("~~~") % 2, 0)
        self.assertEqual(self.playbook.count("\x60\x60\x60") % 2, 0)

    def test_black_box_evaluation_is_not_claimed_as_completed(self):
        self.assertIn("모델 평가 필요", self.evals)
        self.assertIn("단순한 문서 텍스트 검사", self.evals)
        self.assertIn("실제 AI의 지침 준수를 증명할 수 없다", self.evals)


if __name__ == "__main__":
    unittest.main()
