
import sys
from qtpy.QtWidgets import QApplication

# Start QApplication if not running yet.
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

del sys, QApplication
