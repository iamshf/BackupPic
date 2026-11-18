import sqlite3
import queue
import threading
from typing import List, Tuple, Optional, Any
import configparser

class MySqlite():
    def __init__(self, db_path: str = None, max_conn: int = 5):
        self.db_path = db_path
        if self.db_path is None:
            config = configparser.ConfigParser()
            config.read('config.ini')
            self.db_path = config.get('database', 'db_path', fallback='file_info.db')
        
        self.max_conn = max_conn
        self._pool = queue.Queue(maxsize=max_conn)
        self._lock = threading.Lock()
        self._closed = False
        self._auto_close = False

    def _create_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def get_conn(self) -> sqlite3.Connection:
        if self._closed:
            raise RuntimeError("连接池已经关闭，无法获取连接")
        try:
            conn = self._pool.get(block=False)
        except queue.Empty:
            with self._lock:
                if self._pool.qsize() < self.max_conn:
                    conn = self._create_conn()
                else:
                    conn = self._pool.get(block=True)
        return conn

    def return_conn(self, conn: sqlite3.Connection):
        if self._closed:
            conn.close()
            return
        self._pool.put(conn)

    def close_pool(self):
        with self._lock:
            self._closed = True
        while not self._pool.empty():
            conn = self._pool.get()
            conn.close()

    def acquire_conn(self):
        class ConnCtx:
            def __init__(self, pool: MySqlite):
                self.pool = pool
                self.conn: Optional[sqlite3.Connection] = None
            def __enter__(self):
                self.conn = self.pool.get_conn()
                return self.conn
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.conn is not None:
                    self.pool.return_conn(self.conn)
        return ConnCtx(self)

    def __enter__(self):
        self._auto_close = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._auto_close:
            self.close_pool()

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> int:
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount
        finally:
            cur.close()
            self.return_conn(conn)

    def executemany(self, sql: str, params_list: List[Tuple[Any, ...]]) -> int:
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            cur.executemany(sql, params_list)
            conn.commit()
            return cur.rowcount
        finally:
            cur.close()
            self.return_conn(conn)

    def query_one(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            cur.execute(sql, params)
            return cur.fetchone()
        finally:
            cur.close()
            self.return_conn(conn)

    def query_all(self, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            cur.execute(sql, params)
            return cur.fetchall()
        finally:
            cur.close()
            self.return_conn(conn)

    def transaction(self, func, *args, **kwargs):
        conn = self.get_conn()
        cur = conn.cursor()
        try:
            res = func(cur, *args, **kwargs)
            conn.commit()
            return res
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cur.close()
            self.return_conn(conn)