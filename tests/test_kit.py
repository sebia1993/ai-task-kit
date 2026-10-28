"""Black-box contracts: helpers never execute task files or send network requests."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
CLI = REPO / 'kit.py'
SKILL = REPO / '.agents/skills/ai-task-kit'


class KitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='task kit 한글 ')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def put(self, name, text):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def call(self, *args, status=None, script=CLI):
        proc = subprocess.run([sys.executable, '-S', str(script), *map(str, args), '--json'],
                              cwd=self.root, capture_output=True, text=True, timeout=10)
        self.assertTrue(proc.stdout.strip(), proc.stderr)
        try:
            result = json.loads(proc.stdout)
        except ValueError:
            self.fail(proc.stdout + proc.stderr)
        self.assertEqual(proc.returncode, {'PASS': 0, 'FAIL': 1, 'UNVERIFIED': 2}[result['status']])
        if status:
            self.assertEqual(result['status'], status, result)
        return result

    def test_help_works(self):
        p = subprocess.run([sys.executable, '-S', str(CLI), '--help'], capture_output=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_doctor(self):
        r = self.call('doctor', '--root', self.root, status='PASS')
        self.assertFalse(r['details']['platform_compatibility_verified'])

    def test_inspect_mixed(self):
        self.put('README.md', '원하는 결과: 보고서')
        self.put('main.py', 'print(1)')
        self.put('data/input.csv', 'a\n1\n')
        self.put('node_modules/hidden.py', '')
        r = self.call('inspect', '--root', self.root, status='PASS')
        self.assertIn('python', r['details']['task_hints'])
        self.assertIn('data', r['details']['task_hints'])
        self.assertNotIn('node_modules/hidden.py', r['details']['files'])

    def test_inspect_does_not_read_secrets(self):
        self.put('.env', 'PASSWORD=secret')
        r = self.call('inspect', '--root', self.root)
        self.assertNotIn('PASSWORD', json.dumps(r))
        self.assertNotIn('.env', r['details']['files'])

    def test_json_duplicate_key(self):
        self.put('a.json', '{"x":1,"x":2}')
        self.call('audit', '--root', self.root, '--file', 'a.json', status='FAIL')

    def test_json_nan(self):
        self.put('a.json', '{"x": NaN}')
        self.call('audit', '--root', self.root, '--file', 'a.json', status='FAIL')

    def test_json_object_is_not_table(self):
        self.put('a.json', '{"settings": {"x": 1}}')
        r = self.call('audit', '--root', self.root, '--file', 'a.json', status='PASS')
        self.assertEqual(r['details']['kind'], 'json-object')
        self.assertIsNone(r['details']['rows'])

    def test_json_table_union_columns(self):
        self.put('a.json', '[{"a":1},{"b":2}]')
        r = self.call('audit', '--root', self.root, '--file', 'a.json', status='PASS')
        self.assertEqual(r['details']['missing'], {'a': 1, 'b': 1})

    def test_empty_json_array_unverified(self):
        self.put('a.json', '[]')
        self.call('audit', '--root', self.root, '--file', 'a.json', status='UNVERIFIED')

    def test_json_scalar_column_fails(self):
        self.put('a.json', '[1,2,3]')
        self.call('audit', '--root', self.root, '--file', 'a.json', '--column', 'x', status='FAIL')

    def test_csv_basic(self):
        self.put('a.csv', 'id,amount\na,0.1\nb,0.2\n')
        r = self.call('audit', '--root', self.root, '--file', 'a.csv', '--column', 'amount',
                      '--expect-sum', '0.3', '--expect-rows', '2', status='PASS')
        self.assertEqual(r['details']['sum'], '0.3')

    def test_csv_wrong_sum(self):
        self.put('a.csv', 'x\n1\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--column', 'x', '--expect-sum', '2', status='FAIL')

    def test_csv_missing_not_zero(self):
        self.put('a.csv', 'id,x\na,\nb,0\n')
        r = self.call('audit', '--root', self.root, '--file', 'a.csv', '--column', 'x', status='FAIL')
        self.assertEqual(r['details']['missing']['x'], 1)

    def test_csv_missing_explicit(self):
        self.put('a.csv', 'id,x\na,\nb,2\n')
        r = self.call('audit', '--root', self.root, '--file', 'a.csv', '--column', 'x', '--allow-missing', status='PASS')
        self.assertEqual(r['details']['sum'], '2')
        self.assertEqual(r['details']['excluded_missing'], 1)

    def test_csv_duplicate_header(self):
        self.put('a.csv', 'x,x\n1,2\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', status='FAIL')

    def test_csv_row_width(self):
        self.put('a.csv', 'a,b\n1,2,3\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', status='FAIL')

    def test_csv_bad_quote(self):
        self.put('a.csv', 'a,b\n"unterminated,3')
        self.call('audit', '--root', self.root, '--file', 'a.csv', status='FAIL')

    def test_csv_blank_line_not_silently_dropped(self):
        self.put('a.csv', 'id,x\n\na,1\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', status='FAIL')

    def test_csv_bom(self):
        self.put('a.csv', '\ufeffx\n1\n')
        r = self.call('audit', '--root', self.root, '--file', 'a.csv', status='PASS')
        self.assertEqual(r['details']['columns'], ['x'])

    def test_cp949_explicit(self):
        (self.root / 'a.csv').write_bytes('항목,값\n시험,1\n'.encode('cp949'))
        self.call('audit', '--root', self.root, '--file', 'a.csv', status='FAIL')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--encoding', 'cp949', status='PASS')

    def test_delimiter_explicit(self):
        self.put('a.csv', 'id;x\na;2\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--delimiter', ';', '--require-column', 'x', status='PASS')

    def test_missing_column(self):
        self.put('a.csv', 'id\na\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--require-column', 'amount', status='FAIL')

    def test_unique_duplicate(self):
        self.put('a.csv', 'id,x\na,1\na,2\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--unique', 'id', status='FAIL')

    def test_unique_missing(self):
        self.put('a.csv', 'id,x\n,1\na,2\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--unique', 'id', status='FAIL')

    def test_date_invalid(self):
        self.put('a.csv', 'date\n2026-02-30\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--date-column', 'date', status='FAIL')

    def test_date_valid(self):
        self.put('a.csv', 'date\n2026-10-28\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--date-column', 'date', status='PASS')

    def test_nonfinite_sum_fails(self):
        for number in ('NaN', 'Infinity', '1e999999', '1,000'):
            self.put('a.json', json.dumps([{'x': number}]))
            self.call('audit', '--root', self.root, '--file', 'a.json', '--column', 'x', status='FAIL')

    def test_path_escape(self):
        self.call('audit', '--root', self.root, '--file', '../outside.json', status='FAIL')

    def test_absolute_path_rejected(self):
        p = self.put('a.json', '{}')
        self.call('audit', '--root', self.root, '--file', p, status='FAIL')

    def test_symlink_rejected(self):
        p = self.put('a.json', '{}')
        try:
            (self.root / 'link.json').symlink_to(p)
        except OSError:
            self.skipTest('symlinks unavailable')
        self.call('audit', '--root', self.root, '--file', 'link.json', status='FAIL')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX only')
    def test_fifo_not_opened(self):
        os.mkfifo(self.root / 'a.json')
        self.call('audit', '--root', self.root, '--file', 'a.json', status='FAIL')

    def test_size_limit(self):
        (self.root / 'a.json').write_bytes(b' ' * (8 * 1024 * 1024 + 1))
        self.call('audit', '--root', self.root, '--file', 'a.json', status='UNVERIFIED')

    def test_row_limit(self):
        self.put('a.csv', 'x\n' + '1\n' * 100001)
        self.call('audit', '--root', self.root, '--file', 'a.csv', status='UNVERIFIED')

    def test_verify_no_required_is_unverified(self):
        self.call('verify', '--root', self.root, status='UNVERIFIED')

    def test_verify_valid_is_not_functional_pass(self):
        self.put('main.py', 'raise RuntimeError("should not execute")')
        r = self.call('verify', '--root', self.root, '--require', 'main.py', status='UNVERIFIED')
        self.assertEqual(r['details']['checks'][0]['status'], 'PASS')
        self.assertEqual(r['details']['functional_status'], 'UNVERIFIED')

    def test_verify_missing(self):
        self.call('verify', '--root', self.root, '--require', 'main.py', status='FAIL')

    def test_verify_syntax(self):
        self.put('main.py', 'def broken(')
        self.call('verify', '--root', self.root, '--require', 'main.py', status='FAIL')

    def test_verify_blank(self):
        self.put('out.md', '   \n')
        self.call('verify', '--root', self.root, '--require', 'out.md', status='FAIL')

    def test_verify_bad_json(self):
        self.put('out.json', '{')
        self.call('verify', '--root', self.root, '--require', 'out.json', status='FAIL')

    def test_verify_hash_and_no_changes(self):
        p = self.put('out.json', '{"ok":true}')
        before = p.read_bytes()
        r = self.call('verify', '--root', self.root, '--require', 'out.json')
        self.assertEqual(r['details']['checks'][0]['sha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(p.read_bytes(), before)
        self.assertFalse((self.root / '.ai-task-kit').exists())

    def test_explain_keyerror_is_hypothesis(self):
        self.put('error.log', "KeyError: 'date'\nPASSWORD=not-for-output")
        r = self.call('explain', '--root', self.root, '--file', 'error.log', status='UNVERIFIED')
        self.assertEqual(r['details']['category'], 'KeyError')
        self.assertNotIn('not-for-output', json.dumps(r))

    def test_retry_status_without_record_is_read_only(self):
        r = self.call('retry', 'status', '--root', self.root, status='UNVERIFIED')
        self.assertEqual(r['details']['counts'], {})
        self.assertFalse((self.root / '.ai-task-kit').exists())

    def test_retry_first_and_second_attempt_without_timer(self):
        first = self.call('retry', 'attempt', '--root', self.root, '--issue', 'csv-error', status='PASS')
        self.assertEqual(first['details']['attempts'], 1)
        self.assertEqual(first['details']['action'], 'INVESTIGATE')
        saved = json.loads((self.root / '.ai-task-kit/retries.json').read_text())
        self.assertEqual(set(saved), {'schema_version', 'root', 'attempts'})
        self.assertEqual(saved['attempts'], {'csv-error': 1})
        second = self.call('retry', 'attempt', '--root', self.root, '--issue', 'csv-error',
                           status='UNVERIFIED')
        self.assertEqual(second['details']['attempts'], 2)
        self.assertEqual(second['details']['action'], 'CHANGE_STRATEGY')
        status = self.call('retry', 'status', '--root', self.root, status='PASS')
        self.assertEqual(status['details']['counts'], {'csv-error': 2})
        self.assertEqual(status['details']['change_strategy_issues'], ['csv-error'])

    def test_retry_records_multiple_independent_issues(self):
        self.call('retry', 'attempt', '--root', self.root, '--issue', 'csv-error')
        self.call('retry', 'attempt', '--root', self.root, '--issue', 'api-error')
        self.call('retry', 'attempt', '--root', self.root, '--issue', 'api-error')
        r = self.call('retry', 'status', '--root', self.root, status='PASS')
        self.assertEqual(r['details']['counts'], {'csv-error': 1, 'api-error': 2})
        self.assertEqual(r['details']['change_strategy_issues'], ['api-error'])

    def test_retry_invalid_issue_rejected_without_state(self):
        for issue in ('../outside', 'with spaces', 'abc/123'):
            self.call('retry', 'attempt', '--root', self.root, '--issue', issue, status='FAIL')
        self.assertFalse((self.root / '.ai-task-kit').exists())

    def test_retry_session_and_timer_options_removed(self):
        self.call('session', 'status', '--root', self.root, status='FAIL')
        self.call('retry', 'attempt', '--root', self.root, '--issue', 'x',
                  '--minutes', '180', status='FAIL')
        self.call('retry', 'status', '--root', self.root, '--reserve', '15', status='FAIL')
        self.assertFalse((self.root / '.ai-task-kit').exists())

    def test_retry_symlink_directory_rejected(self):
        dest = self.root / 'other'
        dest.mkdir()
        try:
            (self.root / '.ai-task-kit').symlink_to(dest, target_is_directory=True)
        except OSError:
            self.skipTest('symlinks unavailable')
        self.call('retry', 'attempt', '--root', self.root, '--issue', 'x', status='FAIL')
        self.assertEqual(list(dest.iterdir()), [])

    def test_retry_symlink_record_file_rejected(self):
        target = self.put('safe.json', '{}')
        try:
            folder = self.root / '.ai-task-kit'
            folder.mkdir()
            (folder / 'retries.json').symlink_to(target)
        except OSError:
            self.skipTest('symlinks unavailable')
        self.call('retry', 'attempt', '--root', self.root, '--issue', 'x', status='FAIL')
        self.assertEqual(target.read_text(), '{}')

    def test_retry_legacy_session_is_never_edited_or_resumed(self):
        old = self.put('.ai-task-kit/session.json',
                       '{"schema_version":1,"root":"foreign","minutes":180,"attempts":{"old":3}}')
        original = old.read_bytes()
        self.call('retry', 'status', '--root', self.root, status='UNVERIFIED')
        self.call('retry', 'attempt', '--root', self.root, '--issue', 'new', status='PASS')
        self.assertEqual(old.read_bytes(), original)
        state = json.loads((self.root / '.ai-task-kit/retries.json').read_text())
        self.assertEqual(state['attempts'], {'new': 1})

    def test_retry_corrupt_record_refused_without_reset(self):
        file = self.put('.ai-task-kit/retries.json', '{"foreign":true}')
        self.call('retry', 'status', '--root', self.root, status='FAIL')
        self.call('retry', 'attempt', '--root', self.root, '--issue', 'x', status='FAIL')
        self.assertEqual(file.read_text(), '{"foreign":true}')

    def test_retry_invalid_counts_are_not_silently_accepted(self):
        file = self.put('.ai-task-kit/retries.json', json.dumps({
            'schema_version': 1, 'root': str(self.root), 'attempts': {'bad': True}}))
        self.call('retry', 'status', '--root', self.root, status='FAIL')
        self.assertIn('"bad": true', file.read_text())

    def test_retry_standalone_skill(self):
        r = self.call('retry', 'attempt', '--root', self.root, '--issue', 'error',
                      script=SKILL / 'scripts/taskkit.py', status='PASS')
        self.assertEqual(r['details']['attempts'], 1)


    def test_standalone_skill(self):
        self.call('doctor', '--root', self.root, script=SKILL / 'scripts/taskkit.py', status='PASS')

    def test_no_network_or_process_imports(self):
        source = SKILL / 'scripts/taskkit.py'
        self.assertTrue(source.exists())
        tree = ast.parse(source.read_text())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(x.name.split('.')[0] for x in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or '').split('.')[0])
        self.assertFalse(names & {'subprocess', 'socket', 'urllib', 'http', 'requests', 'webbrowser'})

    def test_json_number_and_string_are_not_duplicate(self):
        self.put('a.json', '[{"id":1.0},{"id":"1.0"}]')
        r = self.call('audit', '--root', self.root, '--file', 'a.json', '--unique', 'id', status='PASS')
        self.assertEqual(r['details']['duplicate_rows'], 0)

    def test_json_equivalent_numbers_are_duplicate(self):
        self.put('a.json', '[{"id":1.0},{"id":1}]')
        r = self.call('audit', '--root', self.root, '--file', 'a.json', '--unique', 'id', status='FAIL')
        self.assertEqual(r['details']['duplicate_rows'], 1)

    def test_columns_limit(self):
        self.put('a.csv', ','.join('c' + str(i) for i in range(1025)) + '\n' + ','.join('1' for _ in range(1025)) + '\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', status='UNVERIFIED')

    def test_sparse_json_cell_budget(self):
        self.put('a.json', json.dumps([{'c' + str(i % 128): i} for i in range(20000)]))
        self.call('audit', '--root', self.root, '--file', 'a.json', status='UNVERIFIED')

    def test_all_missing_sum_unverified(self):
        self.put('a.csv', 'id,x\na,\nb,\n')
        self.call('audit', '--root', self.root, '--file', 'a.csv', '--column', 'x', '--allow-missing', status='UNVERIFIED')


    def test_unknown_error_no_source_echo(self):
        self.put('e.txt', 'unexpected private data')
        r = self.call('explain', '--root', self.root, '--file', 'e.txt', status='UNVERIFIED')
        self.assertEqual(r['details']['category'], 'UNKNOWN')
        self.assertNotIn('private data', json.dumps(r))

    def test_parent_symlink_rejected(self):
        self.put('real/a.csv', 'x\n1\n')
        try:
            (self.root / 'link').symlink_to(self.root / 'real', target_is_directory=True)
        except OSError:
            self.skipTest('symlinks unavailable')
        self.call('audit', '--root', self.root, '--file', 'link/a.csv', status='FAIL')

    def test_verify_does_not_execute_file(self):
        self.put('main.py', "open('executed.txt', 'w').write('BAD')")
        self.call('verify', '--root', self.root, '--require', 'main.py', status='UNVERIFIED')
        self.assertFalse((self.root / 'executed.txt').exists())


    def test_normal_output_is_korean_and_no_traceback(self):
        self.put('a.csv', 'x\n1\n')
        p = subprocess.run([sys.executable, '-S', str(CLI), 'audit', '--root', str(self.root), '--file', 'a.csv'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0)
        self.assertIn('검사', p.stdout)
        self.assertNotIn('Traceback', p.stderr)

    def test_inspect_truncation_reported(self):
        for i in range(501):
            self.put(str(i) + '.txt', 'x')
        r = self.call('inspect', '--root', self.root, status='UNVERIFIED')
        self.assertTrue(r['details']['truncated'])

    def test_json_overflow_rejected(self):
        self.put('a.json', '{"x":1e999}')
        self.call('audit', '--root', self.root, '--file', 'a.json', status='FAIL')


    def test_toolkit_root_supports_shallow_standalone(self):
        import runpy
        module = runpy.run_path(str(SKILL / 'scripts/taskkit.py'))
        self.assertIn('toolkit_root', module)
        self.assertEqual(module['toolkit_root'](Path('/tool/scripts/taskkit.py')), Path('/tool'))
        self.assertEqual(module['toolkit_root'](Path('/repo/.agents/skills/ai-task-kit/scripts/taskkit.py')), Path('/repo'))


class DocumentationTests(unittest.TestCase):
    def test_skill_contract(self):
        p = SKILL / 'SKILL.md'
        self.assertTrue(p.exists())
        text = p.read_text()
        for required in ('name: ai-task-kit', 'description:', 'UNVERIFIED', '과제', '서술형', 'Git Push', '공식 타이머'):
            self.assertIn(required, text)
        self.assertLess(len(text), 14000)

    def test_handoff_exists(self):
        for name in ('BOOTSTRAP.md', 'README.md', 'docs/CODEX_WORK_ORDER.md', 'evals/SCENARIOS.md'):
            self.assertTrue((REPO / name).exists(), name)


if __name__ == '__main__':
    unittest.main()
