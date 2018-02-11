
# The source code in this file is modified from:
# https://github.com/baoboa/pyqt5/blob/master/examples/itemviews/simpletreemodel/simpletreemodel.py
# See below for the original copyright notice.

#############################################################################
##
## Copyright (C) 2013 Riverbank Computing Limited.
## Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
## All rights reserved.
##
## This file is part of the examples of PyQt.
##
## $QT_BEGIN_LICENSE:BSD$
## You may use this file under the terms of the BSD license as follows:
##
## "Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are
## met:
##   * Redistributions of source code must retain the above copyright
##     notice, this list of conditions and the following disclaimer.
##   * Redistributions in binary form must reproduce the above copyright
##     notice, this list of conditions and the following disclaimer in
##     the documentation and/or other materials provided with the
##     distribution.
##   * Neither the name of Nokia Corporation and its Subsidiary(-ies) nor
##     the names of its contributors may be used to endorse or promote
##     products derived from this software without specific prior written
##     permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
## "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
## LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
## A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
## OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
## SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
## LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
## DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
## THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
## $QT_END_LICENSE$
##
#############################################################################

import sys
import modelx as mx
from qtpy.QtCore import QAbstractItemModel, QModelIndex, Qt
from qtpy.QtWidgets import QApplication, QTreeView


class BaseItem(object):
    """Base Item class for all tree item classes."""
    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []
        self.updateChild()

    def updateChild(self):
        raise NotImplementedError

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return 1 # len(self.itemData)

    def data(self, column):
        try:
            return self.itemData.name
        except IndexError:
            return None

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)

        return 0


class SpaceContainerItem(BaseItem):
    """Base Item class for Models and Spaces which inherit SpaceContainer."""
    def updateChild(self):
        self.childItems.clear()
        for space in self.itemData.spaces.values():
            self.childItems.append(SpaceItem(space, self))


class SpaceItem(SpaceContainerItem):
    """Item class for Space objects."""
    def updateChild(self):
        self.childItems.clear()
        for space in self.itemData.static_spaces.values():
            self.childItems.append(SpaceItem(space, self))

        dynspaces = self.itemData.dynamic_spaces
        if len(dynspaces) > 0:
            self.childItems.append(DynamicSpaceMapItem(dynspaces, self))

        cellsmap = self.itemData.cells
        for cells in cellsmap.values():
            self.childItems.append(CellsItem(cells, self))


class DynamicSpaceMapItem(BaseItem):
    """Item class for parent nodes of dynamic spaces of a space."""
    def updateChild(self):
        self.childItems.clear()
        for space in self.itemData.values():
            self.childItems.append(SpaceItem(space, self))

    def data(self, column):
        return 'Dynamic Spaces'


class CellsItem(BaseItem):
    """Item class for cells objects."""
    def updateChild(self):
        pass


class ModelTreeModel(QAbstractItemModel):

    def __init__(self, model, parent=None):
        super(ModelTreeModel, self).__init__(parent)
        self.rootItem = SpaceContainerItem(model)

    def columnCount(self, parent):
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self.rootItem.columnCount()

    def data(self, index, role):
        if not index.isValid():
            return None

        if role != Qt.DisplayRole:
            return None

        item = index.internalPointer()

        return item.data(index.column())

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags

        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def headerData(self, section, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return 'Objects'  # self.rootItem.data(section)

        return None

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()


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


if __name__ == '__main__':

    model, space = mx.new_model('Fibonacci'), mx.new_space()

    @mx.defcells()
    def fibo(x):
        if x == 0 or x == 1:
            return x
        else:
            return fibo[x - 1] + fibo[x - 2]

    show_modeltree(mx.cur_model())
