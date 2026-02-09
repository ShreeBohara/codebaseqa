"""
Tests for Tree-sitter parser.
"""

import pytest


class TestTreeSitterParser:
    """Test suite for Tree-sitter parser."""

    @pytest.mark.parametrize(
        "language",
        ["python", "javascript", "typescript", "java", "go", "rust", "csharp", "cpp", "ruby"],
    )
    def test_parser_init_for_supported_languages(self, language):
        """Test parser initialization for all supported languages."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser

        parser = TreeSitterParser(language)
        assert parser._language == language

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
        from src.core.parser.tree_sitter_parser import ChunkType, TreeSitterParser

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

    @pytest.mark.parametrize(
        "language,fixture_name,file_name,expected_markers",
        [
            ("go", "sample_go_code", "main.go", ["add", "Greeter"]),
            ("rust", "sample_rust_code", "main.rs", ["sum", "Counter"]),
            ("csharp", "sample_csharp_code", "main.cs", ["Calculator", "Add"]),
            ("cpp", "sample_cpp_code", "main.cpp", ["Greeter", "add"]),
            ("ruby", "sample_ruby_code", "main.rb", ["Billing", "helper"]),
        ],
    )
    def test_new_language_parsers_extract_symbols(
        self,
        request: pytest.FixtureRequest,
        language: str,
        fixture_name: str,
        file_name: str,
        expected_markers: list[str],
    ):
        """Test semantic parsing for newly added languages."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser

        parser = TreeSitterParser(language)
        sample = request.getfixturevalue(fixture_name)
        result = parser.parse(sample, file_name)

        assert result.language == language
        assert len(result.chunks) > 0
        extracted = " ".join(name for name in (c.name for c in result.chunks) if name)
        for marker in expected_markers:
            assert marker in extracted

    def test_get_parser_for_file(self):
        """Test automatic parser selection by file extension."""
        from src.core.parser.tree_sitter_parser import get_parser_for_file

        cases = {
            "app.py": "python",
            "app.js": "javascript",
            "app.ts": "typescript",
            "app.java": "java",
            "app.go": "go",
            "app.rs": "rust",
            "app.cs": "csharp",
            "script.csx": "csharp",
            "main.cpp": "cpp",
            "main.cc": "cpp",
            "header.hpp": "cpp",
            "app.rb": "ruby",
            "tasks.rake": "ruby",
            "mygem.gemspec": "ruby",
        }
        for file_path, expected_language in cases.items():
            parser = get_parser_for_file(file_path)
            assert parser is not None
            assert parser._language == expected_language

        # Unknown extension should return None
        unknown = get_parser_for_file("file.xyz")
        assert unknown is None

    def test_unsupported_language_raises(self):
        """Test that unsupported language raises error."""
        from src.core.parser.tree_sitter_parser import TreeSitterParser

        with pytest.raises(ValueError):
            TreeSitterParser("haskell")
