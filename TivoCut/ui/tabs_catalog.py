import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
    QTableWidget, QTableWidgetItem, QMessageBox, QInputDialog, QLabel
)
from core.repo import fetch_all, exec_one
from ui.i18n import grain_rule_to_fr, grain_rule_from_fr

class CatalogTab(QWidget):
    def __init__(self, con: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.con = con

        layout = QVBoxLayout(self)
        self.subtabs = QTabWidget()
        layout.addWidget(self.subtabs, 1)

        self.tbl_formats = self._make_table(["ID", "Largeur (mm)", "Hauteur (mm)", "Label"])
        self.tbl_suppliers = self._make_table(["ID", "Nom", "Notes"])
        self.tbl_materials = self._make_table(["ID", "Nom"])
        self.tbl_cores = self._make_table(["ID", "Nom", "Notes"])
        self.tbl_finishes = self._make_table(["ID", "Nom", "Multiplier", "Surcharge", "Notes"])
        self.tbl_colors = self._make_table(["ID", "Matière", "Couleur", "Grain", "Notes"])

        self.subtabs.addTab(self._wrap_crud(self.tbl_formats, self.add_format, self.edit_format, self.delete_format, self.reload_formats), "Formats")
        self.subtabs.addTab(self._wrap_crud(self.tbl_suppliers, self.add_supplier, self.edit_supplier, self.delete_supplier, self.reload_suppliers), "Fournisseurs")
        self.subtabs.addTab(self._wrap_crud(self.tbl_materials, self.add_material, self.edit_material, self.delete_material, self.reload_materials), "Matières")
        self.subtabs.addTab(self._wrap_crud(self.tbl_cores, self.add_core, self.edit_core, self.delete_core, self.reload_cores), "Âmes")
        self.subtabs.addTab(self._wrap_crud(self.tbl_finishes, self.add_finish, self.edit_finish, self.delete_finish, self.reload_finishes), "Finitions")
        self.subtabs.addTab(self._wrap_crud(self.tbl_colors, self.add_color, self.edit_color, self.delete_color, self.reload_colors), "Couleurs")

        layout.addWidget(QLabel("Astuce: sélectionne une ligne puis Modifier/Supprimer."))

        self.reload_all()

    # ---------------- UI helpers ----------------
    def _make_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.setSelectionMode(QTableWidget.SingleSelection)
        t.setAlternatingRowColors(True)
        return t

    def _wrap_crud(self, table, add_fn, edit_fn, del_fn, reload_fn):
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(table, 1)

        bar = QHBoxLayout()
        btn_add = QPushButton("Ajouter")
        btn_edit = QPushButton("Modifier")
        btn_del = QPushButton("Supprimer")
        btn_reload = QPushButton("Rafraîchir")

        btn_add.clicked.connect(add_fn)
        btn_edit.clicked.connect(lambda: edit_fn(table))
        btn_del.clicked.connect(lambda: del_fn(table))
        btn_reload.clicked.connect(reload_fn)

        bar.addWidget(btn_add)
        bar.addWidget(btn_edit)
        bar.addWidget(btn_del)
        bar.addWidget(btn_reload)
        bar.addStretch(1)
        v.addLayout(bar)
        return w

    def _selected_id(self, table) -> int | None:
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        if not item:
            return None
        try:
            return int(item.text())
        except ValueError:
            return None

    def _confirm_delete(self, label: str) -> bool:
        return QMessageBox.question(
            self,
            "Confirmation",
            f"Supprimer : {label} ?\nCette action est irréversible.",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.Yes

    def _safe_exec(self, fn):
        try:
            fn()
        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Suppression impossible", f"Référence en cours d'utilisation.\n\nDétail:\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # ---------------- Reloaders ----------------
    def reload_all(self):
        self.reload_formats()
        self.reload_suppliers()
        self.reload_materials()
        self.reload_cores()
        self.reload_finishes()
        self.reload_colors()

    def reload_formats(self):
        rows = fetch_all(self.con, "SELECT id, width_mm, height_mm, label FROM panel_formats ORDER BY width_mm, height_mm;")
        self._fill(self.tbl_formats, rows, ["id", "width_mm", "height_mm", "label"])

    def reload_suppliers(self):
        rows = fetch_all(self.con, "SELECT id, name, COALESCE(notes,'') as notes FROM suppliers ORDER BY name;")
        self._fill(self.tbl_suppliers, rows, ["id", "name", "notes"])

    def reload_materials(self):
        rows = fetch_all(self.con, "SELECT id, name FROM materials ORDER BY name;")
        self._fill(self.tbl_materials, rows, ["id", "name"])

    def reload_cores(self):
        rows = fetch_all(self.con, "SELECT id, name, COALESCE(notes,'') as notes FROM cores ORDER BY name;")
        self._fill(self.tbl_cores, rows, ["id", "name", "notes"])

    def reload_finishes(self):
        rows = fetch_all(self.con, "SELECT id, name, multiplier, surcharge, COALESCE(notes,'') as notes FROM finishes ORDER BY name;")
        self._fill(self.tbl_finishes, rows, ["id", "name", "multiplier", "surcharge", "notes"])

    def reload_colors(self):
        rows = fetch_all(self.con, """
            SELECT c.id,
                   m.name as material,
                   c.name as color,
                   c.grain_rule as grain,
                   COALESCE(c.notes,'') as notes
            FROM colors c
            JOIN materials m ON m.id = c.material_id
            ORDER BY m.name, c.name;
        """)

        self.tbl_colors.setRowCount(0)
        for r in rows:
            i = self.tbl_colors.rowCount()
            self.tbl_colors.insertRow(i)
            self.tbl_colors.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.tbl_colors.setItem(i, 1, QTableWidgetItem(r["material"]))
            self.tbl_colors.setItem(i, 2, QTableWidgetItem(r["color"]))
            self.tbl_colors.setItem(i, 3, QTableWidgetItem(grain_rule_to_fr(r["grain"])))
            self.tbl_colors.setItem(i, 4, QTableWidgetItem(r["notes"]))

    def _fill(self, table, rows, cols):
        table.setRowCount(0)
        for r in rows:
            row_i = table.rowCount()
            table.insertRow(row_i)
            for c_i, col in enumerate(cols):
                table.setItem(row_i, c_i, QTableWidgetItem(str(r[col])))

    # ---------------- CRUD: Formats ----------------
    def add_format(self):
        label, ok = QInputDialog.getText(self, "Nouveau format", "Label (ex: 900x2100):")
        if not ok or not label.strip():
            return
        w, ok2 = QInputDialog.getInt(self, "Nouveau format", "Largeur (mm):", 900, 1, 10000, 1)
        if not ok2: return
        h, ok3 = QInputDialog.getInt(self, "Nouveau format", "Hauteur (mm):", 2100, 1, 10000, 1)
        if not ok3: return

        self._safe_exec(lambda: (exec_one(self.con,
            "INSERT INTO panel_formats(width_mm,height_mm,label) VALUES (?,?,?);",
            (w, h, label.strip())), self.reload_formats()))

    def edit_format(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        row = fetch_all(self.con, "SELECT id, width_mm, height_mm, label FROM panel_formats WHERE id=?;", (id_,))
        if not row: return
        r = row[0]
        label, ok = QInputDialog.getText(self, "Modifier format", "Label:", text=r["label"])
        if not ok or not label.strip(): return
        w, ok2 = QInputDialog.getInt(self, "Modifier format", "Largeur (mm):", int(r["width_mm"]), 1, 10000, 1)
        if not ok2: return
        h, ok3 = QInputDialog.getInt(self, "Modifier format", "Hauteur (mm):", int(r["height_mm"]), 1, 10000, 1)
        if not ok3: return

        self._safe_exec(lambda: (exec_one(self.con,
            "UPDATE panel_formats SET width_mm=?, height_mm=?, label=? WHERE id=?;",
            (w, h, label.strip(), id_)), self.reload_formats()))

    def delete_format(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        if not self._confirm_delete(f"Format ID {id_}"):
            return
        self._safe_exec(lambda: (exec_one(self.con, "DELETE FROM panel_formats WHERE id=?;", (id_,)), self.reload_formats()))

    # ---------------- CRUD: Suppliers ----------------
    def add_supplier(self):
        name, ok = QInputDialog.getText(self, "Nouveau fournisseur", "Nom:")
        if not ok or not name.strip(): return
        self._safe_exec(lambda: (exec_one(self.con, "INSERT INTO suppliers(name) VALUES (?);", (name.strip(),)), self.reload_suppliers()))

    def edit_supplier(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        row = fetch_all(self.con, "SELECT id, name, COALESCE(notes,'') as notes FROM suppliers WHERE id=?;", (id_,))
        if not row: return
        r = row[0]
        name, ok = QInputDialog.getText(self, "Modifier fournisseur", "Nom:", text=r["name"])
        if not ok or not name.strip(): return
        notes, ok2 = QInputDialog.getText(self, "Modifier fournisseur", "Notes:", text=r["notes"])
        if not ok2: return
        self._safe_exec(lambda: (exec_one(self.con, "UPDATE suppliers SET name=?, notes=? WHERE id=?;", (name.strip(), notes, id_)), self.reload_suppliers()))

    def delete_supplier(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        if not self._confirm_delete(f"Fournisseur ID {id_}"):
            return
        self._safe_exec(lambda: (exec_one(self.con, "DELETE FROM suppliers WHERE id=?;", (id_,)), self.reload_suppliers()))

    # ---------------- CRUD: Materials ----------------
    def add_material(self):
        name, ok = QInputDialog.getText(self, "Nouvelle matière", "Nom (PVC/ALU/HPL…):")
        if not ok or not name.strip(): return
        self._safe_exec(lambda: (exec_one(self.con, "INSERT INTO materials(name) VALUES (?);", (name.strip(),)), self.reload_materials()))

    def edit_material(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        row = fetch_all(self.con, "SELECT id, name FROM materials WHERE id=?;", (id_,))
        if not row: return
        r = row[0]
        name, ok = QInputDialog.getText(self, "Modifier matière", "Nom:", text=r["name"])
        if not ok or not name.strip(): return
        self._safe_exec(lambda: (exec_one(self.con, "UPDATE materials SET name=? WHERE id=?;", (name.strip(), id_)), self.reload_materials()))

    def delete_material(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        if not self._confirm_delete(f"Matière ID {id_}"):
            return
        self._safe_exec(lambda: (exec_one(self.con, "DELETE FROM materials WHERE id=?;", (id_,)), self.reload_materials()))

    # ---------------- CRUD: Cores ----------------
    def add_core(self):
        name, ok = QInputDialog.getText(self, "Nouvelle âme", "Nom (ex: XPS33):")
        if not ok or not name.strip(): return
        notes, ok2 = QInputDialog.getText(self, "Nouvelle âme", "Notes (optionnel):")
        if not ok2: return
        self._safe_exec(lambda: (exec_one(self.con, "INSERT INTO cores(name,notes) VALUES (?,?);", (name.strip(), notes)), self.reload_cores()))

    def edit_core(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        row = fetch_all(self.con, "SELECT id, name, COALESCE(notes,'') as notes FROM cores WHERE id=?;", (id_,))
        if not row: return
        r = row[0]
        name, ok = QInputDialog.getText(self, "Modifier âme", "Nom:", text=r["name"])
        if not ok or not name.strip(): return
        notes, ok2 = QInputDialog.getText(self, "Modifier âme", "Notes:", text=r["notes"])
        if not ok2: return
        self._safe_exec(lambda: (exec_one(self.con, "UPDATE cores SET name=?, notes=? WHERE id=?;", (name.strip(), notes, id_)), self.reload_cores()))

    def delete_core(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        if not self._confirm_delete(f"Âme ID {id_}"):
            return
        self._safe_exec(lambda: (exec_one(self.con, "DELETE FROM cores WHERE id=?;", (id_,)), self.reload_cores()))

    # ---------------- CRUD: Finishes ----------------
    def add_finish(self):
        name, ok = QInputDialog.getText(self, "Nouvelle finition", "Nom (UNICOLORE/BICOLORE…):")
        if not ok or not name.strip(): return
        mult, ok2 = QInputDialog.getDouble(self, "Nouvelle finition", "Multiplier:", 1.0, 0.0, 100.0, 3)
        if not ok2: return
        sur, ok3 = QInputDialog.getDouble(self, "Nouvelle finition", "Surcharge (€):", 0.0, -100000.0, 100000.0, 2)
        if not ok3: return
        notes, ok4 = QInputDialog.getText(self, "Nouvelle finition", "Notes (optionnel):")
        if not ok4: return
        self._safe_exec(lambda: (exec_one(self.con,
            "INSERT INTO finishes(name,multiplier,surcharge,notes) VALUES (?,?,?,?);",
            (name.strip(), mult, sur, notes)), self.reload_finishes()))

    def edit_finish(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        row = fetch_all(self.con, "SELECT * FROM finishes WHERE id=?;", (id_,))
        if not row: return
        r = row[0]
        name, ok = QInputDialog.getText(self, "Modifier finition", "Nom:", text=r["name"])
        if not ok or not name.strip(): return
        mult, ok2 = QInputDialog.getDouble(self, "Modifier finition", "Multiplier:", float(r["multiplier"]), 0.0, 100.0, 3)
        if not ok2: return
        sur, ok3 = QInputDialog.getDouble(self, "Modifier finition", "Surcharge (€):", float(r["surcharge"]), -100000.0, 100000.0, 2)
        if not ok3: return
        notes, ok4 = QInputDialog.getText(self, "Modifier finition", "Notes:", text=r["notes"] or "")
        if not ok4: return
        self._safe_exec(lambda: (exec_one(self.con,
            "UPDATE finishes SET name=?, multiplier=?, surcharge=?, notes=? WHERE id=?;",
            (name.strip(), mult, sur, notes, id_)), self.reload_finishes()))

    def delete_finish(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        if not self._confirm_delete(f"Finition ID {id_}"):
            return
        self._safe_exec(lambda: (exec_one(self.con, "DELETE FROM finishes WHERE id=?;", (id_,)), self.reload_finishes()))

    # ---------------- CRUD: Colors ----------------
    def add_color(self):
        mats = fetch_all(self.con, "SELECT id, name FROM materials ORDER BY name;")
        if not mats:
            QMessageBox.warning(self, "Info", "Ajoute d'abord des matières.")
            return

        mat_names = [m["name"] for m in mats]
        mat_name, ok = QInputDialog.getItem(self, "Couleur", "Matière:", mat_names, 0, False)
        if not ok: return
        mat_id = next(m["id"] for m in mats if m["name"] == mat_name)

        color, ok2 = QInputDialog.getText(self, "Couleur", "Nom couleur (ex: Blanc, RAL7016…):")
        if not ok2 or not color.strip(): return

        grain, ok3 = QInputDialog.getItem(self, "Couleur", "Règle fibre:", ["Sans","Optionnelle","Obligatoire"], 0, False)
        if not ok3: return

        notes, ok4 = QInputDialog.getText(self, "Couleur", "Notes (optionnel):")
        if not ok4: return

        grain_db = grain_rule_from_fr(grain)

        self._safe_exec(lambda: (exec_one(self.con,
            "INSERT INTO colors(material_id,name,grain_rule,notes) VALUES (?,?,?,?);",
            (mat_id, color.strip(), grain_db, notes)), self.reload_colors()))

    def edit_color(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        row = fetch_all(self.con, """
            SELECT c.id, c.material_id, c.name, c.grain_rule, COALESCE(c.notes,'') as notes
            FROM colors c WHERE c.id=?;
        """, (id_,))
        if not row: return
        r = row[0]

        mats = fetch_all(self.con, "SELECT id, name FROM materials ORDER BY name;")
        mat_names = [m["name"] for m in mats]
        current_mat = next(m["name"] for m in mats if m["id"] == r["material_id"])

        mat_name, ok = QInputDialog.getItem(self, "Modifier couleur", "Matière:", mat_names, mat_names.index(current_mat), False)
        if not ok: return
        mat_id = next(m["id"] for m in mats if m["name"] == mat_name)

        color, ok2 = QInputDialog.getText(self, "Modifier couleur", "Nom couleur:", text=r["name"])
        if not ok2 or not color.strip(): return

        grain_fr_current = grain_rule_to_fr(r["grain_rule"])

        grain, ok3 = QInputDialog.getItem(
            self,
            "Modifier couleur",
            "Règle fibre:",
            ["Sans", "Optionnelle", "Obligatoire"],
            ["Sans", "Optionnelle", "Obligatoire"].index(grain_fr_current),
            False
        )
        if not ok3:
            return

        grain_db = grain_rule_from_fr(grain)

        notes, ok4 = QInputDialog.getText(self, "Modifier couleur", "Notes:", text=r["notes"])
        if not ok4: return

        self._safe_exec(lambda: (exec_one(self.con,
            "UPDATE colors SET material_id=?, name=?, grain_rule=?, notes=? WHERE id=?;",
            (mat_id, color.strip(), grain_db, notes, id_)), self.reload_colors()))

    def delete_color(self, table):
        id_ = self._selected_id(table)
        if not id_:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        # label utile
        name = table.item(table.currentRow(), 2).text() if table.currentRow() >= 0 else f"ID {id_}"
        if not self._confirm_delete(f"Couleur {name} (ID {id_})"):
            return
        self._safe_exec(lambda: (exec_one(self.con, "DELETE FROM colors WHERE id=?;", (id_,)), self.reload_colors()))