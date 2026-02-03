"""
Tests for Tree-sitter parser.
"""

import pytest


class TestTreeSitterParser:
    """Test suite for Tree-sitter parser."""

    def test_python_parser_init(self):
        """Test Python parser initialization."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser

        parser = TreeSitterParser("python")
        assert parser._language == "python"

    def test_python_parse_functions(self, sample_python_code):
        """Test parsing Python functions."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser

        parser = TreeSitterParser("python")
        result = parser.parse(sample_python_code, "test.py")

        assert result.language == "python"
        assert result.file_path == "test.py"
        assert len(result.chunks) > 0

        # Should find fibonacci function
        func_names = [c.name for c in result.chunks if c.name]
        assert "fibonacci" in func_names

    def test_python_parse_classes(self, sample_python_code):
        """Test parsing Python classes and methods."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser, ChunkType

        parser = TreeSitterParser("python")
        result = parser.parse(sample_python_code, "test.py")

        # Should find Calculator class
        class_chunks = [c for c in result.chunks if c.chunk_type == ChunkType.CLASS]
        assert len(class_chunks) >= 1
        assert class_chunks[0].name == "Calculator"

    def test_python_imports(self, sample_python_code):
        """Test extracting Python imports."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser

        parser = TreeSitterParser("python")
        result = parser.parse(sample_python_code, "test.py")

        assert len(result.imports) >= 1
        assert any("os" in imp for imp in result.imports)

    def test_javascript_parser(self, sample_javascript_code):
        """Test JavaScript parser."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser

        parser = TreeSitterParser("javascript")
        result = parser.parse(sample_javascript_code, "test.js")

        assert result.language == "javascript"
        assert len(result.chunks) > 0

        # Should find formatName function
        func_names = [c.name for c in result.chunks if c.name]
        assert "formatName" in func_names

    def test_get_parser_for_file(self):
        """Test automatic parser selection by file extension."""
        from src.core.parser.tree_sitter_parser import get_parser_for_file

        py_parser = get_parser_for_file("app.py")
        assert py_parser is not None
        assert py_parser._language == "python"

        js_parser = get_parser_for_file("app.js")
        assert js_parser is not None
        assert js_parser._language == "javascript"

        ts_parser = get_parser_for_file("app.ts")
        assert ts_parser is not None
        assert ts_parser._language == "typescript"

        # Unknown extension should return None
        unknown = get_parser_for_file("file.xyz")
        assert unknown is None

    def test_unsupported_language_raises(self):
        """Test that unsupported language raises error."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser

        with pytest.raises(ValueError):
            TreeSitterParser("ruby")
