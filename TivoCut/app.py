import sys
import traceback
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMessageBox

from core.lock import SingleInstanceLock
from core.db import connect, init_db
from ui.main_window import MainWindow

from ui.tabs_nesting import NestingTab

def show_fatal_error(title: str, details: str) -> None:
    # On crée une app Qt minimale pour afficher une boîte de dialogue
    app = QApplication.instance() or QApplication(sys.argv)
    QMessageBox.critical(None, title, details)
    sys.exit(1)


def main():
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data"
    db_path = str(data_dir / "tivocut.sqlite")
    lock_path = str(data_dir / "tivocut.lock")

    #self.tabs.addTab(NestingTab(self.con), "Nesting")
    
    schema_path = base_dir / "db" / "schema.sql"
    seed_path = base_dir / "db" / "seed.sql"

    try:
        # Vérifs fichiers SQL
        if not schema_path.exists():
            raise FileNotFoundError(f"schema.sql introuvable: {schema_path}")
        if not seed_path.exists():
            print(f"seed.sql introuvable (OK si volontaire): {seed_path}")

        # Lock
        lock = SingleInstanceLock(lock_path)
        if not lock.acquire():
            raise RuntimeError("Application déjà ouverte (lock actif).")

        try:
            # DB init
            con = connect(db_path)
           
            #print("order_parts columns:")
            #rows = con.execute("PRAGMA table_info(order_parts);").fetchall()
            #for r in rows:
            #   print(r["cid"], r["name"], r["type"], "NOT NULL" if r["notnull"] else "NULL", "DEFAULT", r["dflt_value"])
                
            init_db(con, schema_path=schema_path, seed_path=seed_path if seed_path.exists() else None)

            from core.db import ensure_panel_prices_columns, ensure_orders_columns
            
            from core.db import ensure_order_parts_columns
            ensure_order_parts_columns(con)
            
            init_db(con, schema_path=schema_path, seed_path=seed_path if seed_path.exists() else None)
            
            ensure_panel_prices_columns(con)
            ensure_orders_columns(con)


            # Test DB
            #cur = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            #tables = [r[0] for r in cur.fetchall()]
            #print("Tables DB:", tables)

            # UI
            app = QApplication(sys.argv)
            win = MainWindow(con)
            win.show()
            sys.exit(app.exec())

        finally:
            lock.release()

    except Exception:
        err = traceback.format_exc()
        print(err)  # console
        show_fatal_error("Crash au démarrage", err)


if __name__ == "__main__":
    main()