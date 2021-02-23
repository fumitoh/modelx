Saving Model (Draft)
====================

.. currentmodule:: modelx

modelx offers two ways to save models.

Pickling Models
---------------

By "Pickling", a model is saved into a single file as a byte stream.
It is like taking a snapshot of a model.
"Pickling" is meant for a short-term storage.

* :meth:`~core.model.Model.save`
* :func:`open_model`


Writing Models
--------------

By "Writing", a model is saved into text files under a directory tree.


* :meth:`~core.model.Model.write`
* :func:`write_model`
* :func:`read_model`
