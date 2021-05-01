from textwalker import PatternParser


def run_tests(test_cases: list):
    """
    test_cases must be formated as a triples of (pattern, match, expected_result)
    to run a test is to create attempt to match the string `match` with `pattern` pattern
    the result of the match is compared with the `expected_result`

    iterate through test cases
    a set of tests
    """
    for idx, (pattern, match, expected) in enumerate(test_cases):
        pat = PatternParser(pattern)
        pat.compile()
        result = pat.match(match)
        assert result == expected, f'{idx+1} failed pattern:{pattern}, match:{match}, expected:{expected}, actual:{result}'
#            print(f'{idx+1} passed')
#        else:
#            print(f'{idx+1} failed pattern:{pattern}, match:{match}, expected:{expected}, actual:{result}')


def test_literals():
    """
    tests for literals
    """

    # triples of pattern, match, expected_result
    test_cases = [
        ("car", "car", "car"),
        # double escape because single escape, escapes the bracket, which
        # is an invalid escape
        ("\\(", "(", "("),
    ]

    run_tests(test_cases)


def test_charsets():
    """
    tests for charsets
    """

    test_cases = [
        ("[a-z]+", "dat9", "dat"),
        ("[\nx]*", "\nxxxx", "\nxxxx"),
    ]

    run_tests(test_cases)


def test_groups0():
    """
    tests for groups
    """

    # triples of pattern, match, expected_result
    test_cases = [
        # simple cases
        ("([a-z]+)", "dat9", "dat"),
        ("([a-z]+)3", "a32", "a3"),
        ("([a-z]+)3", "3a", ""),
        ("(hello)+", "hellohello", "hellohello"),
        ("(hel[a-z]p)+", "helxphelyp", "helxphelyp"),
        ("(hel[a-z]p)+", "helxphelyp9", "helxphelyp"),
        ("(x[a-z]y)+", "xay9", "xay"),

        # complex quantifier combinations
        ("(x[a-z]+y)*a", "a", "a"),

        # special chars, e.g. newline, escape chars
        ("([\nx]*)", "\nxxxx", "\nxxxx"),
        # double escape because single escape, escapes the bracket, which
        # is an invalid escape
        ("(\\()", "(", "("),
    ]

    run_tests(test_cases)


def test_groups1():
    """
    randomly split tests
    """

    # triples of pattern, match, expected_result
    test_cases = [
        ("(ab)(cd)", "abcd", "abcd"),
        ("((a*b)+)", "bcard", "b"),
        ("((a*b)+)(car)", "bcard", "bcar"),
    ]

    run_tests(test_cases)




if __name__ == '__main__':
    test_groups1()
