"""Static contracts for the Lite Mode, time-limited exam instructions.

This suite verifies repository documentation, not Codex latency, behavioral
compliance, Cofa availability or actual assessment performance.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "BOOTSTRAP.md"
SKILL = ROOT / ".agents/skills/ai-task-kit/SKILL.md"
INDEX = ROOT / "docs/EXAM_PROMPT_PLAYBOOK.md"
README = ROOT / "README.md"
EVALS = ROOT / "evals/SCENARIOS.md"
DETAILS = ROOT / "docs/prompts"
IDS = [f"P{i:02}" for i in range(1, 13)]


class LiteModeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bootstrap = BOOTSTRAP.read_text(encoding="utf-8")
        cls.skill = SKILL.read_text(encoding="utf-8")
        cls.index = INDEX.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")
        cls.evals = EVALS.read_text(encoding="utf-8")
        cls.details = {
            prompt_id: (DETAILS / (prompt_id + ".md")).read_text(encoding="utf-8")
            for prompt_id in IDS
        }

    def test_index_has_exactly_twelve_linked_prompts(self):
        linked = re.findall(r"\[P(\d{2})\]\(prompts/P\d{2}\.md\)", self.index)
        self.assertEqual(["P" + x for x in linked], IDS)
        self.assertEqual(sorted(x.name for x in DETAILS.glob("P*.md")),
                         [x + ".md" for x in IDS])

    def test_index_is_short_not_twelve_full_templates(self):
        self.assertLess(len(self.index), 4000)
        self.assertNotIn("### P01.", self.index)
        self.assertIn("색인", self.index)
        self.assertIn("상세 프롬프트 전체를 포함하지 않습니다", self.index)

    def test_all_details_are_small_valid_and_self_contained(self):
        for prompt_id, document in self.details.items():
            with self.subTest(prompt_id=prompt_id):
                self.assertTrue(document.startswith("# " + prompt_id + "."), prompt_id)
                self.assertIn("## 상세 작업 지시", document)
                self.assertEqual(document.count("~~~"), 2)
                self.assertLess(len(document), 1800)
                self.assertIn("과제 수행 단계", document)
                self.assertIn("자동 제출", document)

    def test_bootstrap_entry_and_single_read(self):
        self.assertIn("단일 시작점", self.skill)
        self.assertIn(".agents/skills/ai-task-kit/SKILL.md", self.bootstrap)
        self.assertIn("docs/EXAM_PROMPT_PLAYBOOK.md", self.bootstrap)
        self.assertIn("상세 P01~P12를 전부 읽지 않습니다", self.bootstrap)
        self.assertIn("해당 파일만 읽습니다", self.bootstrap)
        self.assertIn("ai-task-kit/BOOTSTRAP.md를 실제로 읽고", self.readme)

    def test_skill_selects_only_current_details(self):
        self.assertIn("docs/prompts/PXX.md", self.skill)
        self.assertIn("12개 상세 파일을 모두 열지 않는다", self.skill)
        self.assertIn("매번 번호를 지시하게 하지 않는다", self.skill)
        self.assertIn("P01을 적용한다는 이유만으로 BOOTSTRAP", self.skill)

    def test_no_repeated_reads_when_context_is_available(self):
        self.assertIn("세션에서 이미 읽은 상세 내용은 재사용", self.skill)
        self.assertIn("이미 확인한 파일은 재조회하지 않습니다", self.bootstrap)
        self.assertIn("이후 상황 변경 때는", self.index)

    def test_detail_is_required_before_claiming_prompt_applied(self):
        self.assertIn("상세 파일의 내용을 실제로 읽은 경우에만", self.skill)
        self.assertIn("색인만 확인", self.index)
        self.assertIn("색인만 확인", self.skill)
        self.assertIn("상세 파일이 차단되면", self.bootstrap)

    def test_reporting_is_kept_two_lines(self):
        for text in (self.index, self.skill, self.bootstrap):
            for word in ("적용 지침:", "플레이북:", "수행 근거:", "검증:"):
                self.assertIn(word, text)
        self.assertIn("해당 상세 읽기 확인", self.skill)

    def test_failed_or_unconfirmed_load_does_not_claim_p12(self):
        self.assertIn("로드 실패", self.index)
        self.assertIn("읽기 미확인", self.skill)
        self.assertIn("P12를 읽지 않았는데 P12를 적용했다고", self.skill)
        self.assertIn("기본 Codex", self.bootstrap)

    def test_provenance_local_git_is_optional_and_read_only(self):
        rev = 'git -C "<KIT>" rev-parse --verify HEAD'
        status = 'git -C "<KIT>" status --porcelain -- BOOTSTRAP.md .agents/skills/ai-task-kit/SKILL.md docs/EXAM_PROMPT_PLAYBOOK.md docs/prompts'
        for text in (self.index, self.skill, self.bootstrap):
            self.assertIn(rev, text)
            self.assertIn(status, text)
            self.assertIn("미확인", text)
        self.assertIn("파일 읽기와 Git 버전 확인은 별개", self.bootstrap)

    def test_toolkit_and_submission_are_separate(self):
        self.assertIn("과제 폴더 바깥", self.readme)
        self.assertIn("과제 폴더 바깥", self.bootstrap)
        self.assertIn("자동 이동·삭제하지 않는다", self.bootstrap)
        self.assertIn("제출 대상", self.skill)
        self.assertIn('python3 "<KIT>/kit.py" preflight --root "<TASK>"', self.readme)

    def test_p01_prioritizes_required_uncertain_optional(self):
        text = self.details["P01"]
        self.assertIn("반드시 구현할 기능", text)
        self.assertIn("업무 담당자 확인이 필요한 조건", text)
        self.assertIn("선택 기능", text)
        self.assertIn("5줄", text)
        self.assertIn("배점·기준은 추측하지 마", text)

    def test_p03_starts_with_end_to_end_runnable_slice(self):
        p = self.details["P03"]
        self.assertIn("입력→처리→출력", p)
        self.assertIn("실제 실행을 확인", p)
        self.assertIn("필수 기능", p)
        self.assertIn("장문의 계획", p)

    def test_p04_audit_does_not_run_unconditionally(self):
        p = self.details["P04"]
        self.assertIn("필요한 경우에만", p)
        self.assertIn("audit", p)
        self.assertIn("반복 검사", p)

    def test_p05_preserves_web_preview_rules(self):
        p = self.details["P05"]
        self.assertIn("Cofa Browser", p)
        self.assertIn("0.0.0.0", p)
        self.assertIn("외부 터널", p)

    def test_p06_switches_strategy_after_repeated_failure(self):
        p = self.details["P06"]
        self.assertIn("두 번 실패", p)
        self.assertIn("약 5분", p)
        self.assertIn("필수 기능을 임의로 포기", p)
        self.assertIn("다른 독립적인 필수 기능", p)

    def test_p07_separates_quick_from_full_validation(self):
        p = self.details["P07"]
        self.assertIn("방금 변경한 기능의 관련 테스트", p)
        self.assertIn("전체 필수 요구사항", p)
        self.assertIn("UNVERIFIED(종료 코드 2)", p)
        self.assertIn("같은 파일 검사만 반복하지", p)

    def test_p08_worklog_is_optional_and_contextual(self):
        p = self.details["P08"]
        self.assertIn("worklog", p)
        self.assertIn("선택 기능", p)
        self.assertIn("작은 수정마다", p)

    def test_p09_checks_submission_without_auto_submission(self):
        p = self.details["P09"]
        self.assertIn("preflight", p)
        self.assertIn("필수 산출물", p)
        self.assertIn("제출 버튼은 누르지", p)

    def test_p10_preserves_state_on_resume(self):
        p = self.details["P10"]
        self.assertIn("현재 과제 폴더", p)
        self.assertIn("덮어쓰지", p)

    def test_p11_uses_only_official_timer(self):
        p = self.details["P11"]
        self.assertIn("Cofa 공식 타이머", p)
        self.assertIn("별도 타이머", p)
        self.assertIn("최종 제출은 내가 직접", p)
        self.assertIn("공식 타이머", self.skill)

    def test_p12_does_not_bypass_platform_restrictions(self):
        p = self.details["P12"]
        self.assertIn("우회하지", p)
        self.assertIn("기본 환경", p)

    def test_original_exam_boundary_is_retained(self):
        for text in (self.index, self.skill):
            self.assertIn("서술형", text)
            self.assertIn("Git Push", text)
        for word in ("클립보드", "외부 메모", "2차 예선 결과", "자동 제출"):
            self.assertIn(word, self.index)
        for word in ("외부 AI", "Computer Use", "UNVERIFIED"):
            self.assertIn(word, self.skill)

    def test_no_independent_speed_proof_claim(self):
        self.assertIn("실제 Cofa", self.readme)
        self.assertIn("측정하지 않았", self.readme)
        self.assertIn("자기 보고", self.index)
        self.assertIn("모델 평가 필요", self.evals)

    def test_index_links_resolve_without_parent_traversal(self):
        for prompt_id in IDS:
            self.assertTrue((DETAILS / (prompt_id + ".md")).is_file())
            self.assertIn("prompts/" + prompt_id + ".md", self.index)

    def test_fences_are_balanced(self):
        self.assertEqual(self.index.count("~~~") % 2, 0)
        self.assertEqual(self.index.count("\x60\x60\x60") % 2, 0)
        for detail in self.details.values():
            self.assertEqual(detail.count("~~~") % 2, 0)


if __name__ == "__main__":
    unittest.main()
