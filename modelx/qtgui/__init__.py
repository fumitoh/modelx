
import sys
from qtpy.QtWidgets import QApplication

# Start QApplication if not running yet.
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

from modelx.qtgui.modeltree import get_modeltree, show_tree

del sys, QApplication
