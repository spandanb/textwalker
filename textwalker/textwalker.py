from typing import List
from pattern_parser import PatternParser


# commonly used charsets
NEWLINE = "[\r\n]"
NEWLINE_WHITESPACE = "[ \r\n\t]"
WHITESPACE = "[\r\n\t]"


class TextWalker:
    """
    consumes words one word at a time
    """

    def __init__(self, text: str, word_delim=NEWLINE_WHITESPACE, strict_match: bool = False):
        """
        args:
            text: input text to walk
            word_delim: patterns to additionally consume
            strict_match: if no match, raises exception;
        """
        self.text = text
        self.textidx = 0
        # this will be consumed before and after every user specified walk
        self.word_delim = word_delim

    def walk(self, pattern: str):
        """
        consumes the `text` starting at `textidx`, based on the `pattern`
        updates textidx if text is consumed/matched.
        if specified, word_delims are also consumed
        """
        # consume word delim
        if self.word_delim is not None:
            ws_parser = PatternParser(self.word_delim)
            while True:
                match = ws_parser.match(self.text, self.textidx)
                if len(match) == 0:
                    break
                self.textidx += len(match)

        pparser = PatternParser(pattern)
        match = pparser.match(self.text, self.textidx)
        if match is None:
            print('text walker did not find match')
            return ''
        self.textidx += len(match)
        return match

    def walk_until(self, pattern: str) -> (str, str):
        """
        walk until pattern matches, by iterating by one
        character.

        it's an error to be invoked with a pattern that
        can resolve to length 0, since it's not clear
        todo: add support for the above

        returns the pair ( substring upto match, match)
        """
        startidx = self.textidx
        trail = []
        pparser = PatternParser(pattern)
        while self.textidx < len(self.text) - 1:
            # will consume until there is a match
            match = pparser.match(self.text, self.textidx)
            if len(match) > 0:
                return self.text[startidx: self.textidx], match
            self.textidx += 1
        return self.text[startidx:], ''

    def walk_many(self, patterns: List[str]) -> List[str]:
        """
        walk many tokens
        """
        return [self.walk(pattern) for pattern in patterns]
