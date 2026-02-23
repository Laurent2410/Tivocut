import sqlite3
from typing import List, Tuple

def fetch_all(con: sqlite3.Connection, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    cur = con.execute(sql, params)
    return cur.fetchall()

def exec_one(con: sqlite3.Connection, sql: str, params: tuple = ()) -> None:
    con.execute(sql, params)
    con.commit()

def exec_many(con: sqlite3.Connection, sql: str, rows: List[Tuple]) -> None:
    con.executemany(sql, rows)
    con.commit()