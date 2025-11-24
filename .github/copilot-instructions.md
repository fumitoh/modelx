# GitHub Copilot Instructions for modelx

## Overview

**modelx** is a Python library for numerical computing that enables spreadsheet-like behavior through cached functions. It's designed for implementing complex mathematical models with recursive formulas, commonly used in actuarial science, quantitative finance, and risk management.

## Core Architecture

### Impl/Interface Pattern

modelx uses a strict separation between implementation and interface classes:

- **Interface classes** (`Model`, `UserSpace`, `Cells`, etc.) - User-facing API with clean public methods
- **Impl classes** (`ModelImpl`, `UserSpaceImpl`, `CellsImpl`, etc.) - Internal implementation containing actual logic

**Key principles:**
- All user-visible objects are Interface instances
- Interface classes delegate to their `_impl` attribute (the Impl instance)
- Impl classes contain `interface` attribute pointing back to the Interface
- Impl classes expose internal attributes and methods hidden from users
- Use `get_interface_list()` and `get_impl_list()` for conversions between layers

**Example:**
```python
# Interface layer (user-facing)
space = model.new_space('MySpace')  # Returns UserSpace interface

# Implementation layer (internal)
space_impl = space._impl  # Access UserSpaceImpl
assert space_impl.interface is space  # Bidirectional reference
```

### Object Hierarchy: Model → Space → Cells

```
Model (top-level container)
├── UserSpace (static/editable spaces)
│   ├── Cells (formulas with caching)
│   ├── References (data, modules, objects)
│   └── Child UserSpaces (nested structure)
│       └── (recursively contains Cells, Refs, Spaces)
└── ItemSpace (dynamic parameterized instances)
    └── DynamicSpace (read-only derived spaces)
```

**Model** - Top-level container, manages global references and persistence
**UserSpace** - Editable container for cells, child spaces, and references
**ItemSpace** - Root dynamic space created from parameterized UserSpace
**DynamicSpace** - Non-root dynamic spaces within ItemSpace hierarchy
**Cells** - Callable formulas with automatic caching and dependency tracking

### Space Types

1. **UserSpace** - Static, editable spaces created by users
   - Can be modified (add/remove cells, spaces, refs)
   - Support inheritance from base spaces
   - Can be parameterized with a formula

2. **ItemSpace** - Root dynamic space instances from parameterized UserSpace
   - Created by calling `space[args]` or `space(args)`
   - Read-only (cannot add/remove cells)
   - Has `argvalues` attribute with parameter values
   - Root of dynamic hierarchy for specific parameters

3. **DynamicSpace** - Non-root dynamic spaces
   - Child spaces within ItemSpace instances
   - Mirror structure of base UserSpace
   - Read-only and derived from base

**Key distinction:**
```python
space.parameters = ('x', 'y')
item = space[1, 2]  # ItemSpace (root, has parameters)
child = item.ChildSpace  # DynamicSpace (nested, no parameters)
```

## Naming Conventions

### Classes
- Interface classes: `Model`, `UserSpace`, `Cells` (no suffix)
- Impl classes: `ModelImpl`, `UserSpaceImpl`, `CellsImpl` (Impl suffix)
- Mixin classes: End in base class name (e.g., `ItemSpaceParent`)

### Attributes
- Public: `cells`, `spaces`, `refs`, `parameters`
- Private (internal use): `_impl`, `_namespace`, `_dynamic_subs`
- System refs: `_self`, `_space`, `_model` (accessible in formulas)

### Methods
- Public API: `new_cells()`, `new_space()`, `clear_all()`
- Internal hooks: `on_delete()`, `on_inherit()`, `on_notify()`
- Representation: `repr_self()`, `repr_parent()`

## Core Concepts

### Cells - Cached Formulas

Cells are callable functions with automatic result caching:

```python
@mx.defcells
def present_value(t):
    return cashflow(t) / (1 + discount_rate) ** t
```

**Key features:**
- Results cached by arguments
- Can reference other cells, refs, and parameters
- Support input values (override formula)
- Clear values with `cells.clear()` or `cells.clear_at(args)`

### References

References provide access to external data within formulas:

```python
# Set references
space.absref(data=df, rate=0.05)  # Absolute reference
space.relref(child_cells=child_space.foo)  # Relative reference

# Use in formulas
@mx.defcells
def calc():
    return data['column'].sum() * rate
```

**Reference modes:**
- `absolute` - Fixed reference, doesn't adjust for inheritance
- `relative` - Adjusts for derived spaces
- `auto` - Automatically choose based on scope

### Space Inheritance

Spaces can inherit from base spaces (similar to Python classes):

```python
base = model.new_space('Base')
base.new_cells('foo', lambda x: x * 2)

derived = model.new_space('Derived')
derived.add_bases(base)
derived.foo(5)  # Returns 10 (inherited from base)
```

### Parameterized Spaces

Spaces with parameters create ItemSpace instances:

```python
space.parameters = ('product', 'scenario')
item = space['ProductA', 'Base']  # Creates ItemSpace
item.argvalues  # ('ProductA', 'Base')
```

## Formula System

### Formula Objects
- `Formula` class wraps Python functions
- Stores signature, parameters, and source code
- Used by both Cells and parameterized Spaces
- `ModuleSource` for formulas from modules

### Namespace Management
- `NamespaceServer` - Mixin for namespace observers
- `BaseNamespace` - Base class for namespace wrappers
- `CustomChainMap` - Multi-level namespace resolution
- References, cells, and spaces accessible by name in formulas

## Key Implementation Patterns

### Observer Pattern (on_notify)

Objects notify observers when their state changes:

```python
def on_notify(self, subject):
    # React to changes in observed object
    if subject is self.namespace:
        self.refresh_namespace()
```

### Derivable Pattern

For inheritance support (spaces, cells, references):

```python
class Derivable:
    def __init__(self, is_derived=False):
        self.is_derived_id = is_derived
        
    def on_inherit(self, updater, bases):
        # Handle inheritance logic
```

### Node System (Dependency Tracking)

Tracks cell evaluation dependencies:

```python
# Node represents a computation: (object, key)
node = get_node(cells, (arg1, arg2), {})
# Used for tracing, clearing dependent values, etc.
```

## Serialization & Persistence

### File Formats
- **Textual** (`.mx` directory) - Human-readable, version-control friendly
  - `__init__.py` files for Model/Space definitions
  - Module files for Cells formulas
  - Pickle files for data (DataFrames, etc.)

- **Binary** (`.mx` zip file) - Compact single-file format
  - Uses `zipfile` module
  - Contains same structure as directory format

### Key Classes
- `Serializer` - Converts models to file format
- `Deserializer` - Loads models from files
- `IOManager` - Manages data specs and external resources
- `IOSpec` - Handles external data (Excel, CSV, pickle)

### Methods
- `model.write(path)` - Save to directory
- `model.zip(path)` - Save to zip file
- `mx.read_model(path)` - Load from directory or zip
- `mx.restore_model(path)` - Load with partial reading

## Testing Approach

### Test Structure
- Tests located in `modelx/tests/`
- Organized by module: `core/`, `io/`, `serialize/`
- Use pytest framework

### Common Patterns

```python
@pytest.fixture
def sample_model():
    m = mx.new_model()
    s = m.new_space()
    c = s.new_cells()
    yield m
    m._impl._check_sanity()  # Verify integrity
    m.close()

def test_feature(sample_model):
    # Arrange
    space = sample_model.new_space()
    
    # Act
    result = space.new_cells('foo', lambda x: x * 2)
    
    # Assert
    assert result(5) == 10
```

### Testing Best Practices
- Always call `model._impl._check_sanity()` after tests
- Use fixtures for common model structures
- Clean up with `model.close()`
- Test both Interface and Impl behavior
- Test inheritance, caching, and clearing

## Common Development Workflows

### Adding a New Cell Method

1. Add to Interface class (`Cells` in `cells.py`)
2. Implement in Impl class (`CellsImpl` or specific subclass)
3. Handle inheritance if needed (`on_inherit`)
4. Update docstring with examples
5. Add tests in `tests/core/cells/`

### Adding a New Space Feature

1. Determine if it applies to UserSpace only or all spaces
2. Add to appropriate class (`BaseSpace` or `UserSpace`)
3. Implement in `BaseSpaceImpl` or `UserSpaceImpl`
4. Handle dynamic spaces (`DynamicSpaceImpl`, `ItemSpaceImpl`)
5. Update inheritance logic if needed
6. Add comprehensive tests

### Modifying Formula Behavior

1. Update `Formula` class in `formula.py`
2. Consider impact on `ParamFunc` for space parameters
3. Update `AlteredFunction` if namespace changes
4. Test with both cell formulas and space formulas
5. Check serialization compatibility

## Important Implementation Details

### Memory Management
- Use `weakref.WeakValueDictionary` for dynamic caches
- Clear cell values to free memory: `space.clear_all()`
- Models hold strong references to prevent premature GC

### Execution Context
- `callstack` tracks formula execution depth
- `executor` manages evaluation and dependency tracking
- `tracegraph` stores dependency information
- Check `system.callstack.counter` to detect formula context

### Space Manager (spmgr)
- Manages inheritance relationships
- Handles cell/space creation and updates
- Coordinates base space changes
- Accessed via `self.spmgr` in Impl classes

### Reference Manager (refmgr)
- Manages reference creation and updates
- Handles reference mode resolution (absolute/relative)
- Tracks reference dependencies
- Located in `model.refmgr`

## Error Handling

### Common Errors
- `DeletedObjectError` - Object accessed after deletion
- `DeepReferenceError` - Reference resolution depth exceeded
- `FormulaError` - Error in cell formula execution
- `NoneReturnedError` - Formula returned None unexpectedly

### Best Practices
- Use `_is_valid()` to check if interface is still valid
- Clear tracegraph on errors affecting dependencies
- Provide detailed error messages with object names
- Include formula traceback in error context

## Documentation Style

### Docstrings
Use Google/NumPy style with Sphinx directives:

```python
def method(self, arg1, arg2=None):
    """Brief one-line description.
    
    Longer explanation of what the method does, including
    key behaviors and use cases.
    
    Args:
        arg1 (type): Description of arg1
        arg2 (type, optional): Description of arg2. Defaults to None.
        
    Returns:
        type: Description of return value
        
    Example:
        >>> space.method('value')
        <Result>
        
    See Also:
        :meth:`related_method`: Related functionality
        :class:`~modelx.core.cells.Cells`: Related class
        
    .. versionadded:: 0.x.0
    """
```

### Cross-references
- `:class:`~modelx.core.space.UserSpace`` - Class reference
- `:meth:`~UserSpace.new_cells`` - Method reference  
- `:func:`~modelx.new_model`` - Function reference
- `:attr:`parameters`` - Attribute reference

## Performance Considerations

### Caching Strategy
- Cells cache by default (`is_cached=True`)
- Use `@mx.uncached` decorator for non-cacheable formulas
- Clear caches strategically with `clear_cells()`
- ItemSpaces are cached in `dynamic_cache`

### Optimization Tips
- Avoid deep reference chains (affects resolution time)
- Use pandas operations over Python loops in formulas
- Batch operations when possible
- Consider `allow_none` setting for performance in specific contexts

## Version Compatibility

### Serialization Versions
- Version 3-6 supported (check `serializing.version`)
- Older versions may need migration
- Test backward compatibility for format changes

### API Deprecations
- Mark deprecated methods with warnings
- Provide migration path in warning message
- Keep deprecated methods for 2-3 releases
- Document in release notes

## Additional Resources

- Documentation: https://docs.modelx.io
- Repository: https://github.com/fumitoh/modelx
- Issues: https://github.com/fumitoh/modelx/issues
- Spyder plugin: https://github.com/fumitoh/spyder-modelx

---

When working with modelx code, always consider:
1. Are you working with Interface or Impl layer?
2. Does this affect UserSpace, DynamicSpace, or both?
3. How does inheritance impact this change?
4. What happens to cached values?
5. Is serialization affected?
6. Do tests cover this scenario?
