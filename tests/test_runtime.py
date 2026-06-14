from intento_runtime.runtime import run_source
from intento_runtime.errors import IntentoSemanticError, IntentoRuntimeError, IntentoTypeError, IntentoSyntaxError, IntentoConversionError


def test_show_text():
    result = run_source('show "Hello"')
    assert result.output == ['Hello']


def test_remember_and_plus():
    result = run_source('remember name as "Aurora"\nshow "Hello " plus name')
    assert result.output == ['Hello Aurora']


def test_arithmetic_precedence():
    result = run_source('show 2 plus 3 times 4\nshow (2 plus 3) times 4')
    assert result.output == ['14', '20']


def test_symbol_aliases():
    result = run_source('show 10 + 5\nshow 10 * 5')
    assert result.output == ['15', '50']


def test_bool_empty_list():
    result = run_source('show true\nshow empty\nshow ["A", "B"]')
    assert result.output == ['true', '', '["A", "B"]']


def test_ask():
    result = run_source('ask "Name?" and call the answer name\nshow "Hello " plus name', input_func=lambda q: 'Aurora')
    assert result.output == ['Hello Aurora']


def test_if_else():
    result = run_source('remember name as "Aurora"\nif name is "Aurora":\n    show "Correct"\nelse:\n    show "Wrong"')
    assert result.output == ['Correct']


def test_if_else_false_branch():
    result = run_source('remember name as "Ada"\nif name is "Aurora":\n    show "Correct"\nelse:\n    show "Wrong"')
    assert result.output == ['Wrong']


def test_if_empty_and_stop():
    result = run_source('remember name as empty\nif name is empty:\n    show "Name is required"\n    stop\nshow "No"')
    assert result.output == ['Name is required']


def test_comparisons():
    result = run_source('remember age as 20\nif age is at least 18:\n    show "Allowed"\nelse:\n    show "Denied"')
    assert result.output == ['Allowed']


def test_repeat():
    result = run_source('remember counter as 0\nrepeat 3 times:\n    remember counter as counter plus 1\n    show counter')
    assert result.output == ['1', '2', '3']


def test_for_each():
    result = run_source('remember skills as ["Linux", "Python", "INTENTO"]\nfor each skill in skills:\n    show skill')
    assert result.output == ['Linux', 'Python', 'INTENTO']


def test_unknown_name():
    try:
        run_source('show unknown')
    except IntentoSemanticError as exc:
        assert 'unknown name `unknown`' in str(exc)
    else:
        raise AssertionError('Expected IntentoSemanticError')


def test_division_by_zero():
    try:
        run_source('show 10 divided by 0')
    except IntentoRuntimeError as exc:
        assert 'division by zero' in str(exc)
    else:
        raise AssertionError('Expected IntentoRuntimeError')


def test_numeric_type_error():
    try:
        run_source('show "10" minus 5')
    except IntentoTypeError as exc:
        assert 'requires numbers' in str(exc)
    else:
        raise AssertionError('Expected IntentoTypeError')


def test_else_without_if():
    try:
        run_source('else:\n    show "No"')
    except IntentoSyntaxError as exc:
        assert '`else` must follow an `if` block' in str(exc)
    else:
        raise AssertionError('Expected IntentoSyntaxError')


def test_convert_values():
    result = run_source('remember age_text as "42"\nconvert age_text to number and call it age\nshow age plus 1\nremember active_text as "true"\nconvert active_text to boolean and call it active\nshow active')
    assert result.output == ['43', 'true']


def test_bad_conversion():
    try:
        run_source('remember value as "forty-two"\nconvert value to number and call it number_value')
    except IntentoConversionError as exc:
        assert 'cannot convert `forty-two` to number' in str(exc)
    else:
        raise AssertionError('Expected IntentoConversionError')


def test_trace_logs():
    result = run_source('remember name as "Aurora"\nshow name', trace=True)
    assert result.output == ['Aurora']
    assert 'TRACE line 1: Remember' in result.logs
    assert 'TRACE line 2: Show' in result.logs
