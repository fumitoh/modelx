
"""
modelx errors & warnings
"""


class DeepReferenceError(RuntimeError):
    """
    Error raised when the chain of formula reference exceeds the limit
    specified by the user.
    """


class NoneReturnedError(ValueError):
    """
    Error raised when a cells return None while its can_return_none
    attribute is set to False.
    """