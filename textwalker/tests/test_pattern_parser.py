from textwalker import PatternParser

"""
missing dimension of tests:
- case sensitive matching
"""


def run_pattern_match(test_cases: list):
    """
    test_cases must be formatted as a triple of (pattern, match, expected_result)
    to run a test is to create attempt to match the string `match` with `pattern` pattern
    the result of the match is compared with the `expected_result`

    iterate through test cases
    a set of tests
    """
    for idx, (pattern, match, expected) in enumerate(test_cases):
        pat = PatternParser(pattern)
        pat.compile()
        result = pat.match(match)
        assert (
            result == expected
        ), f"{idx+1} failed pattern:{pattern}, match:{match}, expected:{expected}, actual:{result}"


def test_literal_empty():
    """
    test empty literals
    """
    run_pattern_match(
        [
            ("", "", ""),
        ]
    )


def test_literal_single_char():
    """
    test literals with a single char
    """

    # triples of pattern, match, expected_result
    run_pattern_match(
        [
            ("b", "b", "b"),
            ("3", "3b", "3"),
            ("x", "", None),
            # double escape because single escape, escapes the bracket, which
            # is an invalid escape
            ("\\(", "(", "("),
            # quantifiers
            ("b?", "", ""),
        ]
    )


def test_literal_multi_char():
    """
    test literals with a multi chars
    """
    # triples of pattern, match, expected_result
    run_pattern_match(
        [
            ("abc", "abc", "abc"),  # exact match
            # longer pattern matches empty;
            # this may be non-intuitive; but partial matches are not supported
            ("abcd", "abc", None),
            ("abc", "abcd", "abc"),  # longer text
            # quantifiers
            ("ab?", "a", "a"),
        ]
    )


def test_charsets_no_quantifier():
    """
    tests for charsets
    """
    run_pattern_match(
        [
            ("[a-z]", "3a", None),
            ("[a-z]", "a3", "a"),
            ("[a-z0-9]", "3a", "3"),
        ]
    )


def test_charsets():
    """
    tests for charsets
    """
    run_pattern_match(
        [
            ("[a-z]+", "dat9", "dat"),
            ("[a-z0-9]+", "3a", "3a"),
            ("[\nx]*", "\nxxxx", "\nxxxx"),
        ]
    )


def test_groups_simple():
    """
    tests for groups
    """

    # triples of pattern, match, expected_result
    run_pattern_match(
        [
            # simple cases
            ("([a-z]+)", "dat9", "dat"),
            ("([a-z]+)3", "a32", "a3"),
            ("([a-z]+)3", "3a", None),
            ("(hello)+", "hellohello", "hellohello"),
            ("(hel[a-z]p)+", "helxphelyp", "helxphelyp"),
            ("(hel[a-z]p)+", "helxphelyp9", "helxphelyp"),
            ("(x[a-z]y)+", "xay9", "xay"),
            # special chars, e.g. newline, escape chars
            ("([\nx]*)", "\nxxxx", "\nxxxx"),
            # double escape because single escape, escapes the bracket, which
            # is an invalid escape
            ("(\\()", "(", "("),
        ]
    )


def test_groups_complex():
    """
    more complicated grouping
    """

    # triples of pattern, match, expected_result
    run_pattern_match(
        [
            ("(x[a-z]+y)*a", "a", "a"),
            ("(ab)(cd)", "abcd", "abcd"),
            ("((a*b)+)", "bcard", "b"),
            ("((a*b)+)(car)", "bcard", "bcar"),
            ("(abcd)?(xyz)", "xyz", "xyz"),
            ("(abcd)?(xyz)?", "abcdxyz", "abcdxyz"),
            ("(abcd)?(xyz)?", "", ""),
        ]
    )


if __name__ == "__main__":
    pass
