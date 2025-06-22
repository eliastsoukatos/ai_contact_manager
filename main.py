import sys
from PyQt5.QtWidgets import QApplication, QMainWindow

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("VibeList AI Contact Manager")
window.show()

sys.exit(app.exec_())
