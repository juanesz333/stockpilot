import psycopg
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from stockpilot.database.connection import get_connection
from stockpilot.services.inventory_service import InventoryError, register_movement


class MovementDialog(QDialog):
    def __init__(self, sku: str, name: str, stock: int, parent=None):
        super().__init__(parent)
        self.sku = sku  # lo guardamos para usarlo cuando se pulse OK
        self.setWindowTitle("Registrar movimiento")

        # 1. Lista de tipos: texto visible + código que entiende el servicio
        self.type_combo = QComboBox()
        self.type_combo.addItem("Entrada (compra, devolución)", "IN")
        self.type_combo.addItem("Salida (merma, uso interno)", "OUT")
        self.type_combo.addItem("Ajuste (conteo físico, + o -)", "ADJUST")
        # Cuando cambia el tipo, se ajustan los límites de la cantidad
        self.type_combo.currentIndexChanged.connect(self._update_range)

        self.quantity_input = QSpinBox()
        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("Opcional")

        # 2. Formulario: el producto y su stock son solo informativos
        form = QFormLayout()
        form.addRow("Producto", QLabel(f"{sku} — {name}"))
        form.addRow("Stock actual", QLabel(str(stock)))
        form.addRow("Tipo", self.type_combo)
        form.addRow("Cantidad", self.quantity_input)
        form.addRow("Motivo", self.reason_input)

        # 3. Botones OK y Cancelar
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # 4. Layout general: formulario arriba, botones abajo
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._update_range()  # deja los límites correctos desde el inicio

    def _update_range(self, *_):
        """Entradas y salidas llevan cantidad positiva; el ajuste admite negativos."""
        if self.type_combo.currentData() == "ADJUST":
            self.quantity_input.setRange(-100_000, 100_000)
        else:
            self.quantity_input.setRange(1, 100_000)

    def accept(self):
        """Se ejecuta al pulsar OK. Si algo falla, el diálogo sigue abierto."""
        try:
            with get_connection() as conn:
                register_movement(
                    conn,
                    self.sku,
                    self.type_combo.currentData(),
                    self.quantity_input.value(),
                    self.reason_input.text().strip() or None,  # texto vacío se guarda como NULL
                )
        except InventoryError as exc:    # error de reglas: aviso amable
            QMessageBox.warning(self, "No se pudo registrar el movimiento", str(exc))
            return
        except psycopg.Error as exc:     # error técnico de la base
            QMessageBox.critical(self, "Error de base de datos", str(exc))
            return

        super().accept()  # todo salió bien: cierra el diálogo con resultado "aceptado"