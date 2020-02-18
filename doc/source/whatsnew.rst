.. py:currentmodule:: modelx

==========
What's New
==========

.. Begin Development Sate

.. warning::

   With the release of modelx version 0.1.0 in December 2019,
   the author of modelx will try to consider maintaining
   backward compatibility to a limited extent
   in developing future releases of modelx.
   Especially, he will try to make it possible to read
   models written to files by one version's :func:`write_model`,
   by :func:`read_model` of the next version of modelx.
   However, models saved by :meth:`Model.save <core.model.Model.save>`
   method may not be opened by new version's :func:`open_model`.
   Overall, modelx is still in its early alpha-release stage,
   and its specifications may change without consideration
   on backward compatibility.

.. End Development Sate

Updates
=======

.. include:: updates.rst
   :start-after: Latest Updates Begin
   :end-before: Latest Updates End

:doc:`... See more updates<updates>`

.. toctree::
   :hidden:

   updates

Release Notes
=============

.. toctree::
   :maxdepth: 2

   releases/relnotes_v0_3_0
   releases/relnotes_v0_2_0
   releases/relnotes_v0_1_0
   releases/relnotes_v0_0_25
   releases/relnotes_v0_0_24
   releases/relnotes_v0_0_23
   releases/relnotes_v0_0_22
   releases/old_mx_releases
   releases/spyder_mx_releases