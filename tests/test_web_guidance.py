"""Static contracts for functional web guidance, not browser/model verification.

These assertions pin the approved documentation behavior only. They do not
execute a submitted webpage, prove accessibility conformance, or measure speed.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / '.agents/skills/ai-task-kit/references/WEB_FUNCTIONAL_UI.md'
RELATIVE_GUIDE = '../../.agents/skills/ai-task-kit/references/WEB_FUNCTIONAL_UI.md'


class FunctionalWebGuidanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.guide = GUIDE.read_text(encoding='utf-8') if GUIDE.is_file() else ''
        cls.prompts = {
            pid: (ROOT / 'docs/prompts' / (pid + '.md')).read_text(encoding='utf-8')
            for pid in ('P05', 'P07', 'P09')
        }

    def test_reference_exists_and_stays_lightweight(self):
        self.assertTrue(GUIDE.is_file(), 'The optional web UI reference is missing')
        self.assertGreater(len(self.guide), 400)
        self.assertLessEqual(len(self.guide), 2500)

    def test_p05_loads_reference_only_for_web_tasks(self):
        p05 = self.prompts['P05']
        self.assertIn('웹 과제일 때만', p05)
        self.assertIn('(' + RELATIVE_GUIDE + ')', p05)
        self.assertIn('같은 세션', p05)
        self.assertEqual((ROOT / 'docs/prompts' / RELATIVE_GUIDE).resolve(), GUIDE)

    def test_reference_is_not_added_to_initial_loading(self):
        for path in ('BOOTSTRAP.md', '.agents/skills/ai-task-kit/SKILL.md',
                     'docs/EXAM_PROMPT_PLAYBOOK.md'):
            with self.subTest(path=path):
                self.assertNotIn('WEB_FUNCTIONAL_UI.md',
                                 (ROOT / path).read_text(encoding='utf-8'))

    def test_requirements_override_default_ui(self):
        self.assertIn('실제 과제 지침이 우선', self.guide)
        self.assertIn('웹페이지가 필수인지', self.prompts['P05'])
        self.assertIn('지정한 디자인', self.guide)

    def test_first_goal_is_working_input_action_result(self):
        self.assertIn('입력 → 실행 → 결과', self.guide)
        self.assertIn('실제 데이터', self.guide)
        self.assertIn('예시 숫자', self.guide)
        self.assertIn('기능 완료', self.guide)

    def test_existing_stack_is_preserved(self):
        self.assertIn('기존 기술 스택', self.guide)
        self.assertIn('기존 CSS', self.guide)
        self.assertIn('재작성하지 않는다', self.guide)

    def test_visual_scope_is_minimal_unless_required(self):
        for term in ('애니메이션', '다크모드', '필수 기능', '선택'):
            self.assertIn(term, self.guide)
        self.assertIn('새 라이브러리', self.guide)
        self.assertIn('외부 폰트', self.guide)

    def test_relevant_ui_states_are_defined(self):
        for term in ('입력 전', '처리 중', '결과 없음', '입력 오류', '정상 결과'):
            self.assertIn(term, self.guide)
        self.assertIn('중복 실행', self.guide)
        self.assertIn('실제로 해당하는 상태만', self.guide)

    def test_readable_controls_keyboard_and_layout(self):
        for term in ('글자', '버튼', '표', '라벨', '키보드', '선택 표시', '잘림', '겹침'):
            self.assertIn(term, self.guide)
        self.assertIn('색상만', self.guide)

    def test_actual_ui_evidence_is_not_inferred(self):
        self.assertIn('직접 확인하지 못한', self.guide)
        self.assertIn('UNVERIFIED', self.guide)
        self.assertIn('사용자가', self.guide)
        self.assertIn('Computer Use', self.guide)
        self.assertIn('외부 전송', self.guide)

    def test_p07_adds_conditional_functional_web_checks(self):
        p07 = self.prompts['P07']
        self.assertIn('웹 과제라면', p07)
        for term in ('입력', '버튼', '결과', '미검증', '화면'):
            self.assertIn(term, p07)
        self.assertIn('UNVERIFIED(종료 코드 2)', p07)
        self.assertIn('전체 필수 요구사항', p07)

    def test_p09_keeps_manual_submission_and_web_readiness(self):
        p09 = self.prompts['P09']
        self.assertIn('웹 과제라면', p09)
        for term in ('실행 명령', '경로', '저장', '미검증'):
            self.assertIn(term, p09)
        self.assertIn('제출 버튼은 누르지', p09)
        self.assertIn('Git Push', p09)

    def test_preview_contract_and_prompt_budget_are_preserved(self):
        p05 = self.prompts['P05']
        for term in ('Cofa Browser', '0.0.0.0', '외부 터널', '미검증'):
            self.assertIn(term, p05)
        for pid, text in self.prompts.items():
            with self.subTest(pid=pid):
                self.assertTrue(text.startswith('# ' + pid + '.'))
                self.assertLess(len(text), 1800)
                self.assertEqual(text.count('~~~') % 2, 0)
                self.assertIn('AI 사용 금지', text)

    def test_p05_relative_links_resolve(self):
        self.assertIn(RELATIVE_GUIDE, self.prompts['P05'])
        links = re.findall(r'\]\(([^)]+)\)', self.prompts['P05'])
        for link in links:
            if '://' not in link and not link.startswith('#'):
                target = (ROOT / 'docs/prompts' / link.split('#', 1)[0]).resolve()
                self.assertTrue(target.is_relative_to(ROOT))
                self.assertTrue(target.is_file(), link)


if __name__ == '__main__':
    unittest.main()
