
"""
modelx errors & warnings
"""


class DeepReferenceError(RuntimeError):
    """
    Exception raised when the chain of formula reference exceeds the limit
    specified by the user.
    """