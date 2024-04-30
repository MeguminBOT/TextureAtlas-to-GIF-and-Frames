from PySide6.QtWidgets import QApplication

from app import AppWindow, UpdateWindow
from update_checker import UpdateChecker

def main():
    app = QApplication()
    
    current_version = '1.4.0'
    update_checker = UpdateChecker(current_version)
    update_available = update_checker.check_for_updates()

    if update_available:
        update_window = UpdateWindow(current_version, update_checker.latest_version)
        update_window.show()
        update_window.raise_()

    window = AppWindow()
    window.show()
    app.exec()

if __name__ == '__main__':
    main()