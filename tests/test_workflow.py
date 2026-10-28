"""Synthetic tests for opt-in local evidence/workflow records and submission preflight."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / 'kit.py'
SKILL_CLI = REPO / '.agents/skills/ai-task-kit/scripts/taskkit.py'


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='과제 test ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def put(self, name, content='text'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def run_kit(self, *argv, status=None, script=CLI):
        p = subprocess.run([sys.executable, '-S', str(script), *argv, '--json'],
                           capture_output=True, text=True, timeout=15)
        self.assertTrue(p.stdout.strip(), p.stderr)
        try:
            report = json.loads(p.stdout)
        except json.JSONDecodeError:
            self.fail(p.stdout + p.stderr)
        self.assertEqual(p.returncode, {'PASS': 0, 'FAIL': 1, 'UNVERIFIED': 2}[report['status']], report)
        if status:
            self.assertEqual(report['status'], status, report)
        self.assertNotIn('Traceback', p.stderr)
        return report

    def req(self, *files):
        argv = ['worklog', 'requirement', '--root', str(self.root),
                '--id', 'r1', '--text', '설명용 합계 검증']
        for name in files:
            argv += ['--file', name]
        return self.run_kit(*argv, status='PASS')

    def status(self):
        return self.run_kit('worklog', 'status', '--root', str(self.root), status='UNVERIFIED')['details']

    def test_record_is_opt_in_and_local(self):
        self.assertFalse((self.root / '.ai-task-kit').exists())
        self.assertFalse(self.status()['exists'])
        self.assertFalse((self.root / '.ai-task-kit').exists())
        self.req('out.txt')
        self.assertTrue((self.root / '.ai-task-kit/worklog.json').exists())
        self.assertEqual(self.status()['requirements'][0]['state'], 'EVIDENCE_MISSING')

    def test_question_answer_apply_and_staleness(self):
        self.put('out.txt', 'original')
        self.req('out.txt')
        self.run_kit('worklog', 'ask', '--root', str(self.root),
                     '--id', 'q1', '--requirement', 'r1', '--text', '취소 건 처리?', status='PASS')
        self.assertEqual(self.status()['requirements'][0]['state'], 'QUESTION_PENDING')
        self.run_kit('worklog', 'answer', '--root', str(self.root), '--id', 'q1',
                     '--text', '제외', '--source', '담당자 답변', status='PASS')
        self.assertEqual(self.status()['requirements'][0]['state'], 'ANSWER_NOT_APPLIED')
        self.run_kit('worklog', 'apply', '--root', str(self.root),
                     '--id', 'q1', '--file', 'out.txt', status='PASS')
        self.assertEqual(self.status()['questions'][0]['state'], 'APPLICATION_RECORDED')
        self.put('out.txt', 'modified')
        self.assertEqual(self.status()['questions'][0]['state'], 'APPLIED_FILE_CHANGED')

    def test_declared_evidence_is_not_functional_proof(self):
        self.put('out.txt', 'original')
        self.req('out.txt')
        report = self.run_kit('worklog', 'evidence', '--root', str(self.root),
                              '--id', 'e1', '--requirement', 'r1', '--file', 'out.txt',
                              '--command', 'python test.py', '--outcome', 'PASS',
                              '--note', '테스트 실행 결과 2건', status='PASS')
        self.assertFalse(report['details']['executed_commands'])
        self.assertEqual(self.status()['requirements'][0]['state'], 'PASS_RECORDED_ONLY')
        self.put('out.txt', 'changed')
        self.assertEqual(self.status()['requirements'][0]['state'], 'EVIDENCE_STALE')

    def test_latest_failure_overrides_previous_pass(self):
        self.put('out.txt', 'original')
        self.req('out.txt')
        common = ['--root', str(self.root), '--requirement', 'r1',
                  '--file', 'out.txt', '--command', 'python -m unittest', '--note', '실제 결과']
        self.run_kit('worklog', 'evidence', '--id', 'e1', *common, '--outcome', 'PASS', status='PASS')
        self.run_kit('worklog', 'evidence', '--id', 'e2', *common, '--outcome', 'FAIL', status='PASS')
        self.assertEqual(self.status()['requirements'][0]['state'], 'FAIL_RECORDED')

    def test_decision_and_duplicate_ids(self):
        self.req('out.txt')
        self.run_kit('worklog', 'decision', '--root', str(self.root),
                     '--id', 'd1', '--requirement', 'r1', '--text', '중복 제외',
                     '--reason', '업무 조건', '--source', '담당자', status='PASS')
        self.assertEqual(self.status()['decision_count'], 1)
        self.run_kit('worklog', 'decision', '--root', str(self.root),
                     '--id', 'd1', '--requirement', 'r1', '--text', '덮어쓰기',
                     '--reason', '무효', '--source', '담당자', status='FAIL')
        self.assertEqual(self.status()['decision_count'], 1)

    def test_unknown_requirement_and_answer_rejected(self):
        self.run_kit('worklog', 'ask', '--root', str(self.root), '--id', 'q1',
                     '--requirement', 'missing', '--text', '질문', status='FAIL')
        self.run_kit('worklog', 'answer', '--root', str(self.root), '--id', 'q1',
                     '--text', '답변', '--source', '담당자', status='FAIL')

    def test_relative_path_escape_rejected(self):
        self.run_kit('worklog', 'requirement', '--root', str(self.root),
                     '--id', 'r1', '--text', '요구', '--file', '../outside', status='FAIL')
        self.run_kit('worklog', 'requirement', '--root', str(self.root),
                     '--id', 'r1', '--text', '요구', '--file', '.ai-task-kit/worklog.json', status='FAIL')
        self.assertFalse((self.root / '.ai-task-kit').exists())

    def test_symlink_artifact_rejected(self):
        original = self.put('file.txt', 'okay')
        try:
            (self.root / 'link.txt').symlink_to(original)
        except OSError:
            self.skipTest('symlinks unavailable')
        self.run_kit('worklog', 'requirement', '--root', str(self.root),
                     '--id', 'r1', '--text', '요구사항',
                     '--file', 'link.txt', status='FAIL')
        self.assertFalse((self.root / '.ai-task-kit').exists())

    def test_corrupt_record_does_not_get_overwritten(self):
        self.put('.ai-task-kit/worklog.json', '{"foreign":true}')
        self.run_kit('worklog', 'requirement', '--root', str(self.root),
                     '--id', 'r1', '--text', 'test', status='FAIL')
        self.assertEqual((self.root / '.ai-task-kit/worklog.json').read_text(), '{"foreign":true}')

    def test_malformed_nested_worklog_is_fail_not_traceback(self):
        state = {'schema_version': 1, 'root': str(self.root),
                 'requirements': {'r1': {}}, 'questions': {},
                 'decisions': {}, 'evidence': {}}
        self.put('.ai-task-kit/worklog.json', json.dumps(state))
        r = self.run_kit('worklog', 'status', '--root', str(self.root), status='FAIL')
        self.assertIn('형식', r['summary'])

    def test_worklog_directory_symlink_rejected(self):
        dest = self.root / 'real'
        dest.mkdir()
        try:
            (self.root / '.ai-task-kit').symlink_to(dest, target_is_directory=True)
        except OSError:
            self.skipTest('symlinks unavailable')
        self.run_kit('worklog', 'requirement', '--root', str(self.root),
                     '--id', 'r1', '--text', 'test', status='FAIL')
        self.assertEqual(list(dest.iterdir()), [])

    def test_preflight_missing_required_is_fail(self):
        report = self.run_kit('preflight', '--root', str(self.root),
                              '--require', 'missing.py', status='FAIL')
        self.assertFalse(report['details']['submission_confirmed'])
        self.assertEqual(report['details']['required_checks'][0]['status'], 'FAIL')

    def test_preflight_valid_is_still_unverified(self):
        self.put('main.py', 'raise Exception("should not execute")')
        self.put('tmp.bak', 'backup')
        report = self.run_kit('preflight', '--root', str(self.root),
                              '--require', 'main.py', status='UNVERIFIED')
        d = report['details']
        self.assertEqual(d['required_checks'][0]['status'], 'PASS')
        self.assertIn('tmp.bak', d['review_candidates'])
        self.assertFalse(d['submission_confirmed'])
        self.assertFalse(d['editor_save_confirmed'])
        self.assertFalse(d['internal_tool_state_dir_present'])
        self.assertFalse((self.root / 'should not execute').exists())

    def test_preflight_reports_pending_questions(self):
        self.put('main.py', 'print(1)')
        self.run_kit('worklog', 'requirement', '--root', str(self.root),
                     '--id', 'r1', '--text', '요구', '--file', 'main.py', status='PASS')
        self.run_kit('worklog', 'ask', '--root', str(self.root),
                     '--id', 'q1', '--requirement', 'r1', '--text', '확인할 조건', status='PASS')
        report = self.run_kit('preflight', '--root', str(self.root),
                              '--require', 'main.py', status='UNVERIFIED')
        self.assertEqual(report['details']['worklog']['questions'][0]['state'], 'UNANSWERED')

    def test_commands_are_recorded_not_executed(self):
        self.put('main.py', 'print(1)')
        self.req('main.py')
        self.run_kit('worklog', 'evidence', '--root', str(self.root),
                     '--id', 'e1', '--requirement', 'r1', '--file', 'main.py',
                     '--command', 'touch should_not_exist', '--outcome', 'PASS',
                     '--note', '주장만 기록', status='PASS')
        self.assertFalse((self.root / 'should_not_exist').exists())


    def test_web_error_hints(self):
        self.put('error.log', 'Error: listen EADDRINUSE: address already in use')
        r = self.run_kit('explain', '--root', str(self.root), '--file', 'error.log', status='UNVERIFIED')
        self.assertEqual(r['details']['category'], 'EADDRINUSE')
        self.put('error.log', 'ECONNREFUSED while loading local server')
        r = self.run_kit('explain', '--root', str(self.root), '--file', 'error.log', status='UNVERIFIED')
        self.assertEqual(r['details']['category'], 'ECONNREFUSED')

    def test_standalone_skill_entrypoint(self):
        self.put('main.py', 'print(1)')
        self.run_kit('preflight', '--root', str(self.root),
                     '--require', 'main.py', status='UNVERIFIED', script=SKILL_CLI)

    def test_no_required_file_does_not_mean_ready(self):
        report = self.run_kit('preflight', '--root', str(self.root), status='UNVERIFIED')
        self.assertFalse(report['details']['requirements_supplied'])
        self.assertFalse(report['details']['submission_confirmed'])


if __name__ == '__main__':
    unittest.main()
