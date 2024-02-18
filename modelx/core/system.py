# Copyright (c) 2017-2024 Fumito Hamamura <fumito.ham@gmail.com>

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

import sys
if sys.platform == "linux":
    import resource
import time
import os.path
import warnings
import pickle
import threading
import traceback
import pathlib
from collections import deque
from contextlib import contextmanager
import modelx   # https://bugs.python.org/issue18145
from modelx.core.node import get_node_repr
from modelx.core.base import NullImpl, null_impl
from modelx.core.model import ModelImpl
from modelx.core.util import AutoNamer, is_valid_name
from modelx.core.errors import DeepReferenceError, FormulaError
from modelx.core.node import OBJ, KEY, ItemNode
from modelx.io.baseio import IOManager, BaseSharedIO


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

        if cells.has_node(key):
            value = cells.data[key]
            if self.callstack:
                cells.model.tracegraph.add_edge(node, self.callstack[-1])
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
            if self.is_formula_error_used:
                errmsg = traceback.format_exception_only(
                    self.excinfo[0],
                    self.excinfo[1]
                )
                errmsg = "".join(errmsg)
                errmsg += self.errorstack.tracemessage()
                err = FormulaError(
                    "Error raised during formula execution\n" + errmsg)
                if self.is_formula_error_handled:
                    print(err, file=sys.stderr)
                else:
                    raise err
            else:
                raise self.excinfo[1]

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

        if len(self) > self.maxdepth:
            raise DeepReferenceError(
                "Formula chain exceeded the %s limit" % self.maxdepth)
        deque.append(self, item)
        self.counter += 1

    def pop(self):
        node = deque.pop(self)
        self.counter -= 1
        cells = node[OBJ]

        graph = cells.model.tracegraph
        if self:
            graph.add_edge(node, self[-1])
        else:
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
        """
        if maxlen > 0, the message is shortened to maxlen traces.
        """
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

    def tracemessage(self, maxlen=6):
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


def custom_showwarning(
    message, category, filename="", lineno=-1, file=None, line=None
):
    """Hook to override default showwarning.

    https://stackoverflow.com/questions/2187269/python-print-only-the-message-on-warnings
    """

    if file is None:
        file = sys.stderr
        if file is None:
            # sys.stderr is None when run with pythonw.exe:
            # warnings get lost
            return
    text = "%s: %s\n" % (category.__name__, message)
    try:
        file.write(text)
    except OSError:
        # the file (probably stderr) is invalid - this warning gets lost.
        pass


def is_ipython():
    """True if the current shell is an IPython shell.

    Note __IPYTHON__ is not yet set before IPython kernel is initialized.

    https://stackoverflow.com/questions/5376837/how-can-i-do-an-if-run-from-ipython-test-in-python
    """
    try:
        __IPYTHON__
        return True
    except NameError:
        return False


class System:

    orig_settings = {
        "sys.recursionlimit": sys.getrecursionlimit(),
        "showwarning": warnings.showwarning
    }
    if sys.platform == "linux":
        orig_settings["resource.RLIMIT_STACK"] = resource.getrlimit(
            resource.RLIMIT_STACK
        )

    def __init__(self, maxdepth=None, setup_shell=False):

        self.configure_python()
        self.is_formula_error_used = True
        if sys.version_info >= (3, 12):
            self.executor = NonThreadedExecutor(maxdepth=maxdepth)
        else:
            if sys.platform == "win32":
                self.executor = ThreadedExecutor(maxdepth=maxdepth)
            else:
                self.executor = NonThreadedExecutor(maxdepth=maxdepth)
        self.callstack = self.executor.callstack
        self.refstack = self.executor.refstack
        self._modelnamer = AutoNamer("Model")
        self._backupnamer = AutoNamer("_BAK")
        self.currentmodel = None
        self._models = {}
        self.serializing = None
        self._recalc_dependents = False

        if setup_shell:
            if is_ipython():
                self.is_ipysetup = False
                self.setup_ipython()
            else:
                self.shell = None
                self.is_ipysetup = False
        else:
            self.is_ipysetup = False

        self.iomanager = IOManager()

    def setup_ipython(self):
        """Monkey patch shell's error handler.

        This method is to monkey-patch the showtraceback method of
        IPython's InteractiveShell to

        __IPYTHON__ is not detected when starting an IPython kernel,
        so this method is called from start_kernel in spyder-modelx.
        """
        if self.is_ipysetup:
            return

        from ipykernel.kernelapp import IPKernelApp

        self.shell = IPKernelApp.instance().shell  # None in PyCharm console

        if not self.shell and is_ipython():
            self.shell = get_ipython()

        if self.shell:
            shell_class = type(self.shell)
            shell_class.default_showtraceback = shell_class.showtraceback
            shell_class.showtraceback = custom_showtraceback
            self.is_ipysetup = True
        else:
            raise RuntimeError("IPython shell not found.")

    def restore_ipython(self):
        """Restore default IPython showtraceback"""
        if not self.is_ipysetup:
            return

        shell_class = type(self.shell)
        shell_class.showtraceback = shell_class.default_showtraceback
        del shell_class.default_showtraceback

        self.is_ipysetup = False

    def configure_python(self):
        """Configure Python settings for modelx

        The error handler is configured later.
        """
        if sys.platform == "linux":
            _, hard = resource.getrlimit(resource.RLIMIT_STACK)
            if hard != resource.RLIM_INFINITY:
                warnings.warn("Stack is not unlimited")
            resource.setrlimit(resource.RLIMIT_STACK, (hard, hard))

        sys.setrecursionlimit(10**6)
        warnings.showwarning = custom_showwarning

    def restore_python(self):
        """Restore Python settings to the original states"""
        orig = self.orig_settings

        if sys.platform == "linux":
            resource.setrlimit(
                resource.RLIMIT_STACK,
                orig["resource.RLIMIT_STACK"]
            )

        sys.setrecursionlimit(orig["sys.recursionlimit"])

        if "sys.tracebacklimit" in orig:
            sys.tracebacklimit = orig["sys.tracebacklimit"]
        else:
            if hasattr(sys, "tracebacklimit"):
                del sys.tracebacklimit

        if "showwarning" in orig:
            warnings.showwarning = orig["showwarning"]

        orig.clear()

    def new_model(self, name=None):

        if name in self.models:
            self._rename_samename(name)

        self.currentmodel = ModelImpl(system=self, name=name)
        self.models[self.currentmodel.name] = self.currentmodel
        return self.currentmodel

    def rename_model(self, new_name, old_name, rename_old=False):

        if new_name == old_name:
            return False
        else:
            if rename_old and new_name in self.models:
                self._rename_samename(new_name)

            result = self.models[old_name].rename(new_name)
            if result:
                self.models[new_name] = self.models.pop(old_name)
                return True
            else:
                return False

    def _rename_samename(self, name):
        backupname = self._backupnamer.get_next(self.models, prefix=name)
        if self.rename_model(backupname, name):
            warnings.warn(
                "Existing model '%s' renamed to '%s'" % (name, backupname)
            )
        else:
            raise ValueError("Failed to create %s", name)

    @property
    def models(self):
        return self._models

    @property
    def currentspace(self):
        if self.currentmodel:
            return self.currentmodel.currentspace
        else:
            return None

    def get_curspace(self):
        """Get or create current space"""
        if self.currentspace:
            return self.currentspace
        else:
            if self.currentmodel:
                m = self.currentmodel
            else:
                m = self.new_model()    # self.new_model sets current_model
            m.currentspace = m.updater.new_space(m)
            return m.currentspace

    def close_model(self, model):
        model.refmgr.del_all_spec()
        del self.models[model.name]
        if self.currentmodel is model:
            self.currentmodel = None

    def get_object(self, name, as_proxy=False):
        """Retrieve an object by its absolute name."""

        parts = name.split(".")
        try:
            model = self.models[parts.pop(0)].interface
        except  KeyError:
            raise NameError("'%s' not found" % name)

        if parts:
            return model._get_object(".".join(parts), as_proxy)
        else:
            return model

    def get_object_from_idtuple(self, idtuple, as_proxy=False):
        """Retrieve an object from tuple id."""
        obj = None
        ids = list(idtuple)

        while ids:
            key = ids.pop(0)
            if isinstance(key, str):
                if obj:
                    if (not ids) and as_proxy and (key in obj.refs):
                        obj = obj._get_object(key, as_proxy=as_proxy)
                    else:
                        obj = getattr(obj, key)
                else:
                    obj = self.models[key].interface

            elif isinstance(key, tuple):
                obj = obj.__call__(*key)
            else:
                raise ValueError

        return obj

    def _get_object_from_idtuple_reduce(self, idtuple, as_proxy=False):

        if not idtuple[0]:
            model = self.serializing.model.name
            idtuple = (model,) + idtuple[1:]

        return self.get_object_from_idtuple(idtuple, as_proxy)

    # ----------------------------------------------------------------------
    # Call stack tracing

    def _is_stacktrace_active(self):
        return isinstance(self.callstack, TraceableCallStack)

    def start_stacktrace(self, maxlen):
        if self._is_stacktrace_active():
            return False

        if self.callstack.is_empty():
            self.callstack = self.executor.callstack = TraceableCallStack(
                self.executor,
                maxdepth=self.callstack.maxdepth,
                maxlen=maxlen
            )
            warnings.warn("call stack trace activated")
        else:
            raise RuntimeError("callstack not empy")

        return True

    def stop_stacktrace(self):
        if not self._is_stacktrace_active():
            return False

        if self.callstack.is_empty():
            self.callstack = self.executor.callstack = CallStack(
                self.executor,
                maxdepth=self.callstack.maxdepth
            )
            warnings.warn("call stack trace deactivated")
        else:
            raise RuntimeError("callstack not empy")

        return True

    def get_stacktrace(self, summarize):
        if self._is_stacktrace_active():
            trace = self.callstack.get_tracestack()
            if not summarize:
                return trace
            else:
                return self._get_stacktrace_summary(trace)
        else:
            raise RuntimeError("call stack trace not active")

    def clear_stacktrace(self):
        if self._is_stacktrace_active():
            self.callstack.tracestack.clear()
        else:
            raise RuntimeError("call stack trace not active")

    @contextmanager
    def trace_stack(self, maxlen):
        """Context manager to activate stack trace in with statements"""
        self.start_stacktrace(maxlen)
        try:
            yield None
        finally:
            self.clear_stacktrace()
            self.stop_stacktrace()

    def _check_sanity(self, check_members=True):
        self.iomanager._check_sanity()
        if check_members:
            for m in self.models.values():
                m._check_sanity()

    def _get_stacktrace_summary(self, stacktrace):
        """
        To get result as DataFrame:
            pd.DataFrame.from_dict(result, orient='index')
        """
        maxlen = self.callstack.tracestack.maxlen

        if maxlen and maxlen <= len(stacktrace):
            raise RuntimeError("stacktrace truncated beyond max length")

        TYPE, LEVEL, TIME, REPR, ARGS = range(5)

        result = {}
        stack = []
        t_last = 0

        for trace in stacktrace:

            if stack:
                stack[-1][-1] += trace[TIME] - t_last

            if trace[TYPE] == 'ENTER':
                stack.append(list(trace) + [0])

                if trace[REPR] not in result:
                    result[trace[REPR]] = {
                        'calls': 0,
                        'duration': 0,
                        'first_entry_at': trace[TIME],
                        'last_exit_at': None
                    }

            elif trace[TYPE] == 'EXIT':
                last = stack.pop()

                stat = result[last[REPR]]
                stat['calls'] += 1
                stat['duration'] += last[-1]
                stat['last_exit_at'] = trace[TIME]

            else:
                raise RuntimeError('must not happen')

            t_last = trace[TIME]

        return result

mxsys = System()


# --------------------------------------------------------------------------
# Monkey patch functions for custom error messages


def custom_showtraceback(
    self,
    exc_tuple=None,
    filename=None,
    tb_offset=None,
    exception_only=False,
    running_compiled_code=False,
):
    """Custom showtraceback for monkey-patching IPython's InteractiveShell

    https://stackoverflow.com/questions/1261668/cannot-override-sys-excepthook
    """
    self.default_showtraceback(
        exc_tuple,
        filename,
        tb_offset,
        exception_only=True,
        running_compiled_code=running_compiled_code,
    )


def excepthook(self, except_type, exception, traceback):
    """Not Used: Custom exception hook to replace sys.excepthook

    This is for CPython's default shell. IPython does not use sys.exepthook.

    https://stackoverflow.com/questions/27674602/hide-traceback-unless-a-debug-flag-is-set
    """
    if except_type is DeepReferenceError:
        print(exception.msg)
    else:
        self.default_excepthook(except_type, exception, traceback)
