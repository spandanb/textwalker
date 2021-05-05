# Text Walker

## Overview

![tests](https://github.com/spandanb/textwalker/actions/workflows/run-tests.yml/badge.svg)
![tests](https://github.com/spandanb/textwalker/actions/workflows/python-package.yml/badge.svg)
![tests](https://github.com/spandanb/textwalker/actions/workflows/publish-package.yml/badge.svg)

[docs](http://www.spandanbemby.com/textwalker/)

`TextWalker` is a simple utility that allows intuitive way to parse unstructured text.

The `TextWalker` API emulates how a complex regular expression is iteratively constructed.
Typically, when constructing a regex, I'll construct a part of it; test it and build the next part.

```
>>> text = """CREATE TABLE dbo.car_inventory
(
    cp_car_sk        integer               not null,
    cp_car_make_id   char(16)              not null,
)
WITH (OPTION (STATS = ON))"""

>>> from text_walker import TextWalker
>>> tw = TextWalker(text)

>>> tw.walk_many(['CREATE', 'TABLE'])
>>> tname_match = tw.walk('dbo.[a-z0-9_]+')
>>> tablename = tname_match.replace('dbo.', '')
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

## Installation
Textwalker is available on PyPI:
```
python -m pip install requests
```

## Supported Grammar
```
# parse literal

notes: 
- all patterns must fully match, e.g. pattern = "abcd", and text ="abc" -> ""

limitations
- no support for predefined char sets
- charset ranges match depend on how lexical comparison is implemented in python
- only supports case sensitive search
```



