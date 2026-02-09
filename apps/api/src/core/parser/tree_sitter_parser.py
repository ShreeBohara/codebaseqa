"""
Tree-sitter based code parser for supported repository languages.
Extracts semantic chunks (functions, classes, methods) for embedding.
"""

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import List, Optional, Sequence

import tree_sitter_c_sharp as tscsharp
import tree_sitter_cpp as tscpp
import tree_sitter_go as tsgo
import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjavascript
import tree_sitter_python as tspython
import tree_sitter_ruby as tsruby
import tree_sitter_rust as tsrust
import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser


class ChunkType(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"


@dataclass
class CodeChunk:
    """Represents a parsed chunk of code."""
    content: str
    chunk_type: ChunkType
    start_line: int
    end_line: int
    name: Optional[str] = None
    docstring: Optional[str] = None
    signature: Optional[str] = None
    context_before: str = ""


@dataclass
class ParseResult:
    """Result of parsing a code file."""
    file_path: str
    language: str
    chunks: List[CodeChunk]
    imports: List[str]
    exports: List[str]
    line_count: int = 0


class TreeSitterParser:
    """Multi-language parser using Tree-sitter."""

    DEFAULT_FUNCTION_NAME_TYPES = ["identifier", "type_identifier", "field_identifier"]
    DEFAULT_CLASS_NAME_TYPES = ["identifier", "type_identifier", "field_identifier", "constant"]
    DEFAULT_CLASS_BODY_TYPES = ["block", "class_body", "declaration_list", "field_declaration_list", "body_statement"]

    CONFIGS = {
        "python": {
            "extensions": [".py"],
            "language": Language(tspython.language()),
            "function_types": ["function_definition"],
            "class_types": ["class_definition"],
            "import_types": ["import_statement", "import_from_statement"],
            "class_body_types": ["block"],
        },
        "javascript": {
            "extensions": [".js", ".jsx"],
            "language": Language(tsjavascript.language()),
            "function_types": ["function_declaration", "arrow_function"],
            "class_types": ["class_declaration"],
            "import_types": ["import_statement"],
            "class_body_types": ["class_body"],
        },
        "typescript": {
            "extensions": [".ts", ".tsx"],
            "language": Language(tstypescript.language_typescript()),
            "function_types": ["function_declaration", "method_definition", "arrow_function"],
            "class_types": ["class_declaration", "interface_declaration", "enum_declaration"],
            "import_types": ["import_declaration", "import_statement"],
            "class_body_types": ["class_body"],
        },
        "java": {
            "extensions": [".java"],
            "language": Language(tsjava.language()),
            "function_types": ["method_declaration", "constructor_declaration"],
            "class_types": ["class_declaration", "interface_declaration", "enum_declaration"],
            "import_types": ["import_declaration"],
            "class_body_types": ["class_body"],
        },
        "go": {
            "extensions": [".go"],
            "language": Language(tsgo.language()),
            "function_types": ["function_declaration", "method_declaration"],
            "class_types": ["type_declaration", "type_spec"],
            "import_types": ["import_declaration"],
            "class_name_types": ["type_identifier", "identifier"],
        },
        "rust": {
            "extensions": [".rs"],
            "language": Language(tsrust.language()),
            "function_types": ["function_item"],
            "class_types": ["struct_item", "enum_item", "trait_item", "impl_item"],
            "import_types": ["use_declaration"],
            "class_body_types": ["declaration_list", "field_declaration_list", "body"],
        },
        "csharp": {
            "extensions": [".cs", ".csx"],
            "language": Language(tscsharp.language()),
            "function_types": ["method_declaration", "constructor_declaration", "local_function_statement"],
            "class_types": [
                "class_declaration",
                "interface_declaration",
                "struct_declaration",
                "record_declaration",
                "enum_declaration",
            ],
            "import_types": ["using_directive"],
            "class_body_types": ["declaration_list"],
        },
        "cpp": {
            "extensions": [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx", ".ipp", ".tpp", ".h"],
            "language": Language(tscpp.language()),
            "function_types": ["function_definition"],
            "class_types": ["class_specifier", "struct_specifier"],
            "import_types": ["preproc_include"],
            "class_body_types": ["field_declaration_list", "declaration_list"],
        },
        "ruby": {
            "extensions": [".rb", ".rake", ".gemspec"],
            "language": Language(tsruby.language()),
            "function_types": ["method", "singleton_method"],
            "class_types": ["class", "module"],
            "import_types": [],
            "function_name_types": ["identifier", "constant", "field_identifier"],
            "class_name_types": ["constant", "identifier"],
            "class_body_types": ["body_statement", "body"],
        },
    }

    def __init__(self, language: str):
        if language not in self.CONFIGS:
            raise ValueError(f"Unsupported language: {language}")

        self._language = language
        self._config = self.CONFIGS[language]
        self._parser = Parser(self._config["language"])

    def parse(self, content: str, file_path: str) -> ParseResult:
        """Parse code and extract semantic chunks."""
        tree = self._parser.parse(bytes(content, "utf-8"))
        root = tree.root_node

        chunks = []
        imports = []
        seen = set()

        # Extract imports
        for child in root.children:
            if child.type in self._config.get("import_types", []):
                imports.append(self._get_text(child, content))

        import_context = '\n'.join(imports[:10]) + '\n\n' if imports else ""

        # Extract functions/classes recursively so exported wrappers and nested declarations are included.
        class_types = set(self._config.get("class_types", []))
        function_types = set(self._config.get("function_types", []))

        def add_chunk(chunk: CodeChunk) -> None:
            key = (chunk.start_line, chunk.end_line, chunk.chunk_type.value, chunk.name or "")
            if key in seen:
                return
            seen.add(key)
            chunks.append(chunk)

        def visit(node: Node, in_class: bool = False) -> None:
            node_is_class = node.type in class_types
            if node_is_class:
                for class_chunk in self._process_class(node, content, import_context):
                    add_chunk(class_chunk)
            elif node.type in function_types:
                if not in_class and node.type != "method_definition":
                    fn_chunk = self._process_function(node, content, import_context)
                    if fn_chunk:
                        add_chunk(fn_chunk)

            for child in node.children:
                visit(child, in_class=in_class or node_is_class)

        visit(root)

        # If nothing found, create module-level chunk
        if not chunks and content.strip():
            fallback_content = content
            if len(fallback_content) > 4000:
                fallback_content = fallback_content[:4000] + "\n... [truncated]"
            chunks.append(CodeChunk(
                content=fallback_content,
                chunk_type=ChunkType.MODULE,
                start_line=1,
                end_line=content.count('\n') + 1,
                context_before=import_context,
            ))

        return ParseResult(
            file_path=file_path,
            language=self._language,
            chunks=chunks,
            imports=imports,
            exports=[],
            line_count=content.count('\n') + 1,
        )

    def _process_function(self, node: Node, content: str, context: str) -> Optional[CodeChunk]:
        """Extract function chunk."""
        name_node = self._find_name_node(
            node,
            self._config_list("function_name_types", self.DEFAULT_FUNCTION_NAME_TYPES),
        )
        if not name_node:
            return None

        return CodeChunk(
            content=self._get_text(node, content),
            chunk_type=ChunkType.FUNCTION,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            name=self._get_text(name_node, content),
            docstring=self._extract_docstring(node, content),
            context_before=context,
        )

    def _process_class(self, node: Node, content: str, context: str) -> List[CodeChunk]:
        """Extract class and method chunks."""
        chunks = []

        name_node = self._find_name_node(
            node,
            self._config_list("class_name_types", self.DEFAULT_CLASS_NAME_TYPES),
        )
        if not name_node:
            return chunks

        class_name = self._get_text(name_node, content)

        # Class chunk
        chunks.append(CodeChunk(
            content=self._get_text(node, content),
            chunk_type=ChunkType.CLASS,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            name=class_name,
            docstring=self._extract_docstring(node, content),
            context_before=context,
        ))

        # Also extract methods
        body = self._find_first_child(
            node,
            self._config_list("class_body_types", self.DEFAULT_CLASS_BODY_TYPES),
        )
        if body:
            function_types = set(self._config.get("function_types", []))
            function_name_types = self._config_list("function_name_types", self.DEFAULT_FUNCTION_NAME_TYPES)

            def visit_methods(method_node: Node) -> None:
                for child in method_node.children:
                    if child.type in function_types or child.type == "method_definition":
                        method_name_node = self._find_name_node(child, function_name_types)
                        if method_name_node:
                            method_name = self._get_text(method_name_node, content)
                            chunks.append(CodeChunk(
                                content=self._get_text(child, content),
                                chunk_type=ChunkType.METHOD,
                                start_line=child.start_point[0] + 1,
                                end_line=child.end_point[0] + 1,
                                name=f"{class_name}.{method_name}",
                                context_before=context,
                            ))
                    visit_methods(child)

            visit_methods(body)

        return chunks

    def _extract_docstring(self, node: Node, content: str) -> Optional[str]:
        """Extract docstring from function/class."""
        if self._language == "python":
            body = self._find_child(node, "block")
            if body and body.children:
                first = body.children[0]
                if first.type == "expression_statement":
                    string = self._find_child(first, "string")
                    if string:
                        return self._get_text(string, content).strip('"\' ')
        return None

    def _find_child(self, node: Node, type_name: str) -> Optional[Node]:
        for child in node.children:
            if child.type == type_name:
                return child
        return None

    def _find_descendant(self, node: Node, type_name: str) -> Optional[Node]:
        for child in node.children:
            if child.type == type_name:
                return child
            nested = self._find_descendant(child, type_name)
            if nested:
                return nested
        return None

    def _find_first_child(self, node: Node, type_names: Sequence[str]) -> Optional[Node]:
        for type_name in type_names:
            child = self._find_child(node, type_name)
            if child:
                return child
        return None

    def _find_name_node(self, node: Node, type_names: Sequence[str]) -> Optional[Node]:
        for type_name in type_names:
            child = self._find_child(node, type_name)
            if child:
                return child
        for type_name in type_names:
            nested = self._find_descendant(node, type_name)
            if nested:
                return nested
        return None

    def _config_list(self, key: str, default: Sequence[str]) -> List[str]:
        values = self._config.get(key)
        if isinstance(values, list) and values:
            return values
        return list(default)

    def _get_text(self, node: Node, content: str) -> str:
        return content[node.start_byte:node.end_byte]


@lru_cache(maxsize=20)
def _get_cached_parser(language: str) -> TreeSitterParser:
    """Get cached parser instance for language."""
    return TreeSitterParser(language)


def get_parser_for_file(file_path: str) -> Optional[TreeSitterParser]:
    """Get parser based on file extension."""
    normalized_file_path = file_path.lower()
    for lang, config in TreeSitterParser.CONFIGS.items():
        for ext in config["extensions"]:
            if normalized_file_path.endswith(ext):
                return _get_cached_parser(lang)
    return None
