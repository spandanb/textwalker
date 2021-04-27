from typing import List


# Utilities

def arr2str(arr):
    return ''.join(arr) if len(arr) > 0 else ''


# Globals

ESCAPABLE_CHARS = {'(', ')', '[', ']', '{', '}', '-'}


# Exceptions


class MinMatchesNotFound(Exception):
    pass


class UnescapedChar(Exception):
    """
    These represent the constraint that special chars be escaped
    """


class UnrecognizedEscapedChar(Exception):
    """
    This represents that random characters should not be escaped
    """


# Quantifier classes

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
    a child range in a charset, e.g. a-z
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
    """
    e.g. [a-z01]
    """
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
    """
    e.g. (foo)
    """
    def __init__(self, groups: list, quantifier=None):
        self.groups = groups
        super().__init__(quantifier)

    def __repr__(self):
        if self.quantifier is not None:
            return f'G[{self.groups}{self.quantifier}]'
        return f'G[{self.groups}]'


class MatchResult:
    """
    Result for match
    """
    def __init__(self, matched: bool, content: str = ''):
        self.matched = matched
        self.content = content


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

    def coalesce_literals(self, tokens: List[Token]) -> List[Token]:
        """
        utility to coalesce adjacent literal chars into literal word;
        non-literal Tokens' relative ordering is untouched

        context: in a group, initially each char is it's own literal
        we need to coalesce literals to words so we can
        match on, e.g. word repetitions
        """
        coalesced = []
        partials = []
        for idx, token in enumerate(tokens):
            if isinstance(token, Literal):
                partials.append(token)
            elif len(partials) > 0:
                # coalesce and add to result
                value = ''.join([literal.value for literal in partials])
                coalesced.append(Literal(value))
                partials = []

            # add all other tokens as is
            if not isinstance(token, Literal):
                coalesced.append(token)

        if len(partials) > 0:
            value = ''.join([literal.value for literal in partials])
            coalesced.append(Literal(value))
        return coalesced

    def compile(self):
        self.compiled = self.compile_grouping()

    def compile_grouping(self, is_nested=False) -> Grouping:
        """
        compile the pattern.
        args:
            is_nested: whether this is nested call, i.e. grouping

        pattern can be of form:
        foo  : literal
        [a-z]: charset (range)
        [3-9]
        [az] charsets (enumeration)
        fox* : single-char quantifier: *,+,?
        [3-9]{3,4}: quantity/numeric range
        (foo)*: groupings
        (foo_[a-z]*)+: groupings

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
                    return Grouping(self.coalesce_literals(compiled))
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
                else:
                    assert ch == '?', "unknown quantifier"
                    matchable.quantifier = ZeroOrOne()
            elif ch == '{':
                # this will either succeed and consume the entire quantifier
                pass
            # handle escape char
            elif ch == '\\':
                next_char = self.advance()
                if next_char not in ESCAPABLE_CHARS:
                    # NOTE: currently not supporting all escape chars
                    raise UnrecognizedEscapedChar
                # add the escaped char as a literal
                compiled.append(Literal(next_char))

            else:
                compiled.append(Literal(ch))

        if is_nested:
            # this is error; since this was a nested call we should have found
            # a closing bracket; the choice of exception is imprecise
            # because the user's intention could be to: 1) create a group
            # and perhaps forgot the closing bracket; or 2) a literal match
            # on open bracket "(" and forgot to escape; for now bracket "(" must be escaped
            raise UnescapedChar("Unclosed bracket")

        return Grouping(self.coalesce_literals(compiled))

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
                next_char = self.advance()
                if next_char not in ESCAPABLE_CHARS:
                    # NOTE: currently not supporting all escape chars
                    raise UnrecognizedEscapedChar
                # add the escaped char as a literal
                result.append(Literal(next_char))

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
                # TODO: keep a separate list of chars to be escaped
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

    def match_literal(self, literal: Literal, string: str, startidx: int = 0) -> MatchResult:
        for idx, lch in enumerate(literal.value):
            if lch != string[startidx + idx]:
                return MatchResult(False)
        return MatchResult(True, literal.value)

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

    def match_grouping(self, groupings: Grouping, string: str, startidx: int = 0) -> MatchResult:
        """
        return longest match
        if this gets too complex, consider moving matching logic
        to separate class

        NOTES: on the matching logic:
        - the user string may be partially consumed
        - but generally, the pattern must be fully consumed

        args:
            # a better name might be consume_full_pattern
            match_partial: if True, will return if pattern partially matches;
                else raises Exception
                user string partially matching is never an error

            startidx: of string

            return[MatchResult].matched is True if there is a complete match; else False
        """

        groups = groupings.groups
        gptr = 0  # sub group ptr
        sptr = startidx  # string ptr
        repetition = 0
        matched = []
        # the last gptr location where a match was found
        # needed to determine if the pattern was fully consumed
        last_matched_gptr = -1
        # whether the subgroup has matched
        while sptr < len(string) and gptr < len(groups):

            # there are 2 things to check:
            # 1) is there a match
            # 2) is the number of repetitions of match as expected

            # consume as much of string (maximum munch) using subgroup
            subgroup = groups[gptr]

            # does the quantifier on this subgroup, allow it to consume more chars
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
                    res = self.match_grouping(subgroup, string, sptr)
                    # if quantifier is [0,..] and no-match, this is treated
                    # as a match of len 0;
                    if res.matched is False and isinstance(subgroup.quantifier, ZeroOrMore) or isinstance(subgroup.quantifier, ZeroOrOne):
                        res = MatchResult(True, "")

                assert res is not None

                # current component matched
                if res.matched:
                    repetition += 1
                    matched.append(res.content)
                    # increment string pointer
                    sptr += len(res.content)
                    last_matched_gptr = gptr

                    # increment the gptr; this represents
                    # something not matching with [0,...] quantifier
                    # we treat this as-a 0len match
                    if len(res.content) == 0:
                        gptr += 1
                        repetition = 0

                # current component did not match
                else:
                    # no match, move to next matchable
                    # check minimum match cond was violated
                    if not self.sufficient_consumed(repetition, subgroup.quantifier):
                        raise MinMatchesNotFound

                    repetition = 0
                    # increment component pointer
                    gptr += 1
            else:
                # quantifier restricts further consume
                # consider next subgroup
                gptr += 1
                repetition = 0
                continue

        # we want the pattern to be fully consumed and at least one
        # group has not been matched
        content = arr2str(matched)
        if len(content) == 0 or last_matched_gptr < len(groups) - 1:
            # this seems to be needed because it attempts partial match
            # perhaps this should be labelled better
            return MatchResult(False)

        return MatchResult(True, content)

    def match(self, string: str, startidx: int = 0) -> str:
        if self.compiled is None:
            self.compile()

        try:
            result = self.match_grouping(self.compiled, string, startidx)
            return result.content
        except MinMatchesNotFound:
            # print("No match found")
            return ""


def test():
    pattern, match, _ = "(hel[a-z]p)+", "helxphelyp9", "helxphelyp"
    pattern, match, _ = ("(x[a-z]+y)*a", "a", "a")
    pattern, match = "\(", "("
    # specify i

    pat = PatternParser(pattern)
    pat.compile()
    print(f'compiled pattern is {pat.compiled}')
    print(pat.match(match))


if __name__ == '__main__':
    test()