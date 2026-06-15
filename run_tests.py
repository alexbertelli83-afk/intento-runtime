from pathlib import Path
from tempfile import TemporaryDirectory

from intento_runtime.runtime import run_source
from intento_runtime.errors import (
    IntentoError,
    IntentoSyntaxError,
    IntentoTypeError,
    IntentoSafetyError,
    IntentoFileError,
    IntentoLibraryError,
    IntentoActionError,
    IntentoSemanticError,
    IntentoModuleError,
    IntentoProjectError,
    IntentoDateError,
    IntentoJSONError,
    IntentoCSVError,
    IntentoConversionError,
)

CASES = [
    ('show text', 'show "Hello"', ['Hello']),
    ('memory', 'remember name as "Aurora"\nshow "Hello " plus name', ['Hello Aurora']),
    ('arithmetic', 'show 2 plus 3 times 4\nshow (2 plus 3) times 4', ['14', '20']),
    ('symbols', 'show 10 + 5\nshow 10 * 5', ['15', '50']),
    ('values', 'show true\nshow empty\nshow ["A", "B"]', ['true', '', '["A", "B"]']),
    ('convert values', 'remember age_text as "42"\nconvert age_text to number and call it age\nshow age plus 1\nremember active_text as "true"\nconvert active_text to boolean and call it active\nshow active\nconvert age to text and call it age_label\nshow "Age: " plus age_label', ['43', 'true', 'Age: 42']),
    ('if true branch', 'remember name as "Aurora"\nif name is "Aurora":\n    show "Correct"\nelse:\n    show "Wrong"', ['Correct']),
    ('if else branch', 'remember name as "Ada"\nif name is "Aurora":\n    show "Correct"\nelse:\n    show "Wrong"', ['Wrong']),
    ('if empty and stop', 'remember name as empty\nif name is empty:\n    show "Name is required"\n    stop\nshow "No"', ['Name is required']),
    ('comparisons', 'remember age as 20\nif age is at least 18:\n    show "Access allowed"\nelse:\n    show "Access denied"', ['Access allowed']),
    ('repeat', 'remember counter as 0\nrepeat 3 times:\n    remember counter as counter plus 1\n    show counter', ['1', '2', '3']),
    ('for each', 'remember skills as ["Linux", "Python", "INTENTO"]\nfor each skill in skills:\n    show skill', ['Linux', 'Python', 'INTENTO']),
]

ERROR_CASES = [
    ('else without if', 'else:\n    show "No condition"', IntentoSyntaxError),
    ('bad indentation', 'show "Start"\n    show "Bad indentation"', IntentoSyntaxError),
    ('repeat text', 'repeat "3" times:\n    show "Hello"', IntentoTypeError),
    ('for each text', 'remember skills as "Linux"\nfor each skill in skills:\n    show skill', IntentoTypeError),
    ('bad number conversion', 'remember value as "forty-two"\nconvert value to number and call it number_value', IntentoConversionError),
    ('bad boolean conversion', 'remember value as "yes"\nconvert value to boolean and call it flag', IntentoConversionError),
]


def run_memory_tests() -> int:
    failed = 0
    for name, source, expected in CASES:
        try:
            result = run_source(source, input_func=lambda q: 'Aurora')
            if result.output != expected:
                failed += 1
                print(f'FAIL {name}: expected {expected}, got {result.output}')
            else:
                print(f'OK   {name}')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL {name}: {exc}')
    for name, source, error_type in ERROR_CASES:
        try:
            run_source(source, input_func=lambda q: 'Aurora')
        except error_type:
            print(f'OK   {name}')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL {name}: expected {error_type.__name__}, got {type(exc).__name__}: {exc}')
        else:
            failed += 1
            print(f'FAIL {name}: expected {error_type.__name__}')
    return failed


def run_file_tests() -> int:
    failed = 0
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        data = workspace / 'notes.txt'
        data.write_text('Hello from file', encoding='utf-8')

        file_cases = [
            ('read file', 'read file "notes.txt" and call it notes\nshow notes', ['Hello from file']),
            ('create folder and file', 'with confirmation:\n    create folder "project"\n    create file "project/README.txt" with "# Demo"\nshow "done"', ['done']),
            ('append file', 'with confirmation:\n    append to file "notes.txt" with "!"\nread file "notes.txt" and call it notes\nshow notes', ['Hello from file!']),
            ('dry-run write', 'with confirmation:\n    create folder "dry"\n    create file "dry/README.txt" with "# Dry"\nshow "finished"', ['DRY RUN: would create folder dry', 'DRY RUN: would create file dry/README.txt', 'finished']),
        ]
        for name, source, expected in file_cases:
            try:
                result = run_source(source, workspace=workspace, confirm_func=lambda desc: True, dry_run=(name == 'dry-run write'))
                if result.output != expected:
                    failed += 1
                    print(f'FAIL {name}: expected {expected}, got {result.output}')
                else:
                    print(f'OK   {name}')
            except IntentoError as exc:
                failed += 1
                print(f'FAIL {name}: {exc}')

        if not (workspace / 'project' / 'README.txt').exists():
            failed += 1
            print('FAIL create file effect: README.txt was not created')
        elif (workspace / 'project' / 'README.txt').read_text(encoding='utf-8') != '# Demo':
            failed += 1
            print('FAIL create file effect: wrong README.txt content')
        else:
            print('OK   create file effect')

        if (workspace / 'dry').exists():
            failed += 1
            print('FAIL dry-run effect: dry folder should not exist')
        else:
            print('OK   dry-run effect')

        file_errors = [
            ('write without confirmation', 'create folder "unsafe"', IntentoSafetyError),
            ('outside workspace', 'read file "../outside.txt" and call it data', IntentoSafetyError),
            ('missing file', 'read file "missing.txt" and call it data', IntentoFileError),
            ('create existing file', 'with confirmation:\n    create file "notes.txt" with "replacement"', IntentoFileError),
        ]
        for name, source, error_type in file_errors:
            try:
                run_source(source, workspace=workspace, confirm_func=lambda desc: True)
            except error_type:
                print(f'OK   {name}')
            except IntentoError as exc:
                failed += 1
                print(f'FAIL {name}: expected {error_type.__name__}, got {type(exc).__name__}: {exc}')
            else:
                failed += 1
                print(f'FAIL {name}: expected {error_type.__name__}')
    return failed



def run_stdlib_tests() -> int:
    failed = 0
    stdlib_cases = [
        (
            'text library actions',
            'use library "text"\nremember title as "  Human Readable Code  "\nuse action "text.trim" with title and call the result clean_title\nuse action "text.slugify" with clean_title and call the result slug\nuse action "text.count_words" with clean_title and call the result words\nshow clean_title\nshow slug\nshow words',
            ['Human Readable Code', 'human-readable-code', '3'],
        ),
        (
            'number library actions',
            'use library "number"\nremember value as -12\nuse action "number.absolute" with value and call the result positive\nuse action "number.round" with 12.7 and call the result rounded\nuse action "number.minimum" with 10 and 5 and call the result smaller\nuse action "number.maximum" with 10 and 5 and call the result larger\nshow positive\nshow rounded\nshow smaller\nshow larger',
            ['12', '13', '5', '10'],
        ),
        (
            'list library actions',
            'use library "list"\nremember skills as ["Linux", "Python", "INTENTO"]\nuse action "list.count" with skills and call the result total\nuse action "list.join" with skills and ", " and call the result joined\nuse action "list.contains" with skills and "Python" and call the result has_python\nuse action "list.first" with skills and call the result first\nuse action "list.last" with skills and call the result last\nshow total\nshow joined\nshow has_python\nshow first\nshow last',
            ['3', 'Linux, Python, INTENTO', 'true', 'Linux', 'INTENTO'],
        ),
        (
            'describe action',
            'describe action "text.slugify"',
            ['Action: text.slugify', 'Accepts: text', 'Returns: text', 'Safety: safe', 'Description: Converts text into a lowercase URL-safe slug.'],
        ),
    ]
    for name, source, expected in stdlib_cases:
        try:
            result = run_source(source)
            if result.output != expected:
                failed += 1
                print(f'FAIL {name}: expected {expected}, got {result.output}')
            else:
                print(f'OK   {name}')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL {name}: {exc}')

    with TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        (workspace / 'notes.txt').write_text('Hello', encoding='utf-8')
        file_source = 'use library "file"\nuse action "file.exists" with "notes.txt" and call the result exists\nuse action "file.name" with "notes.txt" and call the result file_name\nuse action "file.extension" with "notes.txt" and call the result extension\nshow exists\nshow file_name\nshow extension'
        try:
            result = run_source(file_source, workspace=workspace)
            expected = ['true', 'notes.txt', 'txt']
            if result.output != expected:
                failed += 1
                print(f'FAIL file library actions: expected {expected}, got {result.output}')
            else:
                print('OK   file library actions')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL file library actions: {exc}')

    try:
        result = run_source('use library "log"\nuse action "log.info" with "Program started"\nshow "Done"')
        if result.output != ['Done'] or result.logs != ['INFO Program started']:
            failed += 1
            print(f'FAIL log library action: output={result.output}, logs={result.logs}')
        else:
            print('OK   log library action')
    except IntentoError as exc:
        failed += 1
        print(f'FAIL log library action: {exc}')

    stdlib_errors = [
        ('unknown library', 'use library "unknown"', IntentoLibraryError),
        ('action without library', 'use action "text.slugify" with "Hello" and call the result slug', IntentoLibraryError),
        ('unknown action', 'use library "text"\nuse action "text.unknown" with "Hello" and call the result value', IntentoSemanticError),
        ('wrong action type', 'use library "text"\nuse action "text.count_words" with 42 and call the result count', IntentoTypeError),
        ('no-return action result', 'use library "log"\nuse action "log.info" with "Hello" and call the result value', IntentoActionError),
    ]
    for name, source, error_type in stdlib_errors:
        try:
            run_source(source)
        except error_type:
            print(f'OK   {name}')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL {name}: expected {error_type.__name__}, got {type(exc).__name__}: {exc}')
        else:
            failed += 1
            print(f'FAIL {name}: expected {error_type.__name__}')
    return failed




def run_richer_stdlib_tests() -> int:
    failed = 0
    richer_cases = [
        (
            'date library actions',
            'use library "date"\nremember raw_date as "2026-06-13"\nuse action "date.format" with raw_date and "long" and call the result long_date\nuse action "date.add_days" with raw_date and 7 and call the result next_week\nshow long_date\nshow next_week',
            ['June 13, 2026', '2026-06-20'],
        ),
        (
            'json library actions',
            'use library "json"\nremember data as "{\\"name\\":\\"Aurora\\",\\"language\\":\\"INTENTO\\"}"\nuse action "json.get" with data and "name" and call the result name\nuse action "json.has_key" with data and "language" and call the result has_language\nshow name\nshow has_language',
            ['Aurora', 'true'],
        ),
        (
            'csv library actions',
            'use library "csv"\nremember rows as "name,role\\nAda,mathematician\\nGrace,computer scientist"\nuse action "csv.count_rows" with rows and call the result count\nuse action "csv.get_column" with rows and "name" and call the result names\nshow count\nshow names',
            ['2', '["Ada", "Grace"]'],
        ),
    ]
    for name, source, expected in richer_cases:
        try:
            result = run_source(source)
            if result.output != expected:
                failed += 1
                print(f'FAIL {name}: expected {expected}, got {result.output}')
            else:
                print(f'OK   {name}')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL {name}: {exc}')

    richer_errors = [
        ('bad date', 'use library "date"\nuse action "date.format" with "not-a-date" and "long" and call the result value', IntentoDateError),
        ('bad json', 'use library "json"\nuse action "json.get" with "{bad json}" and "name" and call the result value', IntentoJSONError),
        ('missing json key', 'use library "json"\nremember data as "{\\"name\\":\\"Aurora\\"}"\nuse action "json.get" with data and "language" and call the result value', IntentoJSONError),
        ('bad csv column', 'use library "csv"\nremember rows as "name,role\\nAda,mathematician"\nuse action "csv.get_column" with rows and "age" and call the result ages', IntentoCSVError),
    ]
    for name, source, error_type in richer_errors:
        try:
            run_source(source)
        except error_type:
            print(f'OK   {name}')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL {name}: expected {error_type.__name__}, got {type(exc).__name__}: {exc}')
        else:
            failed += 1
            print(f'FAIL {name}: expected {error_type.__name__}')
    return failed

def run_module_project_tests() -> int:
    failed = 0
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        modules = workspace / 'modules'
        modules.mkdir()
        (modules / 'formatting.intento').write_text('to show_title with title:\n    show "== " plus title plus " =="\n', encoding='utf-8')
        module_cases = [
            (
                'custom action',
                'to greet with name:\n    show "Hello " plus name\n\ngreet with "Aurora"',
                ['Hello Aurora'],
            ),
            (
                'module basic',
                'use module "modules/formatting.intento"\nshow_title with "INTENTO"',
                ['== INTENTO =='],
            ),
            (
                'module alias',
                'use module "modules/formatting.intento" as formatting\nformatting.show_title with "INTENTO"',
                ['== INTENTO =='],
            ),
        ]
        for name, source, expected in module_cases:
            try:
                result = run_source(source, workspace=workspace)
                if result.output != expected:
                    failed += 1
                    print(f'FAIL {name}: expected {expected}, got {result.output}')
                else:
                    print(f'OK   {name}')
            except IntentoError as exc:
                failed += 1
                print(f'FAIL {name}: {exc}')

        (modules / 'bad_module.intento').write_text('show "Loaded"\n\nto greet:\n    show "Hello"\n', encoding='utf-8')
        module_errors = [
            ('module top-level executable', 'use module "modules/bad_module.intento"', IntentoModuleError),
            ('unknown custom action', 'missing_action', IntentoSemanticError),
        ]
        for name, source, error_type in module_errors:
            try:
                run_source(source, workspace=workspace)
            except error_type:
                print(f'OK   {name}')
            except IntentoError as exc:
                failed += 1
                print(f'FAIL {name}: expected {error_type.__name__}, got {type(exc).__name__}: {exc}')
            else:
                failed += 1
                print(f'FAIL {name}: expected {error_type.__name__}')

    # Project format test through the project resolver.
    from intento_runtime.project import resolve_target, read_source
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / 'demo_project'
        (root / 'modules').mkdir(parents=True)
        (root / 'intento.project').write_text(
            'runtime: INTENTO 1.0\nentry: main.intento\nlibraries: text\npermissions: read project files, write project files with confirmation\nfeatures: modules\n',
            encoding='utf-8',
        )
        (root / 'modules' / 'formatting.intento').write_text('to show_title with title:\n    show "== " plus title plus " =="\n', encoding='utf-8')
        (root / 'main.intento').write_text(
            'use library "text"\nuse module "modules/formatting.intento" as formatting\nremember title as "Project Demo"\nuse action "text.slugify" with title and call the result slug\nformatting.show_title with title\nshow slug\n',
            encoding='utf-8',
        )
        try:
            source_path, workspace, project = resolve_target(root)
            result = run_source(read_source(source_path), workspace=workspace)
            expected = ['== Project Demo ==', 'project-demo']
            if result.output != expected:
                failed += 1
                print(f'FAIL project format: expected {expected}, got {result.output}')
            else:
                print('OK   project format')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL project format: {exc}')
    return failed


def run_dev_polish_tests() -> int:
    failed = 0
    try:
        result = run_source('use library "text"\nremember title as "Human Readable Code"\nuse action "text.slugify" with title and call the result slug\nshow slug', trace=True)
        expected_output = ['human-readable-code']
        expected_fragments = ['TRACE line 1: UseLibrary', 'TRACE line 2: Remember', 'TRACE line 3: UseAction', 'TRACE line 4: Show']
        if result.output != expected_output:
            failed += 1
            print(f'FAIL trace output: expected {expected_output}, got {result.output}')
        elif not all(fragment in result.logs for fragment in expected_fragments):
            failed += 1
            print(f'FAIL trace logs: missing trace entries in {result.logs}')
        else:
            print('OK   trace logs')
    except IntentoError as exc:
        failed += 1
        print(f'FAIL trace logs: {exc}')
    return failed



def run_intentotest_tests() -> int:
    from intento_runtime.testrunner import run_intento_tests
    failed = 0
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / 'hello.intento').write_text('show "Hello from test"\n', encoding='utf-8')
        (root / 'hello.intentotest').write_text(
            'name: hello intentotest\nprogram: hello.intento\nexpect output:\nHello from test\nend\n',
            encoding='utf-8',
        )
        (root / 'bad.intento').write_text('show missing_value\n', encoding='utf-8')
        (root / 'bad.intentotest').write_text(
            'name: error intentotest\nprogram: bad.intento\nexpect error:\nSemantic error on line 1: unknown name `missing_value`\nend\n',
            encoding='utf-8',
        )
        try:
            report = run_intento_tests(root)
            names = {result.name: result.passed for result in report.results}
            if not report.passed or names.get('hello intentotest') is not True or names.get('error intentotest') is not True:
                failed += 1
                print(f'FAIL intentotest runner: {report.results}')
            else:
                print('OK   intentotest runner')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL intentotest runner: {exc}')
    return failed


def run_project_init_package_tests() -> int:
    from zipfile import ZipFile
    from intento_runtime.project import init_project, package_project, resolve_target, read_source
    failed = 0
    with TemporaryDirectory() as tmp:
        root = Path(tmp) / 'aurora_demo'
        try:
            init_project(root)
            required = [
                root / 'main.intento',
                root / 'intento.project',
                root / 'README.md',
                root / 'modules' / 'formatting.intento',
                root / 'tests' / 'intentotests' / 'project.intentotest',
            ]
            missing = [str(path.relative_to(root)) for path in required if not path.exists()]
            if missing:
                failed += 1
                print(f'FAIL project init: missing {missing}')
            else:
                source_path, workspace, project = resolve_target(root)
                result = run_source(read_source(source_path), workspace=workspace)
                expected = ['== Aurora Demo ==', 'aurora-demo']
                if result.output != expected:
                    failed += 1
                    print(f'FAIL project init run: expected {expected}, got {result.output}')
                else:
                    print('OK   project init')

            zip_path, count = package_project(root, Path(tmp) / 'aurora_demo.zip')
            with ZipFile(zip_path) as zf:
                names = set(zf.namelist())
            expected_names = {
                'aurora_demo/main.intento',
                'aurora_demo/intento.project',
                'aurora_demo/README.md',
                'aurora_demo/modules/formatting.intento',
                'aurora_demo/tests/intentotests/project.intentotest',
            }
            if count < len(expected_names) or not expected_names.issubset(names):
                failed += 1
                print(f'FAIL project package: missing {sorted(expected_names - names)}')
            else:
                print('OK   project package')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL project init/package: {exc}')
    return failed



def run_python_actions_tests() -> int:
    failed = 0
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        actions_dir = workspace / 'actions'
        actions_dir.mkdir()
        (actions_dir / 'intento_actions.py').write_text(
            'def clean_title(value):\n'
            '    return value.strip().replace("!!!", "").strip()\n\n'
            'def count_letters(value):\n'
            '    return len(value.replace(" ", ""))\n\n'
            'ACTIONS = {\n'
            '    "local.clean_title": {\n'
            '        "accepts": ["text"],\n'
            '        "returns": "text",\n'
            '        "safety": "project-python",\n'
            '        "description": "Cleans a project title.",\n'
            '        "function": clean_title,\n'
            '    },\n'
            '    "local.count_letters": {\n'
            '        "accepts": ["text"],\n'
            '        "returns": "number",\n'
            '        "safety": "project-python",\n'
            '        "description": "Counts letters except spaces.",\n'
            '        "function": "count_letters",\n'
            '    },\n'
            '}\n',
            encoding='utf-8',
        )
        source = (
            'use library "local"\n'
            'remember title as "  INTENTO Runtime v1.1 !!!  "\n'
            'use action "local.clean_title" with title and call the result clean\n'
            'use action "local.count_letters" with clean and call the result letters\n'
            'show clean\n'
            'show letters\n'
        )
        try:
            result = run_source(source, workspace=workspace, allow_python_actions=True)
            expected = ['INTENTO Runtime v1.1', '18']
            if result.output != expected:
                failed += 1
                print(f'FAIL python actions: expected {expected}, got {result.output}')
            else:
                print('OK   python actions')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL python actions: {exc}')

        try:
            run_source('use library "local"', workspace=workspace)
        except IntentoLibraryError:
            print('OK   python actions require explicit flag')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL python actions flag: expected IntentoLibraryError, got {type(exc).__name__}: {exc}')
        else:
            failed += 1
            print('FAIL python actions flag: expected IntentoLibraryError')

    with TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        actions_dir = workspace / 'actions'
        actions_dir.mkdir()
        (actions_dir / 'intento_actions.py').write_text(
            'import os\n\n'
            'def bad(value):\n'
            '    return value\n\n'
            'ACTIONS = {"local.bad": {"accepts": ["text"], "returns": "text", "function": bad}}\n',
            encoding='utf-8',
        )
        try:
            run_source('use library "local"', workspace=workspace, allow_python_actions=True)
        except IntentoSafetyError:
            print('OK   python actions blocked forbidden import')
        except IntentoError as exc:
            failed += 1
            print(f'FAIL python actions safety: expected IntentoSafetyError, got {type(exc).__name__}: {exc}')
        else:
            failed += 1
            print('FAIL python actions safety: expected IntentoSafetyError')
    return failed

def main():
    failed = run_memory_tests()
    failed += run_file_tests()
    failed += run_stdlib_tests()
    failed += run_richer_stdlib_tests()
    failed += run_module_project_tests()
    failed += run_dev_polish_tests()
    failed += run_intentotest_tests()
    failed += run_project_init_package_tests()
    failed += run_python_actions_tests()
    if failed:
        raise SystemExit(1)
    print('All tests passed.')


if __name__ == '__main__':
    main()

# v0.8 intentotest smoke tests are included above.
