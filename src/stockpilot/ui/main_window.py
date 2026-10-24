from PySide6.QtWidgets import QMainWindow, QTabWidget

from stockpilot.ui.products_view import ProductsView
from stockpilot.ui.sales_view import SalesView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StockPilot — Inventario y ventas")
        self.resize(1000, 600)

        self.products_view = ProductsView()
        self.sales_view = SalesView()

        tabs = QTabWidget()
        tabs.addTab(self.products_view, "Productos")
        tabs.addTab(self.sales_view, "Ventas")
        tabs.currentChanged.connect(self.on_tab_changed)  # se avisa al cambiar de pestaña
        self.setCentralWidget(tabs)

    def on_tab_changed(self, index: int):
        """Al entrar a una pestaña, se recargan sus datos."""
        if index == 0:
            self.products_view.load_products()
        elif index == 1:
            self.sales_view.reload_data()