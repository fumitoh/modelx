import itertools
import networkx as nx
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import cast, Dict, List, Tuple, Set, Union, Generator, Callable, Optional
from modelx.managers.inheritance import InheritanceGraph


# -----------------------------------------------------------------------------
# Component classes
# -----------------------------------------------------------------------------


class BaseComponent(ABC):

    __slots__ = (
        "name",
        "comp_mgr"
    )

    name: str
    comp_mgr: "BaseComponentManager"

    def __init__(self, name: str, comp_mgr: "BaseComponentManager") -> None:
        self.name = name
        self.comp_mgr = comp_mgr

    @property
    @abstractmethod
    def comp_path(self) -> str:
        """Return the path of the component"""
        ...
    
    @property
    @abstractmethod
    def type_name(self) -> str:
        """Return the type of the component"""
        ...

    def __eq__(self, other: "BaseComponent") -> bool:
        return self.comp_path == other.comp_path

    def __hash__(self) -> int:
        return hash(self.comp_path)
    
    def __repr__(self) -> str:
        return f"<{self.type_name} {self.comp_path}>"


class Parent(BaseComponent):

    __slots__ = ()

    def has_child(self, name: str) -> bool:
        return self.get_child(name) is not None

    @abstractmethod
    def get_child(self, name: str) -> Optional["Child"]:
        ...

    @abstractmethod
    def has_branch(self, name: str) -> bool:
        ...
    
    @abstractmethod
    def get_branch(self, name: str) -> Optional["Branch"]:
        ...
    
    @abstractmethod
    def get_branches(self) -> Generator["Branch", None, None]:
        ...

    def traverse_branch_bfs(self) -> Generator["Branch", None, None]:
        queue = [self]
        while queue:
            node = queue.pop(0)
            yield node
            queue.extend(node.get_branches())

    @abstractmethod
    def create_branch(self, name: str, type_: type, **kwargs) -> "Branch":
        ...

    @abstractmethod
    def delete_branch(self, name: str) -> None:
        ...


class Child(BaseComponent):

    __slots__ = ("parent",)

    parent: Parent

    def __init__(self, parent: Parent, name: str, comp_mgr: "BaseComponentManager") -> None:
        super().__init__(name, comp_mgr)
        self.parent = parent

    @property
    def comp_path(self) -> str:
        return self.parent.comp_path + "." + self.name if self.parent.comp_path else self.name


class Branch(Child, Parent):

    __slots__ = ()

    def get_child(self, name: str) -> Optional[Child]:
        for child in itertools.chain(self.get_branches(), self.get_leaves()):
            if child.name == name:
                return child

        return None

    @abstractmethod
    def get_leaves(self) -> Generator["Leaf", None, None]:
        ...

    @abstractmethod
    def create_leaf(self, name: str, type_: type, base: Optional["Leaf"], **kwargs) -> "Leaf":
        ...

    @abstractmethod
    def delete_leaf(self, name: str) -> None:
        ...


class Root(Parent):

    __slots__ = ()

    @property
    def comp_path(self) -> str:
        return ""
    
    def get_child(self, name: str) -> "Branch":
        return self.get_branch(name)


class Leaf(Child):

    __slots__ = ("base",)

    base: "Leaf"

    def __init__(self, parent: Branch, name: str, comp_mgr: "ComponentManager", base: "Leaf") -> None:
        super().__init__(parent, name, comp_mgr)
        self.base = base

    def is_derived(self) -> bool:
        return self.base is not None

    @abstractmethod
    def update_base(self, base: "Leaf") -> None:
        ...


# -----------------------------------------------------------------------------
# Mock classes
# -----------------------------------------------------------------------------


class MockBaseComponent:

    __slots__ = ()  # "_type_name" is defined in subclasses

    @property
    def type_name(self) -> str:
        return self._type_name


class MockParent(MockBaseComponent, Parent):

    __slots__ = ()  # "branches" is defined in subclasses

    # -----------------------------------------------------------------------
    # Parent Method Implementations
    # -----------------------------------------------------------------------

    def has_branch(self, name: str) -> bool:
        return name in self.branches
    
    def get_branch(self, name: str) -> Optional["Branch"]:
        return self.branches.get(name)

    def get_branches(self) -> Generator["Branch", None, None]:
        return self.branches.values()

    def create_branch(self, name: str, type_: type, **kwargs) -> Branch:
        branch = self.branches[name] = MockBranch.from_branch(
                self,
                type_(self, name, self.comp_mgr, **kwargs)
            )
        return branch

    def delete_branch(self, name: str) -> None:
        del self.branches[name]


class MockChild(MockBaseComponent, Child):
    __slots__ = ()
    pass


class MockRoot(MockParent, Root):
    __slots__ = ("_type_name", "branches")

    branches: Dict[str, "MockBranch"]

    def __init__(self, name: str, comp_mgr: "MockComponentManager") -> None:
        super().__init__(name, comp_mgr)
        self._type_name = ""
        self.branches = {}

    @classmethod
    def from_root(cls, original: Root, comp_mgr: "MockComponentManager") -> "MockRoot":
        self = cls(original.name, comp_mgr)
        self.branches = {branch.name: MockBranch.from_branch(self, branch) for branch in original.get_branches()}
        self._type_name = original.type_name
        return self


class MockBranch(MockParent, Branch):

    __slots__ = ("_type_name", "branches", "leaves")

    branches: Dict[str, "MockBranch"]
    leaves: Dict[str, "MockLeaf"]

    def __init__(self, parent: MockParent, name: str, comp_mgr: "MockComponentManager") -> None:
        super().__init__(parent, name, comp_mgr)
        self._type_name = ""
        self.branches = {}
        self.leaves = {}

    @classmethod
    def from_branch(cls, parent: MockParent, original: Branch) -> "MockBranch":
        self = cls(parent, original.name, parent.comp_mgr)
        self._type_name = original.type_name
        self.branches = {branch.name: MockBranch.from_branch(self, branch) for branch in original.get_branches()}
        self.leaves = {leaf.name: MockLeaf.from_leaf(self, leaf) for leaf in original.get_leaves()}
        return self

    # -----------------------------------------------------------------------
    # Branch Method Implementations
    # -----------------------------------------------------------------------
    
    def get_leaves(self) -> Generator["Leaf", None, None]:
        return self.leaves.values()

    def create_leaf(self, name: str, type_: type, base: "MockLeaf", **kwargs) -> "MockLeaf":
        leaf = self.leaves[name] = MockLeaf.from_leaf(
            self,
            type_(self, name, self.comp_mgr, base)
        )
        return leaf

    def delete_leaf(self, name: str) -> None:
        del self.leaves[name]


class MockLeaf(MockChild, Leaf):

    __slots__ = ("_type_name",)

    def __init__(self, parent: MockBranch, name: str, comp_mgr: "MockComponentManager", base: Optional["MockLeaf"]) -> None:
        super().__init__(parent, name, comp_mgr, base)
        self._type_name = "" if base is None else base.type_name

    @classmethod
    def from_leaf(cls, parent: MockBranch, original: Leaf) -> "MockLeaf":
        self = cls(parent, original.name, parent.comp_mgr,
                   MockLeaf.from_leaf(parent, original.base) if original.is_derived() else None)
        self._type_name = original.type_name
        return self

    def update_base(self, base: "MockLeaf") -> None:
        self.base = base


class MROUpdater:
    
    __slots__ = ("mro",)

    mro: List[Branch]
    
    def __init__(self, mro: List[Branch]) -> None:
        self.mro = mro

    @staticmethod
    def list_names_by_type(branch) -> Dict[str, List[str]]:
        result = {}
        for comp in itertools.chain(branch.get_branches(), branch.get_leaves()):
            result.setdefault(comp.type_name, []).append(comp.name)
        return result

    def get_duplicates(self) -> Dict[Tuple[str], Set[str]]:
        names_by_type = {}     # type_name: [name, ...]
        for branch in self.mro:
            names_by_type_in_a_branch = self.list_names_by_type(branch)
            for type_, names in names_by_type_in_a_branch.items():
                list_ = names_by_type.setdefault(type_, [])
                for name in names:
                    if name not in list_:
                        list_.append(name)
        
        result = {}
        for r in range(2, len(names_by_type) + 1):
            for combination in itertools.combinations(names_by_type, r):
                intersection = set.intersection(*[set(names_by_type[t]) for t in combination])
                if intersection:    # not empty
                    result[combination] = intersection

        return result

    def update_mro(self, excluded: Set[Branch]) -> None:
        """Update the derived leaves of the branches in the MRO.

        Walk through the MRO from the last branch to the first branch, 
        and update the derived leaves of the branches in the MRO.

        Args:
            excluded: Branches to exclude from the update.
        
        """
        name_to_base: Dict[str, Leaf] = {}
        for branch in reversed(self.mro):

            leaves = set(l.name for l in branch.get_leaves())
            if branch not in excluded:
                # Add the derived leaves that are not in the branch
                for name in name_to_base:
                    if name not in leaves:
                        base = name_to_base[name]
                        branch.create_leaf(base.name, type(base), base)

            for leaf in list(branch.get_leaves()):
                if leaf.is_derived():
                    if branch not in excluded:
                        base = name_to_base.get(leaf.name, None)
                        if base is None:
                            branch.delete_leaf(leaf.name)
                        elif base.comp_path != leaf.base.comp_path:
                            leaf.update_base(base)

                else:   # leaf is defined
                    name_to_base[leaf.name] = leaf


@dataclass
class ComponentOperation:
    """Atomic operation to create, delete, rename, add_base, or update a component
    
    Args:
        operation: Operation type (create, delete, rename, add_base, update)
    
    """
    operation: str
    parent: Parent
    name: str
    type_: type
    kwargs: Dict


@dataclass
class ComponentInstruction:
    """Instruction to create, delete, rename or update a component"""

    instruction: str
    parent: Parent
    name: str
    type_: type
    kwargs: Dict
    
# -----------------------------------------------------------------------------
# Component Manager
# -----------------------------------------------------------------------------


class BaseComponentManager(ABC):
    """Manage components

    Atomic branch operations:

        * create
        * delete
        * rename
        * update
        * add base
        * remove base

    Atomic leaf operations:

        * create
        * delete
        * rename
        * update
    """
    __slots__ = ("_root", "_graph")

    _root: Root
    _graph: InheritanceGraph

    def __init__(self) -> None:
        self._root = None
        self._graph = InheritanceGraph()

    def set_root(self, root: Root) -> None:
        self._root = root

    @property
    def root(self):
        return self._root

    def _get_subs(self, branch: Branch, include_branch=False) -> Generator[Branch, None, None]:
        for sub_path in self._graph.ordered_subs(branch.comp_path, incdlue_node=include_branch):
            yield cast(Branch, self.get_component(sub_path))

    def get_component(self, path: str) -> BaseComponent:
        comp: BaseComponent = self._root
        names: List[str] = path.split(".")

        while names:
            name = names.pop(0)
            comp = cast(Parent, comp).get_child(name)
        
        return comp

    def get_mro(self, comp_path: str) -> Generator[Branch, None, None]:
        for node in self._graph.get_mro(comp_path):
            yield cast(Branch, self.get_component(node))

    def _create_branch(self, parent: Parent, name: str, type_: type, **kwargs) -> Branch:
        """Create a new branch.

        parent can be a Root or a Branch. create a new branch under the parent.
        """
        branch = parent.create_branch(name, type_, **kwargs)
        self._graph.add_node(branch.comp_path)
        return branch

    def _delete_branch(self, parent: MockParent, name: str) -> None:
        """Delete a branch. 
        
        The branch must neither have any children nor sub-branches.
        """
        branch = parent.get_branch(name)
        self._graph.remove_node(branch.comp_path)
        parent.delete_branch(name)

    @abstractmethod
    def _add_base(self, branch: Branch, base: Branch) -> None:
        ...

    # -----------------------------------------------------------------------
    # Leaf Operations
    # -----------------------------------------------------------------------

    @abstractmethod
    def _create_leaf(self, parent: Branch, name: str, type_: type, **kwargs) -> Leaf:
        """Create a new leaf."""
        ...

    @abstractmethod
    def _delete_leaf(self, parent: Branch, name: str) -> None:
        """Delete a leaf."""
        ...    

    @abstractmethod
    def _rename_leaf(self, leaf: Leaf, name: str) -> None:
        """Rename a leaf."""
        ...
    
    @abstractmethod
    def _update_leaf(self, leaf: Leaf, **kwargs) -> None:
        """Update a leaf."""
        ...


class ComponentManager(BaseComponentManager):

    def get_mock_manager(self) -> "MockComponentManager":
        return MockComponentManager(self)

    # -----------------------------------------------------------------------
    # Branch Operations
    # -----------------------------------------------------------------------

    def _add_base(self, branch: Branch, base: Branch) -> None:
        """Add a base to a branch."""

        self._graph.add_edge(base.comp_path, branch.comp_path)        
        excluded = set()
        for sub in self._graph.ordered_subs(branch.comp_path, incdlue_node=True, leaves_only=True):
            mro = MROUpdater(list(self.get_mro(sub)))
            mro.update_mro(excluded=excluded)
            excluded.update(mro.mro)        

    def _remove_base(self, branch: Branch, base: Branch) -> None:
        """Remove a base from a branch."""

        excluded = set()
        self._graph.remove_edge(base.comp_path, branch.comp_path)
        for sub in self._graph.ordered_subs(branch.comp_path, incdlue_node=True, leaves_only=True):
            mro = MROUpdater(list(self.get_mro(sub)))
            mro.update_mro(excluded=excluded)
            excluded.update(mro.mro)

    # -----------------------------------------------------------------------
    # Leaf Operations
    # -----------------------------------------------------------------------

    def _create_leaf(self, parent: Branch, name: str, type_: type, **kwargs) -> Leaf:
        """Create a new leaf."""

        leaf = parent.create_leaf(name, type_, None, **kwargs)
        excluded = set(self.get_mro(parent.comp_path))
        for sub in self._graph.ordered_subs(parent.comp_path, leaves_only=True):
            mro = MROUpdater(list(self.get_mro(sub)))
            mro.update_mro(excluded=excluded)
            excluded.update(mro.mro)

        return leaf

    def _delete_leaf(self, parent: Branch, name: str) -> None:
        """Delete a leaf."""

        parent.delete_leaf(name)
        excluded = set()
        for sub in self._graph.ordered_subs(parent.comp_path, leaves_only=True):
            mro = MROUpdater(list(self.get_mro(sub)))
            mro.update_mro(excluded=excluded)
            excluded.update(mro.mro)

    def _rename_leaf(self, leaf: MockLeaf, name: str) -> None:
        """Rename a leaf."""
        pass

    def _update_leaf(self, leaf: MockLeaf, **kwargs) -> None:
        """Update a leaf."""
        pass


class ComponentError(Exception):
    """Error associated with component operations."""


class MockComponentManager(BaseComponentManager):
    """Manage components

    Atomic branch operations:

        * create
        * delete
        * add base
        * remove base
        * rename
        * update

    Atomic leaf operations:

        * create
        * delete
        * rename
        * update
    """

    __slots__ = ("_orig_graph",)

    def __init__(self, manager: ComponentManager) -> None: 
        self._orig_graph = manager._graph
        self._graph = manager._graph.copy()
        self._root = MockRoot.from_root(manager._root, self)

    # -----------------------------------------------------------------------
    # Branch Operations 
    # -----------------------------------------------------------------------

    def _create_branch(self, parent: MockParent, name: str, type_: type, **kwargs) -> MockBranch:

        if parent.has_branch(name):
            raise ComponentError(f"Branch {name} already exists under {parent.comp_path}")
        
        branch = super()._create_branch(parent, name, type_, **kwargs)
        if isinstance(parent, Branch):
            for sub in self._graph.ordered_subs(parent.comp_path, incdlue_node=True, leaves_only=True):
                mro = MROUpdater(list(self.get_mro(sub)))
                duplicates = mro.get_duplicates()
                if duplicates:
                    raise ComponentError(f"Duplicate names found: {duplicates}")

        return branch
    
    def _delete_branch(self, parent: MockParent, name: str) -> None:
        """Delete a branch. 
        
        The branch must neither have any children nor sub-branches.
        """

        if not parent.has_branch(name):
            raise ComponentError(f"Branch {name} does not exist under {parent.comp_path}")
        
        super()._delete_branch(parent, name)

    def _add_base(self, branch: MockBranch, base: MockBranch) -> None:
        """Add a base to a branch."""

        self._graph.add_edge(base.comp_path, branch.comp_path)
        
        if not nx.is_directed_acyclic_graph(self._graph):
            raise ComponentError("Cyclic inheritance detected")
        try:
            self._graph.get_mro(branch.comp_path)
        except:
            raise ComponentError("Inconsistent hierarchy, no C3 MRO is possible")
        
        excluded = set()
        for sub in self._graph.ordered_subs(branch.comp_path, incdlue_node=True, leaves_only=True):
            mro = MROUpdater(list(self.get_mro(sub)))
            duplicates = mro.get_duplicates()
            if duplicates:
                raise ComponentError(f"Duplicate names found: {duplicates}")

            mro.update_mro(excluded=excluded)
            excluded.update(mro.mro)
        
    def _remove_base(self, branch: MockBranch, base: MockBranch) -> None:
        """Remove a base from a branch."""

        excluded = set()
        self._graph.remove_edge(base.comp_path, branch.comp_path)
        for sub in self._graph.ordered_subs(branch.comp_path, incdlue_node=True, leaves_only=True):
            mro = MROUpdater(list(self.get_mro(sub)))
            duplicates = mro.get_duplicates()
            if duplicates:
                raise ComponentError(f"Duplicate names found: {duplicates}")
            
            mro.update_mro(excluded=excluded)
            excluded.update(mro.mro)

    def _rename_branch(self, branch: MockBranch, name: str) -> None:
        """Rename a branch."""
        
        children = [branch.comp_path]
        for child in branch.traverse_branch_bfs():
            children.append(child.comp_path) 

    def _update_branch(self, branch: MockBranch, **kwargs) -> None:
        """Update a branch."""
        pass

    # -----------------------------------------------------------------------
    # Leaf Operations
    # -----------------------------------------------------------------------

    def _create_leaf(self, parent: MockBranch, name: str, type_: type, **kwargs) -> MockLeaf:
        """Create a new leaf."""

        if parent.has_child(name):
            raise ComponentError(f"Leaf {name} already exists under {parent.comp_path}")
        
        leaf = parent.create_leaf(name, type_, None, **kwargs)
        excluded = set(self.get_mro(parent.comp_path))
        for sub in self._graph.ordered_subs(parent.comp_path, leaves_only=True):
            mro = MROUpdater(list(self.get_mro(sub)))
            duplicates = mro.get_duplicates()
            if duplicates:
                raise ComponentError(f"Duplicate names found: {duplicates}")
            
            mro.update_mro(excluded=excluded)
            excluded.update(mro.mro)

        return leaf

    def _delete_leaf(self, parent: MockBranch, name: str) -> None:
        """Delete a leaf."""

        if not parent.has_child(name):
            raise ComponentError(f"Leaf {name} does not exist under {parent.comp_path}")
        
        parent.delete_leaf(name)
        excluded = set()
        for sub in self._graph.ordered_subs(parent.comp_path, leaves_only=True):
            mro = MROUpdater(list(self.get_mro(sub)))
            mro.update_mro(excluded=excluded)
            excluded.update(mro.mro)

    def _rename_leaf(self, leaf: MockLeaf, name: str) -> None:
        """Rename a leaf."""
        pass

    def _update_leaf(self, leaf: MockLeaf, **kwargs) -> None:
        """Update a leaf."""
        pass