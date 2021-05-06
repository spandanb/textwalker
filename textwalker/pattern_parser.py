"""
Contains classes for parsing pattern and matching text against the pattern
"""
from typing import List, Optional

from .utils import arr2str

# Globals

ESCAPABLE_CHARS = {"(", ")", "[", "]", "{", "}", "-"}


# Exceptions


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


class UnclosedCharSet(Exception):
    """
    A char set was not closed, i.e. missing ']'
    """

    pass


# Quantifier classes


class Quantifier:
    """
    base quantifier class
    """

    pass


class ZeroOrMore(Quantifier):
    """
    Represents quantifier zero or more repetitions
    """

    def __str__(self):
        return "*"


class OneOrMore(Quantifier):
    """
    Represents quantifier one or more repetitions
    """

    def __str__(self):
        return "+"

    def __repr__(self):
        return str(self)


class ZeroOrOne(Quantifier):
    """
    Represents quantifier zero or one repetitions
    """

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
    Represents a literal token
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
    Represents a child range in a charset, e.g. a-z
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
    Represents a charset e.g. [a-z01]
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
    Represents a grouping e.g. (foo)
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

    def __str__(self):
        if self.matched is False:
            return "NoMatch"
        return f"Match({self.content})"

    def __repr__(self):
        return str(self)


class PatternParser:
    """
    Class responsible for parsing logic.
    """

    def __init__(self, pattern: str):
        # when parsing a chunk, `start` is the start of the chunk
        # and `current` points to the `current` char
        self.start = 0
        self.current = 0
        self.pattern = pattern
        self.compiled = None
        self.compile()

    def is_at_end(self) -> bool:
        """
        Determine whether parser is at the end of the pattern text
        """
        return self.current >= len(self.pattern)

    def advance(self) -> str:
        """
        Consume and return the current char.
        Consumption increments `current`
        """
        char = self.pattern[self.current]
        self.current += 1
        return char

    def has_next(self) -> bool:
        """
        Determines whether there is a next element to consume
        """
        return self.current < len(self.pattern) - 1

    def has_next_next(self) -> bool:
        """
        Determines whether there is a next to next element to consume
        """
        return self.current < len(self.pattern) - 2

    def peek(self) -> str:
        """
        View the current element without consuming it
        """
        return self.pattern[self.current]

    def peek_next(self) -> str:
        """
        View the next element without consuming it.
        NOTE: This call is only valid if `has_next` is True
        """
        return self.pattern[self.current + 1]

    def peek_next_next(self) -> str:
        """
        View the next to next element without consuming it
        NOTE: This call is only valid if `has_next_next` is True
        """
        return self.pattern[self.current + 2]

    @staticmethod
    def coalesce_literals(tokens: List[Token]) -> List[Token]:
        """
        Combine adjacent literal chars with no quantifier into a literal word;
        e.g. L[a]L[b] -> L[ab]

        This is needed because the parsing pass, does not peek to the next
        char and treats each char as a single-char literal. This coalescing is needed
        to match word level repetitions.

        The relative ordering of non-`Literal` tokens and `Literal` tokens with
        quantifiers is unchanged.
        """

        coalesced = []
        partials = (
            []
        )  # partial list of chars that will be coalesced into in a single Literal
        for idx, token in enumerate(tokens):
            # if quantifier is not None, can't coalesce into one literal
            if isinstance(token, Literal) and token.quantifier is None:
                partials.append(token)
            elif len(partials) > 0:
                # we're at coalesce boundary; coalesce `partials` into a single
                # Literal and add to result
                value = "".join([literal.value for literal in partials])
                coalesced.append(Literal(value))
                partials = []

            # add all other tokens, as-is
            if (
                not isinstance(token, Literal)
                or isinstance(token, Literal)
                and token.quantifier is not None
            ):
                coalesced.append(token)

        if len(partials) > 0:
            # add remaining chars as a literal
            value = "".join([literal.value for literal in partials])
            coalesced.append(Literal(value))
        return coalesced

    def compile(self):
        """
        compile the user supplied pattern
        """
        if self.compiled is None:
            self.compiled = self.compile_grouping()

    def compile_subgroups(self, subgroups: List[Token]) -> Token:
        """
        Compile subgroups.

        When compiling a pattern, a pattern may consist of
        one or more subgroups. If there is a single sub-group, return
        the subgroup as is. This is needed to avoid excessive nesting,
        which leads to incorrect behavior. If there are multiple sub-groups, then
        wrap them in a coalesced `Grouping`
        """
        coalesced = self.coalesce_literals(subgroups)
        if len(coalesced) == 1:
            # return single sub group as is
            return coalesced.pop()
        # wrap multiple sub-groups in a grouping
        return Grouping(coalesced)

    def compile_grouping(self, is_nested: bool = False) -> Grouping:
        """
        Compile the pattern/grouping. A grouping consists of any number of
        literals, charsets, and sub-groups, and is the most general
        representation of a pattern. Hence, the user input is treated as a `Grouping`

        args:
            is_nested: whether this is nested grouping

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

        An escaped char, that should not be escaped in an error.

        Returns:
            compiled grouping; for the root call this is a `Grouping`
            object; for a non-root call this could be any other `Token`
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
                    return self.compile_subgroups(compiled)
                raise UnescapedChar(ch)
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
                    raise UnescapedChar(ch)
                if ch == "*":
                    matchable.quantifier = ZeroOrMore()
                elif ch == "+":
                    matchable.quantifier = OneOrMore()
                else:
                    assert ch == "?", "unknown quantifier"
                    matchable.quantifier = ZeroOrOne()
            elif ch == "{":
                # this will either succeed and consume the entire quantifier or raise
                # TODO: implememt me
                raise NotImplementedError
            elif ch == '-':
                # this is an unescaped dash
                raise UnescapedChar(ch)
            # handle escape char
            elif ch == "\\":
                next_char = self.advance()
                if next_char not in ESCAPABLE_CHARS:
                    # NOTE: currently not supporting all escape chars
                    raise UnrecognizedEscapedChar(next_char)
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

        grouping = self.compile_subgroups(compiled)
        if not is_nested and not isinstance(grouping, Grouping):
            # this is the root call- the returned must be wrapped in a Grouping
            grouping = Grouping([grouping])
        return grouping

    def compile_charset(self) -> Charset:
        """
        Consume characters in the pattern, corresponding to a charset,
        i.e. started with '[', terminated with ']' with literals and char ranges
        in between.

        Returns:
            compiled `Charset`

        Raises:
            - UnclosedSet and UnescapedChar
        """
        result = []
        closed = False  # whether the charset is closed
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
                raise UnescapedChar(ch)
            if ch == "]":
                # closing bracket found
                closed = True
                break
            else:  # ch is non-special
                # check if it's part of a range
                if self.has_next() and self.peek() == "-":
                    if not self.has_next_next():
                        # unescaped dash's are only supported in range
                        raise UnescapedChar(self.peek())
                    self.advance()  # consume the dash
                    rng_end = self.advance()
                    rng = CharRange(ch, rng_end)
                    result.append(rng)
                else:  # handle literal
                    result.append(Literal(ch))
        if not closed:
            raise UnclosedCharSet()

        return Charset(result)

    def match(self, string: str, startidx: int = 0) -> Optional[str]:
        """
        Attempt to match `string` starting at `startidx`
        Args:
            string: string to match
            startidx: location to start search
        Return
            None: no-match
            str: match (possibly zero length)
        """
        matcher = PatternMatcher(self.compiled)
        return matcher.match(string, startidx)


class PatternMatcher:
    """
    Encapsulates pattern matching logic
    """

    def __init__(self, compiled: Grouping):
        self.compiled = compiled

    @staticmethod
    def can_consume(to_run_iteration: int, quantifier: Quantifier) -> bool:
        """
        Determines whether the `quantifier` allows consuming another repetition
        NOTE: this should be invoked before consuming
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
    def sufficient_consumed(last_repetition: int, quantifier: Quantifier) -> bool:
        """
        Determines whether the minimum number of elements was consumed
        NOTE: this should be invoked after consuming
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

    @staticmethod
    def accepts_empty(quantifier: Quantifier) -> bool:
        """
        Determines whether the quantifier allows for an empty match
        """
        # TODO: add check for quantity range
        return isinstance(quantifier, ZeroOrMore) or isinstance(quantifier, ZeroOrOne)

    def check_and_update_empty(
        self, result: MatchResult, quantifier: Quantifier
    ) -> MatchResult:
        """
        In cases where the quantifier, permits 0 matches, e.g. *, ?,
        a "no-match" of a sub-group is to be treated as a match of length zero.

        Returns:
            If there is a no-match, and the quantifier allows zero matches,
            then this will update the result to be an empty match;
            Otherwise, it will return the `result`
        """
        # if quantifier is [0,..] and no-match, this is treated
        # as a match of len 0;
        if result.matched is False and self.accepts_empty(quantifier):
            result = MatchResult(True, "")
        # else return original result
        return result

    @staticmethod
    def match_literal(literal: Literal, string: str, stridx: int = 0) -> MatchResult:
        """
        Attempt to match a literal
        """
        for idx, lch in enumerate(literal.value):
            if stridx + idx == len(string):
                return MatchResult(False)
            if lch != string[stridx + idx]:
                return MatchResult(False)
        return MatchResult(True, literal.value)

    @staticmethod
    def match_charset(charset: Charset, string: str, stridx: int = 0) -> MatchResult:
        """
        Attempt to match a charset
        """
        for charset_member in charset.matches:
            if stridx == len(string):
                # handle empty string
                return MatchResult(False)
            if isinstance(charset_member, Literal):
                if charset_member.value == string[stridx]:
                    return MatchResult(True, string[stridx])
            elif isinstance(charset_member, CharRange):
                # NOTE: this comparison relies on python's lexical ordering
                if (
                    charset_member.range_start
                    <= string[stridx]
                    <= charset_member.range_end
                ):
                    return MatchResult(True, string[stridx])
        return MatchResult(False)

    def match_sub_groups(self, groups: List[Token], string: str, stridx: int = 0):
        """
        Attempt to match a list of sub groups.
        """
        sgptr = 0  # sub-group ptr
        sgroup_repetition = 0  # count of repetitions of current sub group
        matched = []
        # the last gptr location where a match was found
        # needed to determine if the pattern was fully consumed
        last_matched_sgptr = -1

        while sgptr < len(groups):

            # there are 2 things to check:
            # 1) is there a match
            # 2) is the number of repetitions of match as expected

            # consume as much of string (maximum munch) using subgroup
            subgroup = groups[sgptr]

            # does the quantifier on this subgroup, allow it to consume more chars
            if self.can_consume(sgroup_repetition, subgroup.quantifier):

                # invoke the right handler
                res = None
                if isinstance(subgroup, Literal):
                    res = self.match_literal(subgroup, string, stridx)
                    res = self.check_and_update_empty(res, subgroup.quantifier)
                elif isinstance(subgroup, Charset):
                    res = self.match_charset(subgroup, string, stridx)
                    res = self.check_and_update_empty(res, subgroup.quantifier)
                else:
                    assert isinstance(
                        subgroup, Grouping
                    ), "unexpected sub-expression type"
                    # groupings can be nested
                    # so the matching algorithm must be recursive
                    res = self.match_grouping(subgroup, string, stridx)
                    res = self.check_and_update_empty(res, subgroup.quantifier)

                # current component matched
                if res.matched:
                    sgroup_repetition += 1
                    matched.append(res.content)
                    # increment string pointer
                    stridx += len(res.content)
                    last_matched_sgptr = sgptr

                    # increment the gptr; this represents
                    # something not matching with [0,...] quantifier
                    # we treat this as a match of length 0
                    if len(res.content) == 0:
                        sgptr += 1
                        sgroup_repetition = 0

                # current component did not match
                else:
                    # no match, move to next matchable
                    # check minimum match cond was violated
                    if not self.sufficient_consumed(
                        sgroup_repetition, subgroup.quantifier
                    ):
                        return MatchResult(False)

                    sgroup_repetition = 0
                    # increment component pointer
                    sgptr += 1
            else:
                # quantifier restricts further consume
                # consider next subgroup
                sgptr += 1
                sgroup_repetition = 0
                continue

        # we want the pattern to be fully consumed and at least one
        # group has not been matched
        if last_matched_sgptr < len(groups) - 1:
            return MatchResult(False)

        content = arr2str(matched)
        return MatchResult(True, content)

    def match_grouping(
        self, grouping: Grouping, string: str, stridx: int = 0
    ) -> MatchResult:
        """
        Finds the longest match by greedily matching characters.
        Greedy here implies, that when matching text on a sub-group, it will consume
        as many characters from the text, as the sub-group can match. This is
        noteworthy since a non-greedy sub-group match may result in a overall pattern match; whereas
        the greedy approach results in a non-match; e.g.:

        for pattern = (aa)*a, text = aaaa, the greedy algorithm would consider this a
        non-match since, the pattern must be fully consumed, and the final 'a' does not get
        consumed.

        The user string may be partially consumed. However, if the pattern
        is not consumed, then this is considered a non-match.

        An empty string is a valid input to match. Further an empty string can
        match an arbitrary pattern, as long as each child pattern allows
        zero matches. Thus all matching handlers must handle zero-length input string

        Args:
            stridx: idx where to start matching string

        Returns:
            MatchResult.matched is True if there is a complete match; else False
        """

        groups = grouping.groups

        group_repetition = 0  # count of repetitions of group
        matched = []  # chars that have matched
        sg_matched = True
        while self.can_consume(group_repetition, grouping.quantifier):
            res = self.match_sub_groups(groups, string, stridx)
            if res.matched:
                matched.append(res.content)
                group_repetition += 1
                stridx += len(res.content)
                if len(res.content) == 0:
                    break
            else:
                # sub group did not match
                sg_matched = False
                break

        content = arr2str(matched)
        # the following distinguishes a non-match from an empty match
        # i.e. content length is 0 and the quantifier does not allow a zero match
        if (len(content) == 0 and sg_matched is False) and self.accepts_empty(
            grouping.quantifier
        ) is False:
            return MatchResult(False)

        return MatchResult(True, content)

    def match(self, string: str, stridx: int = 0) -> Optional[str]:
        """
        Attempt to match `string` starting at `startidx`
        Args:
            string: string to match
            startidx: location to start search
        Return
            None: no-match
            str: match (possibly zero length)
        """
        matched = None
        result = self.match_grouping(self.compiled, string, stridx)
        if result.matched:
            matched = result.content
        return matched
