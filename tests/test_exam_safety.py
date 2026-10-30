"""Synthetic regressions for the approved path and reporting polish.

No actual exam files, platform access, model calls or submission are used.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / 'kit.py'
SOURCE = REPO / '.agents/skills/ai-task-kit/scripts/taskkit.py'


class ExamSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='kit safety 한글 ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.task = self.base / '과제 폴더'
        self.task.mkdir()
        (self.task / 'main.py').write_text('raise RuntimeError("must not run")\n', encoding='utf-8')
        self.cwd = self.base / '다른 작업 위치'
        self.cwd.mkdir()

    def invoke(self, command='preflight', *, script=CLI, root=None,
               required=('main.py',), as_json=True):
        args = [sys.executable, '-S', str(script), command,
                '--root', str(root or self.task)]
        for name in required:
            args.extend(('--require', name))
        if as_json:
            args.append('--json')
        result = subprocess.run(args, cwd=self.cwd, capture_output=True,
                                text=True, encoding='utf-8', timeout=15)
        self.assertNotIn('Traceback', result.stderr)
        self.assertTrue(result.stdout.strip(), result.stderr)
        return result

    def report(self, **kwargs):
        result = self.invoke(**kwargs)
        payload = json.loads(result.stdout)
        self.assertEqual(result.returncode,
                         {'PASS': 0, 'FAIL': 1, 'UNVERIFIED': 2}[payload['status']])
        return payload

    def copy_script(self, directory, *, standalone=False):
        relative = 'scripts/taskkit.py' if standalone else '.agents/skills/ai-task-kit/scripts/taskkit.py'
        target = directory / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE, target)
        return target

    def assert_inside(self, kit, *, standalone=False):
        script = self.copy_script(kit, standalone=standalone)
        before = {p.relative_to(self.task).as_posix(): p.read_bytes()
                  for p in self.task.rglob('*') if p.is_file()}
        report = self.report(script=script)
        details = report['details']
        self.assertTrue(details['nested_toolkit_candidate'], details)
        self.assertIs(details.get('executing_toolkit_inside_task'), True)
        self.assertEqual(details.get('executing_toolkit_path'), str(kit.resolve()))
        self.assertEqual(report['status'], 'UNVERIFIED')
        self.assertFalse(details['submission_confirmed'])
        after = {p.relative_to(self.task).as_posix(): p.read_bytes()
                 for p in self.task.rglob('*') if p.is_file()}
        self.assertEqual(before, after)
        self.assertFalse((self.task / '.ai-task-kit').exists())

    def test_renamed_running_toolkit_inside_task(self):
        self.assert_inside(self.task / 'renamed-kit')

    def test_deeply_nested_running_toolkit_inside_task(self):
        self.assert_inside(self.task / 'tools' / 'support' / '별도 도구')

    def test_running_toolkit_equal_to_task_root(self):
        self.assert_inside(self.task)

    def test_standalone_skill_inside_task(self):
        self.assert_inside(self.task / 'local skill', standalone=True)

    def test_outside_sibling_with_same_prefix_is_not_inside(self):
        kit = self.base / (self.task.name + '-toolkit')
        script = self.copy_script(kit)
        details = self.report(script=script)['details']
        self.assertFalse(details['nested_toolkit_candidate'])
        self.assertIs(details.get('executing_toolkit_inside_task'), False)
        self.assertEqual(details.get('executing_toolkit_path'), str(kit))

    def test_standalone_skill_outside_task(self):
        kit = self.base / '독립 skill'
        script = self.copy_script(kit, standalone=True)
        details = self.report(script=script)['details']
        self.assertFalse(details['nested_toolkit_candidate'])
        self.assertIs(details.get('executing_toolkit_inside_task'), False)
        self.assertEqual(details.get('executing_toolkit_path'), str(kit))

    def test_symlink_task_uses_resolved_root(self):
        kit = self.task / 'tools' / 'renamed'
        script = self.copy_script(kit)
        alias = self.base / 'task-alias'
        try:
            alias.symlink_to(self.task, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        details = self.report(script=script, root=alias)['details']
        self.assertTrue(details['nested_toolkit_candidate'])
        self.assertEqual(details.get('executing_toolkit_path'), str(kit))

    def test_symlink_script_uses_real_location(self):
        kit = self.task / 'actual-kit'
        script = self.copy_script(kit)
        alias = self.base / 'outside-alias.py'
        try:
            alias.symlink_to(script)
        except (OSError, NotImplementedError):
            self.skipTest('symlinks unavailable')
        details = self.report(script=alias)['details']
        self.assertTrue(details['nested_toolkit_candidate'])
        self.assertEqual(details.get('executing_toolkit_path'), str(kit))

    def test_legacy_named_candidate_warning_is_retained(self):
        candidate = self.task / 'ai-task-kit' / 'BOOTSTRAP.md'
        candidate.parent.mkdir()
        candidate.write_text('# synthetic tool marker\n', encoding='utf-8')
        details = self.report()['details']
        self.assertTrue(details['nested_toolkit_candidate'])
        self.assertIs(details.get('executing_toolkit_inside_task'), False)
        self.assertEqual(candidate.read_text(encoding='utf-8'), '# synthetic tool marker\n')

    def test_inside_warning_is_readable_without_automatic_action(self):
        script = self.copy_script(self.task / 'nested' / 'renamed')
        result = self.invoke(script=script, as_json=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn('실행 중인 보조 도구가 과제 폴더 안', result.stdout)
        self.assertIn('자동 이동·삭제하지 않습니다', result.stdout)
        self.assertTrue(script.is_file())

    def test_report_paths_do_not_emit_terminal_control_codes(self):
        kit = self.task / 'tool-\x1b[31m'
        script = self.copy_script(kit)
        result = self.invoke(script=script, as_json=False)
        self.assertEqual(result.returncode, 2)
        self.assertIn('executing_toolkit_path', result.stdout)
        self.assertNotIn('\x1b', result.stdout)

    def test_valid_file_summary_does_not_change_overall_status(self):
        for command in ('verify', 'preflight'):
            with self.subTest(command=command):
                report = self.report(command=command)
                self.assertEqual(report['status'], 'UNVERIFIED')
                self.assertEqual(report['details'].get('file_check_status'), 'PASS')
                self.assertEqual(report['details'].get('functional_status'), 'UNVERIFIED')

    def test_missing_file_keeps_fail_and_exit_one(self):
        for command in ('verify', 'preflight'):
            with self.subTest(command=command):
                result = self.invoke(command, required=('missing.py',))
                self.assertEqual(result.returncode, 1)
                report = json.loads(result.stdout)
                self.assertEqual(report['status'], 'FAIL')
                self.assertEqual(report['details'].get('file_check_status'), 'FAIL')

    def test_syntax_error_is_not_reported_as_normal(self):
        (self.task / 'bad.py').write_text('def broken(:\n', encoding='utf-8')
        for command in ('verify', 'preflight'):
            with self.subTest(command=command):
                result = self.invoke(command, required=('bad.py',), as_json=False)
                self.assertEqual(result.returncode, 1)
                self.assertIn('파일 검사: 실패', result.stdout)
                self.assertNotIn('파일 검사: 정상', result.stdout)

    def test_no_required_files_remain_unverified(self):
        for command in ('verify', 'preflight'):
            with self.subTest(command=command):
                report = self.report(command=command, required=())
                self.assertEqual(report['status'], 'UNVERIFIED')
                self.assertEqual(report['details'].get('file_check_status'), 'UNVERIFIED')
                text = self.invoke(command, required=(), as_json=False).stdout
                self.assertIn('파일 검사: 미검증', text)
                self.assertNotIn('파일 검사: 정상', text)

    def test_limit_exceeded_does_not_become_file_pass(self):
        large = self.task / 'large.txt'
        with large.open('wb') as stream:
            stream.truncate(8 * 1024 * 1024 + 1)
        for command in ('verify', 'preflight'):
            with self.subTest(command=command):
                report = self.report(command=command, required=('main.py', 'large.txt'))
                self.assertEqual(report['status'], 'UNVERIFIED')
                self.assertEqual(report['details'].get('file_check_status'), 'UNVERIFIED')

    def test_failure_takes_priority_over_unverified_files(self):
        large = self.task / 'large.txt'
        with large.open('wb') as stream:
            stream.truncate(8 * 1024 * 1024 + 1)
        for command in ('verify', 'preflight'):
            with self.subTest(command=command):
                report = self.report(command=command, required=('large.txt', 'missing.py'))
                self.assertEqual(report['status'], 'FAIL')
                self.assertEqual(report['details'].get('file_check_status'), 'FAIL')

    def test_human_output_separates_file_and_function_checks(self):
        for command in ('verify', 'preflight'):
            with self.subTest(command=command):
                result = self.invoke(command, as_json=False)
                self.assertEqual(result.returncode, 2)
                self.assertIn('파일 검사: 정상', result.stdout)
                self.assertIn('실제 기능 검사: 이 도구에서는 수행하지 않음', result.stdout)
                self.assertIn('다음 작업: 과제의 실행·테스트 명령으로 기능 확인', result.stdout)

    def test_json_remains_a_single_object_and_check_does_not_execute(self):
        marker = self.task / 'must-not-exist.txt'
        (self.task / 'main.py').write_text(
            'from pathlib import Path\nPath(' + repr(str(marker)) + ').write_text("executed")\n',
            encoding='utf-8')
        for command in ('verify', 'preflight'):
            with self.subTest(command=command):
                result = self.invoke(command)
                report = json.loads(result.stdout)
                self.assertEqual(report['details'].get('file_check_status'), 'PASS')
                self.assertNotIn('파일 검사: 정상', result.stdout)
                self.assertFalse(marker.exists())
                self.assertFalse((self.task / '.ai-task-kit').exists())


class AbsoluteStartupContractTests(unittest.TestCase):
    def test_readme_start_request_uses_confirmed_absolute_kit(self):
        text = (REPO / 'README.md').read_text(encoding='utf-8')
        self.assertIn('<KIT>/BOOTSTRAP.md를 실제로 읽고', text)
        self.assertIn('git -C ai-task-kit rev-parse --show-toplevel', text)
        self.assertNotIn('\nai-task-kit/BOOTSTRAP.md를 실제로 읽고', text)
        self.assertIn('실제 절대 경로', text)

    def test_bootstrap_resolves_document_links_from_kit_not_cwd(self):
        text = (REPO / 'BOOTSTRAP.md').read_text(encoding='utf-8')
        self.assertIn('실제 절대 경로', text)
        self.assertIn('상대 링크는 KIT 기준', text)
        self.assertIn('과제 작업 폴더를 바꾸지 않습니다', text)
        self.assertIn('기본 Codex', text)


if __name__ == '__main__':
    unittest.main()
