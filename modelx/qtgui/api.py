# Copyright (c) 2017-2018 Fumito Hamamura <fumito.ham@gmail.com>

# This library is free software: you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation version 3.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

"""modelx Qt GUI functions.

Functions listed here are available directly in ``modelx`` module,
either by::

    import modelx as mx

or by::

    from modelx import *

"""
import sys, warnings
import modelx as mx

__all__ = ['get_modeltree',
           'get_tree',
           'show_tree']

try:
    from qtpy.QtWidgets import QApplication, QTreeView
    from modelx.qtgui.modeltree import ModelTreeModel
except ImportError:
    warnings.warn("QtPy package not found."
                  "GUI will not be available.", ImportWarning)


def get_modeltree(model=None):
    """Alias to :func:`get_tree`."""
    if model is None:
        model = mx.cur_model()
    treemodel = ModelTreeModel(model._baseattrs)
    view = QTreeView()
    view.setModel(treemodel)
    view.setWindowTitle("Model %s" % model.name)
    view.setAlternatingRowColors(True)
    return view


def get_tree(model=None):
    """Get QTreeView object containing the model tree.

    Args:
        model: :class:`Model <modelx.core.model.Model>` object.
            Defaults to the current model.
    """
    if model is None:
        model = mx.cur_model()
    treemodel = ModelTreeModel(model._baseattrs)
    view = QTreeView()
    view.setModel(treemodel)
    view.setWindowTitle("Model %s" % model.name)
    view.setAlternatingRowColors(True)
    return view


def show_tree(model=None):
    """Display the model tree window.

    Args:
        model: :class:`Model <modelx.core.model.Model>` object.
            Defaults to the current model.

    Warnings:
        For this function to work with Spyder, *Graphics backend* option
        of Spyder must be set to *inline*.
    """
    if model is None:
        model = mx.cur_model()
    view = get_modeltree(model)
    app = QApplication.instance()
    if not app:
        raise RuntimeError("QApplication does not exist.")
    view.show()
    app.exec_()


if __name__ == '__main__':

    model, space = mx.new_model('Fibonacci'), mx.new_space()

    @mx.defcells()
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo[x - 1] + fibo[x - 2]

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    show_tree()
