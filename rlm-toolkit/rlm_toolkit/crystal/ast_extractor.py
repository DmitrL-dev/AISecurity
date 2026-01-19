"""
AST-based Python Extractor.

Provides accurate extraction using Python's ast module instead of regex.
"""

import ast
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .hierarchy import FileCrystal, Primitive
from .extractor import PrimitiveType

logger = logging.getLogger("rlm_crystal.ast_extractor")


@dataclass
class ExtractedRelation:
    """Relation between code elements."""

    source: str
    target: str
    relation_type: str  # imports, calls, inherits, uses
    source_file: str
    line: int


class ASTExtractor:
    """
    AST-based Python code extractor.

    Uses Python's ast module for accurate extraction:
    - Functions, classes, methods
    - Imports and dependencies
    - Call relationships
    - Inheritance

    Example:
        >>> extractor = ASTExtractor()
        >>> crystal = extractor.extract_from_file("/path/to/file.py", content)
    """

    def __init__(self):
        self.current_file = ""
        self.current_class = None

    def extract_from_file(self, path: str, content: str) -> FileCrystal:
        """Extract primitives from Python file using AST."""
        self.current_file = path
        name = Path(path).name

        crystal = FileCrystal(path=path, name=name)
        crystal.token_count = len(content) // 4
        crystal.content_hash = str(hash(content))[:8]

        try:
            tree = ast.parse(content)
            self._extract_from_node(tree, crystal, content)
        except SyntaxError as e:
            logger.warning(f"Syntax error in {path}: {e}")
            # Fall back to basic extraction
            crystal.add_primitive(
                Primitive(
                    ptype="ERROR",
                    name="syntax_error",
                    value=str(e),
                    source_file=path,
                    source_line=e.lineno or 1,
                    confidence=0.5,
                )
            )

        return crystal

    def _extract_from_node(
        self,
        node: ast.AST,
        crystal: FileCrystal,
        source: str,
    ) -> None:
        """Recursively extract from AST nodes."""

        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef):
                self._extract_function(child, crystal, source)
            elif isinstance(child, ast.AsyncFunctionDef):
                self._extract_function(child, crystal, source, is_async=True)
            elif isinstance(child, ast.ClassDef):
                self._extract_class(child, crystal, source)
            elif isinstance(child, ast.Import):
                self._extract_import(child, crystal)
            elif isinstance(child, ast.ImportFrom):
                self._extract_import_from(child, crystal)
            elif isinstance(child, ast.Assign):
                self._extract_assignment(child, crystal, source)

            # Recurse into child nodes
            self._extract_from_node(child, crystal, source)

    def _extract_function(
        self,
        node: ast.FunctionDef,
        crystal: FileCrystal,
        source: str,
        is_async: bool = False,
    ) -> None:
        """Extract function definition."""
        # Get docstring
        docstring = ast.get_docstring(node) or ""

        # Get signature
        args = self._get_function_args(node)
        returns = self._get_return_annotation(node)

        # Determine if method
        is_method = self.current_class is not None
        ptype = (
            PrimitiveType.METHOD.value if is_method else PrimitiveType.FUNCTION.value
        )

        # Full name
        name = f"{self.current_class}.{node.name}" if is_method else node.name

        # Build value
        prefix = "async " if is_async else ""
        value = f"{prefix}def {node.name}({args})"
        if returns:
            value += f" -> {returns}"

        crystal.add_primitive(
            Primitive(
                ptype=ptype,
                name=name,
                value=value,
                source_file=self.current_file,
                source_line=node.lineno,
                confidence=1.0,
                metadata={
                    "docstring": docstring[:200] if docstring else None,
                    "args": args,
                    "returns": returns,
                    "is_async": is_async,
                    "decorators": [
                        self._get_decorator_name(d) for d in node.decorator_list
                    ],
                },
            )
        )

        # Extract call relations (who this function calls)
        for call_node in ast.walk(node):
            if isinstance(call_node, ast.Call):
                called_name = self._get_call_name(call_node)
                if called_name and called_name != name:
                    crystal.add_primitive(
                        Primitive(
                            ptype="RELATION",
                            name=f"{name}->calls->{called_name}",
                            value=f"{name} calls {called_name}",
                            source_file=self.current_file,
                            source_line=call_node.lineno,
                            confidence=0.9,
                            metadata={"relation_type": "calls"},
                        )
                    )

        # Extract docstring as separate primitive
        if docstring:
            crystal.add_primitive(
                Primitive(
                    ptype=PrimitiveType.DOCSTRING.value,
                    name=f"{name}.__doc__",
                    value=docstring[:500],
                    source_file=self.current_file,
                    source_line=node.lineno + 1,
                    confidence=1.0,
                )
            )

    def _extract_class(
        self,
        node: ast.ClassDef,
        crystal: FileCrystal,
        source: str,
    ) -> None:
        """Extract class definition."""
        # Get bases
        bases = [self._get_node_name(b) for b in node.bases]

        # Get docstring
        docstring = ast.get_docstring(node) or ""

        crystal.add_primitive(
            Primitive(
                ptype=PrimitiveType.CLASS.value,
                name=node.name,
                value=(
                    f"class {node.name}({', '.join(bases)})"
                    if bases
                    else f"class {node.name}"
                ),
                source_file=self.current_file,
                source_line=node.lineno,
                confidence=1.0,
                metadata={
                    "bases": bases,
                    "docstring": docstring[:200] if docstring else None,
                    "decorators": [
                        self._get_decorator_name(d) for d in node.decorator_list
                    ],
                },
            )
        )

        # Add inheritance relations
        for base in bases:
            crystal.add_primitive(
                Primitive(
                    ptype="RELATION",
                    name=f"{node.name}->inherits->{base}",
                    value=f"{node.name} inherits from {base}",
                    source_file=self.current_file,
                    source_line=node.lineno,
                    confidence=1.0,
                    metadata={"relation_type": "inherits"},
                )
            )

        # Extract docstring
        if docstring:
            crystal.add_primitive(
                Primitive(
                    ptype=PrimitiveType.DOCSTRING.value,
                    name=f"{node.name}.__doc__",
                    value=docstring[:500],
                    source_file=self.current_file,
                    source_line=node.lineno + 1,
                    confidence=1.0,
                )
            )

        # Process class body with context
        old_class = self.current_class
        self.current_class = node.name
        self._extract_from_node(node, crystal, source)
        self.current_class = old_class

    def _extract_import(self, node: ast.Import, crystal: FileCrystal) -> None:
        """Extract import statement."""
        for alias in node.names:
            crystal.add_primitive(
                Primitive(
                    ptype=PrimitiveType.IMPORT.value,
                    name=alias.asname or alias.name,
                    value=f"import {alias.name}"
                    + (f" as {alias.asname}" if alias.asname else ""),
                    source_file=self.current_file,
                    source_line=node.lineno,
                    confidence=1.0,
                    metadata={"module": alias.name, "alias": alias.asname},
                )
            )

    def _extract_import_from(self, node: ast.ImportFrom, crystal: FileCrystal) -> None:
        """Extract from ... import statement."""
        module = node.module or ""

        for alias in node.names:
            crystal.add_primitive(
                Primitive(
                    ptype=PrimitiveType.IMPORT.value,
                    name=alias.asname or alias.name,
                    value=f"from {module} import {alias.name}"
                    + (f" as {alias.asname}" if alias.asname else ""),
                    source_file=self.current_file,
                    source_line=node.lineno,
                    confidence=1.0,
                    metadata={
                        "module": module,
                        "name": alias.name,
                        "alias": alias.asname,
                    },
                )
            )

    def _extract_assignment(
        self,
        node: ast.Assign,
        crystal: FileCrystal,
        source: str,
    ) -> None:
        """Extract top-level assignments (constants, globals)."""
        # Only extract module-level assignments
        if self.current_class is not None:
            return

        for target in node.targets:
            if isinstance(target, ast.Name):
                # Check if it looks like a constant (UPPER_CASE)
                if target.id.isupper():
                    value = self._get_node_value(node.value)
                    crystal.add_primitive(
                        Primitive(
                            ptype=PrimitiveType.CONSTANT.value,
                            name=target.id,
                            value=f"{target.id} = {value}",
                            source_file=self.current_file,
                            source_line=node.lineno,
                            confidence=0.9,
                        )
                    )

    def _get_function_args(self, node: ast.FunctionDef) -> str:
        """Get function arguments as string."""
        args = []

        # Regular args
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_node_name(arg.annotation)}"
            args.append(arg_str)

        # *args
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")

        # **kwargs
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")

        return ", ".join(args)

    def _get_return_annotation(self, node: ast.FunctionDef) -> Optional[str]:
        """Get return type annotation."""
        if node.returns:
            return self._get_node_name(node.returns)
        return None

    def _get_node_name(self, node: ast.AST) -> str:
        """Get string representation of a node (for types, etc.)."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_node_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return (
                f"{self._get_node_name(node.value)}[{self._get_node_name(node.slice)}]"
            )
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Tuple):
            return f"({', '.join(self._get_node_name(e) for e in node.elts)})"
        elif isinstance(node, ast.List):
            return f"[{', '.join(self._get_node_name(e) for e in node.elts)}]"
        else:
            return "..."

    def _get_node_value(self, node: ast.AST) -> str:
        """Get value from assignment."""
        if isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.List):
            return "[...]"
        elif isinstance(node, ast.Dict):
            return "{...}"
        elif isinstance(node, ast.Call):
            return f"{self._get_node_name(node.func)}(...)"
        else:
            return "..."

    def _get_decorator_name(self, node: ast.AST) -> str:
        """Get decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_node_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return "..."

    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Get name of called function."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def extract_relations(self, crystal: FileCrystal) -> List[ExtractedRelation]:
        """Extract all relations from a crystal."""
        relations = []

        for prim in crystal.primitives:
            if prim.ptype == "RELATION":
                # Parse relation from name
                parts = prim.name.split("->")
                if len(parts) == 3:
                    relations.append(
                        ExtractedRelation(
                            source=parts[0],
                            target=parts[2],
                            relation_type=parts[1],
                            source_file=prim.source_file,
                            line=prim.source_line,
                        )
                    )

        return relations


def create_ast_extractor() -> ASTExtractor:
    """Create AST extractor."""
    return ASTExtractor()
