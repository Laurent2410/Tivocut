import sqlite3
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QMessageBox, QInputDialog, QLabel, QComboBox, QFormLayout
)
from PySide6.QtCore import Qt

from core.repo import fetch_all, exec_one
from ui.i18n import prix_mode_to_fr
from ui.i18n import prix_mode_from_fr

def _combo_items(rows, label_col="name"):
    # returns list of (id, label)
    return [(r["id"], r[label_col]) for r in rows]


class SkusTab(QWidget):
    def __init__(self, con: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.con = con

        layout = QVBoxLayout(self)

        # --- Filters
        filters = QWidget()
        fl = QHBoxLayout(filters)

        self.f_supplier = QComboBox()
        self.f_material = QComboBox()
        self.f_format = QComboBox()
        self.f_active = QComboBox()
        self.f_active.addItems(["Actifs", "Tous"])

        fl.addWidget(QLabel("Fournisseur"))
        fl.addWidget(self.f_supplier)
        fl.addWidget(QLabel("Matière"))
        fl.addWidget(self.f_material)
        fl.addWidget(QLabel("Format"))
        fl.addWidget(self.f_format)
        fl.addWidget(QLabel("Affichage"))
        fl.addWidget(self.f_active)
        fl.addStretch(1)

        btn_apply = QPushButton("Appliquer filtre")
        btn_apply.clicked.connect(self.reload_skus)
        fl.addWidget(btn_apply)

        layout.addWidget(filters)

        # --- Table SKUs
        self.tbl = QTableWidget(0, 18)
        self.tbl.setHorizontalHeaderLabels([
            "ID", "Actif", "Fournisseur", "Matière", "Âme", "Ép (mm)", "Format",
            "Face", "Dos", "Finition",
            "Mode", "Brut", "Remise", "Net HT", "Chute %", "Net + chute", "Coeff", "Brut après coeff"
        ])
        self.tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl.setSelectionMode(QTableWidget.SingleSelection)
        self.tbl.setAlternatingRowColors(True)
        layout.addWidget(self.tbl, 1)

        # --- Buttons
        bar = QHBoxLayout()
        btn_add = QPushButton("Ajouter SKU")
        btn_edit = QPushButton("Modifier SKU")
        btn_del = QPushButton("Supprimer SKU")
        btn_price = QPushButton("Gérer prix")
        btn_reload = QPushButton("Rafraîchir")

        btn_add.clicked.connect(self.add_sku)
        btn_edit.clicked.connect(self.edit_sku)
        btn_del.clicked.connect(self.delete_sku)
        btn_price.clicked.connect(self.manage_price)
        btn_reload.clicked.connect(self.reload_all)

        bar.addWidget(btn_add)
        bar.addWidget(btn_edit)
        bar.addWidget(btn_del)
        bar.addWidget(btn_price)
        bar.addWidget(btn_reload)
        bar.addStretch(1)
        layout.addLayout(bar)

        self.reload_all()

    def reload_all(self):
        self.reload_filters()
        self.reload_skus()

    def reload_filters(self):
        suppliers = fetch_all(self.con, "SELECT id, name FROM suppliers ORDER BY name;")
        materials = fetch_all(self.con, "SELECT id, name FROM materials ORDER BY name;")
        formats = fetch_all(self.con, "SELECT id, label FROM panel_formats ORDER BY width_mm, height_mm;")

        self._fill_filter(self.f_supplier, suppliers, "Tous")
        self._fill_filter(self.f_material, materials, "Toutes")
        self._fill_filter(self.f_format, formats, "Tous", label_col="label")

    def _fill_filter(self, combo: QComboBox, rows, all_label: str, label_col="name"):
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(all_label, None)
        for r in rows:
            combo.addItem(r[label_col], r["id"])
        combo.blockSignals(False)

    def _selected_id(self) -> int | None:
        row = self.tbl.currentRow()
        if row < 0:
            return None
        try:
            return int(self.tbl.item(row, 0).text())
        except Exception:
            return None

    def reload_skus(self):
        supplier_id = self.f_supplier.currentData()
        material_id = self.f_material.currentData()
        format_id = self.f_format.currentData()
        active_only = (self.f_active.currentIndex() == 0)

        where = []
        params = []

        if supplier_id is not None:
            where.append("s.supplier_id = ?")
            params.append(supplier_id)
        if material_id is not None:
            where.append("s.material_id = ?")
            params.append(material_id)
        if format_id is not None:
            where.append("s.format_id = ?")
            params.append(format_id)
        if active_only:
            where.append("s.active = 1")

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        rows = fetch_all(self.con, f"""
            SELECT
                s.id,
                s.active,
                sup.name as supplier,
                m.name as material,
                c.name as core,
                s.thickness_mm,
                pf.label as format,
                cf.name as front,
                COALESCE(cb.name,'') as back,
                f.name as finish,

                -- latest price (valid_to is null or future) ordered by valid_from desc
                p.pricing_mode as pricing_mode,
                p.price_value as price_value,
                p.discount_value as discount_value,
                p.waste_rate_pct as waste_rate_pct,
                p.coefficient as coefficient,
                p.valid_from as valid_from

            FROM panel_skus s
            JOIN suppliers sup ON sup.id = s.supplier_id
            JOIN materials m ON m.id = s.material_id
            JOIN cores c ON c.id = s.core_id
            JOIN panel_formats pf ON pf.id = s.format_id
            JOIN colors cf ON cf.id = s.color_front_id
            LEFT JOIN colors cb ON cb.id = s.color_back_id
            JOIN finishes f ON f.id = s.finish_id
            LEFT JOIN panel_prices p ON p.id = (
                SELECT p2.id FROM panel_prices p2
                WHERE p2.panel_sku_id = s.id
                  AND (p2.valid_to IS NULL OR p2.valid_to >= date('now'))
                ORDER BY p2.valid_from DESC, p2.id DESC
                LIMIT 1
            )
            {where_sql}
            ORDER BY m.name, pf.width_mm, pf.height_mm, cf.name;
        """, tuple(params))

        # IMPORTANT: ne pas recalculer hors boucle, r n'existe pas encore
        self.tbl.setRowCount(0)

        for r in rows:
            i = self.tbl.rowCount()
            self.tbl.insertRow(i)

            brut = 0.0 if r["price_value"] is None else float(r["price_value"])
            remise = 0.0 if r["discount_value"] is None else float(r["discount_value"])
            chute = 0.0 if r["waste_rate_pct"] is None else float(r["waste_rate_pct"])
            coeff = 1.0 if r["coefficient"] is None else float(r["coefficient"])

            net_ht = brut - remise
            net_avec_chute = net_ht * (1.0 + chute / 100.0)
            brut_apres_coeff = net_avec_chute * coeff

            self.tbl.setItem(i, 0, QTableWidgetItem(str(r["id"])))
            self.tbl.setItem(i, 1, QTableWidgetItem("Oui" if r["active"] else "Non"))
            self.tbl.setItem(i, 2, QTableWidgetItem(r["supplier"]))
            self.tbl.setItem(i, 3, QTableWidgetItem(r["material"]))
            self.tbl.setItem(i, 4, QTableWidgetItem(r["core"]))
            self.tbl.setItem(i, 5, QTableWidgetItem(str(r["thickness_mm"])))
            self.tbl.setItem(i, 6, QTableWidgetItem(r["format"]))
            self.tbl.setItem(i, 7, QTableWidgetItem(r["front"]))
            self.tbl.setItem(i, 8, QTableWidgetItem(r["back"]))
            self.tbl.setItem(i, 9, QTableWidgetItem(r["finish"]))

            # Colonnes prix (10..17)
            self.tbl.setItem(i, 10, QTableWidgetItem(prix_mode_to_fr(r["pricing_mode"])))
            self.tbl.setItem(i, 11, QTableWidgetItem("" if r["price_value"] is None else f"{brut:.4f}"))
            self.tbl.setItem(i, 12, QTableWidgetItem("" if r["price_value"] is None else f"{remise:.4f}"))
            self.tbl.setItem(i, 13, QTableWidgetItem("" if r["price_value"] is None else f"{net_ht:.4f}"))
            self.tbl.setItem(i, 14, QTableWidgetItem("" if r["price_value"] is None else f"{chute:.2f}"))
            self.tbl.setItem(i, 15, QTableWidgetItem("" if r["price_value"] is None else f"{net_avec_chute:.4f}"))
            self.tbl.setItem(i, 16, QTableWidgetItem("" if r["price_value"] is None else f"{coeff:.4f}"))
            self.tbl.setItem(i, 17, QTableWidgetItem("" if r["price_value"] is None else f"{brut_apres_coeff:.4f}"))

    # ---------------------------
    # CRUD SKU
    # ---------------------------
    def add_sku(self):
        self._edit_sku_dialog(None)

    def edit_sku(self):
        sku_id = self._selected_id()
        if not sku_id:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        self._edit_sku_dialog(sku_id)

    def _edit_sku_dialog(self, sku_id: int | None):
        suppliers = fetch_all(self.con, "SELECT id, name FROM suppliers ORDER BY name;")
        materials = fetch_all(self.con, "SELECT id, name FROM materials ORDER BY name;")
        cores = fetch_all(self.con, "SELECT id, name FROM cores ORDER BY name;")
        formats = fetch_all(self.con, "SELECT id, label FROM panel_formats ORDER BY width_mm, height_mm;")
        finishes = fetch_all(self.con, "SELECT id, name FROM finishes ORDER BY name;")
        colors = fetch_all(self.con, """
            SELECT c.id, (m.name || ' - ' || c.name) as label
            FROM colors c JOIN materials m ON m.id=c.material_id
            ORDER BY m.name, c.name;
        """)

        if not suppliers or not materials or not cores or not formats or not finishes or not colors:
            QMessageBox.warning(self, "Catalogue incomplet",
                                "Il faut au minimum: fournisseurs, matières, âmes, formats, finitions, couleurs.")
            return

        # valeurs existantes
        existing = None
        if sku_id:
            ex = fetch_all(self.con, "SELECT * FROM panel_skus WHERE id=?;", (sku_id,))
            if ex:
                existing = ex[0]

        # helpers pour choix
        def pick(title, label, items, current_id=None):
            labels = [x[1] for x in items]
            idx = 0
            if current_id is not None:
                for i, (id_, _) in enumerate(items):
                    if id_ == current_id:
                        idx = i
                        break
            choice, ok = QInputDialog.getItem(self, title, label, labels, idx, False)
            if not ok:
                return None
            return items[labels.index(choice)][0]

        sup_id = pick("SKU", "Fournisseur:", _combo_items(suppliers), existing["supplier_id"] if existing else None)
        if sup_id is None: return
        mat_id = pick("SKU", "Matière:", _combo_items(materials), existing["material_id"] if existing else None)
        if mat_id is None: return
        core_id = pick("SKU", "Âme:", _combo_items(cores), existing["core_id"] if existing else None)
        if core_id is None: return
        fmt_id = pick("SKU", "Format:", _combo_items(formats, "label"), existing["format_id"] if existing else None)
        if fmt_id is None: return

        thickness_default = int(existing["thickness_mm"]) if existing else 36
        thickness, ok = QInputDialog.getInt(self, "SKU", "Épaisseur (mm):", thickness_default, 1, 200, 1)
        if not ok: return

        fin_id = pick("SKU", "Finition:", _combo_items(finishes), existing["finish_id"] if existing else None)
        if fin_id is None: return

        # couleurs filtrées par matière (confort)
        cols_mat = fetch_all(self.con, """
            SELECT c.id, c.name as label
            FROM colors c WHERE c.material_id=?
            ORDER BY c.name;
        """, (mat_id,))
        if not cols_mat:
            QMessageBox.warning(self, "Info", "Aucune couleur définie pour cette matière.")
            return
        front_id = pick("SKU", "Couleur face:", _combo_items(cols_mat, "label"),
                        existing["color_front_id"] if existing else None)
        if front_id is None: return

        back_id = None
        bico, okb = QInputDialog.getItem(self, "SKU", "Dos:", ["Unicolore (même couleur)", "Choisir une couleur dos"], 0, False)
        if not okb: return
        if bico.startswith("Choisir"):
            back_id = pick("SKU", "Couleur dos:", _combo_items(cols_mat, "label"),
                           existing["color_back_id"] if existing else None)
            if back_id is None: return

        active_default = int(existing["active"]) if existing else 1
        active_choice, oka = QInputDialog.getItem(self, "SKU", "Actif ?", ["Oui", "Non"], 0 if active_default else 1, False)
        if not oka: return
        active = 1 if active_choice == "Oui" else 0

        try:
            if sku_id is None:
                exec_one(self.con, """
                    INSERT INTO panel_skus
                    (supplier_id, material_id, core_id, thickness_mm, format_id,
                     color_front_id, color_back_id, finish_id, active)
                    VALUES (?,?,?,?,?,?,?,?,?);
                """, (sup_id, mat_id, core_id, thickness, fmt_id, front_id, back_id, fin_id, active))
            else:
                exec_one(self.con, """
                    UPDATE panel_skus
                    SET supplier_id=?, material_id=?, core_id=?, thickness_mm=?, format_id=?,
                        color_front_id=?, color_back_id=?, finish_id=?, active=?
                    WHERE id=?;
                """, (sup_id, mat_id, core_id, thickness, fmt_id, front_id, back_id, fin_id, active, sku_id))

            self.reload_skus()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    def delete_sku(self):
        sku_id = self._selected_id()
        if not sku_id:
            QMessageBox.information(self, "Info", "Sélectionne une ligne.")
            return
        if QMessageBox.question(self, "Confirmation", f"Supprimer SKU ID {sku_id} ?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            exec_one(self.con, "DELETE FROM panel_skus WHERE id=?;", (sku_id,))
            self.reload_skus()
        except sqlite3.IntegrityError as e:
            QMessageBox.critical(self, "Suppression impossible", f"SKU utilisé ailleurs.\n\n{e}")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))

    # ---------------------------
    # Prix
    # ---------------------------
    def manage_price(self):
        sku_id = self._selected_id()
        if not sku_id:
            QMessageBox.information(self, "Info", "Sélectionne un SKU.")
            return

        mode_fr, ok = QInputDialog.getItem(self, "Prix", "Assiette:", ["Par panneau", "Par m²"], 0, False)
        if not ok: return
        mode = prix_mode_from_fr(mode_fr)

        brut, ok2 = QInputDialog.getDouble(self, "Prix", "Prix brut (€) :", 0.0, 0.0, 10_000_000.0, 4)
        if not ok2: return

        remise, ok3 = QInputDialog.getDouble(self, "Prix", "Remise (€) :", 0.0, 0.0, 10_000_000.0, 4)
        if not ok3: return

        chute, ok4 = QInputDialog.getDouble(self, "Prix", "Taux de chute (%) :", 0.0, 0.0, 1000.0, 2)
        if not ok4: return

        coeff, ok5 = QInputDialog.getDouble(self, "Prix", "Coefficient (prix pièce) :", 1.0, 0.0001, 1000.0, 4)
        if not ok5: return

        valid_from, ok6 = QInputDialog.getText(self, "Prix", "Valide depuis (YYYY-MM-DD):")
        if not ok6 or not valid_from.strip(): return

        try:
            exec_one(self.con, """
                INSERT INTO panel_prices(panel_sku_id, pricing_mode, price_value,
                             discount_value, waste_rate_pct, coefficient, valid_from)
                VALUES (?,?,?,?,?,?,?);
            """, (sku_id, mode, brut, remise, chute, coeff, valid_from.strip()))

            self.reload_skus()
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))