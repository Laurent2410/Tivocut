from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QComboBox, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QFormLayout
)
from PySide6.QtCore import Qt
from .graphics import NestingView

from ui.tabs_orders import OrdersTab
from ui.tabs_catalog import CatalogTab
from ui.tabs_skus import SkusTab


class MainWindow(QMainWindow):
    def __init__(self, con):
        super().__init__()
        self.con = con
        self.setWindowTitle("Tivolux Cut Optimizer (Guillotine)")
        self.resize(1400, 900)

        root = QWidget()
        self.setCentralWidget(root)
        main = QVBoxLayout(root)

        # --- Bandeau haut
        banner = QWidget()
        banner_layout = QHBoxLayout(banner)

        self.cde_edit = QLineEdit()
        self.delivery_edit = QLineEdit()
        self.objective = QComboBox()
        self.objective.addItems(["Coût", "Rendement", "Nb panneaux"])

        banner_layout.addWidget(QLabel("CDE:"))
        banner_layout.addWidget(self.cde_edit)
        banner_layout.addWidget(QLabel("Livraison (YYYY-MM-DD):"))
        banner_layout.addWidget(self.delivery_edit)
        banner_layout.addWidget(QLabel("Objectif:"))
        banner_layout.addWidget(self.objective)

        self.btn_opt = QPushButton("Optimiser")
        self.btn_pdf = QPushButton("Exporter PDF")
        banner_layout.addWidget(self.btn_opt)
        banner_layout.addWidget(self.btn_pdf)
        banner_layout.addStretch(1)

        main.addWidget(banner)

        # --- Onglets
        self.tabs = QTabWidget()
        main.addWidget(self.tabs, 1)

        self.tabs.addTab(self._build_tab_nesting(), "Nesting")
        
        self.tabs.addTab(OrdersTab(self.con), "Commandes")
        self.tabs.addTab(CatalogTab(self.con), "Catalogue")
        self.tabs.addTab(SkusTab(self.con), "SKUs + Prix")

    def _build_tab_nesting(self) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Gauche: tableau pièces
        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.parts_table = QTableWidget(0, 7)
        self.parts_table.setHorizontalHeaderLabels(
            ["Label", "Qté", "L (mm)", "H (mm)", "Rotation", "Grain", "Couleur"]
        )
        left_layout.addWidget(self.parts_table, 1)

        btns = QWidget()
        btns_l = QHBoxLayout(btns)
        btn_add = QPushButton("+ Pièce")
        btn_del = QPushButton("Supprimer")
        btns_l.addWidget(btn_add)
        btns_l.addWidget(btn_del)
        btns_l.addStretch(1)
        left_layout.addWidget(btns)

        splitter.addWidget(left)

        # Centre: dessin
        self.view = NestingView()
        splitter.addWidget(self.view)

        # Droite: stats + paramètres coupe
        right = QWidget()
        form = QFormLayout(right)

        self.kerf = QLineEdit("4")
        self.margin = QLineEdit("10")
        self.spacing = QLineEdit("2")
        self.stats = QLabel("Rendement: -\nPanneaux: -\nCoût: -")

        form.addRow(QLabel("<b>Paramètres scie</b>"))
        form.addRow("Trait de Scie (mm)", self.kerf)
        form.addRow("Marge (mm)", self.margin)
        form.addRow("Espace/pièces (mm)", self.spacing)
        form.addRow(QLabel("<b>Résultats</b>"))
        form.addRow(self.stats)

        splitter.addWidget(right)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 6)
        splitter.setStretchFactor(2, 2)

        return w

    def add_dummy_part(self):
        row = self.parts_table.rowCount()
        self.parts_table.insertRow(row)
        self.parts_table.setItem(row, 0, QTableWidgetItem("Pièce A"))
        self.parts_table.setItem(row, 1, QTableWidgetItem("1"))
        self.parts_table.setItem(row, 2, QTableWidgetItem("300"))
        self.parts_table.setItem(row, 3, QTableWidgetItem("500"))
        self.parts_table.setItem(row, 4, QTableWidgetItem("Oui"))
        self.parts_table.setItem(row, 5, QTableWidgetItem("NONE"))
        self.parts_table.setItem(row, 6, QTableWidgetItem("Blanc"))