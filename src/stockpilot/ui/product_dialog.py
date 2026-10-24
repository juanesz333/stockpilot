from decimal import Decimal

import psycopg
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from stockpilot.database.connection import get_connection
from stockpilot.repositories import category_repository
from stockpilot.services import product_service
from stockpilot.services.product_service import ProductError


class ProductDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)  # parent: la ventana de atrás, para centrarse sobre ella
        self.setWindowTitle("Nuevo producto")

        # 1. Los widgets del formulario
        self.category_combo = QComboBox()            # lista desplegable
        self.sku_input = QLineEdit()                 # caja de texto
        self.sku_input.setPlaceholderText("Ej: BEB-004")
        self.name_input = QLineEdit()
        self.price_input = QDoubleSpinBox()          # número con decimales
        self.price_input.setPrefix("$ ")
        self.price_input.setDecimals(2)
        self.price_input.setRange(0, 100_000_000)
        self.price_input.setSingleStep(100)
        self.min_stock_input = QSpinBox()            # número entero
        self.min_stock_input.setRange(0, 100_000)

        # 2. El layout de formulario: etiqueta + campo en cada fila
        form = QFormLayout()
        form.addRow("Categoría", self.category_combo)
        form.addRow("SKU", self.sku_input)
        form.addRow("Nombre", self.name_input)
        form.addRow("Precio", self.price_input)
        form.addRow("Stock mínimo", self.min_stock_input)

        # 3. Botones OK y Cancelar, ya conectados a aceptar y rechazar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # 4. Layout general: formulario arriba, botones abajo
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._load_categories()

    def _load_categories(self):
        """Llena la lista desplegable con las categorías de la base."""
        try:
            with get_connection() as conn:
                for category_id, name in category_repository.list_categories(conn):
                    # addItem(texto visible, dato oculto): guardamos el id junto al nombre
                    self.category_combo.addItem(name, category_id)
        except psycopg.Error as exc:
            QMessageBox.critical(
                self,
                "Error de base de datos",
                f"No se pudieron cargar las categorías:\n{exc}",
            )

    def accept(self):
        """Se ejecuta al pulsar OK. Si algo falla, el diálogo sigue abierto."""
        category_id = self.category_combo.currentData()  # el id oculto de la categoría elegida
        if category_id is None:
            QMessageBox.warning(self, "Falta la categoría", "No hay categorías disponibles.")
            return

        try:
            with get_connection() as conn:
                product_service.create_product(
                    conn,
                    category_id=category_id,
                    sku=self.sku_input.text(),
                    name=self.name_input.text(),
                    price=Decimal(f"{self.price_input.value():.2f}"),
                    min_stock=self.min_stock_input.value(),
                )
        except ProductError as exc:      # error de reglas: aviso amable
            QMessageBox.warning(self, "No se pudo crear el producto", str(exc))
            return
        except psycopg.Error as exc:     # error técnico de la base
            QMessageBox.critical(self, "Error de base de datos", str(exc))
            return

        super().accept()  # todo salió bien: cierra el diálogo con resultado "aceptado"