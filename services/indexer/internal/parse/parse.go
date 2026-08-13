// Package parse extracts semantic chunks with tree-sitter.
//
// Uses the OFFICIAL tree-sitter/go-tree-sitter binding. Not smacker/go-tree-sitter, which
// outranks it in search results and has roughly twice the stars but was last pushed
// 2024-08-27 with 42 open issues and no deprecation notice -- it is the default wrong
// choice here.
//
// Two correctness details carried over from fixing the same bugs in the Python parser:
//
//  1. .tsx uses LanguageTSX(), not LanguageTypescript(). The plain TypeScript grammar
//     cannot parse JSX and returns a tree full of ERROR nodes for every .tsx file.
//  2. Chunk text comes from node.Utf8Text over the source bytes. tree-sitter offsets are
//     BYTE offsets; slicing a decoded string with them corrupts every chunk after the
//     first multi-byte character.
package parse

import (
	"os"

	tree_sitter "github.com/tree-sitter/go-tree-sitter"
	golang "github.com/tree-sitter/tree-sitter-go/bindings/go"
	javascript "github.com/tree-sitter/tree-sitter-javascript/bindings/go"
	python "github.com/tree-sitter/tree-sitter-python/bindings/go"
	typescript "github.com/tree-sitter/tree-sitter-typescript/bindings/go"
)

type Chunk struct {
	FilePath      string
	Language      string
	ChunkType     string
	Name          string
	Content       string
	StartLine     uint32
	EndLine       uint32
	HadParseError bool
}

type langConfig struct {
	name          string
	language      *tree_sitter.Language
	functionTypes map[string]struct{}
	classTypes    map[string]struct{}
	nameTypes     map[string]struct{}
}

func set(items ...string) map[string]struct{} {
	m := make(map[string]struct{}, len(items))
	for _, i := range items {
		m[i] = struct{}{}
	}
	return m
}

// Grammar set is deliberately narrower than the Python side's nine. Each grammar is cgo
// with its own generated parser.c, so every addition costs build time and image size;
// these four cover the languages this project is actually indexed against. Health()
// reports what is linked so the caller never has to assume parity.
var configs = map[string]langConfig{
	"python": {
		name:          "python",
		language:      tree_sitter.NewLanguage(python.Language()),
		functionTypes: set("function_definition"),
		classTypes:    set("class_definition"),
		nameTypes:     set("identifier"),
	},
	"javascript": {
		name:          "javascript",
		language:      tree_sitter.NewLanguage(javascript.Language()),
		functionTypes: set("function_declaration", "method_definition", "arrow_function", "function_expression"),
		classTypes:    set("class_declaration"),
		nameTypes:     set("identifier", "property_identifier"),
	},
	"typescript": {
		name:          "typescript",
		language:      tree_sitter.NewLanguage(typescript.LanguageTypescript()),
		functionTypes: set("function_declaration", "method_definition", "arrow_function", "function_signature"),
		classTypes:    set("class_declaration", "interface_declaration"),
		nameTypes:     set("identifier", "property_identifier", "type_identifier"),
	},
	// Separate entry precisely because LanguageTypescript() cannot parse JSX.
	"tsx": {
		name:          "tsx",
		language:      tree_sitter.NewLanguage(typescript.LanguageTSX()),
		functionTypes: set("function_declaration", "method_definition", "arrow_function", "function_signature"),
		classTypes:    set("class_declaration", "interface_declaration"),
		nameTypes:     set("identifier", "property_identifier", "type_identifier"),
	},
	"go": {
		name:          "go",
		language:      tree_sitter.NewLanguage(golang.Language()),
		functionTypes: set("function_declaration", "method_declaration"),
		classTypes:    set("type_declaration"),
		nameTypes:     set("identifier", "type_identifier", "field_identifier"),
	},
}

var extToLang = map[string]string{
	".py": "python",
	".js": "javascript", ".jsx": "javascript",
	".ts":  "typescript",
	".tsx": "tsx", // never "typescript"
	".go":  "go",
}

// LanguageFor reports the grammar for an extension, and whether one exists.
func LanguageFor(ext string) (string, bool) {
	l, ok := extToLang[ext]
	return l, ok
}

// Linked returns the grammars this build links, for Health().
func Linked() map[string][]string {
	out := map[string][]string{}
	for ext, lang := range extToLang {
		out[lang] = append(out[lang], ext)
	}
	return out
}

// File parses one file and returns its chunks.
//
// A tree containing ERROR nodes is reported via HadParseError rather than swallowed:
// tree-sitter does not fail on a syntax error, it returns a partial tree, so a caller
// that only watches for errors would silently index garbage. The Python side uses the
// same signal to fall back to raw indexing.
func File(absPath, relPath string) ([]Chunk, error) {
	ext := lowerExt(relPath)
	langName, ok := LanguageFor(ext)
	if !ok {
		return nil, nil
	}
	cfg := configs[langName]

	source, err := os.ReadFile(absPath)
	if err != nil {
		return nil, err
	}

	parser := tree_sitter.NewParser()
	defer parser.Close()
	if err := parser.SetLanguage(cfg.language); err != nil {
		return nil, err
	}

	tree := parser.Parse(source, nil)
	if tree == nil {
		return nil, nil
	}
	defer tree.Close()

	root := tree.RootNode()
	hadError := root.HasError()

	var chunks []Chunk
	var visit func(n *tree_sitter.Node, inClass bool)
	visit = func(n *tree_sitter.Node, inClass bool) {
		kind := n.Kind()
		_, isClass := cfg.classTypes[kind]
		_, isFunc := cfg.functionTypes[kind]

		switch {
		case isClass:
			chunks = append(chunks, chunkFrom(n, source, relPath, cfg, "class", hadError))
		case isFunc:
			kindLabel := "function"
			if inClass {
				kindLabel = "method"
			}
			chunks = append(chunks, chunkFrom(n, source, relPath, cfg, kindLabel, hadError))
		}

		for i := uint(0); i < n.ChildCount(); i++ {
			visit(n.Child(i), inClass || isClass)
		}
	}
	visit(root, false)

	// Mirrors the Python fallback: a file with no extractable declarations still carries
	// meaning, so emit it as a module-level chunk rather than dropping it.
	if len(chunks) == 0 && len(source) > 0 {
		chunks = append(chunks, Chunk{
			FilePath:      relPath,
			Language:      cfg.name,
			ChunkType:     "module",
			Content:       truncate(string(source), 4000),
			StartLine:     1,
			EndLine:       uint32(root.EndPosition().Row) + 1,
			HadParseError: hadError,
		})
	}
	return chunks, nil
}

func chunkFrom(
	n *tree_sitter.Node, source []byte, relPath string, cfg langConfig,
	chunkType string, hadError bool,
) Chunk {
	return Chunk{
		FilePath:  relPath,
		Language:  cfg.name,
		ChunkType: chunkType,
		Name:      nameOf(n, source, cfg),
		// Utf8Text slices the SOURCE BYTES, which is what tree-sitter offsets index.
		Content:       n.Utf8Text(source),
		StartLine:     uint32(n.StartPosition().Row) + 1,
		EndLine:       uint32(n.EndPosition().Row) + 1,
		HadParseError: hadError,
	}
}

func nameOf(n *tree_sitter.Node, source []byte, cfg langConfig) string {
	if named := n.ChildByFieldName("name"); named != nil {
		return named.Utf8Text(source)
	}
	for i := uint(0); i < n.ChildCount(); i++ {
		child := n.Child(i)
		if _, ok := cfg.nameTypes[child.Kind()]; ok {
			return child.Utf8Text(source)
		}
	}
	return ""
}

func lowerExt(path string) string {
	for i := len(path) - 1; i >= 0; i-- {
		if path[i] == '.' {
			return lower(path[i:])
		}
		if path[i] == '/' {
			break
		}
	}
	return ""
}

func lower(s string) string {
	b := []byte(s)
	for i := range b {
		if b[i] >= 'A' && b[i] <= 'Z' {
			b[i] += 32
		}
	}
	return string(b)
}

func truncate(s string, max int) string {
	if len(s) <= max {
		return s
	}
	return s[:max] + "\n... [truncated]"
}
