from typing import List, Optional

from .utils import arr2str

# Globals

ESCAPABLE_CHARS = {"(", ")", "[", "]", "{", "}", "-"}


# Exceptions


class MinMatchesNotFound(Exception):
    """
    The minimum number of matches specified by the quantifier is not matched
    """

    pass


class UnescapedChar(Exception):
    """
    These represent the constraint that special chars be escaped
    """
    pass


class UnrecognizedEscapedChar(Exception):
    """
    This represents that random characters should not be escaped
    """
    pass


class UnescapedDash(Exception):
    """
    TODO: replace usage with UnrecognizedEscapedChar
    """
    pass


class UnclosedCharSet(Exception):
    pass


# Quantifier classes


class Quantifier:
    """
    base quantifier class
    """

    pass


class ZeroOrMore(Quantifier):
    """
    zero or more repetitions
    """

    def __str__(self):
        return "*"


class OneOrMore(Quantifier):
    """
    one or more repetitions
    """

    def __str__(self):
        return "+"

    def __repr__(self):
        return str(self)


class ZeroOrOne(Quantifier):
    def __str__(self):
        return "?"


class Token:
    """
    base token type
    """

    def __init__(self, quantifier=None):
        self.quantifier = quantifier


class Literal(Token):
    """
    literal token
    """

    def __init__(self, value, quantifier=None):
        super().__init__(quantifier)
        self.value = value

    def __repr__(self):
        if self.quantifier is not None:
            return f"L[{self.value}{self.quantifier}]"
        return f"L[{self.value}]"

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
            return f"CR[{self.range_start}-{self.range_end}{self.quantifier}]"
        return f"CR({self.range_start}-{self.range_end})"

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
            return f"CS[{self.matches}{self.quantifier}]"
        return f"CS[{self.matches}]"

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
            return f"G[{self.groups}{self.quantifier}]"
        return f"G[{self.groups}]"


class MatchResult:
    """
    Result for match
    """

    def __init__(self, matched: bool, content: str = ""):
        self.matched = matched
        self.content = content


class PatternParser:
    """ """

    def __init__(self, pattern):
        # when parsing a chunk, `start` is the start of the chunk
        # and `current` points to the `current` char
        self.start = 0
        self.current = 0
        self.pattern = pattern
        self.compiled = None
        self.compile()

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

    @staticmethod
    def coalesce_literals(tokens: List[Token]) -> List[Token]:
        """
        utility to coalesce adjacent literal chars into literal word;
        non-literal Tokens' relative ordering is untouched

        context: in a group, initially each char is it's own literal
        we need to coalesce literals to words so we can
        match on, e.g. word repetitions
        """

        # return tokens

        coalesced = []
        partials = []
        for idx, token in enumerate(tokens):
            # if quantifier is not None, can't coalesce into one literal
            if isinstance(token, Literal) and token.quantifier is None:
                partials.append(token)
            elif len(partials) > 0:
                # coalesce and add to result
                value = "".join([literal.value for literal in partials])
                coalesced.append(Literal(value))
                partials = []

            # add all other tokens as is
            if not isinstance(token, Literal):
                coalesced.append(token)

        if len(partials) > 0:
            value = "".join([literal.value for literal in partials])
            coalesced.append(Literal(value))
        return coalesced

    def compile(self):
        """
        compile the user supplied pattern
        """
        if self.compiled is None:
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
            if ch == "(":
                # handle grouping
                grouping = self.compile_grouping(is_nested=True)
                compiled.append(grouping)
            elif ch == ")":
                if is_nested:
                    # this terminates the grouping
                    return Grouping(self.coalesce_literals(compiled))
                raise UnescapedChar(")")
            elif ch == "[":
                # this will either succeed and consume and return
                # entire charset, or raise exception
                charset = self.compile_charset()
                compiled.append(charset)
            # handle quantifiers
            elif ch == "*" or ch == "+" or ch == "?":
                # find matchable to attach quantifier to
                matchable = compiled[-1] if len(compiled) > 0 else None
                if matchable is None:
                    raise UnescapedChar
                if ch == "*":
                    matchable.quantifier = ZeroOrMore()
                elif ch == "+":
                    matchable.quantifier = OneOrMore()
                else:
                    assert ch == "?", "unknown quantifier"
                    matchable.quantifier = ZeroOrOne()
            elif ch == "{":
                # this will either succeed and consume the entire quantifier or raise
                pass
            # handle escape char
            elif ch == "\\":
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
            if ch == "\\":
                next_char = self.advance()
                if next_char not in ESCAPABLE_CHARS:
                    # NOTE: currently not supporting all escape chars
                    raise UnrecognizedEscapedChar
                # add the escaped char as a literal
                result.append(Literal(next_char))

            # handle range dash
            if ch == "-":
                # an unescaped dash, should only appear between a range
                # this simplifies the case, where it's the first or last char in set
                raise UnescapedDash
            if ch == "]":
                # closing bracket found
                closed = True
                break
            else:  # ch is non-special
                # check if it's part of a range
                if self.has_next() and self.peek() == "-":
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
            raise UnclosedCharSet()

        return Charset(result)

    @staticmethod
    def can_consume(to_run_iteration: int, quantifier: Quantifier) -> bool:
        """
        true if can consume based on `current_repetition`; note this
        invoked before consuming
        """
        if isinstance(quantifier, ZeroOrMore) or isinstance(quantifier, OneOrMore):
            return True
        elif isinstance(quantifier, ZeroOrOne):
            return to_run_iteration < 1
        elif quantifier is None:
            # interpret None as 1
            return to_run_iteration < 1
        return True

    @staticmethod
    def sufficient_consumed(last_repetition, quantifier: Quantifier) -> bool:
        """
        return True if the minimum number of elements was consumed
        NOTE this is invoked after consuming
        """
        if isinstance(quantifier, ZeroOrOne):
            return True
        elif isinstance(quantifier, ZeroOrMore):
            return True
        elif isinstance(quantifier, OneOrMore):
            return last_repetition >= 1
        elif quantifier is None:
            # TODO: not sure if this correct
            return True
        else:
            return True

    def match_literal(
        self, literal: Literal, string: str, startidx: int = 0
    ) -> MatchResult:
        for idx, lch in enumerate(literal.value):
            if startidx + idx == len(string):
                return MatchResult(False)
            if lch != string[startidx + idx]:
                return MatchResult(False)
        return MatchResult(True, literal.value)

    def match_charset(
        self, charset: Charset, string: str, startidx: int = 0
    ) -> MatchResult:
        for charset_member in charset.matches:
            if isinstance(charset_member, Literal):
                if charset_member.value == string[startidx]:
                    return MatchResult(True, string[startidx])
            elif isinstance(charset_member, CharRange):
                # not sure if this comparison will always work
                if (
                    charset_member.range_start
                    <= string[startidx]
                    <= charset_member.range_end
                ):
                    return MatchResult(True, string[startidx])
        return MatchResult(False)

    @staticmethod
    def check_and_update_empty(
        result: MatchResult, quantifier: Quantifier
    ) -> MatchResult:
        """
        In some cases, a "no-match" of a sub-group is a match
        is a match of zero, according to the grammar, e.g. if the quantifier is *, ?.

        Returns:
        If there is a no-match, and the quantifier allows zero matches,
        then this will update the result to be an empty match;
        In all other cases, it will return the `result`
        """
        # if quantifier is [0,..] and no-match, this is treated
        # as a match of len 0;
        if (
            result.matched is False
            and isinstance(quantifier, ZeroOrMore)
            or isinstance(quantifier, ZeroOrOne)
        ):
            result = MatchResult(True, "")
        # else return original result
        return result

    def match_grouping(
        self, groupings: Grouping, string: str, startidx: int = 0
    ) -> MatchResult:
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
        repetition = 0  # count of repetitions of current sub group
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
                    res = self.check_and_update_empty(res, subgroup.quantifier)
                elif isinstance(subgroup, Charset):
                    res = self.match_charset(subgroup, string, sptr)
                    res = self.check_and_update_empty(res, subgroup.quantifier)
                else:
                    assert isinstance(
                        subgroup, Grouping
                    ), "unexpected sub-expression type"
                    # groupings can be nested
                    # so the matching algorithm must be recursive
                    res = self.match_grouping(subgroup, string, sptr)
                    res = self.check_and_update_empty(res, subgroup.quantifier)

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

    def match(self, string: str, startidx: int = 0) -> Optional[str]:
        """
        Attempt to match `string` starting at `startidx`
        Args:
            string: string to match
            startidx: location to start search
        Return
            None: no-match
            str: match (could be zero length)
        """
        matched = None
        try:
            result = self.match_grouping(self.compiled, string, startidx)
            if result.matched:
                matched = result.content
        except MinMatchesNotFound:
            pass

        return matched
