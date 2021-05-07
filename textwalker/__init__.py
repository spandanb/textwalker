"""
## Grammar

### Literals

- Can be any literal string
```
foo
bar
123
x?
```
- Can have quantifiers

### Character Sets
- A character set is defined within a pair of left and right square brackets, `[...]`
- Can contain ranges, specified via a dash, `[a-z]` or individual chars `[a-z8]`
- Support quantifiers, `[0-9]{1,3}`
- NOTE: There are no predefined ranges!

### Groups
- A group is defined with a pair of parentheses `(...)`
- A group can contain `Literals`, `Character Sets` and arbitrarily nested `Groups`, `(hello[a-zA-z]+)*`

### Quantifiers
- zero or more `*`
- zero or one `?`
- one or more `+`
- range `{1,3}`


### Special Characters
- Special characters (below) need to be escaped in all contexts.
```
"(", ")", "[", "]", "{", "}", "-", "+", "*", "?"
```
- To escape a character it must be escaped with a double backslash, e.g. left parentheses
`\\(`
- This need two backslashes, because a single `\ ` is treated by the python interpreter as an escape on the following character.
- Even in cases, where a special character is unambiguously non-special, e.g. `[*]`, can only mean match the literal `*` character, it must still be escaped. `[*]` is an invalid expression.

### Limitations/Gotchas/Notes
- The matching semantics are such that a pattern must fully match to be considered a match. For the `walk` methods `None` means not a match. This is different from a match of zero length, e.g. `(foo)?`
- If a quantifier is not specified it must have exactly one match.
- charset ranges match depend on how lexical comparison is implemented in python
- only supports case-sensitive search
- all operators are greedy. This is noteworthy, because in some cases, a non-greedy match on a sub-group would lead to match on the entire e.g. if matching `(ab)*ab`, the text `abab` will be a non match, since the subexpression `(ab)*` will consume the entire text. This can be avoided by, e.g. `(ab){1,1}ab` would match `abab`
"""
from .pattern_parser import PatternParser  # noqa: F401
from .textwalker import TextWalker  # noqa: F401

__pdoc__ = {}
__pdoc__["textwalker.conftest"] = False
__pdoc__["textwalker.tests"] = False
