import sys

from PySide6.QtWidgets import QApplication

from stockpilot.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)   # crea el motor de la aplicación
    window = MainWindow()          # crea la ventana principal
    window.show()                  # la muestra en pantalla
    return app.exec()              # se queda esperando clics y teclas hasta que cierres la ventana


if __name__ == "__main__":
    sys.exit(main())