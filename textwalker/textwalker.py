"""
Contains `TextWalker` class for consuming text
"""
from typing import List, Optional, Tuple, Union
from .pattern_parser import PatternParser


# commonly used charsets
NEWLINE = "[\r\n]"
# NOTE: the blank corresponds to space char
NEWLINE_WHITESPACE = "[ \r\n\t]"
WHITESPACE = "[ \t]"


class TextWalker:
    """
    consumes words one word at a time
    """

    def __init__(self, text: str, word_delim: Union[str, None] = NEWLINE_WHITESPACE):
        """
        Args:
            text: input text to walk
            word_delim: Optional list, if set will consume anything that matches this
                before and after a word match
        """
        self.text = text
        self.textidx = 0
        # this will be consumed before and after every user specified walk token
        self.word_delim = word_delim
        # word delimiter parser
        self.wd_parser = None

    def word_delim_parser(self) -> PatternParser:
        """
        cache the parser for the word delim
        """
        if self.wd_parser is None:
            self.wd_parser = PatternParser(self.word_delim)
        return self.wd_parser

    def walk(self, pattern: str) -> Optional[str]:
        """
        Consumes the `text` starting at `textidx`, based on the `pattern`
        updates textidx if text is consumed/matched.
        if specified, `word_delims` are also consumed
        """
        # consume word delimiter
        if self.word_delim is not None:
            wd_parser = self.word_delim_parser()
            while True:
                match = wd_parser.match(self.text, self.textidx)
                if match is None:
                    break
                self.textidx += len(match)

        parser = PatternParser(pattern)
        match = parser.match(self.text, self.textidx)
        if match is None:
            return None
        self.textidx += len(match)
        return match

    def walk_until(self, pattern: str) -> Tuple[str, str]:
        """
        walk until pattern matches, by iterating by one
        character.

        Returns:
            (substring-upto-match(str), match(str))
        """
        startidx = self.textidx
        parser = PatternParser(pattern)
        while self.textidx < len(self.text) - 1:
            # will consume until there is a match
            match = parser.match(self.text, self.textidx)
            if match is not None:
                return self.text[startidx: self.textidx], match
            self.textidx += 1
        return self.text[startidx:], ""

    def walk_many(self, patterns: List[str]) -> List[str]:
        """
        walk many tokens
        Returns:
            - many tokens
        """
        return [self.walk(pattern) for pattern in patterns]
