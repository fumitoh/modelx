from textwrap import dedent
"""
modelx errors & warnings
"""


class DeepReferenceError(RuntimeError):
    """
    Error raised when the chain of formula reference exceeds the limit
    specified by the user.
    """
    message_template = dedent("""
        Formula chain exceeded the {0} limit.
        Call stack traceback:
        {1}""")

    def __init__(self, max_depth, trace_msg):
        msg = self.message_template.format(max_depth, trace_msg)
        RuntimeError.__init__(self, msg)


class NoneReturnedError(ValueError):
    """
    Error raised when a cells return None while its can_return_none
    attribute is set to False.
    """
    message_template = dedent("""
        None returned from {0}.
        Call stack traceback:
        {1}""")

    def __init__(self, last_call, trace_msg):
        msg = self.message_template.format(last_call, trace_msg)
        ValueError.__init__(self, msg)