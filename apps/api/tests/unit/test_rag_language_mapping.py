import pytest

from src.core.rag.pipeline import RAGPipeline


@pytest.mark.parametrize(
    "file_path,expected",
    [
        ("src/main.ts", "typescript"),
        ("src/main.py", "python"),
        ("src/main.js", "javascript"),
        ("src/main.java", "java"),
        ("src/main.go", "go"),
        ("src/main.rs", "rust"),
        ("src/main.cs", "csharp"),
        ("src/main.csx", "csharp"),
        ("src/main.cpp", "cpp"),
        ("src/main.hh", "cpp"),
        ("src/main.rb", "ruby"),
        ("tasks/build.rake", "ruby"),
        ("Gemfile", "ruby"),
        ("config.ru", "ruby"),
        ("app/views/home/index.erb", "erb"),
        ("README.md", "markdown"),
        ("config.yml", "yaml"),
        ("data.json", "json"),
    ],
)
def test_language_for_file_maps_new_extensions(file_path: str, expected: str):
    pipeline = RAGPipeline.__new__(RAGPipeline)
    assert pipeline._language_for_file(file_path) == expected
