import sys
import time
import os.path
import threading
import traceback
from collections import deque
import networkx as nx
import modelx   # https://bugs.python.org/issue18145
from modelx.core.node import get_node_repr
from modelx.core.node import OBJ, KEY, ItemNode, node_has_key
from modelx.core.errors import DeepReferenceError, FormulaError


class TraceGraph(nx.DiGraph):
    """Directed Graph of ObjectArgs"""

    def remove_with_descs(self, source):
        """Remove all descendants of(reachable from) `source`.

        Args:
            source: Node descendants
        Returns:
            set: The removed nodes.
        """
        if not self.has_node(source):
            return set()
        desc = nx.descendants(self, source)
        desc.add(source)
        self.remove_nodes_from(desc)
        return desc

    def clear_obj(self, obj):
        """Remove all nodes with `obj` and their descendants."""
        obj_nodes = self.get_nodes_with(obj)
        removed = set()
        for node in obj_nodes:
            if self.has_node(node):
                removed.update(self.remove_with_descs(node))
        return removed

    def get_nodes_with(self, obj):
        """Return nodes with `obj`."""
        result = set()

        if nx.__version__[0] == "1":
            nodes = self.nodes_iter()
        else:
            nodes = self.nodes

        for node in nodes:
            if node[OBJ] == obj:
                result.add(node)
        return result

    def get_startnodes_from(self, node):
        if node in self:
            return [n for n in nx.descendants(self, node)
                    if self.out_degree(n) == 0]
        else:
            return []

    def fresh_copy(self):
        """Overriding Graph.fresh_copy"""
        return TraceGraph()

    def add_path(self, nodes, **attr):
        """(Not used anymore) In replacement for Deprecated add_path method"""
        if nx.__version__[0] == "1":
            return super().add_path(nodes, **attr)
        else:
            return nx.add_path(self, nodes, **attr)


class ReferenceGraph(nx.DiGraph):

    def remove_with_descs(self, ref):
        if ref not in self:
            return set()
        desc = nx.descendants(self, ref)
        self.remove_nodes_from((ref, *desc))
        return desc     # Not including ref

    def remove_with_referred(self, nodes):
        """Remove nodes that refer to ref nodes.

        If the referred ref nodes become isolated, also remove them.
        """
        refs = []
        for n in nodes:
            if self.has_node(n):
                for pred in self.predecessors(n):
                    if pred not in refs:
                        refs.append(pred)
        self.remove_nodes_from(nodes)
        for n in refs:
            if self.degree(n) == 0:
                self.remove_node(n)


class TraceManager:

    __slots__ = ()
    __mixin_slots = (
        "tracegraph",
        "refgraph"
    )

    def __init__(self):
        self.tracegraph = TraceGraph()
        self.refgraph = ReferenceGraph()

    def clear_with_descs(self, node):
        """Clear values and nodes calculated from `source`."""
        removed = self.tracegraph.remove_with_descs(node)
        self.refgraph.remove_with_referred(removed)
        for node in removed:
            node[OBJ].on_clear_trace(node[KEY])

    def clear_obj(self, obj):
        """Clear values and nodes of `obj` and their dependants."""
        removed = self.tracegraph.clear_obj(obj)
        self.refgraph.remove_with_referred(removed)
        for node in removed:
            if node_has_key(node):
                node[OBJ].on_clear_trace(node[KEY])

    def clear_attr_referrers(self, ref):
        removed = self.refgraph.remove_with_descs(ref)
        for node in removed:
            descs = self.tracegraph.remove_with_descs(node)
            for desc in descs:
                desc[OBJ].on_clear_trace(desc[KEY])

    def get_calcsteps(self, targets, nodes, step_size):
        """ Get calculation steps
        Calculate a new block
        Find nodes to paste in the block
        Find nodes to clear from the earlier blocks
        Push the paste node in the earlier blocks
        """
        subgraph = self.tracegraph.subgraph(nodes)

        ordered = list(nx.topological_sort(subgraph))
        node_len = len(ordered)

        pasted = []         # in reverse order
        step = 0
        result = []
        while step * step_size < node_len:

            start = step * step_size
            stop = min(node_len, (step + 1) * step_size)

            cur_block = ordered[start:stop]
            cur_paste = []
            cur_clear = []
            cur_targets = []    # also included in cur_paste
            for n in cur_block:

                paste = False
                if n in targets:
                    cur_targets.append(n)
                    paste = True
                else:
                    for suc in subgraph.successors(n):
                        if suc not in cur_block:
                            paste = True
                            break
                if paste:
                    cur_paste.append(n)
                else:
                    cur_clear.append(n)

            accum_nodes = set(ordered[:stop])
            for n in pasted.copy():

                paste = False
                for suc in subgraph.successors(n):
                    if suc not in accum_nodes:
                        paste = True
                        break

                if not paste:
                    cur_clear.append(n)
                    pasted.remove(n)

            for n in cur_paste:
                if n not in cur_targets:
                    pasted.append(n)

            result.append(['calc', [ItemNode(n) for n in cur_block]])
            result.append(['paste', [ItemNode(n) for n in reversed(cur_paste)]])
            result.append(['clear', [ItemNode(n) for n in cur_clear]])

            step += 1

        assert not pasted
        return result


class NonThreadedExecutor:

    def __init__(self, maxdepth=None):

        self.refstack = deque()
        self.errorstack = None
        self.rolledback = deque()
        self.callstack = CallStack(self, maxdepth)
        self.is_executing = False
        self.is_formula_error_used = True
        self.is_formula_error_handled = False

    def eval_node(self, node):

        cells = node[OBJ]
        key = node[KEY]

        if cells.is_cached and cells.has_node(key):
            value = cells.data[key]
            if self.callstack:
                # Shortcut for append & pop for performance
                pred = self.callstack.idxstack[-1]
                if pred >= 0:
                    cells.model.tracegraph.add_edge(node, self.callstack[pred])
                # self.callstack.append(node)
                # self.callstack.pop()
        else:
            if self.is_executing:
                value = self._eval_formula(node)
            else:
                value = self._start_exec(node)

        return value

    def _eval_formula(self, node):

        self.callstack.append(node)
        cells, key = node[OBJ], node[KEY]

        try:
            value = cells.on_eval_formula(key)

        except:
            self.callstack.rollback()
            raise
        else:
            self.callstack.pop()

        return value

    def _start_exec(self, node):

        self.excinfo = None
        self.errorstack = None
        self.is_executing = True

        try:
            self.buffer = self._eval_formula(node)
        except:
            self.excinfo = sys.exc_info()
        finally:
            self.is_executing = False

        assert not self.callstack
        assert not self.callstack.counter
        assert not self.refstack

        if self.excinfo:

            self.errorstack = ErrorStack(
                self.excinfo,
                self.rolledback
            )
            e = self.excinfo[1]
            if self.is_formula_error_used:
                errmsg = traceback.format_exception_only(
                    self.excinfo[0],
                    e
                )
                errmsg = "".join(errmsg)

                if e.__cause__ is not None:
                    cause = e.__cause__
                    cause_traceback = ''.join(traceback.format_exception(type(cause), cause, cause.__traceback__))
                    errmsg += "\nCaused by:\n" + cause_traceback

                errmsg += self.errorstack.tracemessage()
                err = FormulaError(
                    "Error raised during formula execution\n" + errmsg)
                if self.is_formula_error_handled:
                    print(err, file=sys.stderr)
                else:
                    raise err
            else:
                raise e

        else:
            return self.buffer


class ThreadedExecutor(NonThreadedExecutor):

    def __init__(self, maxdepth=None):

        # Use thread to increase stack size and deepen callstack
        # Ref: https://bugs.python.org/issue32570

        NonThreadedExecutor.__init__(self, maxdepth=maxdepth)
        self.thread = ThreadedExecutor.ExecThread(self)
        self.thread.daemon = True

        # Set max stack size to nt limit (256MB)
        # https://github.com/python/cpython/blob/v3.9.6/Python/thread_nt.h#L358

        last_size = threading.stack_size(0x10000000 - 1)
        self.thread.start()
        threading.stack_size(last_size)
        self.initnode = None

    class ExecThread(threading.Thread):

        def __init__(self, executor):
            self.executor = executor
            self.buffer = None
            self.signal_start = threading.Event()
            self.signal_stop = threading.Event()
            super().__init__()

        def run(self):
            while True:
                self.signal_start.wait()
                try:
                    self.buffer = self.executor._eval_formula(
                        self.executor.initnode)
                except:
                    self.executor.excinfo = sys.exc_info()

                self.executor.is_executing = False
                self.signal_start.clear()
                self.signal_stop.set()

    def _start_exec(self, node):
        self.initnode = node
        self.excinfo = None
        self.errorstack = None
        try:
            self.is_executing = True
            self.thread.signal_start.set()
            self.thread.signal_stop.wait()
            self.thread.signal_stop.clear()
            assert not self.callstack
            assert not self.callstack.counter
            assert not self.refstack

            if self.excinfo:

                self.errorstack = ErrorStack(
                    self.excinfo,
                    self.rolledback
                )
                if self.is_formula_error_used:
                    errmsg = traceback.format_exception_only(
                        self.excinfo[0],
                        self.excinfo[1]
                    )
                    errmsg = "".join(errmsg)
                    errmsg += self.errorstack.tracemessage()
                    raise FormulaError(
                        "Error raised during formula execution\n" + errmsg)
                else:
                    raise self.excinfo[1]

            else:
                return self.thread.buffer

        except FormulaError as err:
            if self.is_formula_error_handled:
                print(str(err), file=sys.stderr)
            else:
                raise

        finally:
            self.initnode = None


class CallStack(deque):

    if sys.version_info >= (3, 12):
        default_maxdepth = 100_000
    else:
        if sys.platform == "win32":
            default_maxdepth = 50000
        else:
            default_maxdepth = 65000

    def __init__(self, executor, maxdepth=None):
        self.executor = executor
        self.refstack = executor.refstack
        self.idxstack = deque()

        if maxdepth:
            self.maxdepth = maxdepth
        else:
            self.maxdepth = self.default_maxdepth

        self.counter = 0
        deque.__init__(self)

    def last(self):     # Not used anymore
        return self[-1]

    def is_empty(self):
        return len(self) == 0

    def append(self, item):

        stacklen = len(self)
        if stacklen > self.maxdepth:
            raise DeepReferenceError(
                "Formula chain exceeded the %s limit" % self.maxdepth)

        if item[OBJ].is_cached:
            self.idxstack.append(stacklen)
        elif stacklen:
            self.idxstack.append(self.idxstack[-1])
        else:   # idxstack is empty
            self.idxstack.append(-1)

        deque.append(self, item)
        self.counter += 1

    def pop(self):
        node = deque.pop(self)
        self.idxstack.pop()
        self.counter -= 1
        cells = node[OBJ]

        graph = cells.model.tracegraph
        if self:    # Not empty
            pred = self.idxstack[-1]    # index of last cached cells
            if pred >= 0:
                if cells.is_cached:
                    graph.add_edge(node, self[pred])
                else:
                    graph.add_edge((cells,), self[pred])
            else:
                if cells.is_cached:
                    graph.add_node(node)
        else:
            if cells.is_cached:
                graph.add_node(node)

        while self.refstack:
            if self.refstack[-1][0] == self.counter:
                _, ref = self.refstack.pop()
                cells.model.refgraph.add_edge(ref, node)
            else:
                break

        return node

    def rollback(self):
        node = deque.pop(self)
        self.idxstack.pop()
        self.executor.rolledback.append(node)
        self.counter -= 1
        cells = node[OBJ]

        graph = cells.model.tracegraph
        if graph.has_node(node):
            graph.remove_node(node)

        while self.refstack:
            if self.refstack[-1][0] == self.counter:
                _, ref = self.refstack.pop()
            else:
                break

    def tracemessage(self, maxlen=6):
        """ Not Used?
        if maxlen > 0, the message is shortened to maxlen traces.
        """
        assert False    # TODO: This method is not used. Deleted in future version.

        result = ""
        for i, value in enumerate(self):
            result += "{0}: {1}\n".format(i, get_node_repr(value))

        result = result.strip("\n")
        lines = result.split("\n")

        if maxlen and len(lines) > maxlen:
            i = int(maxlen / 2)
            lines = lines[:i] + ["..."] + lines[-(maxlen - i) :]
            result = "\n".join(lines)

        return result


if sys.version_info < (3, 7, 0):
    _trace_time = time.time
else:
    def time_ns():
        return time.time_ns() / 10**9
    _trace_time = time_ns


class TraceableCallStack(CallStack):

    def __init__(self, executor, maxdepth=None, maxlen=None):

        CallStack.__init__(self, executor, maxdepth)
        self.tracestack = deque(maxlen=maxlen)

    def append(self, item):

        CallStack.append(self, item)
        self.tracestack.append(
            ("ENTER", len(self) - 1, _trace_time(), item)
        )

    def pop(self):
        item = super().pop()
        self.tracestack.append(
            ("EXIT", len(self), _trace_time(), item)
        )

    def get_tracestack(self):
        return list(
            (sign,
             depth,
             t_stamp,
             item[OBJ].get_repr(fullname=True, add_params=True),
             item[KEY]
             ) for sign, depth, t_stamp, item in self.tracestack
        )

    def get_nodes(self):
        return list(
            trace[3] for trace in self.tracestack if trace[0] == "ENTER")


class ErrorStack(deque):

    def __init__(self, execinfo, rolledback):
        deque.__init__(self)
        tbexc = traceback.TracebackException.from_exception(execinfo[1])
        tb = execinfo[2]
        self.on_eval_flag = False

        mxdir = os.path.dirname(modelx.__file__)

        for frame in tbexc.stack:
            if mxdir in frame.filename and frame.name == "on_eval_formula":
                self.on_eval_flag = True
            elif not mxdir in frame.filename and self.on_eval_flag:
                node = rolledback.pop()
                self.append(
                    (node, frame.lineno, tb.tb_frame.f_locals.copy())
                )
                self.on_eval_flag = False
            tb = tb.tb_next

        while rolledback:
            node = rolledback.pop()
            self.append(
                (node, 0, None)
            )

    def get_traceback(self, show_locals):
        if show_locals:
            return [(ItemNode(frame[0]), frame[1], frame[2]) for frame in self]
        else:
            return [(ItemNode(frame[0]), frame[1]) for frame in self]

    def tracemessage(self, maxlen=20):
        """
        if maxlen > 0, the message is shortened to maxlen traces.
        """
        result = "\nFormula traceback:\n"
        for i, frame in enumerate(self):
            result += "{0}: {1}".format(i, get_node_repr(frame[0]))
            if frame[1]:
                result += ", line %s" % frame[1]
            result += "\n"

        result = result.rstrip("\n")
        lines = result.split("\n")

        if maxlen and len(lines) > maxlen:
            i = int(maxlen / 2)
            lines = lines[:i] + ["..."] + lines[-(maxlen - i):]
            result = "\n".join(lines)

        # last formula
        src = "\nFormula source:\n"
        src += self[-1][0][OBJ].formula.source
        result += "\n" + src

        return result

