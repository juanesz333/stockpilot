from decimal import Decimal

import psycopg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from stockpilot.database.connection import get_connection
from stockpilot.repositories import customer_repository
from stockpilot.repositories import product_repository as product_repo
from stockpilot.services.inventory_service import InventoryError
from stockpilot.services.sale_service import create_sale

HEADERS = ["SKU", "Nombre", "Cantidad", "Precio", "Subtotal"]


def money(value) -> str:
    return f"${value:,.0f}"


class SalesView(QWidget):
    def __init__(self):
        super().__init__()

        # El carrito vive en memoria: sku -> [producto, cantidad]
        self.cart: dict[str, list] = {}
        # Productos disponibles para vender: sku -> producto
        self.products: dict = {}

        # 1. Fila para agregar productos al carrito
        self.product_combo = QComboBox()
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(1, 100_000)
        self.add_button = QPushButton("Agregar al carrito")
        self.add_button.clicked.connect(self.add_to_cart)

        add_row = QHBoxLayout()
        add_row.addWidget(QLabel("Producto"))
        add_row.addWidget(self.product_combo, 1)  # el 1 le da todo el espacio sobrante
        add_row.addWidget(QLabel("Cantidad"))
        add_row.addWidget(self.quantity_input)
        add_row.addWidget(self.add_button)

        # 2. Tabla del carrito (solo lectura)
        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setColumnWidth(1, 300)
        self.table.horizontalHeader().setStretchLastSection(True)

        # 3. Fila inferior: quitar, cliente, total y confirmar
        self.remove_button = QPushButton("Quitar seleccionado")
        self.remove_button.clicked.connect(self.remove_selected)

        self.customer_combo = QComboBox()

        self.total_label = QLabel()
        font = self.total_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.total_label.setFont(font)

        self.confirm_button = QPushButton("Confirmar venta")
        self.confirm_button.clicked.connect(self.confirm_sale)

        bottom = QHBoxLayout()
        bottom.addWidget(self.remove_button)
        bottom.addStretch()  # espacio flexible: empuja lo que sigue hacia la derecha
        bottom.addWidget(QLabel("Cliente"))
        bottom.addWidget(self.customer_combo)
        bottom.addSpacing(20)
        bottom.addWidget(self.total_label)
        bottom.addWidget(self.confirm_button)

        # 4. Layout general
        layout = QVBoxLayout(self)
        layout.addLayout(add_row)
        layout.addWidget(self.table)
        layout.addLayout(bottom)

        self.reload_data()
        self.refresh_cart()

    def reload_data(self):
        """Lee de la base los productos con stock y los clientes."""
        try:
            with get_connection() as conn:
                products = product_repo.list_products(conn)
                customers = customer_repository.list_customers(conn)
        except psycopg.Error as exc:
            QMessageBox.critical(
                self, "Error de base de datos", f"No se pudieron cargar los datos:\n{exc}"
            )
            return

        # Solo se ofrecen productos con stock disponible
        self.products = {p.sku: p for p in products if p.stock > 0}
        self.product_combo.clear()
        for product in self.products.values():
            label = f"{product.sku} — {product.name} (stock {product.stock}) — {money(product.price)}"
            self.product_combo.addItem(label, product.sku)

        # Se conserva el cliente elegido, si sigue existiendo
        previous_customer = self.customer_combo.currentData()
        self.customer_combo.clear()
        self.customer_combo.addItem("Sin cliente", None)
        for customer_id, name in customers:
            self.customer_combo.addItem(name, customer_id)
        if previous_customer is not None:
            index = self.customer_combo.findData(previous_customer)
            if index >= 0:
                self.customer_combo.setCurrentIndex(index)

    def add_to_cart(self):
        sku = self.product_combo.currentData()
        if sku is None:
            QMessageBox.information(
                self, "Sin productos", "No hay productos con stock para vender."
            )
            return

        product = self.products[sku]
        quantity = self.quantity_input.value()
        in_cart = self.cart[sku][1] if sku in self.cart else 0

        if in_cart + quantity > product.stock:
            QMessageBox.warning(
                self,
                "Stock insuficiente",
                f"De {sku} hay {product.stock} unidades y ya tienes {in_cart} en el carrito.",
            )
            return

        if sku in self.cart:
            self.cart[sku][1] += quantity  # si ya estaba, se suman las cantidades
        else:
            self.cart[sku] = [product, quantity]
        self.refresh_cart()

    def remove_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.information(
                self, "Selecciona una línea", "Haz clic en una línea del carrito primero."
            )
            return
        sku = self.table.item(row, 0).text()
        del self.cart[sku]
        self.refresh_cart()

    def refresh_cart(self):
        """Dibuja el carrito en la tabla y recalcula el total."""
        self.table.setRowCount(len(self.cart))
        total = Decimal("0")
        for row, (product, quantity) in enumerate(self.cart.values()):
            subtotal = product.price * quantity
            total += subtotal
            values = [
                product.sku,
                product.name,
                str(quantity),
                money(product.price),
                money(subtotal),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2:  # los números van alineados a la derecha
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row, col, item)
        self.total_label.setText(f"Total: {money(total)}")

    def confirm_sale(self):
        if not self.cart:
            QMessageBox.information(self, "Carrito vacío", "Agrega al menos un producto.")
            return

        items = [(sku, line[1]) for sku, line in self.cart.items()]
        customer_id = self.customer_combo.currentData()  # None si es "Sin cliente"

        try:
            with get_connection() as conn:
                sale_id, total = create_sale(conn, items, customer_id)
        except InventoryError as exc:  # incluye SaleError: errores de reglas
            QMessageBox.warning(self, "No se pudo registrar la venta", str(exc))
            return
        except psycopg.Error as exc:
            QMessageBox.critical(self, "Error de base de datos", str(exc))
            return

        QMessageBox.information(
            self, "Venta registrada", f"Venta #{sale_id} registrada.\nTotal: {money(total)}"
        )
        self.cart.clear()
        self.refresh_cart()
        self.reload_data()  # el stock cambió: se actualiza la lista de productos