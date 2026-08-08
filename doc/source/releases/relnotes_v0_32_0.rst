====================================
modelx v0.32.0 (8 August 2026)
====================================

This release introduces the following enhancements,
backward-incompatible changes and bug fixes.

To update modelx to the latest version, use the following command::

    >>> pip install modelx --upgrade

Anaconda users should use the ``conda`` command instead::

    >>> conda update modelx


Enhancements
==============

.. rubric:: IO specs are saved as readable declarations

This release introduces a new version of the model serializer, version 8,
which is now the default format written by :func:`~modelx.write_model` and
:func:`~modelx.zip_model` (`GH266`_).

Until version 7, the IO specs of a model, i.e. the objects created by
:meth:`Model.new_pandas<modelx.core.model.Model.new_pandas>`,
:meth:`Model.new_excel_range<modelx.core.model.Model.new_excel_range>` and
:meth:`Model.new_module<modelx.core.model.Model.new_module>` and their
:class:`~modelx.core.space.UserSpace` counterparts, were pickled — into a
binary ``_data/iospecs.pickle`` file since version 5. Version 8 declares
them instead as plain literal tuples in a text file, ``_data/iospecs.py``::

    # modelx: iospecs
    # (key, class, version, path, io_args, spec_args)
    (1, 'PandasData', 1, 'files/data.csv', {'file_type': 'csv'}, {'sheet': None, ...})

and the References that point at them carry a comment naming the spec::

    df = ("IOSpec", 1)  # PandasData path='files/data.csv' file_type='csv'

``_data/data.pickle``, which holds the input values of the model, is now
the only pickle left in a saved model. How a model reads its external
files is therefore reviewable and diffable in version control, and it no
longer depends on modelx's internal module layout, because spec classes
are now saved by their bare class names.

When a version-8 model is read, each declaration line is restored
independently. An unparsable line, an invalid or duplicated key, an
unknown spec class or an unreadable IO file emits a ``UserWarning`` and
skips only that line, letting the rest of the model load. References to a
spec that could not be restored are set to ``None``.

.. rubric:: Byte-stable saved models

Saved models no longer embed CPython memory addresses, and the order in
which they are written is now derived from the model itself instead of
from the history of the session (`GH265`_). As a result, saving a model,
reading it back and saving it again produces byte-identical file
contents, across processes and across runs, except for values whose own
pickled form depends on the process hash seed, such as sets of strings.

For models saved as directories by :func:`~modelx.write_model`, the tree
is byte-identical, so committed models stop showing up as spurious
diffs in version control. For models saved as zip archives by
:func:`~modelx.zip_model`, every archive entry is byte-identical, but the
archive file itself is not, because zip entry headers record the
wall-clock time of the save. Excel workbooks written for IO specs are the
one exception: they are regenerated on every save and embed their own
internal timestamps, so they still differ from save to save.

This applies to serializer versions 6, 7 and 8. The on-disk format of
versions 6 and 7 is unchanged, so earlier versions of modelx still read
what this release writes with ``version=6`` or ``version=7``.

.. rubric:: Tolerant model loading

:func:`~modelx.read_model` no longer aborts the entire load when a value
saved in a model cannot be unpickled in the current environment, which
typically happens when the model was saved with a different version of a
third-party package such as pandas (`GH255`_).

Values that cannot be restored are now skipped and the rest of the model
loads normally. A Reference whose value is lost is set to ``None``;
unrestorable Cells input values and ItemSpace input values are skipped so
that they are recomputed by their formulas. A summary warning for the
model as a whole is issued first, followed by a ``UserWarning`` for each
lost value naming the object it belonged to.

The tolerant path only runs after a normal load has failed, so successful
loads are not slowed down. It covers serializer versions 4 and later.

.. rubric:: Selective ItemSpace invalidation

Previously, a structural edit to a Space that any live
:class:`~modelx.core.space.ItemSpace` depended on — creating or deleting
a Cells or a Reference, or adding, removing or deleting a Space —
deleted **all** the ItemSpaces of every parameterized Space using the
edited Space, including ItemSpaces built on other, unaffected base
Spaces.

ItemSpace deletion is now selective per ItemSpace: an edit (creating or
deleting a Reference or changing its value, creating, deleting or
renaming a Cells, changing a formula, or adding, removing, renaming or
deleting a Space) deletes an ItemSpace only when the edited Space can
actually affect it, namely when the edited Space is one of:

* a Space that a node of the ItemSpace's dynamic tree is based on,
* a base Space of such a Space, or
* the nearest static Space containing the ItemSpace — the
  parameterized Space itself in the normal case, or its nearest static
  ancestor when the parameterized Space is itself dynamic (nested
  ItemSpace trees).

Changing a Cells formula or renaming a Cells deletes only the
ItemSpaces whose dynamic trees are based on the Cells' Space (or on a
Space inheriting the Cells), as before.

ItemSpaces built on unrelated Spaces — including sibling ItemSpaces of
the same parameterized Space built on other base Spaces — now survive
such edits, which avoids costly recalculation of unaffected dynamic
subtrees in large models.

Assigning or deleting a model-level (global) Reference still deletes
all ItemSpaces in the model.

.. rubric:: Failed edits leave the model unchanged

Model edits now run as transactions that are rolled back when they fail.
In particular:

* A failed :meth:`UserSpace.add_bases<modelx.core.space.UserSpace.add_bases>`
  no longer leaves phantom derived Cells and partially inherited
  References behind in the sub Spaces.
* :meth:`UserSpace.new_cells<modelx.core.space.UserSpace.new_cells>` and
  :func:`~modelx.defcells` called with an unparsable formula no longer
  leave a half-built Cells in the Space. Previously the ``SyntaxError``
  was raised but the Space was corrupted, and the next edit on it failed
  with an ``AttributeError``.

.. rubric:: Clearer error for unknown serializer versions

:func:`~modelx.read_model` now raises
``ValueError: unsupported serializer version: ...; the model may have
been saved by a newer version of modelx`` instead of letting a raw
``ModuleNotFoundError`` escape when it meets a model saved in a format
it does not know. The same applies to an unknown ``version`` passed to
:func:`~modelx.write_model` and :func:`~modelx.zip_model`.

.. _GH266: https://github.com/fumitoh/modelx/pull/266
.. _GH265: https://github.com/fumitoh/modelx/pull/265
.. _GH255: https://github.com/fumitoh/modelx/pull/255


Backward Incompatible Changes
==============================

* This release introduces a new version of the model serializer (serializer
  version 8). Models saved by this version of modelx **cannot be read by
  previous versions of modelx**. To save a model in a format that modelx
  v0.31.x can read, pass ``version=7`` to :func:`~modelx.write_model` or
  :func:`~modelx.zip_model`::

      >>> modelx.write_model(model, "model_dir", version=7)

  Serializer version 7 was itself introduced by modelx v0.31.0, so to save
  a model for modelx v0.22.0 through v0.30.x, pass ``version=6`` instead.

* Because serializer version 8 declares IO specs as literals instead of
  pickling them, every IO spec parameter must be representable as a Python
  literal, and every IO spec class must be one of ``PandasData``,
  ``ExcelRange`` and ``ModuleData``. A model that does not satisfy this
  now raises ``TypeError`` from :func:`~modelx.write_model` or
  :func:`~modelx.zip_model`. In practice this affects
  :meth:`Model.new_pandas<modelx.core.model.Model.new_pandas>` and
  :meth:`UserSpace.new_pandas<modelx.core.space.UserSpace.new_pandas>`
  called with a ``Series`` whose ``name`` cannot be written as a Python
  literal — a ``pandas.Timestamp``-named Series, for example, or a
  ``float`` name that is ``NaN`` or infinite. Names that are numpy scalars
  are converted to their plain Python equivalents and are unaffected, and
  so are tuples of literals, such as the name of a Series taken from a
  column of a ``DataFrame`` with ``MultiIndex`` columns.

  Such models can still be saved by passing ``version=7``. The check runs
  before the previous save is rotated into its ``_BAK`` backup and before
  any file is written, so a save that fails this way leaves the previous
  save untouched.

* As described above, edits that previously deleted all ItemSpaces of
  the affected parameterized Spaces now delete only the dependent
  ItemSpaces. Code that relied on unrelated ItemSpaces being implicitly
  deleted by an edit should delete them explicitly, for example with
  :meth:`UserSpace.clear_items<modelx.core.space.UserSpace.clear_items>`
  or :meth:`Model.clear_all<modelx.core.model.Model.clear_all>`.

* Deleting a Space now deletes the live ItemSpaces of that Space and of
  its child Spaces, which previously survived the deletion with dangling
  references to the deleted Space. Code holding such an ItemSpace and
  using it after its Space is deleted now raises ``DeletedObjectError``
  instead of silently returning stale values.

* :meth:`UserSpace.add_bases<modelx.core.space.UserSpace.add_bases>` now
  raises ``NameError`` when the Space or one of its sub Spaces has a child
  Space with the same name as a Cells or a Reference it would inherit.
  Previously the operation silently succeeded, leaving the Space with two
  members under one name: an inherited Cells shadowed the child Space,
  while an inherited Reference was itself shadowed by the child Space on
  attribute access but shadowed it inside formulas. Because
  :func:`~modelx.read_model` replays base relationships through
  ``add_bases``, a model saved by an earlier version of modelx whose child
  Space collides with an inherited Cells now raises the same ``NameError``
  when read; rename the colliding member with an older version of modelx
  before upgrading. (A child Space colliding with an inherited Reference
  already failed to load with ``ValueError: Cannot create reference '...'``
  in earlier versions of modelx.)

* Deleting a derived Reference now raises ``ValueError`` in all cases.
  When the Reference held a modelx object, the deletion was previously a
  silent no-op.


Bug Fixes
============

* Renaming a Cells now refreshes the namespace of its Space, so formulas
  referring to the old name fail with a ``FormulaError`` reporting
  ``NameError: name '...' is not defined`` instead of silently resolving
  to the renamed Cells (`GH220`_, `GH259`_).

* Renaming a Cells to a name already defined in a sub Space is now
  rejected with a ``ValueError``. Previously the sub Space's own member
  was silently overwritten and lost (`GH260`_).

* Deleting a derived Reference no longer corrupts the model. Previously
  ``del`` on an inherited Reference raised
  ``ValueError: list.remove(x): x not in list`` *after* the Reference had
  already been replaced and dependent cached values cleared.

* Deleting a Reference created by ``new_space(refs={...})`` no longer
  raises an ``AssertionError``.

* Deleting a Reference that overrides a Reference in a base Space now
  recalculates the Cells of deeper sub Spaces. Previously those Cells kept
  returning values computed from the removed overriding value.

* :meth:`Model.update_pandas<modelx.core.model.Model.update_pandas>` and
  :meth:`Model.update_module<modelx.core.model.Model.update_module>` no
  longer corrupt the ``refmode`` of the References they update.
  ``'absolute'`` became ``('absolute',)`` and the default ``'auto'``
  became ``('auto',)``, and the corrupted value was inherited by derived
  References in sub Spaces.

* A failed :func:`~modelx.read_model` no longer leaves the IO objects and
  IO specs it created registered in modelx (`GH256`_). Previously such a
  failure could make the model unreadable for the rest of the session,
  keep the half-built model alive in memory, and cause later saves of
  *other* models to overwrite the leaked IO files.

* A failed :func:`~modelx.read_model` now restores the models that were
  open before the read (`GH257`_). Previously a model displaced by the
  read was left stranded under its ``_BAK`` name and
  :func:`~modelx.cur_model` was left unset, so the next operation
  depending on the current model silently created a new empty model.

* Reading a model saved with an old version of pandas no longer aborts
  on pandas 3.0, which removed a compatibility function modelx relied on
  (`GH255`_). The model now loads, with the values that pandas 3.0 can no
  longer rebuild replaced by ``None`` and reported through
  ``UserWarning``.

* The retry warning issued when writing to a zip archive on a network
  drive fails now shows the path of the archive instead of a literal
  ``'%s'`` (`GH82`_).

* The :func:`~modelx.write_model` documentation no longer describes
  serializer 2/4/5 behavior for Spaces and Cells created by
  ``new_space_from_excel`` and ``new_cells_from_excel``. Since serializer
  version 6 (modelx v0.22.0), such Spaces and Cells are written like any
  other member and their source Excel files are neither copied nor needed
  on read.

.. _GH220: https://github.com/fumitoh/modelx/issues/220
.. _GH259: https://github.com/fumitoh/modelx/pull/259
.. _GH260: https://github.com/fumitoh/modelx/issues/260
.. _GH256: https://github.com/fumitoh/modelx/pull/256
.. _GH257: https://github.com/fumitoh/modelx/pull/257
.. _GH82: https://github.com/fumitoh/modelx/issues/82


Changes
==========

* Starting with this release, modelx is no longer tested against
  Python 3.7 and 3.8, both of which have reached their end of life.
  modelx is now tested against Python 3.9 through 3.14 on Linux, macOS
  and Windows. While modelx may still function with Python 3.7 and 3.8,
  it won't be tested against these versions anymore.
