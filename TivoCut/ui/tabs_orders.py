import sqlite3
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QInputDialog, QLabel, QSplitter
)
from PySide6.QtCore import Qt

from core.repo import fetch_all, exec_one
from datetime import datetime
from core.repo import fetch_all, exec_one
from ui.i18n import grain_constraint_from_fr, grain_constraint_to_fr

class OrdersTab(QWidget):
    def __init__(self, con: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.con = con
        self.current_order_id = None

        root = QVBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        # ---------------- LEFT: Orders ----------------
        left = QWidget()
        left_l = QVBoxLayout(left)

        left_l.addWidget(QLabel("Commandes"))
        self.tbl_orders = QTableWidget(0, 3)
        self.tbl_orders.setHorizontalHeaderLabels(["ID", "N° commande", "Livraison"])
        self.tbl_orders.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_orders.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_orders.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl_orders.setAlternatingRowColors(True)
        left_l.addWidget(self.tbl_orders, 1)

        bar_o = QHBoxLayout()
        btn_o_add = QPushButton("Ajouter")
        btn_o_edit = QPushButton("Modifier")
        btn_o_del = QPushButton("Supprimer")
        btn_o_reload = QPushButton("Rafraîchir")
        bar_o.addWidget(btn_o_add)
        bar_o.addWidget(btn_o_edit)
        bar_o.addWidget(btn_o_del)
        bar_o.addWidget(btn_o_reload)
        bar_o.addStretch(1)
        left_l.addLayout(bar_o)

        btn_o_add.clicked.connect(self.add_order)
        btn_o_edit.clicked.connect(self.edit_order)
        btn_o_del.clicked.connect(self.delete_order)
        btn_o_reload.clicked.connect(self.reload_orders)

        self.tbl_orders.itemSelectionChanged.connect(self.on_order_selected)

        splitter.addWidget(left)

        # ---------------- RIGHT: Parts ----------------
        right = QWidget()
        right_l = QVBoxLayout(right)

        right_l.addWidget(QLabel("Pièces de la commande"))
        self.tbl_parts = QTableWidget(0, 9)
        self.tbl_parts.setHorizontalHeaderLabels([
            "ID", "Libellé", "Largeur (mm)", "Hauteur (mm)", "Qté", "Couleur EXT", "Couleur INT", "Rotation", "Fibre"
        ])
        self.tbl_parts.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_parts.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_parts.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl_parts.setAlternatingRowColors(True)
        right_l.addWidget(self.tbl_parts, 1)

        bar_p = QHBoxLayout()
        btn_p_add = QPushButton("Ajouter pièce")
        btn_p_edit = QPushButton("Modifier")
        btn_p_dup = QPushButton("Dupliquer")
        btn_p_del = QPushButton("Supprimer")
        btn_p_reload = QPushButton("Rafraîchir")
        bar_p.addWidget(btn_p_add)
        bar_p.addWidget(btn_p_edit)
        bar_p.addWidget(btn_p_dup)
        bar_p.addWidget(btn_p_del)
        bar_p.addWidget(btn_p_reload)
        bar_p.addStretch(1)
        right_l.addLayout(bar_p)

        btn_p_add.clicked.connect(self.add_part)
        btn_p_edit.clicked.connect(self.edit_part)
        btn_p_dup.clicked.connect(self.duplicate_part)
        btn_p_del.clicked.connect(self.delete_part)
        btn_p_reload.clicked.connect(self.reload_parts)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.reload_orders()

    # ---------------- Helpers ----------------
    def _selected_id(self, table: QTableWidget) -> int | None:
        row = table.currentRow()
        if row < 0:
            return None
        try:
            return int(table.item(row, 0).text())
        except Exception:
            return None

    # ---------------- Orders ----------------
    def reload_orders(self):
        rows = fetch_all(self.con, """
            SELECT id, cde_number, delivery_date
            FROM orders
            ORDER BY id DESC;
        """)
        self.tbl_orders.setRowCount(0)
        for r in rows:
            i = self.tbl_orders.rowCount()
            self.tbl_orders.insertRow(i)
            self.tbl_orders.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.tbl_orders.setItem(i, 1, QTableWidgetItem(r["cde_number"]))
            self.tbl_orders.setItem(i, 2, QTableWidgetItem(r["delivery_date"] or ""))

        # si plus rien sélectionné
        if self.tbl_orders.rowCount() == 0:
            self.current_order_id = None
            self.tbl_parts.setRowCount(0)

    def on_order_selected(self):
        oid = self._selected_id(self.tbl_orders)
        self.current_order_id = oid
        self.reload_parts()

    def add_order(self):
        cde_number, ok = QInputDialog.getText(self, "Nouvelle commande", "N° commande:")
        if not ok or not cde_number.strip():
            return

        delivery, ok2 = QInputDialog.getText(self, "Nouvelle commande", "Date livraison (YYYY-MM-DD):")
        if not ok2:
            return
        if not delivery or not delivery.strip():
            QMessageBox.warning(self, "Info", "La date de livraison est obligatoire.")
            return

        created_at = datetime.now().isoformat(timespec="seconds")

        try:
            exec_one(
                self.con,
                "INSERT INTO orders(cde_number, delivery_date, created_at) VALUES (?,?,?);",
                (cde_number.strip(), delivery.strip(), created_at)
            )
            self.reload_orders()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def edit_order(self):
        oid = self._selected_id(self.tbl_orders)
        if not oid:
            QMessageBox.information(self, "Info", "Sélectionne une commande.")
            return
        row = fetch_all(self.con, "SELECT id, cde_number, delivery_date FROM orders WHERE id=?;", (oid,))
        if not row:
            return
        r = row[0]

        order_no, ok = QInputDialog.getText(self, "Modifier commande", "N° commande:", text=r["cde_number"])
        if not ok or not order_no.strip():
            return
        delivery, ok2 = QInputDialog.getText(self, "Modifier commande", "Date livraison (YYYY-MM-DD):",
                                             text=r["delivery_date"] or "")
        if not ok2:
            return
        try:
            exec_one(self.con, "UPDATE orders SET cde_number=?, delivery_date=? WHERE id=?;",
                    (order_no.strip(), delivery.strip(), oid))
            self.reload_orders()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def delete_order(self):
        oid = self._selected_id(self.tbl_orders)
        if not oid:
            QMessageBox.information(self, "Info", "Sélectionne une commande.")
            return
        if QMessageBox.question(self, "Confirmation", f"Supprimer la commande ID {oid} ?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            exec_one(self.con, "DELETE FROM orders WHERE id=?;", (oid,))
            self.reload_orders()
        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Suppression impossible", f"Commande utilisée.\n\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # ---------------- Parts ----------------
    def reload_parts(self):
        self.tbl_parts.setRowCount(0)
        if not self.current_order_id:
            return

        rows = fetch_all(self.con, """
            SELECT
                p.id, p.label, p.width_mm, p.height_mm, p.qty,
                cf.name AS color_ext,
                cb.name AS color_int,
                p.rotation_allowed,
                p.grain_constraint
            FROM order_parts p
            JOIN colors cf ON cf.id = p.color_front_id
            LEFT JOIN colors cb ON cb.id = p.color_back_id
            WHERE p.order_id=?
            ORDER BY p.id ASC;
        """, (self.current_order_id,))

        for r in rows:
            i = self.tbl_parts.rowCount()
            self.tbl_parts.insertRow(i)
            self.tbl_parts.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.tbl_parts.setItem(i, 1, QTableWidgetItem(r["label"] or ""))
            self.tbl_parts.setItem(i, 2, QTableWidgetItem(str(r["width_mm"])))
            self.tbl_parts.setItem(i, 3, QTableWidgetItem(str(r["height_mm"])))
            self.tbl_parts.setItem(i, 4, QTableWidgetItem(str(r["qty"])))
            #self.tbl_parts.setItem(i, 5, QTableWidgetItem("Oui" if r["rotation_allowed"] else "Non"))
            #self.tbl_parts.setItem(i, 6, QTableWidgetItem(grain_constraint_to_fr(r["grain_constraint"])))
            
            self.tbl_parts.setItem(i, 5, QTableWidgetItem(r["color_ext"] or ""))
            self.tbl_parts.setItem(i, 6, QTableWidgetItem(r["color_int"] or "—"))

            self.tbl_parts.setItem(i, 7, QTableWidgetItem("Oui" if r["rotation_allowed"] else "Non"))
            # si tu as mis le mapping DB->FR pour grain_constraint :
            self.tbl_parts.setItem(i, 8, QTableWidgetItem(grain_constraint_to_fr(r["grain_constraint"])))

    def add_part(self):
        if not self.current_order_id:
            QMessageBox.information(self, "Info", "Sélectionne d'abord une commande.")
            return

        # label NOT NULL
        label, ok = QInputDialog.getText(self, "Nouvelle pièce", "Libellé (obligatoire):")
        if not ok or not label.strip():
            QMessageBox.warning(self, "Info", "Le libellé est obligatoire.")
            return

        w, ok2 = QInputDialog.getInt(self, "Nouvelle pièce", "Largeur (mm):", 500, 1, 10000, 1)
        if not ok2:
            return
        h, ok3 = QInputDialog.getInt(self, "Nouvelle pièce", "Hauteur (mm):", 500, 1, 10000, 1)
        if not ok3:
            return
        qty, ok4 = QInputDialog.getInt(self, "Nouvelle pièce", "Quantité:", 1, 1, 100000, 1)
        if not ok4:
            return

        # rotation_allowed NOT NULL
        rot, ok5 = QInputDialog.getItem(self, "Nouvelle pièce", "Rotation autorisée ?", ["Oui", "Non"], 0, False)
        if not ok5:
            return
        rotation_allowed = 1 if rot == "Oui" else 0

        # grain_constraint NOT NULL
        grain_fr, ok6 = QInputDialog.getItem(
            self, "Nouvelle pièce", "Contrainte fibre:", ["Sans", "Vertical", "Horizontal"], 0, False
        )
        if not ok6:
            return
        grain_constraint = grain_constraint_from_fr(grain_fr)

        # --- catalogue : material_id / core_id / thickness_mm / color_front_id / finish_id
        mats = fetch_all(self.con, "SELECT id, name FROM materials ORDER BY name;")
        if not mats:
            QMessageBox.warning(self, "Catalogue incomplet", "Ajoute d'abord des matières (Catalogue).")
            return
        mat_names = [m["name"] for m in mats]
        mat_name, okm = QInputDialog.getItem(self, "Nouvelle pièce", "Matière:", mat_names, 0, False)
        if not okm:
            return
        material_id = next(m["id"] for m in mats if m["name"] == mat_name)

        cores = fetch_all(self.con, "SELECT id, name FROM cores ORDER BY name;")
        if not cores:
            QMessageBox.warning(self, "Catalogue incomplet", "Ajoute d'abord des âmes (Catalogue).")
            return
        core_names = [c["name"] for c in cores]
        core_name, okc = QInputDialog.getItem(self, "Nouvelle pièce", "Âme:", core_names, 0, False)
        if not okc:
            return
        core_id = next(c["id"] for c in cores if c["name"] == core_name)

        thickness_mm, okt = QInputDialog.getInt(self, "Nouvelle pièce", "Épaisseur (mm):", 36, 1, 200, 1)
        if not okt:
            return

        finishes = fetch_all(self.con, "SELECT id, name FROM finishes ORDER BY name;")
        if not finishes:
            QMessageBox.warning(self, "Catalogue incomplet", "Ajoute d'abord des finitions (Catalogue).")
            return
        fin_names = [f["name"] for f in finishes]
        fin_name, okf = QInputDialog.getItem(self, "Nouvelle pièce", "Finition:", fin_names, 0, False)
        if not okf:
            return
        finish_id = next(f["id"] for f in finishes if f["name"] == fin_name)

        # couleurs filtrées par matière
        cols = fetch_all(self.con, "SELECT id, name FROM colors WHERE material_id=? ORDER BY name;", (material_id,))
        if not cols:
            QMessageBox.warning(self, "Catalogue incomplet", "Ajoute des couleurs pour cette matière (Catalogue).")
            return
        col_names = [c["name"] for c in cols]

        front_name, okcf = QInputDialog.getItem(self, "Nouvelle pièce", "Couleur face:", col_names, 0, False)
        if not okcf:
            return
        color_front_id = next(c["id"] for c in cols if c["name"] == front_name)

        back_mode, okb = QInputDialog.getItem(self, "Nouvelle pièce", "Couleur dos:", ["Identique", "Choisir…"], 0, False)
        if not okb:
            return
        color_back_id = None
        if back_mode == "Choisir…":
            back_name, okcb = QInputDialog.getItem(self, "Nouvelle pièce", "Couleur dos:", col_names, 0, False)
            if not okcb:
                return
            color_back_id = next(c["id"] for c in cols if c["name"] == back_name)

        notes, okn = QInputDialog.getText(self, "Nouvelle pièce", "Notes (optionnel):")
        if not okn:
            return

        try:
            exec_one(self.con, """
                INSERT INTO order_parts(
                    order_id, label, qty, width_mm, height_mm,
                    material_id, core_id, thickness_mm,
                    color_front_id, color_back_id, finish_id,
                    grain_constraint, rotation_allowed,
                    notes
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);
            """, (
                self.current_order_id,
                label.strip(), qty, w, h,
                material_id, core_id, thickness_mm,
                color_front_id, color_back_id, finish_id,
                grain_constraint, rotation_allowed,
                notes.strip() if notes else None
            ))
            self.reload_parts()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def edit_part(self):
        pid = self._selected_id(self.tbl_parts)
        if not pid:
            QMessageBox.information(self, "Info", "Sélectionne une pièce.")
            return

        row = fetch_all(self.con, """
            SELECT id, label, width_mm, height_mm, qty,
                rotation_allowed, grain_constraint,
                material_id, color_front_id, color_back_id, finish_id
            FROM order_parts WHERE id=?;
        """, (pid,))
        if not row:
            return
        r = row[0]

        label, ok = QInputDialog.getText(self, "Modifier pièce", "Libellé:", text=r["label"] or "")
        if not ok:
            return
        if not label.strip():
            QMessageBox.warning(self, "Info", "Le libellé est obligatoire.")
            return

        w, ok2 = QInputDialog.getInt(self, "Modifier pièce", "Largeur (mm):", int(r["width_mm"]), 1, 10000, 1)
        if not ok2:
            return
        h, ok3 = QInputDialog.getInt(self, "Modifier pièce", "Hauteur (mm):", int(r["height_mm"]), 1, 10000, 1)
        if not ok3:
            return
        qty, ok4 = QInputDialog.getInt(self, "Modifier pièce", "Quantité:", int(r["qty"]), 1, 100000, 1)
        if not ok4:
            return

        rotate, ok5 = QInputDialog.getItem(
            self, "Modifier pièce", "Rotation autorisée ?",
            ["Oui", "Non"],
            0 if int(r["rotation_allowed"]) == 1 else 1,
            False
        )
        if not ok5:
            return
        rotation_allowed = 1 if rotate == "Oui" else 0

        grain_opts_fr = ["Sans", "Vertical", "Horizontal"]
        grain_cur_fr = grain_constraint_to_fr(r["grain_constraint"])
        grain_fr, ok6 = QInputDialog.getItem(
            self, "Modifier pièce", "Contrainte fibre:",
            grain_opts_fr,
            grain_opts_fr.index(grain_cur_fr),
            False
        )
        if not ok6:
            return
        grain_constraint = grain_constraint_from_fr(grain_fr)  # ✅ DB: NONE/VERTICAL/HORIZONTAL

        # --- couleurs (filtrées par matière)
        cols = fetch_all(self.con, "SELECT id, name FROM colors WHERE material_id=? ORDER BY name;", (r["material_id"],))
        if not cols:
            QMessageBox.warning(self, "Catalogue incomplet", "Aucune couleur pour cette matière.")
            return

        col_names = [c["name"] for c in cols]

        # Couleur EXT (face) - obligatoire
        cur_front_name = next((c["name"] for c in cols if c["id"] == r["color_front_id"]), col_names[0])
        front_name, okc1 = QInputDialog.getItem(
            self, "Modifier pièce", "Couleur EXT (face):",
            col_names, col_names.index(cur_front_name), False
        )
        if not okc1:
            return
        color_front_id = next(c["id"] for c in cols if c["name"] == front_name)

        # Couleur INT (dos) - optionnelle
        back_choices = ["Identique"] + col_names
        if r["color_back_id"] is None:
            cur_back_idx = 0
        else:
            cur_back_name = next((c["name"] for c in cols if c["id"] == r["color_back_id"]), None)
            cur_back_idx = 0 if cur_back_name is None else (1 + col_names.index(cur_back_name))

        back_sel, okc2 = QInputDialog.getItem(
            self, "Modifier pièce", "Couleur INT (dos):",
            back_choices, cur_back_idx, False
        )
        if not okc2:
            return

        color_back_id = None
        if back_sel != "Identique":
            color_back_id = next(c["id"] for c in cols if c["name"] == back_sel)


        try:
            exec_one(self.con, """
                UPDATE order_parts
                SET label=?, width_mm=?, height_mm=?, qty=?,
                    rotation_allowed=?, grain_constraint=?,
                    color_front_id=?, color_back_id=?
                WHERE id=?;
            """, (
                label.strip(), w, h, qty,
                rotation_allowed, grain_constraint,
                color_front_id, color_back_id,
                pid
            ))
            self.reload_parts()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def duplicate_part(self):
        pid = self._selected_id(self.tbl_parts)
        if not pid:
            QMessageBox.information(self, "Info", "Sélectionne une pièce.")
            return

        row = fetch_all(self.con, """
            SELECT label, qty, width_mm, height_mm,
                   material_id, core_id, thickness_mm,
                   color_front_id, color_back_id, finish_id,
                   grain_constraint, rotation_allowed, notes
            FROM order_parts
            WHERE id=?;
        """, (pid,))
        if not row:
            return
        r = row[0]

        try:
            exec_one(self.con, """
                INSERT INTO order_parts(
                    order_id, label, qty, width_mm, height_mm,
                    material_id, core_id, thickness_mm,
                    color_front_id, color_back_id, finish_id,
                    grain_constraint, rotation_allowed,
                    notes
                )
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);
            """, (
                self.current_order_id,
                #r["label"], r["qty"], r["width_mm"], r["height_mm"],
                (r["label"] + " (copie)") if r["label"] else "Copie", r["qty"], r["width_mm"], r["height_mm"],
                r["material_id"], r["core_id"], r["thickness_mm"],
                r["color_front_id"], r["color_back_id"], r["finish_id"],
                r["grain_constraint"], r["rotation_allowed"],
                r["notes"]
            ))
            self.reload_parts()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def delete_part(self):
        pid = self._selected_id(self.tbl_parts)
        if not pid:
            QMessageBox.information(self, "Info", "Sélectionne une pièce.")
            return
        if QMessageBox.question(self, "Confirmation", f"Supprimer la pièce ID {pid} ?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            exec_one(self.con, "DELETE FROM order_parts WHERE id=?;", (pid,))
            self.reload_parts()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))