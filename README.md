# Text Walker

![tests](https://github.com/spandanb/textwalker/actions/workflows/run-tests.yml/badge.svg)
![tests](https://github.com/spandanb/textwalker/actions/workflows/python-package.yml/badge.svg)
![tests](https://github.com/spandanb/textwalker/actions/workflows/publish-package.yml/badge.svg)
[![codecov](https://codecov.io/gh/spandanb/textwalker/branch/main/graph/badge.svg?token=SXS209QVCC)](https://codecov.io/gh/spandanb/textwalker)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## [Documentation](http://www.spandanbemby.com/textwalker/)

## Getting Started

`textwalker` is a simple utility to incrementally parse (un|semi)structured text.

The `textwalker` API emulates how a complex regular expression is iteratively constructed.
Typically, when constructing a regex, I'll construct a part of it; test it and build the next part.

Consider trying to parse an SQL table definition:

```
>>> text = """CREATE TABLE dbo.car_inventory
(
    cp_car_sk        integer               not null,
    cp_car_make_id   char(16)              not null,
)
WITH (OPTION (STATS = ON))"""

>>> from text_walker import TextWalker
>>> tw = TextWalker(text)

>>> tw.walk('CREATE')
>>> tw.walk('TABLE')
```
The `TextWalker` class is initialized with the `text` to parse. 
The `walk(pattern)` method consumes and returns the `pattern`. Here, the return value is the literal matched. 
This `pattern` can be a string representing a:
- literal, e.g. `foo` 
- character set, with character ranges and individual characters e.g. `[a-z9]`
- grouping, e.g. `(foo)+`

See supported grammar [here](#section-grammar).

Internally, when `walk` is invoked the `TextWalker` tracks how much of the input text has been matched. 

This is essentially, the key thought behind the design: by making the text parsing stateful, it can be done incrementally, and this reduces the complexity of the expression for matching text and allows combining with python text processing capabilities.

```
>>> table_name_match = tw.walk('dbo.[a-z0-9_]+')
>>> tablename = table_ame_match.replace('dbo.', '')
>>> print(f'table name is {tablename}')

table name is car_inventory

>>> tw.walk('\(')

# now print column names
>>> cols_text, _ = tw.walk_until('WITH')
>>> for col_def in cols_text.split(','):
        col_name = col_def.strip().split(' ')[0]
        print(f'column name is: {}')

column name is cp_car_sk
column name is cp_car_make_id
```

Or trying to parse a phone number, e.g.

```
>>> from textwalker import TextWalker
>>> text = "(+1)123-456-7890"
>>> tw = TextWalker(text)
>>> area_code = tw.walk('(\\(\\+[0-9]+\\))?')
>>> print(f'area code is {area_code}')
```

Note, special characters need to be escaped in all contexts.

```
>>> steps = tw.walk_many(['[0-9]{3,3}', '\\-', '[0-9]{3,3}', '\\-', '[0-9]{4,4}'])
>>> print(f'first 3 digits are {steps[0]}; next 3 digits are {steps[2]}; last 3 digits are {steps[4]}')
first 3 digits are 123; next 3 digits are 456; last 3 digits are 7890
```
## More Examples 
See more examples in `.\examples`

## Installation
Textwalker is available on PyPI:
```
python -m pip install textwalker
```

## [Grammar](#section-grammar)

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

