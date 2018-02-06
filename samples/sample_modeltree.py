
from modelx.qtgui.modeltree import *
from qtpy.QtWidgets import QApplication, QTreeView

from lifelib.projects.simplelife.build import *


def show_modeltree(model):
    app = QApplication(sys.argv)
    treemodel = ModelTreeModel(model)
    view = QTreeView()
    view.setModel(treemodel)
    view.setWindowTitle("Model %s" % model.name)
    view.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    show_modeltree(model)