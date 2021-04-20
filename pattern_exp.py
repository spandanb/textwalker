

def arr2str(arr):
    return ''.join(arr) if len(arr) > 0 else ''


QUANTIFIERS = ['*', '+', '?']


class Quantifier:
    pass


class ZeroOrMore(Quantifier):
    def __str__(self):
        return '*'


class OneOrMore(Quantifier):
    def __str__(self):
        return '+'

    def __repr__(self):
        return str(self)


class ZeroOrOne(Quantifier):
    def __str__(self):
        return '?'


class UnescapedDash(Exception):
    pass


class UnclosedCharSet(Exception):
    pass


class MinMatchesNotFound(Exception):
    pass


class UnescapedChar(Exception):
    """
    These represent the constraint that special chars be escaped
    """


class Token:
    def __init__(self, quantifier=None):
        self.quantifier = quantifier


class Literal(Token):
    def __init__(self, value, quantifier=None):
        super().__init__(quantifier)
        self.value = value

    def __repr__(self):
        if self.quantifier is not None:
            return f'L[{self.value}{self.quantifier}]'
        return f'L[{self.value}]'

    def __str__(self):
        return self.__repr__()


class CharRange(Token):
    """
    a child range in a charset
    """
    def __init__(self, range_start, range_end, quantifier=None):
        super().__init__(quantifier)
        self.range_start = range_start
        self.range_end = range_end

    def __repr__(self):
        if self.quantifier is not None:
            return f'L[{self.range_start}-{self.range_end}{self.quantifier}]'
        return f'CR({self.range_start}-{self.range_end})'

    def __str__(self):
        return self.__repr__()


class Charset(Token):
    def __init__(self, matches: list, quantifier=None):
        super().__init__(quantifier)
        # matches is composed of either literals or ranges
        self.matches = matches

    def __repr__(self):
        if self.quantifier is not None:
            return f'L[{self.matches}{self.quantifier}]'
        return f'CS[{self.matches}]'

    def __str__(self):
        return self.__repr__()


class Grouping(Token):
    def __init__(self, groups: list, quantifier=None):
        self.groups = groups
        super().__init__(quantifier)

    def __repr__(self):
        if self.quantifier is not None:
            return f'G[{self.groups}{self.quantifier}]'
        return f'G[{self.groups}]'


class Disjunction:
    def __init__(self, *elements):
        self.elements = elements


class MatchResult:
    def __init__(self, matched: bool, content: str = None, partial_match: bool = False, sufficient_consumed: bool = True):
        self.matched = matched
        self.content = content
        self.partial_match = partial_match
        self.sufficient_consumed = sufficient_consumed


class PatternParser:
    def __init__(self, pattern):
        # when parsing a chunk, `start` is the start of the chunk
        # and `current` points to the `current` char
        self.start = 0
        self.current = 0
        self.pattern = pattern
        self.compiled = None

    def is_at_end(self) -> bool:
        return self.current >= len(self.pattern)

    def advance(self) -> str:
        char = self.pattern[self.current]
        self.current += 1
        return char

    def has_next(self) -> bool:
        return self.current < len(self.pattern) - 1

    def has_next_next(self) -> bool:
        return self.current < len(self.pattern) - 2

    def peek(self) -> str:
        return self.pattern[self.current]

    def peek_next(self) -> str:
        return self.pattern[self.current + 1]

    def peek_next_next(self) -> str:
        return self.pattern[self.current + 2]

    def compile(self):
        self.compiled = self.compile_grouping()

    def compile_grouping(self, is_nested=False) -> Grouping:
        """
        compile the pattern.
        args:
            is_nested: whether this is nested call, i.e. grouping

        pattern can be of form:
        foo  : literal
        [a-z]: charset
        [3-9]
        [az]
        fox* : single-char quantifier: *,+,?
        [3-9]{3,4}: quantity/numeric range
        (foo)*: groupings
        (foo_[a-z]*)+: groupings
            - not sure if groups should be nestable
        NB: quantifiers can apply to any other element, except another quantifier

        special chars, namely:
            -, {, }, [, ], *, +, ?, (, ) must be escaped

        escape via backslash prepended to char

        An unescaped special char is an error


        _[a-z]{1,2} i.e. can contain:
        (foo_){1,2}
        foo_*
            literals: foo_
            character sets, which can contain ranges, or specific chars: [a-z][xyz]
            quantifier on character sets: [a-z]*
        """
        compiled = []
        while self.is_at_end() is False:
            ch = self.advance()
            if ch == '(':
                # handle grouping
                grouping = self.compile_grouping(is_nested=True)
                compiled.append(grouping)
            elif ch == ')':
                if is_nested:
                    # this terminates the grouping
                    return Grouping(compiled)
                raise UnescapedChar(")")
            elif ch == '[':
                # this will either succeed and consume and return
                # entire charset, or raise exception
                charset = self.compile_charset()
                compiled.append(charset)
            # handle quantifiers
            elif ch == '*' or ch == '+' or ch == '?':
                # find matchable to attach quantifier to
                matchable = compiled[-1] if len(compiled) > 0 else None
                if matchable is None:
                    raise UnescapedChar
                quantifier = None
                if ch == '*':
                    matchable.quantifier = ZeroOrMore()
                elif ch == '+':
                    matchable.quantifier = OneOrMore()
                else:  # ?
                    matchable.quantifier = ZeroOrOne()
            elif ch == '{':
                # this will either succeed and consume the entire quantifier
                pass
            # handle escape char
            elif ch == '\\':
                pass
            else:
                compiled.append(Literal(ch))

        return Grouping(compiled)

    def compile_charset(self) -> Charset:
        """
        should consume entire charset, i.e. should be invoked with pattern[current] == '['
        and should return '[...]'

        raises on unclosedSet and unescapedDash
        """
        result = []
        closed = False
        while self.is_at_end() is False:
            ch = self.advance()  # consume char
            # handle escape char
            if ch == '\\':
                pass
            # handle range dash
            if ch == '-':
                # an unescaped dash, should only appear between a range
                # this simplifies the case, where it's the first or last char in set
                raise UnescapedDash
            if ch == ']':
                # closing bracket found
                closed = True
                break
            else:  # ch is non-special
                # check if it's part of a range
                # TODO: keep a seperate list of chars to be escaped
                if self.has_next() and self.peek() == '-':
                    if not self.has_next_next():
                        # unescaped dash's are only supported in range
                        raise UnescapedDash
                    self.advance()  # consume the dash
                    rng_end = self.advance()
                    rng = CharRange(ch, rng_end)
                    result.append(rng)
                else:  # handle literal
                    result.append(Literal(ch))
        if not closed:
            raise UnclosedCharSet

        return Charset(result)

    def can_consume(self, current_repetition, quantifier) -> bool:
        """
        true if can consume based on `current_repetition`; note this
        invoked before consuming
        """
        if isinstance(quantifier, ZeroOrMore) or isinstance(quantifier, OneOrMore):
            return True
        elif isinstance(quantifier, ZeroOrOne):
            return current_repetition < 1
        elif quantifier is None:
            # interpret None as 1
            return current_repetition < 1

    def sufficient_consumed(self, current_repetition, quantifier) -> bool:
        """
        return True if the minimum number of elements was consumed
        NOTE this is invoked after consuming
        """
        if isinstance(quantifier, ZeroOrOne):
            return True
        elif isinstance(quantifier, ZeroOrMore):
            return True
        elif isinstance(quantifier, OneOrMore):
            return current_repetition >= 1
        elif quantifier is None:
            # TODO: not sure if this correct
            return True
            # return current_repetition >= 1

    def match_literal(self, literal: Literal, string: str, startidx: int = 0) -> MatchResult:
        if literal.value == string[startidx]:
            return MatchResult(True, literal.value)
        return MatchResult(False)

    def match_charset(self, charset: Charset, string: str, startidx: int = 0) -> MatchResult:
        for charset_member in charset.matches:
            if isinstance(charset_member, Literal):
                if charset_member.value == string[startidx]:
                    return MatchResult(True, string[startidx])
            elif isinstance(charset_member, CharRange):
                # not sure if this comparison will always work
                if charset_member.range_start <= string[startidx] <= charset_member.range_end:
                    return MatchResult(True, string[startidx])
        return MatchResult(False)

    def match_grouping(self, groupings: Grouping, string: str, startidx: int = 0, match_partial=True) -> MatchResult:
        """
        return longest match
        if this gets too complex, it might make sense to have separate classes for
        compiling and matching

        args:
            match_partial: whether to return a partial match or raise an exception

                in the top call, return partial, but any nested
        """

        groups = groupings.groups
        gptr = 0  # sub group ptr
        sptr = startidx  # string ptr
        repetition = 0
        matched = []
        # whether the subgroup has matched
        # e.g. "[a-z]+", "a9" should match "a"; this tracks
        subgroup_matched = False
        while sptr < len(string) and gptr < len(groups):

            # there are 2 things to check:
            # 1) is there a match
            # 2) is the number of repetitions of match as expected

            # consume as much of string (maximum munch) using subgroup
            subgroup = groups[gptr]

            if self.can_consume(repetition, subgroup.quantifier):

                # invoke the right handler
                res = None
                if isinstance(subgroup, Literal):
                    res = self.match_literal(subgroup, string, sptr)
                elif isinstance(subgroup, Charset):
                    res = self.match_charset(subgroup, string, sptr)
                else:
                    assert isinstance(subgroup, Grouping), "unexpected sub-expression type"
                    # groupings can be nested
                    # so the matching algorithm must be recursive
                    # res = None
                    # try:
                    # todo for *, if a child errs, should still pass
                    # e.g. ((foo)+)* ""
                    res = self.match_grouping(subgroup, string, sptr)
                    # except MinMatchesNotFound:
                        # this means the child group was unable to consume
                        # the minimum number of consumptions
                        # this may be okay
                        # pass

                # current component matched
                if res.matched:
                    repetition += 1
                    matched.append(res.content)
                    # increment string pointer
                    sptr += len(res.content)

                    if self.sufficient_consumed(repetition, subgroup.quantifier):
                        # thus if a new bit of pattern appears, we know we've met
                        # the requirement and hence this is not an error
                        subgroup_matched = True

                # current component partially matched
                elif res.partial_match:
                    matched.append(res.content)
                    sptr += len(res.content)
                    # also increment gptr
                    repetition = 0
                    gptr += 1
                # current component did not match
                else:
                    # no match, move to next matchable
                    # do I need to check minimum match cond was violated

                    if not self.sufficient_consumed(repetition, subgroup.quantifier) and subgroup_matched is False:
                        #print('In-suff consumed')
                        raise MinMatchesNotFound
                    """
                        # this sub group does not match;
                        # we need to break from this matching loop
                        # if there was a partial match, pipe it through
                        # NOTE: not entirely sure about this logic
                        content = arr2str(matched)
                        if res.partial_match:
                            content += res.content
                        return MatchResult(False, content, partial_match=True)
                    """

                    repetition = 0
                    # increment component pointer
                    gptr += 1
            else:
                # quantifier restricts further consume
                # consider next subgroup
                gptr += 1
                repetition = 0
                continue

        # check whether min number of times consumed
        if not self.sufficient_consumed(repetition, groupings.quantifier):
            raise MinMatchesNotFound
            # return MatchResult(False, arr2str(matched), partial_match=True)

        return MatchResult(True, arr2str(matched))

    def match(self, string) -> str:
        if self.compiled is None:
            self.compile()

        try:
            result = self.match_grouping(self.compiled, string)
            return result.content
        except MinMatchesNotFound:
            print("No match found")
            return ""


def tests():
    # triples of pattern, match, expected_result
    test_cases = [("car", "car", "car"),
                  ("[a-z]+", "dat9", "dat"),
                  ("([a-z]+)", "dat9", "dat"),
                  ("([a-z]+)3", "a32", "a3"),
                  ("([a-z]+)3", "3a", ""),
                  ]
    for idx, (pattern, match, expected) in enumerate(test_cases):
        pat = PatternParser(pattern)
        pat.compile()
        result = pat.match(match)
        if result == expected:
            print(f'{idx+1} passed')
        else:
            print(f'{idx+1} failed pattern:{pattern}, match:{match}, expected:{expected}, actual:{result}')
            break


def test0():
    pat = PatternParser("([a-z]+)3")
    pat.compile()
    print(f'compiled pattern is {pat.compiled}')
    print(pat.match("3a"))


def test1():
    # pattern, match, _ = ("[a-z]+", "dat9", "dat")
    # pattern, match = "([a-z]+)3", "a3"
    pattern, match = "(hello)+", "hellohello"
    pat = PatternParser(pattern)
    pat.compile()
    print(f'compiled pattern is {pat.compiled}')
    print(pat.match(match))


if __name__ == '__main__':
    #test0()
    test1()
    #tests()