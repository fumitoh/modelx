import pytest
import modelx as mx


@pytest.fixture
def simple_model():
    """Create a simple model for testing"""
    model = mx.new_model(name="TestModel")
    yield model
    model._impl._check_sanity()
    model.close()


def test_defmacro_basic(simple_model):
    """Test basic macro creation without arguments"""
    m = simple_model
    
    @mx.defmacro
    def get_name():
        return mx_model._name
    
    assert 'get_name' in m.macros
    assert get_name is m.macros['get_name']
    assert m.get_name() == 'TestModel'


def test_defmacro_with_args(simple_model):
    """Test macro creation with model and name arguments"""
    m = simple_model
    
    @mx.defmacro(model=m, name='custom_name')
    def original_name():
        return mx_model._name
    
    assert 'custom_name' in m.macros
    assert original_name is m.macros['custom_name']
    assert m.custom_name() == 'TestModel'


def test_defmacro_with_params():
    """Test macro with parameters"""
    m = mx.new_model('ParamModel')
    
    @mx.defmacro
    def add_numbers(a, b):
        return a + b
    
    assert m.add_numbers(2, 3) == 5
    assert m.add_numbers(10, 20) == 30
    
    m.close()


def test_macros_share_namespace():
    """Test that macros in a model share the same namespace"""
    m = mx.new_model('SharedNS')
    
    @mx.defmacro
    def get_value():
        return 42
    
    @mx.defmacro
    def use_other_macro():
        return get_value() * 2
    
    assert m.get_value() == 42
    assert m.use_other_macro() == 84
    
    m.close()


def test_macro_access_model_as_mx_model():
    """Test that macros can access model as mx_model"""
    m = mx.new_model('AccessTest')
    
    @mx.defmacro
    def get_model_via_mx_model():
        return mx_model._name
    
    assert m.get_model_via_mx_model() == 'AccessTest'
    
    m.close()


def test_macro_access_model_by_name():
    """Test that macros can access model by its name"""
    m = mx.new_model('NamedAccess')
    
    @mx.defmacro
    def get_model_via_name():
        return NamedAccess.name
    
    assert m.get_model_via_name() == 'NamedAccess'
    
    m.close()


def test_macros_property(simple_model):
    """Test the macros property returns correct mapping"""
    m = simple_model
    
    @mx.defmacro
    def macro1():
        return 1
    
    @mx.defmacro
    def macro2():
        return 2
    
    macros = m.macros
    assert len(macros) == 2
    assert 'macro1' in macros
    assert 'macro2' in macros
    assert macros['macro1'] is macro1
    assert macros['macro2'] is macro2


def test_macro_update_formula(simple_model):
    """Test updating an existing macro's formula"""
    m = simple_model
    
    @mx.defmacro
    def my_macro():
        return "original"
    
    assert m.my_macro() == "original"
    
    @mx.defmacro
    def my_macro():
        return "updated"
    
    assert m.my_macro() == "updated"
    assert len(m.macros) == 1


def test_macro_delete(simple_model):
    """Test deleting a macro"""
    m = simple_model
    
    @mx.defmacro
    def to_delete():
        return "value"
    
    assert 'to_delete' in m.macros
    
    # Call macro to ensure namespace is created
    m.to_delete()
    assert 'to_delete' in m._impl._macro_namespace
    
    del m.to_delete
    
    assert 'to_delete' not in m.macros
    # Verify macro is also removed from the namespace (bug fix)
    assert 'to_delete' not in m._impl._macro_namespace
    with pytest.raises(AttributeError):
        m.to_delete()


def test_macro_repr():
    """Test macro representation"""
    m = mx.new_model('ReprTest')
    
    @mx.defmacro
    def test_macro():
        return None
    
    repr_str = repr(test_macro)
    assert 'Macro' in repr_str
    assert 'ReprTest' in repr_str
    assert 'test_macro' in repr_str
    
    m.close()


def test_defmacro_multiple_functions():
    """Test creating multiple macros at once"""
    m = mx.new_model('MultiMacro')
    
    def func1():
        return 1
    
    def func2():
        return 2
    
    def func3():
        return 3
    
    f1, f2, f3 = mx.defmacro(func1, func2, func3)
    
    assert m.func1() == 1
    assert m.func2() == 2
    assert m.func3() == 3
    
    m.close()


def test_macro_no_model_creates_model():
    """Test that defmacro creates a model if none exists"""
    # Close all models first
    for model_name in list(mx.get_models().keys()):
        mx.get_models()[model_name].close()
    
    @mx.defmacro
    def test_func():
        return "created"
    
    # A model should have been created
    models = mx.get_models()
    assert len(models) > 0
    
    # Clean up
    for model in models.values():
        model.close()


def test_macro_with_kwargs():
    """Test macro with keyword arguments"""
    m = mx.new_model('KwargsTest')
    
    @mx.defmacro
    def greet(name, greeting="Hello"):
        return f"{greeting}, {name}!"
    
    assert m.greet("World") == "Hello, World!"
    assert m.greet("World", greeting="Hi") == "Hi, World!"
    
    m.close()


def test_macro_dir_includes_macros(simple_model):
    """Test that dir() includes macro names"""
    m = simple_model
    
    @mx.defmacro
    def visible_macro():
        return None
    
    dir_result = dir(m)
    assert 'visible_macro' in dir_result


def test_macro_error_duplicate_name():
    """Test that creating a macro with a duplicate name updates it"""
    m = mx.new_model('DupTest')
    
    @mx.defmacro
    def dup_name():
        return 1
    
    # Should update, not error
    @mx.defmacro
    def dup_name():
        return 2
    
    assert m.dup_name() == 2
    assert len(m.macros) == 1
    
    m.close()


def test_new_macro_basic(simple_model):
    """Test basic macro creation using new_macro"""
    m = simple_model
    
    def get_name():
        return mx_model._name
    
    macro = m.new_macro(formula=get_name)
    
    assert 'get_name' in m.macros
    assert macro is m.macros['get_name']
    assert m.get_name() == 'TestModel'


def test_new_macro_with_name(simple_model):
    """Test macro creation with custom name using new_macro"""
    m = simple_model
    
    def original_func():
        return mx_model._name
    
    macro = m.new_macro(name='custom_name', formula=original_func)
    
    assert 'custom_name' in m.macros
    assert macro is m.macros['custom_name']
    assert m.custom_name() == 'TestModel'


def test_new_macro_with_params(simple_model):
    """Test macro with parameters using new_macro"""
    m = simple_model
    
    macro = m.new_macro('add_numbers', lambda a, b: a + b)
    
    assert m.add_numbers(2, 3) == 5
    assert m.add_numbers(10, 20) == 30


def test_new_macro_no_formula_error(simple_model):
    """Test that new_macro raises error when formula is None"""
    m = simple_model
    
    with pytest.raises(ValueError, match="formula must be provided"):
        m.new_macro(name='test')


def test_new_macro_no_name_error(simple_model):
    """Test that new_macro raises error when name is None and formula has no __name__"""
    m = simple_model
    
    # Create a callable object without __name__
    class CallableWithoutName:
        def __call__(self):
            return 42
    
    with pytest.raises(ValueError, match="name must be provided"):
        m.new_macro(formula=CallableWithoutName())


def test_new_macro_lambda_with_name(simple_model):
    """Test that new_macro works with lambda and explicit name"""
    m = simple_model
    
    macro = m.new_macro('my_lambda', lambda x: x * 3)
    
    assert 'my_lambda' in m.macros
    assert m.my_lambda(5) == 15

