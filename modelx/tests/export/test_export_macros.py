import sys
import tempfile
import pathlib
import pytest
import modelx as mx


@pytest.fixture
def macro_model():
    """Create a model with macros for testing"""
    m = mx.new_model('MacroTestModel')
    
    @mx.defmacro
    def get_model_name():
        return mx_model._name
    
    @mx.defmacro
    def add_numbers(a, b):
        return a + b
    
    @mx.defmacro
    def call_other_macro():
        return get_model_name() + "_suffix"
    
    yield m
    m.close()


def test_export_macros_creates_file(macro_model, tmp_path):
    """Test that exporting model with macros creates _mx_macros.py"""
    export_path = tmp_path / 'exported_model'
    macro_model.export(export_path)
    
    # Check that _mx_macros.py exists
    macro_file = export_path / '_mx_macros.py'
    assert macro_file.exists()


def test_export_macros_file_content(macro_model, tmp_path):
    """Test that _mx_macros.py contains the macro definitions"""
    export_path = tmp_path / 'exported_model'
    macro_model.export(export_path)
    
    macro_file = export_path / '_mx_macros.py'
    content = macro_file.read_text()
    
    # Check imports
    assert 'from ._mx_model import' in content
    assert 'mx_model' in content
    assert 'MacroTestModel' in content
    
    # Check macro definitions
    assert 'def get_model_name()' in content
    assert 'def add_numbers(a, b)' in content
    assert 'def call_other_macro()' in content


def test_export_macros_in_init(macro_model, tmp_path):
    """Test that __init__.py imports macros"""
    export_path = tmp_path / 'exported_model'
    macro_model.export(export_path)
    
    init_file = export_path / '__init__.py'
    content = init_file.read_text()
    
    # Check that macros are imported
    assert 'from ._mx_macros import' in content
    assert 'get_model_name' in content
    assert 'add_numbers' in content
    assert 'call_other_macro' in content


def test_export_macros_executable(macro_model, tmp_path):
    """Test that exported macros can be executed"""
    export_path = tmp_path / 'exported_model'
    macro_model.export(export_path)
    
    try:
        sys.path.insert(0, str(tmp_path))
        
        # Import the exported module
        from exported_model import get_model_name, add_numbers, call_other_macro
        
        # Test macros
        assert get_model_name() == 'MacroTestModel'
        assert add_numbers(3, 4) == 7
        assert call_other_macro() == 'MacroTestModel_suffix'
        
    finally:
        sys.path.pop(0)
        # Clean up imported modules
        for mod in list(sys.modules.keys()):
            if 'exported_model' in mod:
                del sys.modules[mod]


def test_export_model_without_macros(tmp_path):
    """Test that exporting model without macros doesn't create _mx_macros.py"""
    m = mx.new_model('NoMacros')
    export_path = tmp_path / 'exported_no_macros'
    m.export(export_path)
    
    # Check that _mx_macros.py does NOT exist
    macro_file = export_path / '_mx_macros.py'
    assert not macro_file.exists()
    
    # Check that __init__.py doesn't import macros
    init_file = export_path / '__init__.py'
    content = init_file.read_text()
    assert '_mx_macros' not in content
    
    m.close()


def test_export_macros_with_kwargs(tmp_path):
    """Test that macros with default parameters are exported correctly"""
    m = mx.new_model('KwargsModel')
    
    @mx.defmacro
    def greet(name, greeting="Hello"):
        return f"{greeting}, {name}!"
    
    export_path = tmp_path / 'exported_kwargs'
    m.export(export_path)
    
    try:
        sys.path.insert(0, str(tmp_path))
        from exported_kwargs import greet
        
        assert greet("World") == "Hello, World!"
        assert greet("World", greeting="Hi") == "Hi, World!"
        
    finally:
        sys.path.pop(0)
        for mod in list(sys.modules.keys()):
            if 'exported_kwargs' in mod:
                del sys.modules[mod]
        m.close()


def test_export_macro_access_model(tmp_path):
    """Test that exported macros can access the model via mx_model"""
    m = mx.new_model('AccessModel')
    s = m.new_space('TestSpace')
    
    @mx.defcells
    def foo(x):
        return x * 2
    
    @mx.defmacro
    def use_model():
        return mx_model.TestSpace.foo(5)
    
    export_path = tmp_path / 'exported_access'
    m.export(export_path)
    
    try:
        sys.path.insert(0, str(tmp_path))
        from exported_access import use_model, mx_model as exported_model
        
        assert use_model() == 10
        assert exported_model.TestSpace.foo(5) == 10
        
    finally:
        sys.path.pop(0)
        for mod in list(sys.modules.keys()):
            if 'exported_access' in mod:
                del sys.modules[mod]
        m.close()
