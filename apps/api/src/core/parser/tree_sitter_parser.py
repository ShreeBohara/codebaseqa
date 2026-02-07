"""
Tree-sitter based code parser for Python, JavaScript, and TypeScript.
Extracts semantic chunks (functions, classes, methods) for embedding.
"""

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import List, Optional

import tree_sitter_java as tsjava
import tree_sitter_javascript as tsjavascript
import tree_sitter_python as tspython
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

    CONFIGS = {
        "python": {
            "extensions": [".py"],
            "language": Language(tspython.language()),
            "function_types": ["function_definition"],
            "class_types": ["class_definition"],
            "import_types": ["import_statement", "import_from_statement"],
        },
        "javascript": {
            "extensions": [".js", ".jsx"],
            "language": Language(tsjavascript.language()),
            "function_types": ["function_declaration", "arrow_function"],
            "class_types": ["class_declaration"],
            "import_types": ["import_statement"],
        },
        "typescript": {
            "extensions": [".ts", ".tsx"],
            "language": Language(tstypescript.language_typescript()),
            "function_types": ["function_declaration", "method_definition", "arrow_function"],
            "class_types": ["class_declaration", "interface_declaration", "enum_declaration"],
            "import_types": ["import_declaration", "import_statement"],
        },
        "java": {
            "extensions": [".java"],
            "language": Language(tsjava.language()),
            "function_types": ["method_declaration", "constructor_declaration"],
            "class_types": ["class_declaration", "interface_declaration", "enum_declaration"],
            "import_types": ["import_declaration"],
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

        # Extract imports
        for child in root.children:
            if child.type in self._config["import_types"]:
                imports.append(self._get_text(child, content))

        import_context = '\n'.join(imports[:10]) + '\n\n' if imports else ""

        # Extract functions and classes
        for child in root.children:
            if child.type in self._config["function_types"]:
                chunk = self._process_function(child, content, import_context)
                if chunk:
                    chunks.append(chunk)

            elif child.type in self._config["class_types"]:
                class_chunks = self._process_class(child, content, import_context)
                chunks.extend(class_chunks)

        # If nothing found, create module-level chunk
        if not chunks and content.strip():
            chunks.append(CodeChunk(
                content=content,
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
        name_node = self._find_child(node, "identifier")
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

        name_node = self._find_child(node, "identifier")
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
        body = self._find_child(node, "block") or self._find_child(node, "class_body")
        if body:
            for child in body.children:
                if child.type in self._config["function_types"] or child.type == "method_definition":
                    method_name_node = self._find_child(child, "identifier")
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

    def _get_text(self, node: Node, content: str) -> str:
        return content[node.start_byte:node.end_byte]


@lru_cache(maxsize=10)
def _get_cached_parser(language: str) -> TreeSitterParser:
    """Get cached parser instance for language."""
    return TreeSitterParser(language)


def get_parser_for_file(file_path: str) -> Optional[TreeSitterParser]:
    """Get parser based on file extension."""
    for lang, config in TreeSitterParser.CONFIGS.items():
        for ext in config["extensions"]:
            if file_path.endswith(ext):
                return _get_cached_parser(lang)
    return None

