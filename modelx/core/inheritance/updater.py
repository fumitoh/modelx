# Copyright (c) 2017-2026 Fumito Hamamura <fumito.ham@gmail.com>

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

"""Step C2: the per-space inheritance algorithm, extracted.

``inherit_members`` is the verbatim body of the former
``UserSpaceImpl.on_inherit`` (which is now a thin delegate). It diffs a
space's member container (``cells`` or ``own_refs``) against the
corresponding containers of its bases and:

* creates a derived placeholder member for each base name missing locally,
* reorders members so base-introduced names precede locally defined ones,
* recurses into derived members (``member.on_inherit``) to pull formula/
  value from the base, and
* drops local derived members no longer backed by any base.

This is a behavior-preserving relocation: the container mutations remain
the raw dict operations the original used (``MemberContainer`` is a dict
subclass, so these do not notify -- the notification timing is unchanged).
Switching these to the notifying container API is intentionally deferred so
this step changes only *where* the algorithm lives, not *what* it does.
``space.on_del_cells`` / ``space.on_del_ref`` remain on the space and are
invoked here exactly as before.
"""

from modelx.core.chainmap import CustomChainMap
from modelx.core.cells import UserCellsImpl
from modelx.core.reference import ReferenceImpl


def inherit_members(space, updater, bases, attr):
    """Relocated body of ``UserSpaceImpl.on_inherit(updater, bases, attr)``.

    ``attr`` is ``"cells"`` or ``"own_refs"``; ``space`` is the
    ``UserSpaceImpl`` being updated; ``bases`` is its ordered base list.
    """

    attrs = {
        "cells": space.on_del_cells,
        "own_refs": space.on_del_ref
    }

    selfdict = getattr(space, attr)
    basedict = CustomChainMap(*[getattr(b, attr) for b in bases])
    selfkeys = list(selfdict)

    for name in basedict:  # ChainMap iterates from the last map

        bs = [bm[name] for bm in basedict.maps
              if name in bm and bm[name].is_defined()]

        if name not in selfdict:

            if attr == "cells":
                selfdict[name] = UserCellsImpl(
                    space=space, name=name, formula=None,
                    is_derived=True)

            elif attr == "own_refs":
                selfdict[name] = ReferenceImpl(
                    space, name, None,
                    container=space.own_refs,
                    is_derived=True,
                    refmode=bs[0].refmode,
                    set_item=False
                )
            else:
                raise RuntimeError("must not happen")

        else:
            # Remove & add back for reorder
            selfdict[name] = selfdict.pop(name)
            selfkeys.remove(name)

        if selfdict[name].is_derived():
            selfdict[name].on_inherit(updater, bs)

    for name in selfkeys:
        if selfdict[name].is_derived():
            attrs[attr](name)
        else:   # defined
            selfdict[name] = selfdict.pop(name)
