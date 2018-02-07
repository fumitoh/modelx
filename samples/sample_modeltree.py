import sys
from qtpy.QtWidgets import QApplication, QTreeView
from modelx.qtgui.modeltree import *
from lifelib.projects.simplelife.build import *

def show_modeltree(model):
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    treemodel = ModelTreeModel(model)
    view = QTreeView()
    view.setModel(treemodel)
    view.setWindowTitle("Model %s" % model.name)
    view.setAlternatingRowColors(True)
    view.show()
    app.exec_()


if __name__ == "__main__":
    show_modeltree(model)