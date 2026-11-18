

def  init_db():
    create_table_sql = (
        "CREATE TABLE IF NOT EXISTS file_info ("
            "id INTEGER PRIMARY KEY,"
            "filename TEXT not null,"
            "filehash CHAR(64) not null,"
            "filesize INTEGER not null,"
            "mimetype TEXT not null,"
            "gmt_createtime INTEGER not null,"
            "filepath text not null"
        ");"
    )

    create_idx_sql = "CREATE INDEX IF NOT EXISTS idx_file_info_hash ON file_info(filehash);"
