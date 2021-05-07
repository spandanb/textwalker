"""
some examples on how to use text walker
"""
from textwalker import TextWalker


def parse_phone_number():
    """
    example: parse phone number
    """

    text = "(+1)123-456-7890"
    tw = TextWalker(text)
    area_code = tw.walk('(\\(\\+[0-9]+\\))?')
    print(f'area code is {area_code}')
    steps = tw.walk_many(['[0-9]{3,3}', '\\-', '[0-9]{3,3}', '\\-', '[0-9]{4,4}'])
    print(f'first 3 digits are {steps[0]}; next 3 digits are {steps[2]}; last 3 digits are {steps[4]}')


def parse_tsql_def_0():
    """
    example: parse t-sql table definition for table and column names
    """

    text = """CREATE TABLE dbo.car_inventory
    (
        cp_catalog_page_sk        integer               not null,
        cp_catalog_page_id        char(16)              not null,
        cp_start_date_sk          integer                       ,
        cp_end_date_sk            integer                       ,
        cp_department             varchar(50)                   ,
        cp_catalog_number         integer                       ,
        cp_catalog_page_number    integer                       ,
        cp_description            varchar(100)                  ,
        cp_type                   varchar(100))
    WITH (OPTION (STATS = ON))"""

    tw = TextWalker(text)
    tw.walk_many(['CREATE', 'TABLE'])
    tname_match = tw.walk('dbo.[a-z0-9_]+')
    tablename = tname_match.replace('dbo.', '')
    print(f'table name is {tablename}')
    tw.walk('\(')

    # now attempt to parse columns
    cols_text, _ = tw.walk_until('WITH')

    # use python string functions
    col_names = []
    for col_def in cols_text.split(','):
        col_names.append(col_def.strip().split(' ')[0])
    print(f'columns names are:  {col_names}')


def parse_tsql_def_1():
    """
    example: parse t-sql table definition for table and column names
    """

    text = """CREATE TABLE dbo.call_center
        (
            cc_call_center_sk         integer               not null,
            cc_call_center_id         char(16)              not null,
            cc_company                integer                       ,
            cc_company_name           char(50)                      ,
            cc_street_number          char(10)                      ,
            cc_street_name            varchar(60)                   ,
            cc_street_type            char(15)                      ,
            cc_suite_number           char(10)                      ,
            cc_city                   varchar(60)                   ,
            cc_county                 varchar(30)                   ,
            cc_state                  char(2)                       ,
            cc_zip                    char(10)                      ,
            cc_country                varchar(20)                   ,
            cc_gmt_offset             decimal(5,2)                  ,
            cc_tax_percentage         decimal(5,2))
        WITH (DISTRIBUTION = ROUND_ROBIN
        ,CLUSTERED COLUMNSTORE INDEX)"""

    tw = TextWalker(text)
    tw.walk_many(['CREATE', 'TABLE'])
    tname_match = tw.walk('dbo.[a-z0-9_]+')
    tablename = tname_match.replace('dbo.', '')
    print(f'table name is {tablename}')
    tw.walk('\(')

    # now attempt to parse columns
    cols_text, _ = tw.walk_until('WITH')

    # use python string functions
    col_names = []
    # split on newline
    for col_def in cols_text.split('\n'):
        col_name = col_def.strip().split(' ')[0]
        if len(col_name) > 0:
            col_names.append(col_name)
    print(f'columns names are:  {col_names}')


if __name__ == '__main__':
    parse_tsql_def_0()
    parse_tsql_def_1()