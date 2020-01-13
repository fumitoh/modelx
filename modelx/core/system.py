# Copyright (c) 2017-2020 Fumito Hamamura <fumito.ham@gmail.com>

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
import time
import warnings
import pickle
import threading
from collections import deque
from modelx.core.node import get_node_repr
from modelx.core.model import ModelImpl
from modelx.core.util import AutoNamer, is_valid_name
from modelx.core.errors import DeepReferenceError
from modelx.core.node import OBJ, KEY
from modelx.core.errors import RewindStackError


class Executor:

    def __init__(self, system, maxdepth=None):

        # Use thread to increase stack size and deepen callstack
        # Ref: https://bugs.python.org/issue32570

        self.system = system
        self.callstack = CallStack(maxdepth)
        self.thread = Executor.ExecThread(self)
        self.thread.daemon = True
        last_size = threading.stack_size(0xFFFFFFF)
        self.thread.start()
        threading.stack_size(last_size)
        self.initnode = None

    def eval_cell(self, node):

        if self.thread.signal_start.is_set():
            return self._eval_formula(node)
        else:
            return self._start_exec(node)

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
                    self.executor.exception = sys.exc_info()

                self.signal_start.clear()
                self.signal_stop.set()

    def _start_exec(self, node):
        self.initnode = node
        self.exception = None
        try:
            self.thread.signal_start.set()
            self.thread.signal_stop.wait()
            self.thread.signal_stop.clear()
            assert not self.callstack

            if self.exception:
                raise self.exception[1].with_traceback(
                    self.exception[2]
                )
            else:
                return self.thread.buffer

        finally:
            self.initnode = None

    def _eval_formula(self, node):

        self.callstack.append(node)
        cells, key = node[OBJ], node[KEY]

        try:
            return cells.on_eval_formula(key)

        except ZeroDivisionError:
            tracemsg = self.callstack.tracemessage()
            raise RewindStackError(node, tracemsg)

        finally:
            self.callstack.pop()


class CallStack(deque):

    if sys.platform == "win32" and sys.version_info[:2] == (3, 8):
        default_maxdepth = 57000
    else:
        default_maxdepth = 65000

    def __init__(self, maxdepth=None):

        if maxdepth:
            self.maxdepth = maxdepth
        else:
            self.maxdepth = self.default_maxdepth

        deque.__init__(self)

    def last(self):
        return self[-1]

    def is_empty(self):
        return len(self) == 0

    def append(self, item):

        if len(self) > self.maxdepth:
            raise DeepReferenceError(self.maxdepth, self.tracemessage())
        deque.append(self, item)

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

    def __init__(self, maxdepth=None, maxlen=None):

        CallStack.__init__(self, maxdepth)
        self.tracestack = deque(maxlen=maxlen)

    def append(self, item):

        CallStack.append(self, item)
        self.tracestack.append(
            ("ENTER", len(self) - 1, _trace_time(),
             item[OBJ].get_repr(fullname=True, add_params=True), item[KEY]))

    def pop(self):
        item = super().pop()
        self.tracestack.append(
            ("EXIT", len(self), _trace_time(),
             item[OBJ].get_repr(fullname=True, add_params=True), item[KEY])
        )


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

    def __init__(self, maxdepth=None, setup_shell=False):

        self.configure_python()
        self.executor = Executor(self, maxdepth)
        self.callstack = self.executor.callstack
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
        sys.setrecursionlimit(10**6)
        warnings.showwarning = custom_showwarning

    def restore_python(self):
        """Restore Python settings to the original states"""
        orig = self.orig_settings
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
            m.currentspace = m.new_space()
            return m.currentspace

    def open_model(self, path, name):
        with open(path, "rb") as file:
            model = pickle.load(file)

        model._impl.restore_state(self)

        if name is not None:
            if not is_valid_name(name):
                raise ValueError("Invalid name '%s'." % name)

        newname = name or model.name

        if newname in self.models:
            self._rename_samename(newname)

        if name is not None:
            if not model._impl.rename(name):
                raise RuntimeError("must not happen")

        self.models[newname] = model._impl
        self.currentmodel = model._impl

        return model

    def close_model(self, model):
        del self.models[model.name]
        if self.currentmodel is model:
            self.currentmodel = None

    def get_object(self, name):
        """Retrieve an object by its absolute name."""

        parts = name.split(".")
        obj = self.models[parts.pop(0)].interface
        while parts:
            attr = parts.pop(0)
            obj = getattr(obj, attr)

        return obj

    def get_object_from_tupleid(self, tupleid):
        """Retrieve an object from tuple id."""
        obj = None
        for key in tupleid:
            if isinstance(key, str):
                if obj:
                    obj = getattr(obj, key)
                else:
                    obj = self.models[key].interface
            elif isinstance(key, tuple):
                obj = obj.__call__(*key)
            else:
                raise ValueError

        return obj

    # ----------------------------------------------------------------------
    # Call stack tracing

    def _is_stacktrace_active(self):
        return isinstance(self.callstack, TraceableCallStack)

    def start_stacktrace(self, maxlen):
        if self._is_stacktrace_active():
            return False

        if self.callstack.is_empty():
            self.callstack = self.executor.callstack = TraceableCallStack(
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
                maxdepth=self.callstack.maxdepth
            )
            warnings.warn("call stack trace deactivated")
        else:
            raise RuntimeError("callstack not empy")

        return True

    def get_stacktrace(self):
        if self._is_stacktrace_active():
            return list(self.callstack.tracestack)
        else:
            raise RuntimeError("call stack trace not active")

    def clear_stacktrace(self):
        if self._is_stacktrace_active():
            self.callstack.tracestack.clear()
        else:
            raise RuntimeError("call stack trace not active")


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
