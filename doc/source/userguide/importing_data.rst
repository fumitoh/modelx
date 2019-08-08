Importing Data
==============

modelx allows you to create Spaces or Cells populated with data
from data sources.

.. contents:: Contents
   :depth: 1
   :local:


Supported data sources
----------------------

The supported types of data sources are:

* Excel files
* Comma-separated values (CSV) files
* Pandas DataFrame and Series objects

Methods to create Cells from data sources
-----------------------------------------

The following methods of UserSpace create cells from the data sources.

.. currentmodule:: modelx.core.space

* :meth:`UserSpace.new_cells_from_excel`
* :meth:`UserSpace.new_cells_from_csv`
* :meth:`UserSpace.new_cells_from_pandas`


Methods to create Spaces and Cells from data sources
----------------------------------------------------

The methods below create a UserSpace and optionally DynamicSpaces
in the Model or UserSpace, and then creates Cells in the Static/Dynamic Spaces
with values imported from the data sources.

.. currentmodule:: modelx.core.model

**Model methods**

* :meth:`Model.new_space_from_excel`
* :meth:`Model.new_space_from_csv`
* :meth:`Model.new_space_from_pandas`

.. currentmodule:: modelx.core.space

**UserSpace methods**

* :meth:`UserSpace.new_space_from_excel`
* :meth:`UserSpace.new_space_from_csv`
* :meth:`UserSpace.new_space_from_pandas`


Saving models with data sources
-------------------------------

If the user writes models to files and the model contains
Spaces and Cells created from the data source files (Excel or CSV files),
those data source files are copied into the model folder/directory.
If a model contains Spaces and Cells created
from Pandas DataFrame or Series objects, those objects are serialized
and saved as binary files in the model folder.

If data source files or objects are modified after the creation of
Space and Cells before the model is written to the files,
the data sources are saved reflecting the changes.
.. See :doc:`saving_models` section for more details.




