import itertools
from typing import Dict, List, Tuple, Generator, Optional
from modelx.managers.component import Root, Branch, Leaf, ComponentManager, Child


class DummyModel(Root):

    __slots__ = ("spaces",)
    spaces: Dict[str, "DummySpace"]

    def __init__(self, name, comp_mgr: ComponentManager):
        super().__init__(name, comp_mgr=comp_mgr)
        self.spaces = {}

    @property
    def type_name(self) -> str:
        return "DummyModel"

    def has_branch(self, name: str) -> bool:
        return name in self.spaces
    
    def get_branch(self, name: str) -> Optional["Child"]:
        return self.spaces.get(name)
    
    def get_branches(self) -> Generator["Branch", None, None]:
        return self.spaces.values()

    def create_branch(self, name: str, type_: type, **kwargs) -> "Child":
        space = self.spaces[name] = DummySpace(self, name, comp_mgr=self.comp_mgr, **kwargs)
        return space
    
    def delete_branch(self, name: str) -> None:
        del self.spaces[name]


class DummySpace(Branch):

    __slots__ = ("spaces", "cells", "refs")

    def __init__(self, parent, name, comp_mgr, **kwargs):
        super().__init__(parent, name, comp_mgr=comp_mgr, **kwargs)

        self.spaces = {}
        self.cells = {}
        self.refs = {}

    @property
    def type_name(self) -> str:
        return "DummySpace"

    def has_branch(self, name: str) -> bool:
        return name in self.spaces 
    
    def get_branch(self, name: str) -> Optional[Branch]:
        return self.spaces.get(name)
    
    def get_branches(self) -> Generator["Branch", None, None]:
        return self.spaces.values()
    
    def create_branch(self, name: str, type_: type, **kwargs) -> Branch:
        space = self.spaces[name] = DummySpace(self, name, comp_mgr=self.comp_mgr, **kwargs)
        return space
    
    def delete_branch(self, name: str) -> None:
        del self.spaces[name]

    def get_leaves(self) -> Generator[Leaf, None, None]:
        return itertools.chain(self.cells.values(), self.refs.values())
    
    def create_leaf(self, name: str, type_: type, base: Leaf, **kwargs) -> Leaf:
        if issubclass(type_, DummyCells):
            leaf = self.cells[name] = DummyCells(self, name, comp_mgr=self.comp_mgr, base=base, **kwargs)
        elif issubclass(type_, DummyRef):
            leaf = self.refs[name] = DummyRef(self, name, comp_mgr=self.comp_mgr, base=base, **kwargs)
        else:
            raise ValueError("Invalid leaf type")
        return leaf
    
    def delete_leaf(self, name: str) -> None:
        if name in self.cells:
            del self.cells[name]
        elif name in self.refs:
            del self.refs[name]
        else:
            raise ValueError("Leaf not found")


class DummyCells(Leaf):

    def __init__(self, parent: Branch, name: str, comp_mgr: ComponentManager, base: Leaf, **kwargs) -> None:
        super().__init__(parent, name, comp_mgr, base)

    @property
    def type_name(self) -> str:
        return "DummyCells"

    def update_base(self, base: "DummyCells") -> None:
        self.base = base


class DummyRef(Leaf):

    def __init__(self, parent: Branch, name: str, comp_mgr: ComponentManager, base: Leaf, **kwargs) -> None:
        super().__init__(parent, name, comp_mgr, base)

    @property
    def type_name(self) -> str:
        return "DummyRef"
    
    def update_base(self, base: "DummyRef") -> None:
        self.base = base



