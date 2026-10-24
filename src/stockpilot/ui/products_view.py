import psycopg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from stockpilot.database.connection import get_connection
from stockpilot.repositories import product_repository as repo
from stockpilot.ui.movement_dialog import MovementDialog
from stockpilot.ui.product_dialog import ProductDialog

HEADERS = ["SKU", "Nombre", "Precio", "Stock", "Mínimo"]


class ProductsView(QWidget):
    def __init__(self):
        super().__init__()

        # 1. Barra superior: búsqueda y botones
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Buscar por nombre o SKU...")
        self.search_box.textChanged.connect(self.load_products)

        self.new_button = QPushButton("Nuevo producto")
        self.new_button.clicked.connect(self.open_product_dialog)

        self.movement_button = QPushButton("Registrar movimiento")
        self.movement_button.clicked.connect(self.open_movement_dialog)

        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.load_products)

        top = QHBoxLayout()
        top.addWidget(self.search_box)
        top.addWidget(self.new_button)
        top.addWidget(self.movement_button)
        top.addWidget(self.refresh_button)

        # 2. Tabla de solo lectura
        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnWidth(1, 300)
        self.table.horizontalHeader().setStretchLastSection(True)

        # 3. Resumen al pie
        self.status = QLabel()

        # 4. Layout general
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.status)

        self.load_products()

    def open_product_dialog(self):
        dialog = ProductDialog(self)
        if dialog.exec():  # verdadero si se pulsó OK y el producto se creó
            self.load_products()

    def open_movement_dialog(self):
        row = self.table.currentRow()  # fila seleccionada (-1 si no hay ninguna)
        if row < 0:
            QMessageBox.information(
                self, "Selecciona un producto", "Haz clic en un producto de la tabla primero."
            )
            return

        # Los datos del producto salen de las celdas de la fila seleccionada
        sku = self.table.item(row, 0).text()
        name = self.table.item(row, 1).text()
        stock = int(self.table.item(row, 3).text())

        dialog = MovementDialog(sku, name, stock, self)
        if dialog.exec():  # verdadero si el movimiento se registró
            self.load_products()  # recarga para ver el stock nuevo

    def load_products(self, *_):
        """Lee los productos de la base y llena la tabla."""
        text = self.search_box.text().strip()
        try:
            with get_connection() as conn:
                if text:
                    products = repo.search(conn, text)
                else:
                    products = repo.list_products(conn)
        except psycopg.Error as exc:
            QMessageBox.critical(
                self, "Error de base de datos", f"No se pudieron cargar los productos:\n{exc}"
            )
            return

        self.table.setRowCount(len(products))
        for row, product in enumerate(products):
            values = [
                product.sku,
                product.name,
                f"${product.price:,.0f}",
                str(product.stock),
                str(product.min_stock),
            ]
            low_stock = product.stock < product.min_stock
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if low_stock:
                    item.setBackground(QColor("#ffd6d6"))
                    item.setForeground(QColor("#7a0000"))
                self.table.setItem(row, col, item)

        low_count = sum(1 for p in products if p.stock < p.min_stock)
        self.status.setText(f"{len(products)} productos · {low_count} con stock bajo")