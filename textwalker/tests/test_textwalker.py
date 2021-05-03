from textwalker import TextWalker


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
    tw.walk_many(["CREATE", "TABLE"])
    tname_match = tw.walk("dbo.[a-z0-9_]+")
    tablename = tname_match.replace("dbo.", "")
    print(f"table name is {tablename}")
    tw.walk("\(")

    # now attempt to parse columns
    cols_text, _ = tw.walk_until("WITH")

    # use python string functions
    col_names = []
    for col_def in cols_text.split(","):
        col_names.append(col_def.strip().split(" ")[0])
    print(f"columns names are:  {col_names}")
