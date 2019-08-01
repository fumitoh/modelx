Importing Data
==============

modelx allows you to create Spaces or Cells populated with data
from data sources.

Supported data sources
----------------------

The supported types of data sources are as Excel files, CSV files,
Pandas DataFrame and Series objects.

Creating Cells from data sources
--------------------------------

There are two methods for each type of the data sources.
One of them is ``new_cells_from_*`` (where ``*`` is
one of the supported data source types).
This is Space's method, and created cells populated with
values from the data source.

Creating Spaces and Cells from data sources
-------------------------------------------

The other method is ``new_space_from_*``.
Models and Spaces have this method.
This method creates a StaticSpace and optionally DynamicSpaces
of the StaticSpace, and then Cells in the Static/Dynamic Spaces.


Importing Excel files
---------------------

Importing CSV files
-------------------




Importing Pandas objects
------------------------




Saving models with data sources
-------------------------------

When the user writes models with
Spaces and Cells created from the data source files (Excel or CSV files),
those files are copied into the model folder/directory.
If a model contains Spaces and Cells created
from Pandas DataFrame or Series objects, those objects are serialized
and saved as binary files in the model folder.

If data source files or objects are modified after the creation of
Space and Cells, before the model is written to the files,
the data sources are saved reflecting the changes.

See "saving_models.rst" section for more details.




