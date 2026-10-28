"""Small, local-only inspection tools. This is not an execution sandbox or grader."""
from __future__ import annotations

import argparse
import ast
import csv
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import stat
import sys
import tempfile
import time

VERSION = '1.0.0'
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 1_024
MAX_CELLS = 2_000_000
MAX_FILES = 500
MAX_ENTRIES = 2_000
MAX_DEPTH = 12
EXIT = {'PASS': 0, 'FAIL': 1, 'UNVERIFIED': 2}
SKIP_DIRS = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', '.ai-task-kit', '.superpowers'}
TEXT_SUFFIXES = {'.md', '.txt', '.html', '.css', '.js', '.ts', '.sql', '.yaml', '.yml', '.toml'}
NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z', re.ASCII)
ISSUE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')


class KitError(Exception):
    def __init__(self, message: str, status: str = 'FAIL'):
        super().__init__(message)
        self.status = status


def result(command: str, status: str, scope: str, summary: str, **details) -> dict:
    return {'schema_version': 1, 'version': VERSION, 'command': command,
            'status': status, 'scope': scope, 'summary': summary, 'details': details}


def task_root(raw: str) -> Path:
    root = Path(raw).resolve(strict=True)
    if not root.is_dir():
        raise KitError('과제 폴더가 아닙니다. --root에 실제 과제 폴더를 지정하세요.')
    return root


def safe_path(root: Path, name: str) -> Path:
    """Require a relative path and reject every existing symlink component."""
    relative = Path(name)
    if (not name or relative.is_absolute() or PureWindowsPath(name).drive
            or '\\' in name or '..' in relative.parts or not relative.parts):
        raise KitError('과제 폴더 안의 상대 경로만 허용합니다. 상위 경로·절대 경로는 사용할 수 없습니다.')
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise KitError('심볼릭 링크는 자동으로 따라가지 않습니다. 실제 과제 파일 경로를 확인하세요.')
    try:
        current.resolve().relative_to(root)
    except ValueError as exc:
        raise KitError('과제 폴더 밖의 경로입니다.') from exc
    return current


def read_bytes(path: Path, limit: int = MAX_BYTES) -> bytes:
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise KitError('일반 파일만 읽을 수 있습니다. 링크·폴더·특수 파일은 제외합니다.')
    if path.stat().st_size > limit:
        raise KitError(f'파일 검사 한도({limit}바이트)를 넘었습니다. 전체 검사는 수행하지 않았습니다.', 'UNVERIFIED')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise KitError('읽기 직전에 파일 종류가 바뀌었습니다.')
        payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise KitError('검사 중 파일 크기 한도를 초과했습니다.', 'UNVERIFIED')
    return payload


def decoded(payload: bytes, encoding: str = 'utf-8-sig') -> str:
    try:
        return payload.decode(encoding, errors='strict')
    except UnicodeError as exc:
        raise KitError('문자 인코딩이 맞지 않습니다. 원본 형식을 확인하고 --encoding을 명시하세요. 자동 변환하지 않았습니다.') from exc


def strict_json(text: str):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise KitError('JSON에 중복 키가 있습니다. 값이 조용히 덮어써지지 않도록 중단했습니다.')
            obj[key] = value
        return obj

    def invalid_constant(_value):
        raise KitError('JSON에 NaN 또는 Infinity가 있습니다. 정상 수치로 처리하지 않습니다.')

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise KitError('JSON 숫자가 유한한 표현 범위를 넘었습니다.')
        # Keep the original decimal value for monetary checks, not the binary float.
        return Decimal(value)

    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid_constant,
                          parse_float=finite_float)
    except (ValueError, RecursionError) as exc:
        raise KitError('JSON 형식 또는 중첩 깊이가 유효하지 않습니다.') from exc



def check_dimensions(rows: int, columns: int):
    if columns > MAX_COLUMNS or rows * columns > MAX_CELLS:
        raise KitError('열 수(1,024) 또는 행×열 검사 한도(2,000,000)를 넘었습니다. 전체 검사를 수행하지 않았습니다.', 'UNVERIFIED')


def fingerprint(value) -> str:
    """Typed identity: JSON numbers 1/1.0 agree, strings never become numbers."""
    def tagged(item):
        if item is None:
            return ['null']
        if isinstance(item, bool):
            return ['bool', item]
        if isinstance(item, (int, Decimal)):
            number = Decimal(item)
            if not number:
                return ['number', 0, [], 0]
            sign, digits, exponent = number.as_tuple()
            digits = list(digits)
            while digits and digits[-1] == 0:
                digits.pop()
                exponent += 1
            return ['number', sign, digits, exponent]
        if isinstance(item, str):
            return ['string', item]
        if isinstance(item, list):
            return ['array', [tagged(x) for x in item]]
        if isinstance(item, dict):
            return ['object', [[k, tagged(item[k])] for k in sorted(item)]]
        raise KitError('비교할 수 없는 데이터 종류입니다.')
    return json.dumps(tagged(value), ensure_ascii=True, separators=(',', ':'))


def table_from(path: Path, encoding: str, delimiter: str) -> tuple[str, list, list, dict]:
    text = decoded(read_bytes(path), encoding)
    if path.suffix.lower() == '.json':
        value = strict_json(text)
        if isinstance(value, dict):
            return 'json-object', [], [], {'keys': list(value), 'rows': None}
        if not isinstance(value, list):
            return 'json-scalar', [], [], {'rows': None}
        if len(value) > MAX_ROWS:
            raise KitError('행 검사 한도(100,000행)를 넘었습니다. 전체 집계 결과가 아닙니다.', 'UNVERIFIED')
        if not value:
            return 'json-table', [], [], {'rows': 0}
        if not all(isinstance(row, dict) for row in value):
            return 'json-array', [], [], {'rows': len(value)}
        columns = list(dict.fromkeys(key for row in value for key in row))
        check_dimensions(len(value), len(columns))
        return 'json-table', columns, value, {'rows': len(value)}
    if path.suffix.lower() != '.csv':
        raise KitError('audit는 CSV 또는 JSON만 검사합니다. 다른 형식은 Codex가 별도로 확인해야 합니다.')
    try:
        reader = csv.reader(io.StringIO(text, newline=''), delimiter=delimiter, strict=True)
        columns = next(reader, None)
        if not columns or any(not column.strip() for column in columns):
            raise KitError('CSV가 비어 있거나 헤더에 빈 열 이름이 있습니다.')
        if len(set(columns)) != len(columns):
            raise KitError('CSV에 중복 열 이름이 있습니다.')
        check_dimensions(0, len(columns))
        rows = []
        for index, values in enumerate(reader, 1):
            if index > MAX_ROWS:
                raise KitError('행 검사 한도(100,000행)를 넘었습니다. 전체 집계 결과가 아닙니다.', 'UNVERIFIED')
            check_dimensions(index, len(columns))
            if len(values) != len(columns):
                raise KitError(f'CSV 데이터 {index}행의 열 수가 헤더와 다릅니다. 빈 행도 임의로 제거하지 않습니다.')
            rows.append(dict(zip(columns, values)))
        return 'csv-table', columns, rows, {'rows': len(rows)}
    except csv.Error as exc:
        raise KitError('CSV 따옴표·구분자·필드 크기 형식을 확인하세요.') from exc


def missing(value) -> bool:
    return value is None or isinstance(value, str) and not value.strip()


def exact_number(value) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise KitError('합계 열에 숫자가 아닌 값이 있습니다. 임의 변환하지 않았습니다.')
    text = str(value).strip()
    if len(text) > 100 or not NUMBER.fullmatch(text):
        raise KitError('합계 열의 숫자 형식이 잘못됐습니다. 쉼표·통화 기호·비유한 값은 자동 변환하지 않습니다.')
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise KitError('숫자를 정확하게 읽을 수 없습니다.') from exc
    if not number.is_finite() or abs(number.adjusted()) > 50:
        raise KitError('검산 가능한 숫자 크기 범위를 벗어났습니다.')
    return number


def doctor(args):
    root = task_root(args.root)
    supported = sys.version_info >= (3, 10)
    installed = {name: importlib.util.find_spec(name) is not None for name in ('pytest', 'pandas', 'openpyxl')}
    return result('doctor', 'PASS' if supported else 'FAIL', 'local_environment',
                  '로컬 도구 상태를 확인했습니다. 플랫폼 사용 허가·호환성은 별도 확인이 필요합니다.',
                  root=str(root), python=sys.version.split()[0], python_supported=supported,
                  available_commands={name: shutil.which(name) is not None for name in ('git', 'node', 'npm', 'codex')},
                  optional_packages=installed, platform_compatibility_verified=False,
                  installs_performed=False, network_requests_performed=False)



def toolkit_root(script: Path) -> Path:
    skill = script.parent.parent
    if skill.parent.name == 'skills' and skill.parent.parent.name == '.agents':
        return skill.parent.parent.parent
    return skill


def inspect_project(args):
    root = task_root(args.root)
    files, skipped, reasons = [], 0, []
    entries = 0
    # Do not mistake this cloned toolkit's files for the actual assessment project.
    own_repo = toolkit_root(Path(__file__).resolve())
    stack = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        try:
            with os.scandir(directory) as listing:
                for entry in listing:
                    entries += 1
                    if entries > MAX_ENTRIES or len(files) >= MAX_FILES:
                        reasons.append('탐색 개수 한도에 도달했습니다.')
                        stack.clear()
                        break
                    p = Path(entry.path)
                    if entry.is_symlink():
                        skipped += 1
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name in SKIP_DIRS or (p.resolve() == own_repo and root != own_repo):
                            skipped += 1
                        elif depth >= MAX_DEPTH:
                            reasons.append('탐색 깊이 한도에 도달했습니다.')
                        else:
                            stack.append((p, depth + 1))
                    elif entry.is_file(follow_symlinks=False):
                        if entry.name == '.env' or entry.name.startswith('.env.') or p.suffix.lower() in {'.pem', '.key'}:
                            skipped += 1
                        else:
                            files.append(p.relative_to(root).as_posix())
                    else:
                        skipped += 1
        except OSError:
            reasons.append('읽을 수 없는 하위 폴더가 있습니다.')
    files.sort()
    suffixes = {Path(name).suffix.lower() for name in files}
    hints = []
    for hint, extensions in (('python', {'.py'}), ('javascript', {'.js', '.ts', '.tsx', '.jsx'}),
                             ('web', {'.html', '.css'}), ('data', {'.csv', '.json', '.xlsx'}),
                             ('sql', {'.sql', '.sqlite', '.db'}), ('documents', {'.md', '.txt', '.pdf'})):
        if suffixes & extensions:
            hints.append(hint)
    return result('inspect', 'UNVERIFIED' if reasons else 'PASS', 'file_inventory_only',
                  '파일 목록과 유형 후보입니다. 과제 요구사항은 README 원문을 읽고 판단해야 합니다.',
                  root=str(root), files=files, task_hints=hints,
                  readme_candidates=[name for name in files if Path(name).name.lower().startswith('readme')],
                  skipped=skipped, truncated=bool(reasons), limitations=sorted(set(reasons)))


def audit(args):
    root = task_root(args.root)
    path = safe_path(root, args.file)
    kind, columns, rows, meta = table_from(path, args.encoding, args.delimiter)
    requested = set(args.require_column or []) | set(filter(None, (args.column, args.unique, args.date_column)))
    findings = []
    unverified = False
    details = {'file': args.file, 'kind': kind, 'columns': columns, **meta,
               'encoding': args.encoding, 'delimiter': args.delimiter if kind.startswith('csv') else None}
    if args.expect_sum is not None and not args.column:
        raise KitError('--expect-sum을 쓰려면 --column을 함께 지정하세요.')
    absent = sorted(requested - set(columns))
    if absent:
        findings.append('필요한 열을 찾지 못했습니다: ' + ', '.join(absent))
    if args.expect_rows is not None and meta['rows'] != args.expect_rows:
        findings.append('행 수가 기대값과 다릅니다.')
    if kind not in {'csv-table', 'json-table'}:
        return result('audit', 'FAIL' if findings else 'PASS', 'data_structure_only',
                      'JSON 형식을 검사했습니다. 표 데이터로 해석하지 않았습니다.', **details, findings=findings)
    nulls = {column: sum(missing(row.get(column)) for row in rows) for column in columns}
    seen = set()
    duplicates = 0
    for row in rows:
        identity = fingerprint(row)
        duplicates += identity in seen
        seen.add(identity)
    details.update(missing=nulls, duplicate_rows=duplicates)
    if args.unique in columns:
        keys = [fingerprint(row.get(args.unique)) for row in rows]
        if nulls[args.unique] or len(set(keys)) != len(keys):
            findings.append('고유값이어야 하는 열에 빈 값 또는 중복이 있습니다.')
    if args.date_column in columns:
        bad_dates = 0
        for row in rows:
            value = row.get(args.date_column)
            try:
                if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value, flags=re.ASCII):
                    raise ValueError
                date.fromisoformat(value)
            except ValueError:
                bad_dates += 1
        details['invalid_dates'] = bad_dates
        if bad_dates:
            findings.append('날짜 열에 비어 있거나 유효한 YYYY-MM-DD가 아닌 값이 있습니다.')
    if args.column in columns:
        excluded = nulls[args.column]
        details['excluded_missing'] = excluded
        if excluded == len(rows):
            unverified = True
            details['numeric_values_verified'] = 0
        if excluded and not args.allow_missing:
            findings.append('합계 열에 빈 값이 있습니다. 임의로 0 처리하지 않았습니다.')
        else:
            try:
                with localcontext() as ctx:
                    ctx.prec = 220
                    total = sum((exact_number(row.get(args.column)) for row in rows
                                 if not missing(row.get(args.column))), Decimal(0))
                    details['sum'] = str(total)
                    if args.expect_sum is not None and total != exact_number(args.expect_sum):
                        findings.append('합계가 기대값과 다릅니다.')
            except KitError as exc:
                findings.append(str(exc))
    state = 'FAIL' if findings else 'UNVERIFIED' if not rows or unverified else 'PASS'
    return result('audit', state, 'data_checks_only',
                  '지정한 데이터 조건의 검사 결과입니다. 업무 해석의 정확성까지 증명하지는 않습니다.',
                  **details, findings=findings)


def verify(args):
    root = task_root(args.root)
    checks = []
    for name in dict.fromkeys(args.require or []):
        try:
            path = safe_path(root, name)
            payload = read_bytes(path)
            if not payload or not payload.strip():
                raise KitError('파일 내용이 비어 있습니다.')
            ext = path.suffix.lower()
            checked = '비어 있지 않은 파일'
            if ext == '.py':
                try:
                    ast.parse(payload, filename=name)
                except (SyntaxError, ValueError, RecursionError) as exc:
                    raise KitError('Python 문법 검사에 실패했습니다. 파일을 실행하지는 않았습니다.') from exc
                checked = 'Python 문법만 검사 (실행하지 않음)'
            elif ext == '.json':
                strict_json(decoded(payload))
                checked = 'JSON 형식만 검사'
            elif ext == '.csv':
                table_from(path, 'utf-8-sig', ',')
                checked = 'UTF-8·쉼표 CSV 구조만 검사'
            elif ext in TEXT_SUFFIXES:
                decoded(payload)
                checked = 'UTF-8 텍스트 존재만 검사'
            checks.append({'file': name, 'status': 'PASS', 'check': checked,
                           'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()})
        except (KitError, OSError) as exc:
            checks.append({'file': name, 'status': getattr(exc, 'status', 'FAIL'),
                           'check': str(exc) if isinstance(exc, KitError) else '파일을 읽을 수 없습니다.'})
    state = 'FAIL' if any(c['status'] == 'FAIL' for c in checks) else 'UNVERIFIED'
    return result('verify', state, 'submission_preflight_only',
                  '제출 전 형식 검사입니다. 실제 기능 검증과 최종 제출 확인은 별도입니다.',
                  checks=checks, functional_status='UNVERIFIED', submitted=False,
                  next_action='Codex가 승인된 실행 도구로 요구사항별 테스트를 수행하고 근거를 확인하세요.')


def explain(args):
    text = decoded(read_bytes(safe_path(task_root(args.root), args.file)))
    guidance = (
        ('KeyError', '예상한 항목 이름을 찾지 못했을 수 있습니다.', '실제 열 이름·JSON 키와 실패 위치를 비교하세요. 누락값을 0으로 바꿔 숨기지 마세요.'),
        ('ModuleNotFoundError', '현재 실행 환경에 필요한 패키지가 없을 수 있습니다.', '프로젝트 지정 환경과 설치 여부를 확인하세요. 무조건 설치하지 말고 허용된 대안을 검토하세요.'),
        ('FileNotFoundError', '입력 파일 또는 실행 위치가 다를 수 있습니다.', '과제 루트와 실제 파일 이름을 확인하세요. 빈 대체 파일을 만들지 마세요.'),
        ('PermissionError', '파일 접근 또는 실행 권한이 제한되었을 수 있습니다.', '플랫폼 권한을 확인하세요. 권한 상승·감독 우회는 하지 마세요.'),
        ('SyntaxError', '코드 문법이 맞지 않을 수 있습니다.', '표시된 위치와 바로 앞 줄을 확인하고 최소 변경 후 다시 검사하세요.'),
        ('TypeError', '값의 종류나 함수 사용 방식이 맞지 않을 수 있습니다.', '실제 입력 종류와 함수가 요구하는 형식을 확인하세요.'),
        ('Timeout', '작업이 제한시간 안에 끝나지 않았을 수 있습니다.', '무한 반복·대용량 처리·승인 대기를 구분하세요. 같은 요청을 반복하지 마세요.'),
    )
    category, cause, action = next((entry for entry in guidance if entry[0] in text),
                                   ('UNKNOWN', '이 기록만으로 원인을 확정할 수 없습니다.', '실패한 명령·종료 코드·관련 위치를 플랫폼 안에서 확인하세요.'))
    return result('explain', 'UNVERIFIED', 'error_hint_not_diagnosis', '가능한 원인과 확인 순서입니다. 원인이 확정된 것은 아닙니다.',
                  category=category, possible_cause=cause, recommended_action=action,
                  user_checkpoint='기술 수정이 업무 규칙·입력 제외·계산 기준을 바꾸면 먼저 확인하세요.')


def state_path(root: Path) -> Path:
    return safe_path(root, '.ai-task-kit/session.json')


def load_state(root: Path) -> tuple[Path, dict]:
    path = state_path(root)
    if not path.exists():
        raise KitError('세션 기록이 없습니다. 공식 남은 시간을 확인한 뒤 session start로 시작하세요.', 'UNVERIFIED')
    s = strict_json(decoded(read_bytes(path, 32_768)))
    fields = {'schema_version', 'root', 'started_at', 'minutes', 'reserve', 'attempts'}
    if not isinstance(s, dict) or set(s) != fields or s['schema_version'] != 1 or s['root'] != str(root):
        raise KitError('세션 기록의 형식 또는 과제 폴더가 맞지 않습니다. 자동 초기화하지 않았습니다.')
    for key in ('started_at', 'minutes', 'reserve'):
        if isinstance(s[key], bool) or not isinstance(s[key], (int, Decimal)) or not math.isfinite(float(s[key])):
            raise KitError('세션 시간 값이 유효하지 않습니다.')
    if not (s['started_at'] >= 0 and 0 < s['minutes'] <= 1440 and 0 <= s['reserve'] < s['minutes']):
        raise KitError('세션 시간 범위가 유효하지 않습니다.')
    if not isinstance(s['attempts'], dict) or any(not ISSUE.fullmatch(k) or type(v) is not int or v < 0 for k, v in s['attempts'].items()):
        raise KitError('오류 재시도 기록이 유효하지 않습니다.')
    return path, s


def write_state(path: Path, state: dict, initial: bool = False):
    """Own state only; refuse symlinks and never replace an existing initial session."""
    if path.parent.is_symlink() or path.is_symlink():
        raise KitError('세션 저장 경로에 링크가 있습니다. 저장하지 않았습니다.')
    path.parent.mkdir(exist_ok=True)
    payload = json.dumps(state, ensure_ascii=False, indent=2, allow_nan=False, default=float) + '\n'
    if len(payload.encode('utf-8')) > 32_768:
        raise KitError('세션 기록 크기 한도에 도달했습니다. 추가 저장을 중단합니다.')
    if initial:
        try:
            with path.open('x', encoding='utf-8') as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise KitError('기존 세션이 있습니다. 시작 시간을 초기화하지 않습니다. session status로 이어가세요.') from exc
    else:
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             prefix='.session-', suffix='.tmp', delete=False) as stream:
                temp_name = stream.name
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name and os.path.exists(temp_name):
                os.unlink(temp_name)


def session(args):
    root = task_root(args.root)
    if args.action == 'start':
        if not 0 < args.minutes <= 1440 or not 0 <= args.reserve < args.minutes:
            raise KitError('남은 시간은 1~1440분, 제출 여유 시간은 남은 시간보다 작아야 합니다.')
        s = {'schema_version': 1, 'root': str(root), 'started_at': time.time(),
             'minutes': args.minutes, 'reserve': args.reserve, 'attempts': {}}
        write_state(state_path(root), s, initial=True)
        return result('session', 'PASS', 'local_timer_estimate', '로컬 시간 추정을 시작했습니다. 공식 타이머가 우선입니다.',
                      remaining_minutes=args.minutes, reserve_minutes=args.reserve, official_timer=False)
    path, s = load_state(root)
    if args.action == 'attempt':
        if not args.issue or not ISSUE.fullmatch(args.issue):
            raise KitError('--issue에는 영문·숫자·하이픈·밑줄의 짧은 이슈 이름을 사용하세요.')
        count = s['attempts'].get(args.issue, 0) + 1
        s['attempts'][args.issue] = count
        write_state(path, s)
        return result('session', 'UNVERIFIED' if count >= 2 else 'PASS', 'recovery_budget_only',
                      '같은 이슈가 2회 이상 실패했습니다. 증거·가설을 바꾸거나 단순한 대안으로 전환하세요.' if count >= 2 else '실패 1회를 기록했습니다. 원인을 확인하고 최소 변경으로 재검증하세요.',
                      attempts=count, action='CHANGE_STRATEGY' if count >= 2 else 'INVESTIGATE',
                      limit_is_advisory=True)
    elapsed = time.time() - float(s['started_at'])
    if elapsed < 0:
        return result('session', 'UNVERIFIED', 'local_timer_estimate',
                      '시계가 뒤로 이동했습니다. 남은 시간을 추정하지 않습니다. 공식 타이머를 확인하세요.',
                      remaining_minutes=None, mode='CHECK_OFFICIAL_TIMER')
    remaining = max(0.0, float(s['minutes']) - elapsed / 60)
    mode = 'STOP' if remaining <= 0 else 'VERIFY_AND_SUBMIT' if remaining <= s['reserve'] else 'IMPLEMENT'
    return result('session', 'PASS', 'local_timer_estimate', '로컬 추정치입니다. 공식 타이머와 다르면 공식 시간을 따르세요.',
                  remaining_minutes=round(remaining, 2), reserve_minutes=s['reserve'], mode=mode,
                  official_timer=False)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise KitError('명령 사용법을 확인하세요: ' + message)


def parser():
    p = Parser(description='AI Task Kit: 승인된 과제 폴더의 로컬 검사만 수행합니다.')
    p.add_argument('--version', action='version', version=VERSION)
    sub = p.add_subparsers(dest='command', required=True)
    for name, help_text in (('doctor', '실행 환경 확인'), ('inspect', '파일 목록·과제 유형 후보'),
                            ('audit', 'CSV/JSON 검사'), ('verify', '필수 제출물 형식 확인'),
                            ('explain', '오류 기록 해석 힌트')):
        child = sub.add_parser(name, help=help_text)
        child.add_argument('--root', required=True, help='실제 과제 폴더, 도구 폴더와 구분')
        child.add_argument('--json', action='store_true', help='구조화된 JSON 결과')
        if name in {'audit', 'explain'}:
            child.add_argument('--file', required=True, help='과제 루트 기준 상대 경로')
        if name == 'audit':
            child.add_argument('--encoding', choices=('utf-8-sig', 'utf-8', 'cp949', 'utf-16'), default='utf-8-sig')
            child.add_argument('--delimiter', choices=(',', ';', '\t', '|'), default=',')
            child.add_argument('--column')
            child.add_argument('--expect-sum')
            child.add_argument('--expect-rows', type=int)
            child.add_argument('--allow-missing', action='store_true')
            child.add_argument('--require-column', action='append')
            child.add_argument('--unique')
            child.add_argument('--date-column')
        if name == 'verify':
            child.add_argument('--require', action='append', help='반복 지정 가능. 과제에서 실제 요구한 파일만 지정')
    s = sub.add_parser('session', help='로컬 시간·재시도 기록')
    actions = s.add_subparsers(dest='action', required=True)
    for action in ('start', 'status', 'attempt'):
        child = actions.add_parser(action)
        child.add_argument('--root', required=True)
        child.add_argument('--json', action='store_true')
        if action == 'start':
            child.add_argument('--minutes', type=int, required=True, help='공식 타이머에 표시된 현재 남은 분')
            child.add_argument('--reserve', type=int, default=15, help='검증·제출 확보 시간 (프로젝트 권장값)')
        if action == 'attempt':
            child.add_argument('--issue', required=True)
    return p


def emit(report: dict, as_json: bool):
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False, default=float))
    else:
        print(f"[{report['status']}] {report['summary']}")
        print(f"검사 범위: {report['scope']}")
        details = dict(report['details'])
        if isinstance(details.get('files'), list) and len(details['files']) > 30:
            details['files'] = details['files'][:30] + ['… 전체 목록은 --json으로 확인']
        rendered = json.dumps(details, ensure_ascii=False, indent=2, allow_nan=False, default=float)
        # Never print raw terminal control codes from file names or column labels.
        print(rendered)
        print('PASS는 위 검사 범위만 의미합니다. 과제 전체 성공·제출 완료를 뜻하지 않습니다.')


def main(argv=None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    as_json = '--json' in raw
    try:
        args = parser().parse_args(raw)
        functions = {'doctor': doctor, 'inspect': inspect_project, 'audit': audit,
                     'verify': verify, 'explain': explain, 'session': session}
        report = functions[args.command](args)
    except KitError as exc:
        report = result('error', exc.status, 'requested_operation', str(exc))
    except (OSError, ValueError, TypeError, RecursionError, OverflowError) as exc:
        report = result('error', 'FAIL', 'requested_operation',
                        '입력·경로·권한 또는 자료 형식을 확인하세요. 자동으로 원본을 수정하지 않았습니다.',
                        error_type=type(exc).__name__)
    emit(report, as_json)
    return EXIT[report['status']]


if __name__ == '__main__':
    raise SystemExit(main())
