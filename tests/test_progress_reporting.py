"""Static contracts for evidence-based, event-driven progress reporting.

These tests inspect instructions and examples. They do not run Codex, measure
model compliance, monitor processes or certify the Cofa environment.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.agents/skills/ai-task-kit/SKILL.md'
BOOTSTRAP = ROOT / 'BOOTSTRAP.md'
README = ROOT / 'README.md'


class ProgressReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill = SKILL.read_text(encoding='utf-8')
        cls.bootstrap = BOOTSTRAP.read_text(encoding='utf-8')
        cls.readme = README.read_text(encoding='utf-8')

    def progress_section(self):
        heading = '## 한국어 보고 형식 — 개발 현황'
        self.assertIn(heading, self.skill)
        return self.skill.split(heading, 1)[1].split('\n## 도구', 1)[0]

    def test_common_skill_contains_progress_rules(self):
        self.progress_section()

    def test_visible_updates_do_not_wait_for_final_response(self):
        section = self.progress_section()
        for text in ('코드 편집·명령 실행 묶음에 들어가기 전', '최종 응답에만 몰아서',
                     '사용자가 다시 묻지 않아도'):
            self.assertIn(text, section)

    def test_meaningful_event_triggers(self):
        section = self.progress_section()
        for text in ('작업 시작', '구현·검증 결과', '오류', '승인 대기', '업무 조건 변경', '제출 전'):
            self.assertIn(text, section)

    def test_fixed_template_has_all_fields(self):
        section = self.progress_section()
        for text in ('[개발 현황 · 마지막 확인 기준]', '필수 기능:', '현재:', '상태:',
                     '검증 완료:', '남은 작업:', '막힘:', '사용자 조치:', '다음:'):
            self.assertIn(text, section)

    def test_counts_are_required_features_not_tool_calls(self):
        section = self.progress_section()
        for text in ('요구사항별 ID', '선택 기능', '코드 줄 수', '명령 실행 횟수',
                     '작업 묶음 수와 필수 기능 수는 다를 수 있다'):
            self.assertIn(text, section)

    def test_unknown_totals_are_not_zero_of_zero(self):
        section = self.progress_section()
        self.assertIn('총수가 아직 불명확하면 `확인 중`', section)
        self.assertIn('`0/0`을 완료로 표시하지 않는다', section)

    def test_denominator_change_has_a_reason(self):
        section = self.progress_section()
        self.assertIn('총수가 바뀌면 변경 이유', section)
        self.assertIn('임의로 필수 기능을 삭제', section)

    def test_all_states_are_defined(self):
        section = self.progress_section()
        for text in ('대기', '구현 중', '구현됨·미검증', '검증 중', '검증 완료',
                     '막힘', '승인 대기', '재검증 필요', '확인 중'):
            self.assertIn(text, section)

    def test_implementation_and_verified_counts_are_distinct(self):
        section = self.progress_section()
        self.assertIn('검증 완료 수 ≤ 구현 수 ≤ 필수 기능 총수', section)
        self.assertIn('검증 완료 항목도 구현 수에 포함', section)

    def test_actual_requirement_evidence_is_required(self):
        section = self.progress_section()
        self.assertIn('요구사항별 실제 실행·검산 근거', section)
        self.assertIn('부분 검증', section)
        self.assertIn('문법·파일 검사만으로 검증 완료', section)

    def test_source_and_dependency_changes_invalidate_verification(self):
        section = self.progress_section()
        for text in ('코드·입력·의존성', '재검증 필요', '검증 완료 수에서 제외'):
            self.assertIn(text, section)

    def test_approval_and_business_decisions_are_distinct(self):
        section = self.progress_section()
        self.assertIn('승인 필요 / 업무 판단 필요 / 화면 확인 필요', section)
        self.assertIn('실제 플랫폼 승인 요청', section)
        self.assertIn('승인을 대신 처리', section)

    def test_long_command_is_announced_before_execution(self):
        section = self.progress_section()
        self.assertIn('긴 명령 전에는 무엇을 실행하고 어떤 결과를 기다리는지', section)
        self.assertIn('결과 확인 대기', section)

    def test_silence_is_not_fabricated_process_liveness(self):
        section = self.progress_section()
        for text in ('새 출력이 없으면', '정상 진행이나 멈춤을 단정하지 않는다',
                     '보고만을 위해 중단·재실행하지 않는다'):
            self.assertIn(text, section)

    def test_resume_does_not_inherit_unverified_completion(self):
        section = self.progress_section()
        self.assertIn('세션이 끊겨 근거가 소실되면', section)
        self.assertIn('이전 완료 수를 추정해 복원하지 않는다', section)

    def test_no_guessed_percent_eta_or_score(self):
        section = self.progress_section()
        for text in ('백분율', '완료 예상 시간', '예상 점수', '추정하지 않는다'):
            self.assertIn(text, section)

    def test_short_updates_no_timer_or_extra_state(self):
        section = self.progress_section()
        for text in ('본문 최대 6줄', '상태 변화 없이 반복', '별도 상태 파일', '타이머',
                     '서버', '백그라운드 감시', 'worklog/retry'):
            self.assertIn(text, section)

    def test_reporting_does_not_add_blocking_confirmation(self):
        section = self.progress_section()
        self.assertIn('진척 보고를 이유로 매번 진행 승인을 요구하지 않는다', section)
        self.assertIn('사용자 조치가 없으면 계속 진행', section)

    def test_self_report_and_no_interval_guarantee(self):
        section = self.progress_section()
        self.assertIn('자기 보고', section)
        self.assertIn('고정 간격 갱신을 보장하지 않는다', section)
        self.assertIn('독립적인 실시간 감시', section)

    def test_exam_boundary_and_manual_submission_retained(self):
        section = self.progress_section()
        self.assertIn('AI 금지 단계에는 현황 보고도 하지 않는다', section)
        self.assertIn('모든 기능을 검증해도 저장·제출 완료를 뜻하지 않는다', section)
        self.assertIn('제출 버튼을 누르거나 제출 완료를 대신 선언하지 않는다', self.skill)

    def test_two_line_footer_and_evidence_are_preserved(self):
        for doc in (self.skill, self.bootstrap):
            for text in ('적용 지침:', '플레이북:', '수행 근거:', '검증:'):
                self.assertIn(text, doc)
        section = self.progress_section()
        self.assertIn('기존 두 줄 보고', section)
        self.assertIn('수행 근거', section)

    def test_bootstrap_activates_progress_without_extra_reference_loading(self):
        self.assertIn('개발 현황', self.bootstrap)
        self.assertIn('작업 시작·구현·검증·오류·승인 대기', self.bootstrap)
        self.assertIn('새 문서나 상태 파일', self.bootstrap)
        self.assertNotIn('PROGRESS.md', self.bootstrap)

    def test_readme_start_request_asks_for_updates(self):
        start_section = self.readme.split('### 2. 플랫폼에서 제공하는 Codex에 한국어로 요청', 1)[1]
        block = start_section.split('```text', 1)[1].split('```', 1)[0]
        self.assertIn('개발 현황', block)
        self.assertIn('현재 작업·남은 작업·사용자 조치', block)
        self.assertIn('구현 수와 검증 완료 수', block)

    def test_readme_explains_instruction_not_a_new_cli(self):
        self.assertIn('## 개발 현황 표시', self.readme)
        self.assertIn('새 CLI 명령', self.readme)
        self.assertIn('자기 보고', self.readme)
        self.assertIn('고정 간격', self.readme)
        self.assertIn('독립적인 실시간 감시', self.readme)

    def test_example_is_labeled_and_numerically_consistent(self):
        section = self.readme.split('## 개발 현황 표시', 1)
        self.assertEqual(len(section), 2)
        self.assertIn('가상 예시', section[1])
        blocks = re.findall(r'```text\n(.*?)\n```', section[1], flags=re.S)
        panels = [b for b in blocks if b.startswith('[개발 현황')]
        self.assertGreaterEqual(len(panels), 1)
        for panel in panels:
            match = re.search(r'필수 기능: (\d+)개 중 구현 (\d+)개 / 검증 완료 (\d+)개', panel)
            self.assertIsNotNone(match)
            total, implemented, verified = map(int, match.groups())
            self.assertLessEqual(verified, implemented)
            self.assertLessEqual(implemented, total)
            self.assertNotIn('%', panel)
            self.assertLessEqual(len(panel.splitlines()), 9)
            self.assertIn('사용자 조치:', panel)
            self.assertIn('수행 근거:', panel)

    def test_existing_lightweight_loading_is_preserved(self):
        self.assertIn('12개 상세 파일을 모두 열지 않는다', self.skill)
        self.assertIn('해당 파일만 읽습니다', self.bootstrap)
        self.assertLess(len(self.skill), 14000)
        self.assertNotIn('## 개발 현황', self.bootstrap.split('## 3.', 1)[0])

    def test_progress_template_fences_are_balanced(self):
        section = self.progress_section()
        self.assertEqual(section.count('~~~') % 2, 0)
        self.assertEqual(self.readme.count('```') % 2, 0)


if __name__ == '__main__':
    unittest.main()
