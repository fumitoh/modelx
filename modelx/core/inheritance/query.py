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

"""Inheritance read for tools: ``BaseSpace._get_inheritance()``.

devnotes/ToolAPIDesign.md, T4. One call per Space answers, for every
Cells and every name in ``refs``, whether it is defined in the Space,
defined there over a base's member of that name, or derived, which Space
holds the definition in use, and where a Reference comes from.

It reads only names, the derived flags of members and the inheritance
graph. It never reads a Reference's value, so it evaluates nothing and
never resolves a derived relative Reference whose value is a null Space.

The MRO is computed once per call, from the static Space. Asking each
member for its ``bases`` instead walks the graph once per member: a
whole-model read cost 382, 717 and 1,768 us on BasicTerm_S,
BasicTermASL_ME and simplelife, against 9.6, 58.3 and 112.7 us for the
states alone with one MRO per Space (inheritance/i04). A call on every
UserSpace of those models costs 17-19, 108-111 and 164-172 us, against
7-8, 44-47 and 77-82 us for i04's states alone in the same processes
(min of 7 x 200 in 5 alternating rounds, 3 processes, CPython 3.11.15):
it also builds a dict for each member, the scopes of the names in
``refs`` and the two lists of bases. The graph's MRO is the largest
part: 22-33 of the 81 us a call takes on simplelife's Projection, with 2
bases and 93 Cells, and ``bases`` costs the same.

A dynamic Space has no node in the inheritance graph, so it is read
through its static Space, ``_dynbase``. Querying the graph with the
idstr of an ItemSpace gave the bases of unrelated Spaces whose names are
letters of that idstr: ``'Sub.__Space1'`` gave the bases of a Space
``S`` (inheritance/i08; F6 fixed the graph itself).
"""

from modelx.core.base import get_interface_list

DEFINED = "defined"
OVERRIDING = "overriding"
DERIVED = "derived"


def _member_states(static, mro, attr):
    """``{name: {'state': ..., 'defined_in': ...}}`` for the members
    ``attr`` (``'cells'`` or ``'own_refs'``) of the UserSpaceImpl
    ``static``, in their order.

    ``mro`` is ``static``'s C3 MRO without ``static``. A derived member
    is re-derived from the first base in the MRO whose member of that
    name is defined (``InheritanceSync.reconcile``), so that base is
    ``defined_in``.
    """
    here = static.interface
    base_maps = [(b.interface, getattr(b, attr)) for b in mro]
    base_names = set().union(*(found for _, found in base_maps))
    result = {}
    for name, member in getattr(static, attr).items():
        if member._is_derived:
            defined_in = None
            for base, found in base_maps:
                other = found.get(name)
                if other is not None and not other._is_derived:
                    defined_in = base
                    break
            result[name] = {"state": DERIVED, "defined_in": defined_in}
        elif name in base_names:
            result[name] = {"state": OVERRIDING, "defined_in": here}
        else:
            result[name] = {"state": DEFINED, "defined_in": here}
    return result


def get_inheritance(impl):
    """The dict ``BaseSpace._get_inheritance()`` returns, for the Space
    ``impl``. New containers on each call."""

    dynamic = impl.is_dynamic()
    static = impl._dynbase if dynamic else impl
    mro = static.bases
    if dynamic:
        bases = [static.interface]
        direct_bases = [static.interface]
    else:
        bases = get_interface_list(mro)
        # The direct bases are in the MRO, so a Space with an empty MRO has
        # none, and the graph is not asked again: impl.direct_bases cost 3.2
        # of the 35 us a call took on BasicTerm_S's Projection, which has no
        # bases.
        direct_bases = get_interface_list(impl.direct_bases) if mro else []

    cells = _member_states(static, mro, "cells")
    if dynamic:     # in the order of the dynamic Space's own cells
        cells = {name: cells[name] for name in impl.cells}

    # Scopes follow the layers of refs_outer, which the public refs view
    # lists, in lookup order, so a name hidden by an earlier layer gets
    # the scope of the binding in use. sys_refs (_self, _space, _model) is
    # not a layer of refs_outer, so the system names are never reported.
    #   UserSpace: own_refs, then the Model's _global_refs.
    #   dynamic:   the arguments of each ItemSpace from this Space up
    #              (_allargs), own_refs (refs the Space formula returned),
    #              _dynbase_refs (the static Space's References, resolved
    #              slots included), then _global_refs.
    ref_states = _member_states(static, mro, "own_refs")
    if dynamic:
        layers = (("argument", set().union(*impl._allargs.maps)),
                  ("formula", impl.own_refs))
        members, member_scope = impl._dynbase_refs, "base"
    else:
        layers = ()
        members, member_scope = impl.own_refs, "space"
    model = impl.model.interface
    refs = {}
    for name in impl.refs_outer:
        for scope, layer in layers:
            if name in layer:
                refs[name] = {"scope": scope, "state": None,
                              "defined_in": None}
                break
        else:
            if name in members:
                state = ref_states[name]
                refs[name] = {"scope": member_scope,
                              "state": state["state"],
                              "defined_in": state["defined_in"]}
            elif name == "__builtins__":
                refs[name] = {"scope": "builtins", "state": None,
                              "defined_in": None}
            else:
                refs[name] = {"scope": "global", "state": None,
                              "defined_in": model}

    return {
        "bases": bases,
        "direct_bases": direct_bases,
        "cells": cells,
        "refs": refs,
    }
