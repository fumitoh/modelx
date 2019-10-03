.. currentmodule:: modelx

===============================
modelx v0.0.24 (4 October 2019)
===============================

Code around implementing inheritance is extensively refactored in this release,
and a couple of small enhancements are incorporated based of user's feature requests.


.. contents:: What's new in v0.0.24
   :depth: 1
   :local:

Enhancements
============

* Models with modules included in them as references can now be saved with
  :meth:`~core.model.Model.save` method (`GitHub #8 Comment`_).

.. _GitHub #8 Comment: https://github.com/fumitoh/modelx/issues/8#issuecomment-536170506

* ``name`` parameter is added to :func:`~read_model` to overwrite
  the opened model name (`GitHub #8`_).

.. _GitHub #8: https://github.com/fumitoh/modelx/issues/8


Bug Fixes
=========
* Getting cells values from the shell iteratively was taking too slow
  (`GitHub #12`_)

.. _GitHub #12: https://github.com/fumitoh/modelx/issues/12

