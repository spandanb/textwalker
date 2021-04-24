from pattern_parser import PatternParser


def tests():
    """
    a set of tests

    """
    # triples of pattern, match, expected_result
    test_cases = [
        ("car", "car", "car"),
        ("[a-z]+", "dat9", "dat"),
        ("([a-z]+)", "dat9", "dat"),
        ("([a-z]+)3", "a32", "a3"),
        ("([a-z]+)3", "3a", ""),
        ("(hello)+", "hellohello", "hellohello"),
        ("(hel[a-z]p)+", "helxphelyp", "helxphelyp"),
        ("(hel[a-z]p)+", "helxphelyp9", "helxphelyp"), # erroring
        ("(x[a-z]y)+", "xay9", "xay"),
        ("(x[a-z]+y)*a", "a", "a"),
        ("[\nx]*", "\nxxxx", "\nxxxx"),
        ("\(", "(", "("),
    ]
    for idx, (pattern, match, expected) in enumerate(test_cases):
        pat = PatternParser(pattern)
        pat.compile()
        result = pat.match(match)
        if result == expected:
            print(f'{idx+1} passed')
        else:
            print(f'{idx+1} failed pattern:{pattern}, match:{match}, expected:{expected}, actual:{result}')


if __name__ == '__main__':
    tests()