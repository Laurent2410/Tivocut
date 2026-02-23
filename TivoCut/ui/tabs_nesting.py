from __future__ import annotations

import sqlite3
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QMessageBox, QGroupBox, QFormLayout, QDoubleSpinBox
)

from core.repo import fetch_all
from ui.i18n import grain_constraint_to_fr


class NestingTab(QWidget):
    def __init__(self, con: sqlite3.Connection, parent=None):
        super().__init__(parent)
        self.con = con
        self._order_parts = []

        root = QVBoxLayout(self)

        # ---------------- Bandeau commande ----------------
        top = QHBoxLayout()
        top.addWidget(QLabel("Commande :"))

        self.cmb_orders = QComboBox()
        top.addWidget(self.cmb_orders, 1)

        self.btn_load = QPushButton("Charger pièces")
        self.btn_opt = QPushButton("Optimiser")
        self.btn_pdf = QPushButton("Exporter PDF")
        top.addWidget(self.btn_load)
        top.addWidget(self.btn_opt)
        top.addWidget(self.btn_pdf)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(self.lbl_summary)

        root.addLayout(top)

        # ---------------- Paramètres scie ----------------
        grp = QGroupBox("Paramètres scie")
        form = QFormLayout(grp)

        self.kerf = QDoubleSpinBox()
        self.kerf.setRange(0.0, 50.0)
        self.kerf.setDecimals(2)
        self.kerf.setValue(3.0)

        self.margin = QDoubleSpinBox()
        self.margin.setRange(0.0, 200.0)
        self.margin.setDecimals(2)
        self.margin.setValue(10.0)

        self.spacing = QDoubleSpinBox()
        self.spacing.setRange(0.0, 200.0)
        self.spacing.setDecimals(2)
        self.spacing.setValue(0.0)

        # Tes libellés FR (comme tu as demandé)
        form.addRow("Trait de Scie (mm)", self.kerf)
        form.addRow("Marge (mm)", self.margin)
        form.addRow("Espace/pièces (mm)", self.spacing)

        root.addWidget(grp)

        # ---------------- Zone placeholder (dessin/plan) ----------------
        self.lbl_canvas = QLabel("Zone plan de découpe (à venir)")
        self.lbl_canvas.setAlignment(Qt.AlignCenter)
        self.lbl_canvas.setMinimumHeight(240)
        self.lbl_canvas.setStyleSheet("border: 1px solid #999; border-radius: 6px;")
        root.addWidget(self.lbl_canvas, 1)

        # Events
        self.btn_load.clicked.connect(self.load_order_parts)
        self.btn_opt.clicked.connect(self.optimize_placeholder)
        self.btn_pdf.clicked.connect(self.export_pdf_placeholder)

        self.reload_orders_combo()

    # ---------------- Data ----------------
    def reload_orders_combo(self):
        self.cmb_orders.clear()
        rows = fetch_all(self.con, "SELECT id, cde_number, delivery_date FROM orders ORDER BY id DESC;")
        for r in rows:
            txt = f"{r['cde_number']}  (Livraison: {r['delivery_date']})"
            self.cmb_orders.addItem(txt, r["id"])

        if self.cmb_orders.count() == 0:
            self.lbl_summary.setText("Aucune commande")
        else:
            self.lbl_summary.setText("")

    def selected_order_id(self):
        if self.cmb_orders.currentIndex() < 0:
            return None
        return self.cmb_orders.currentData()

    def load_order_parts(self):
        oid = self.selected_order_id()
        if not oid:
            QMessageBox.information(self, "Info", "Sélectionne une commande.")
            return

        parts = fetch_all(self.con, """
            SELECT id, label, qty, width_mm, height_mm,
                   material_id, core_id, thickness_mm,
                   color_front_id, color_back_id, finish_id,
                   grain_constraint, rotation_allowed
            FROM order_parts
            WHERE order_id=?
            ORDER BY id ASC;
        """, (oid,))

        self._order_parts = parts

        # Résumé simple
        total_qty = sum(int(p["qty"]) for p in parts) if parts else 0
        grains = sorted({grain_constraint_to_fr(p["grain_constraint"]) for p in parts}) if parts else []
        gtxt = ", ".join(grains) if grains else "—"
        self.lbl_summary.setText(f"{len(parts)} lignes / {total_qty} pièces | Fibre: {gtxt}")

        QMessageBox.information(self, "Commande", f"Pièces chargées : {len(parts)} lignes ({total_qty} pièces)")

    # ---------------- Placeholders ----------------
    def optimize_placeholder(self):
        if not self._order_parts:
            QMessageBox.information(self, "Info", "Charge d'abord une commande.")
            return
        QMessageBox.information(
            self,
            "Optimisation",
            f"OK (placeholder).\nKerf={self.kerf.value()} mm, Marge={self.margin.value()} mm, Espacement={self.spacing.value()} mm"
        )

    def export_pdf_placeholder(self):
        QMessageBox.information(self, "PDF", "Export PDF : à brancher après génération d’un plan.")