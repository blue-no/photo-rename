import sys

from PySide6.QtCore import QFile
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from photo_rename.config import APP_DIR, APP_NAME, load_config
from photo_rename.model import MainWindowModel
from photo_rename.view import MainWindow
from photo_rename.vm import MainWindowViewModel


def main() -> None:
    app = QApplication(sys.argv)
    config = load_config()

    with open(APP_DIR / "resources" / "style.qss", "r") as f:
        app.setStyleSheet(f.read())

    icon = QIcon((APP_DIR / "resources" / "favicon.ico").as_posix())
    app.setWindowIcon(icon)

    ui = QFile(APP_DIR / "resources" / "main_window.ui")

    model = MainWindowModel(config)
    vm = MainWindowViewModel(model)
    window = MainWindow(vm, ui)
    window.setWindowTitle(APP_NAME)
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
