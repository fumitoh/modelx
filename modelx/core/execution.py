import sys
import time
import os.path
import threading
import traceback
from collections import deque
from typing import Optional
import modelx   # https://bugs.python.org/issue18145
from modelx.core.errors import DeepReferenceError, FormulaError
from modelx.core.trace import (
    OBJ, KEY, get_node_repr, TraceObject, TraceGraph, ReferenceGraph, TraceKey, TraceNode
)


class NonThreadedExecutor:

    def __init__(self, maxdepth=None):

        self.refstack = deque()
        self.errorstack = None
        self.rolledback = deque()
        self.callstack = CallStack(self, maxdepth)
        self.is_executing: bool = False
        self.tracegraph: Optional[TraceGraph] = None
        self.refgraph: Optional[ReferenceGraph] = None
        self.is_formula_error_used = True
        self.is_formula_error_handled = False

    def eval_node(self, node: TraceNode):

        obj = node[OBJ]
        key = node[KEY]

        if obj.is_cached and obj.has_node(key):
            value = obj.data[key]
            if self.callstack:
                # Shortcut for append & pop for performance
                pred = self.callstack.idxstack[-1]
                if pred >= 0:
                    self.tracegraph.add_edge(node, self.callstack[pred])
                # self.callstack.append(node)
                # self.callstack.pop()
        else:
            if self.is_executing:
                value = self._eval_formula(node)
            else:
                value = self._start_exec(node)

        return value

    def _eval_formula(self, node: TraceNode):

        self.callstack.append(node)
        obj, key = node[OBJ], node[KEY]

        try:
            value = obj.on_eval_formula(key)

        except:
            self.callstack.rollback()
            raise
        else:
            self.callstack.pop()

        return value

    def _start_exec(self, node: TraceNode):

        self.excinfo = None
        self.errorstack = None
        self.is_executing = True
        self.tracegraph = node[OBJ].model.tracegraph
        self.refgraph = node[OBJ].model.refgraph

        try:
            self.buffer = self._eval_formula(node)
        except:
            self.excinfo = sys.exc_info()
        finally:
            self.is_executing = False
            self.tracegraph = None
            self.refgraph = None

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

                # self.executor.is_executing = False
                self.signal_start.clear()
                self.signal_stop.set()

    def _start_exec(self, node):
        self.initnode = node
        self.excinfo = None
        self.errorstack = None
        try:
            self.is_executing = True
            self.tracegraph = node[OBJ].model.tracegraph
            self.refgraph = node[OBJ].model.refgraph
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
            self.is_executing = False
            self.tracegraph = None
            self.refgraph = None


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
        obj = node[OBJ]

        graph = self.executor.tracegraph
        if self:    # Not empty
            pred = self.idxstack[-1]    # index of last cached cells
            if pred >= 0:
                if obj.is_cached:
                    graph.add_edge(node, self[pred])
                else:
                    self.executor.refgraph.add_edge(obj, self[pred])
            else:
                if obj.is_cached:
                    graph.add_node(node)
        else:
            if obj.is_cached:
                graph.add_node(node)

        while self.refstack:
            if self.refstack[-1][0] == self.counter:
                _, ref = self.refstack.pop()
                self.executor.refgraph.add_edge(ref, node)
            else:
                break

        return node

    def rollback(self):
        node = deque.pop(self)
        self.idxstack.pop()
        self.executor.rolledback.append(node)
        self.counter -= 1
        obj = node[OBJ]

        graph = self.executor.tracegraph
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
        from modelx.core.node import ItemNode   # TODO: Resolve dependency integrity

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

