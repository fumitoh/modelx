"""RAM-saving collection over ordinary parameterized Spaces.

``collect_over`` declares the one Space parameter iterated by ``collect()``.
``collect_outputs`` is a normal zero-argument Cells formula evaluated in each
transient ItemSpace namespace. It returns optional ``individual`` and ``sum``
sections. Individual leaves are collected across ItemSpaces; sum leaves are
accumulated immediately. The ItemSpace is released after its outputs are detached.
"""

from collections import OrderedDict
from collections.abc import Mapping
from inspect import BoundArguments, Signature, Parameter
from itertools import product

from modelx.core.base import Interface, Impl
from modelx.core.binding.namespace import BaseNamespace
from modelx.core.cells import Cells, CellsImpl
from modelx.core.dynamic import ItemSpaceImpl
from modelx.core.formula import Formula
from modelx.core.reference import ReferenceImpl, ReferenceProxy
from modelx.core.node import NodeFactory, BaseNodeFactoryImpl
from modelx.export._mx_collect_semantics import Accumulator, normalize_domain, prepare_output


class _IdentityArgument:
    """Hashable identity wrapper for unhashable collect-call arguments."""

    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __hash__(self):
        return id(self.value)

    def __eq__(self, other):
        return type(other) is _IdentityArgument and self.value is other.value


def _key_arg(value):
    try:
        hash(value)
    except TypeError:
        return _IdentityArgument(value)
    return value


def _unkey_arg(value):
    return value.value if type(value) is _IdentityArgument else value


class CollectResult:
    """Attribute-style container returned by ``Space.collect()``.

    The public result mirrors the declared collection modes. For example,
    ``result.individual[policy_id].net_cf`` contains one ItemSpace's retained
    outputs while ``result.sum.net_cf`` contains values summed over the
    collection domain. Nested dictionaries below an output name are preserved.
    """

    __slots__ = ("_fields",)

    def __init__(self, fields):
        self._fields = fields

    def __getattr__(self, name):
        try:
            return self._fields[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(self._fields))

    def __repr__(self):
        fields = ", ".join(self._fields)
        return f"CollectResult({fields})"


def validate_collect_contract(formula, collect_over, collect_outputs):
    """Validate the optional collection declaration.

    Domain objects are intentionally not normalized here. They may be ordinary
    Python iterables, modelx References, or zero-argument Cells and are resolved
    after the Space and its References have been created.
    """

    if collect_over is None and collect_outputs is None:
        return None, None
    if collect_over is None or collect_outputs is None:
        raise TypeError("collect_over and collect_outputs must be supplied together")
    if formula is None:
        raise TypeError("a collect-enabled Space must have a parameter formula")
    if not isinstance(collect_over, Mapping) or not collect_over:
        raise TypeError("collect_over must be a non-empty mapping")

    space_formula = Formula(formula)
    params = space_formula.signature.parameters
    normalized = dict(collect_over)
    if len(normalized) != 1:
        raise ValueError("collect_over must declare exactly one Space parameter")
    for name in normalized:
        if name not in params:
            raise ValueError(
                f"collect_over parameter {name!r} is not in the Space formula signature")
        param = params[name]
        if param.kind not in (
            param.POSITIONAL_ONLY,
            param.POSITIONAL_OR_KEYWORD,
            param.KEYWORD_ONLY,
        ):
            raise TypeError(f"collect_over parameter {name!r} cannot be variadic")

    if any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params.values()):
        raise TypeError("collect-enabled Space formulas cannot use *args or **kwargs")

    output_formula = Formula(collect_outputs)
    if output_formula.parameters:
        raise TypeError("collect_outputs must be a zero-argument formula")

    return normalized, output_formula


class _CollectFormulaView:
    __slots__ = ("signature", "parameters", "source", "_bind_tails")

    def __init__(self, signature):
        self.signature = signature
        self.parameters = tuple(signature.parameters)
        self.source = "collect(...)"
        self._bind_tails = None


class _CollectDomain:
    """One collect domain backed by a Ref, Cells, or ordinary Python object."""

    __slots__ = ("source", "ref_parent", "ref_name")

    def __init__(self, source):
        if isinstance(source, ReferenceImpl):
            self.source = None
            self.ref_parent = source.parent
            self.ref_name = source.name
        else:
            self.source = source
            self.ref_parent = None
            self.ref_name = None

    def value(self, space):
        if self.ref_parent is not None:
            source = self.ref_parent.refs[self.ref_name]
            value = space.system.executor.add_reference(source).interface
        else:
            source = self.source
            if isinstance(source, CellsImpl):
                if source.formula.parameters:
                    raise TypeError("collect_over Cells must take no arguments")
                value = source.interface()
            else:
                value = source

        return normalize_domain(value)


def resolve_collect_over(space, collect_over):
    """Bind collect domain declarations to live modelx objects where possible.

    If a plain Python object is also installed as one of the Space's own Refs,
    the domain is bound to that Ref by identity. This keeps the declaration
    natural::

        refs={"policy_ids": policy_ids},
        collect_over={"point_id": policy_ids},

    while still tracing later updates to the ``policy_ids`` Reference.
    """

    result = OrderedDict()
    for name, source in collect_over.items():
        if isinstance(source, ReferenceProxy):
            source = source._impl
        elif isinstance(source, Cells):
            source = source._impl
        elif isinstance(source, (ReferenceImpl, CellsImpl)):
            pass
        else:
            matches = [ref for ref in space.own_refs.values() if ref.interface is source]
            if len(matches) == 1:
                source = matches[0]
            elif len(matches) > 1:
                raise ValueError(
                    "collect_over domain matches more than one Space Reference by identity")
        result[name] = _CollectDomain(source)
    return result


class _TransientItemSpaceImpl(ItemSpaceImpl):
    """Private ItemSpace used only during one collect iteration."""

    __slots__ = ("_released",)

    def __init__(self, *args, **kwargs):
        self._released = False
        super().__init__(*args, **kwargs)

    @property
    def dynamic_key(self):
        # Keep the transient tree outside the ordinary ItemSpace cache key space.
        return (("__collect__", self.name),)

    def release(self):
        if self._released:
            return
        self._released = True
        try:
            self.on_delete()
        finally:
            self.parent.named_itemspaces.pop(self.name, None)
            prefix = self.dynamic_key
            for key in list(self.parent.dynamic_cache):
                if key[:len(prefix)] == prefix:
                    self.parent.dynamic_cache.pop(key, None)


class _CollectNodeView(NodeFactory):
    """Small callable view for ordinary modelx dependency-node inspection."""

    __slots__ = ("_impl",)

    def __init__(self, runner):
        self._impl = runner

    def __call__(self, *args, **kwargs):
        return self._impl.call(args, kwargs)

    def _get_repr(self, fullname=False, add_params=True):
        return self._impl.get_repr(fullname=fullname, add_params=add_params)

    def __repr__(self):
        return self._get_repr(fullname=True)

    @property
    def _baseattrs(self):
        return {"type": "Collect", "name": "collect",
                "parameters": self._impl.formula.parameters,
                "repr": repr(self)}

    def _get_attrdict(self, extattrs=None, recursive=True):
        return self._baseattrs


class CollectRunner(BaseNodeFactoryImpl):
    """Cached ``Space.collect(...)`` node owned by a UserSpaceImpl."""

    __slots__ = ("space", "model", "is_cached", "data", "formula", "_signature",
                 "_bind_tails", "_template_ids", "interface")

    def __init__(self, space):
        self.space = space
        self.model = space.model
        self.is_cached = True
        self.data = {}
        self.interface = _CollectNodeView(self)
        self._template_ids = {space.idstr}
        self.reset_signature()

    def _make_signature(self):
        if self.space.formula is None:
            return Signature()
        omitted = set(self.space.collect_over_spec or {})
        return self.space.formula.signature.replace(parameters=[
            p for p in self.space.formula.signature.parameters.values()
            if p.name not in omitted
        ])

    def reset_signature(self):
        self._signature = self._make_signature()
        self.formula = _CollectFormulaView(self._signature)
        params = tuple(self._signature.parameters.values())
        self._bind_tails = None
        if all(p.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)
               for p in params):
            tails = [None] * (len(params) + 1)
            tail = tails[-1] = ()
            for i in range(len(params) - 1, -1, -1):
                if params[i].default is Parameter.empty:
                    break
                tail = (params[i].default,) + tail
                tails[i] = tail
            self._bind_tails = tuple(tails)

    def invalidate_templates(self, dirty=None):
        # Transient ItemSpaces no longer exist for ItemSpaceManager to inspect.
        # Remember only template IDs, never the deleted calculation trees.
        if dirty is None or self._template_ids.intersection(dirty):
            self.clear()
            self.reset_signature()
            self._template_ids = {self.space.idstr}

    def get_repr(self, fullname=False, add_params=True):
        name = self.space.idstr + ".collect" if fullname else self.space.name + ".collect"
        if add_params:
            return name + "(" + ", ".join(self.formula.parameters) + ")"
        return name

    def get_valuerefs(self):
        # Runtime references were contracted into refgraph, so get_attrpreds()
        # supplies them. The runner has no independent user formula to scan.
        return []

    def repr_parent(self):
        return self.space.get_repr(fullname=True, add_params=False)

    def has_node(self, key):
        return key in self.data

    def get_value_from_key(self, key):
        return self.data[key]

    def on_clear_trace(self, key):
        self.data.pop(key, None)

    def bind_key(self, args, kwargs):
        # Match ordinary modelx's common all-positional shortcut, including
        # defaults. Always route the resulting node through the executor so a
        # cache hit still records its downstream dependency.
        tails = self._bind_tails
        if not kwargs and type(args) is tuple and tails is not None and len(args) < len(tails):
            tail = tails[len(args)]
            if tail is not None:
                key = args + tail
                try:
                    hash(key)
                except TypeError:
                    return tuple(_key_arg(v) for v in key)
                return key
        bound = self._signature.bind(*args, **kwargs)
        bound.apply_defaults()
        return tuple(_key_arg(v) for v in bound.arguments.values())

    def _bound(self, key):
        return BoundArguments(
            self._signature,
            OrderedDict(zip(
                self._signature.parameters,
                (_unkey_arg(v) for v in key),
            )),
        )

    def call(self, args, kwargs):
        return self.space.system.executor.eval_node((self, self.bind_key(args, kwargs)))

    def clear(self):
        if self.data:
            self.model.clear_obj(self)

    def _domains(self):
        return [
            (name, domain.value(self.space))
            for name, domain in (self.space.collect_over_spec or {}).items()
        ]

    def _full_key(self, bound, coordinates):
        values = dict(bound.arguments)
        values.update(coordinates)
        original = self.space.formula.signature
        full = BoundArguments(
            original,
            OrderedDict((name, values[name]) for name in original.parameters),
        )
        return tuple(full.arguments.values())

    def _new_frame(self, full_key):
        base, refs = self.space._resolve_itemspace_params(full_key)
        from modelx.core.execution.trace import key_to_node, node_get_args
        return _TransientItemSpaceImpl(
            parent=self.space,
            base=base,
            name=None,
            refs=refs,
            arguments=node_get_args(key_to_node(self.space, full_key)),
            cache=None,
        )

    @staticmethod
    def _iter_transient_spaces(root):
        yield root
        for child in root.named_spaces.values():
            yield from CollectRunner._iter_transient_spaces(child)
        for item in root.param_spaces.values():
            yield from CollectRunner._iter_transient_spaces(item)

    def _contract_dependencies(self, root, caller):
        """Preserve dependencies while deleting the transient ItemSpace tree."""

        spaces = set(self._iter_transient_spaces(root))
        for space in spaces:
            base = space._dynbase
            self._template_ids.add(base.idstr)
            if base.model is self.model:
                self._template_ids.update(self.model.spmgr._graph.get_mro(base.idstr))
        cells = {cell for sp in spaces for cell in sp.cells.values()}
        internal_objects = spaces | cells
        graph, refgraph = self.model.tracegraph, self.model.refgraph
        nodes = {node for node in graph if node[0] in internal_objects}

        external_nodes = set()
        external_refs = set()
        for node in nodes:
            external_nodes.update(
                pred for pred in graph.predecessors(node)
                if pred not in nodes and pred != caller
            )
            if refgraph.has_node(node):
                external_refs.update(
                    pred for pred in refgraph.predecessors(node)
                    if pred not in internal_objects
                    and getattr(pred, "parent", None) not in spaces
                )

        evaluated_cells = {node[0] for node in nodes if node[0] in cells}
        evaluated_cells.update(
            cell for cell in cells
            if not cell.is_cached and refgraph.has_node(cell)
        )
        for cell in evaluated_cells:
            external_refs.update(
                ref for ref in cell._get_referents().get("refs", {}).values()
                if isinstance(ref, ReferenceImpl) and ref.parent not in spaces
            )

        for node in nodes:
            if graph.has_edge(node, caller):
                graph.remove_edge(node, caller)

        if refgraph.has_node(caller):
            for ref in list(refgraph.predecessors(caller)):
                if ref in internal_objects or getattr(ref, "parent", None) in spaces:
                    refgraph.remove_edge(ref, caller)
                else:
                    external_refs.add(ref)

        for node in external_nodes:
            graph.add_edge(node, caller)
        for ref in external_refs:
            refgraph.add_edge(ref, caller)

    def on_eval_formula(self, key):
        bound = self._bound(key)
        caller = (self, key)
        domains = self._domains()
        accumulator = Accumulator(CollectResult)
        live_types = (Interface, Impl, BaseNamespace, ReferenceProxy)

        for coords in product(*(domain for _, domain in domains)):
            coordinates = dict(zip((name for name, _ in domains), coords))
            root = self._new_frame(self._full_key(bound, coordinates))
            try:
                outputs = root.cells["collect_outputs"].interface()
                accumulator.add(coords[0], prepare_output(outputs, live_types))
                self._contract_dependencies(root, caller)
            finally:
                root.release()

        result = accumulator.result()
        self.data[key] = result
        return result
