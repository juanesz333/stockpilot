from PySide6.QtWidgets import QMainWindow, QTabWidget

from stockpilot.ui.products_view import ProductsView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StockPilot — Inventario y ventas")
        self.resize(1000, 600)

        tabs = QTabWidget()
        tabs.addTab(ProductsView(), "Productos")  # (la pantalla, el texto de la pestaña)
        self.setCentralWidget(tabs)