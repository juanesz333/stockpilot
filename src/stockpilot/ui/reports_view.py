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
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from stockpilot.database.connection import get_connection
from stockpilot.repositories import report_repository


def format_value(value) -> str:
    """Convierte un valor de la base en el texto que se muestra en la celda."""
    if value is None:
        return ""
    if isinstance(value, Decimal):  # los Decimal de nuestros reportes son dinero
        return f"${value:,.0f}"
    return str(value)


class ReportsView(QWidget):
    def __init__(self):
        super().__init__()

        # 1. Barra superior: lista de reportes y botón
        self.report_combo = QComboBox()
        for report in report_repository.REPORTS:
            self.report_combo.addItem(report.title, report.key)  # texto visible, clave oculta
        self.report_combo.currentIndexChanged.connect(self.load_report)

        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.load_report)

        top = QHBoxLayout()
        top.addWidget(QLabel("Reporte"))
        top.addWidget(self.report_combo, 1)  # el 1 le da el espacio sobrante a la lista
        top.addWidget(self.refresh_button)

        # 2. Tabla de solo lectura; sus columnas dependen del reporte elegido
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)

        # 3. Resumen al pie
        self.status = QLabel()

        # 4. Layout general: barra, tabla y resumen, uno debajo del otro
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        layout.addWidget(self.status)

        self.load_report()

    def load_report(self, *_):
        """Ejecuta el reporte elegido y lo muestra en la tabla."""
        key = self.report_combo.currentData()
        try:
            with get_connection() as conn:
                columns, rows = report_repository.run_report(conn, key)
        except psycopg.Error as exc:
            QMessageBox.critical(
                self, "Error de base de datos", f"No se pudo cargar el reporte:\n{exc}"
            )
            return

        self.table.clear()  # borra celdas y encabezados del reporte anterior
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(
            [name.replace("_", " ").capitalize() for name in columns]  # "total_vendido" -> "Total vendido"
        )
        self.table.setRowCount(len(rows))

        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                item = QTableWidgetItem(format_value(value))
                if isinstance(value, (int, Decimal)):  # los números van a la derecha
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row_index, col_index, item)

        self.table.resizeColumnsToContents()
        self.status.setText(f"{len(rows)} filas")