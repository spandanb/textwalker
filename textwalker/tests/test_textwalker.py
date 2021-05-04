from textwalker import TextWalker


def test_parse_sql_table_definition():
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
    assert tablename == "car_inventory", "table name did not match"

    tw.walk("\\(")

    # now attempt to parse columns
    cols_text, _ = tw.walk_until("WITH")

    # use python string functions
    col_names = []
    for col_def in cols_text.split(","):
        col_names.append(col_def.strip().split(" ")[0])
    assert col_names == [
        "cp_catalog_page_sk",
        "cp_catalog_page_id",
        "cp_start_date_sk",
        "cp_end_date_sk",
        "cp_department",
        "cp_catalog_number",
        "cp_catalog_page_number",
        "cp_description",
        "cp_type",
    ]
