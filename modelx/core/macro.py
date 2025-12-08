# Copyright (c) 2017-2025 Fumito Hamamura <fumito.ham@gmail.com>

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

import types
from collections.abc import Callable

from modelx.core.base import (
    Impl, Interface, get_mixin_slots
)
from modelx.core.formula import Formula
from modelx.core.util import is_valid_name


class MacroMaker:
    """Factory for creating Macro objects"""
    
    def __init__(self, *, model, name):
        self.model = model  # ModelImpl
        self.name = name
    
    def __call__(self, func):
        return self.create_or_change_macro(func)
    
    def create_or_change_macro(self, func):
        self.name = func.__name__ if self.name is None else self.name
        
        if not is_valid_name(self.name):
            raise ValueError(f"Invalid macro name: {self.name}")
        
        if self.name in self.model.macros:
            # Update existing macro
            macro = self.model.macros[self.name]
            macro.set_formula(func)
            return macro.interface
        else:
            # Create new macro
            return self.model.new_macro(name=self.name, formula=func).interface


class Macro(Interface, Callable):
    """A callable Python function that can be saved within a Model.
    
    Macros are Python functions stored in a model that can be used to
    manipulate and interact with the model. All macros in a model share
    a dedicated global namespace that includes the model itself as
    both ``mx_model`` and by the model's name.
    
    Creation:
        Macros can be created using the :func:`~modelx.defmacro` decorator::
        
            >>> import modelx as mx
            >>> m = mx.new_model('MyModel')
            
            >>> @mx.defmacro
            ... def get_model_name():
            ...     return mx_model._name
            
            >>> @mx.defmacro(model=m, name='print_name')
            ... def print_model_name(message):
            ...     print(f"{message} {get_model_name()}")
    
    Execution:
        Macros are executed by calling them as model attributes::
        
            >>> m.get_model_name()
            'MyModel'
            
            >>> m.print_name("This model is")
            This model is MyModel
    
    Listing Macros:
        Access all macros through the model's :attr:`~modelx.core.model.Model.macros`
        property::
        
            >>> m.macros
            {'get_model_name': <Macro MyModel.get_model_name>, 
             'print_name': <Macro MyModel.print_name>}
    
    Export:
        When a model is exported, macros are saved in ``_mx_macros.py`` as
        regular Python functions, allowing them to work with both modelx
        models and exported models.
    
    See Also:
        :func:`~modelx.defmacro`: Decorator to create macros
        :attr:`~modelx.core.model.Model.macros`: Access model's macros
        :meth:`~modelx.core.model.Model.export`: Export model as Python package
    
    .. versionadded:: 0.30.0
    """
    
    __slots__ = ()
    
    def __call__(self, *args, **kwargs):
        """Execute the macro with given arguments"""
        return self._impl.execute(*args, **kwargs)
    
    def __repr__(self):
        return f"<Macro {self._impl.repr_parent()}.{self._impl.repr_self()}>"
    
    @property
    def formula(self):
        """The formula object of the macro"""
        return self._impl.formula
    
    @property
    def parent(self):
        """The parent model of the macro"""
        if self._impl.parent is not None:
            return self._impl.parent.interface
        else:
            return None


class MacroImpl(Impl):
    """Implementation of Macro interface"""
    
    interface_cls = Macro
    
    __slots__ = (
        "formula",
        "_namespace"
    ) + get_mixin_slots(Impl)
    
    def __init__(self, *, system, parent, name, formula):
        """Initialize MacroImpl
        
        Args:
            system: The system object
            parent: The parent ModelImpl object
            name: Name of the macro
            formula: Formula object or callable
        """
        Impl.__init__(
            self,
            system=system,
            parent=parent,
            name=name,
            spmgr=parent.spmgr
        )
        
        if not isinstance(formula, Formula):
            formula = Formula(formula)
        
        self.formula = formula
        self._namespace = None
    
    def execute(self, *args, **kwargs):
        """Execute the macro function
        
        Args:
            *args: Positional arguments for the macro function
            **kwargs: Keyword arguments for the macro function
            
        Returns:
            The return value of the macro function
        """
        # Get the namespace with mx_model and model name
        namespace = self.parent.get_macro_namespace()
        
        # Execute the function with the namespace as globals
        func = self.formula.func
        
        # Create a new function with the correct globals
        new_func = types.FunctionType(
            func.__code__,
            namespace,
            func.__name__,
            func.__defaults__,
            func.__closure__
        )
        
        return new_func(*args, **kwargs)
    
    def set_formula(self, func):
        """Update the macro's formula
        
        Args:
            func: New function to use as the formula
        """
        if not isinstance(func, Formula):
            func = Formula(func)
        self.formula = func
    
    def repr_parent(self):
        """Return parent representation"""
        if self.parent.repr_parent():
            return self.parent.repr_parent() + "." + self.parent.repr_self()
        else:
            return self.parent.repr_self()
    
    def repr_self(self, add_params=True):
        """Return self representation"""
        return self.name
    
    def on_delete(self):
        """Cleanup when macro is deleted"""
        pass
