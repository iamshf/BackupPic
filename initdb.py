
import Libs.MySqlite as MySqlite;

def  init_db():
    create_table_sql = (
        "CREATE TABLE IF NOT EXISTS file_info ("
            "id INTEGER PRIMARY KEY,"
            "filename TEXT not null,"
            "filehash CHAR(64) not null unique,"
            "filesize INTEGER not null default 0,"
            "mimetype TEXT not null default 'application/octet-stream',"
            "gmt_createtime INTEGER not null,"
            "filepath text not null,"
            "extension text not null"
        ")"
    )


    with MySqlite.MySqlite() as db:
        db.execute(create_table_sql)

        sql = r"select name from sqlite_master where type='table' and name='file_info';"
        result = db.query_one(sql)
        if(result is None):
            print("初始化失败")
        else:
            print("初始化成功")
