import sqlite3
from pathlib import Path
from typing import Optional

def connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON;")
    return con

def run_sql_file(con: sqlite3.Connection, sql_file: Path) -> None:
    sql = sql_file.read_text(encoding="utf-8")
    con.executescript(sql)
    con.commit()

def _has_any_table(con: sqlite3.Connection) -> bool:
    # True si la DB contient déjà des tables “métier”
    cur = con.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT IN ('sqlite_sequence')
        LIMIT 1;
    """)
    return cur.fetchone() is not None

def init_db(con: sqlite3.Connection, schema_path: Path, seed_path: Optional[Path] = None) -> None:
    # ✅ On n'applique le schema.sql que si la DB est vide
    if not _has_any_table(con):
        run_sql_file(con, schema_path)
        if seed_path is not None and seed_path.exists():
            run_sql_file(con, seed_path)

def ensure_panel_prices_columns(con: sqlite3.Connection) -> None:
    cols = {row["name"] for row in con.execute("PRAGMA table_info(panel_prices);").fetchall()}

    if "discount_value" not in cols:
        con.execute("ALTER TABLE panel_prices ADD COLUMN discount_value REAL NOT NULL DEFAULT 0;")
    if "waste_rate_pct" not in cols:
        con.execute("ALTER TABLE panel_prices ADD COLUMN waste_rate_pct REAL NOT NULL DEFAULT 0;")
    if "coefficient" not in cols:
        con.execute("ALTER TABLE panel_prices ADD COLUMN coefficient REAL NOT NULL DEFAULT 1;")

    con.commit()


def ensure_orders_columns(con: sqlite3.Connection) -> None:
    # ⚠️ Ta table orders s'appelle bien "orders" dans schema.sql
    cols = {row["name"] for row in con.execute("PRAGMA table_info(orders);").fetchall()}

    # Schéma actuel: cde_number, delivery_date, customer, notes, created_at
    # On ne crée PAS order_no (sauf si tu veux compat UI ancienne).
    # On garantit juste les colonnes attendues par ton schema.
    if "cde_number" not in cols:
        con.execute("ALTER TABLE orders ADD COLUMN cde_number TEXT;")
    if "delivery_date" not in cols:
        con.execute("ALTER TABLE orders ADD COLUMN delivery_date TEXT;")
    if "customer" not in cols:
        con.execute("ALTER TABLE orders ADD COLUMN customer TEXT;")
    if "notes" not in cols:
        con.execute("ALTER TABLE orders ADD COLUMN notes TEXT;")
    if "created_at" not in cols:
        con.execute("ALTER TABLE orders ADD COLUMN created_at TEXT;")

    con.commit()
    
def ensure_order_parts_columns(con: sqlite3.Connection) -> None:
    cols = {row["name"] for row in con.execute("PRAGMA table_info(order_parts);").fetchall()}

    if "allow_rotate" not in cols:
        con.execute("ALTER TABLE order_parts ADD COLUMN allow_rotate INTEGER NOT NULL DEFAULT 1;")

    if "grain_dir" not in cols:
        con.execute("ALTER TABLE order_parts ADD COLUMN grain_dir TEXT NOT NULL DEFAULT 'Sans';")

    con.commit()