package parse

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func write(t *testing.T, dir, name, content string) string {
	t.Helper()
	p := filepath.Join(dir, name)
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
	return p
}

// The plain TypeScript grammar cannot parse JSX. Mapping .tsx to it produces a tree full
// of ERROR nodes for every .tsx file -- the exact bug that shipped in the Python parser.
func TestTSXUsesTheTSXGrammar(t *testing.T) {
	dir := t.TempDir()
	src := "export function Widget({ label }: { label: string }) {\n" +
		"  return <div className=\"w\">{label}</div>;\n}\n"
	abs := write(t, dir, "Widget.tsx", src)

	chunks, err := File(abs, "Widget.tsx")
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if len(chunks) == 0 {
		t.Fatal("expected at least one chunk")
	}
	for _, c := range chunks {
		if c.Language != "tsx" {
			t.Errorf("language = %q, want tsx (the plain TS grammar cannot parse JSX)", c.Language)
		}
		if c.HadParseError {
			t.Errorf("chunk %q has a parse error; JSX should parse cleanly under tsx", c.Name)
		}
	}
}

// tree-sitter offsets are BYTE offsets. Slicing a decoded string with them corrupts every
// chunk after the first multi-byte character.
func TestChunksAfterNonASCIIAreNotMisaligned(t *testing.T) {
	dir := t.TempDir()
	src := "# héllo — wörld 日本語 🎉\n" +
		"def after_unicode(x):\n    return x * 2\n" +
		"class Café:\n    def método(self):\n        return \"ok\"\n"
	abs := write(t, dir, "unicode.py", src)

	chunks, err := File(abs, "unicode.py")
	if err != nil {
		t.Fatalf("parse: %v", err)
	}

	byName := map[string]Chunk{}
	for _, c := range chunks {
		if c.Name != "" {
			byName[c.Name] = c
		}
	}

	for _, want := range []struct{ name, prefix string }{
		{"after_unicode", "def after_unicode"},
		{"Café", "class Café:"},
		{"método", "def método(self):"},
	} {
		got, ok := byName[want.name]
		if !ok {
			t.Errorf("missing chunk %q (got %v)", want.name, keys(byName))
			continue
		}
		if !strings.HasPrefix(got.Content, want.prefix) {
			t.Errorf("chunk %q content = %q, want prefix %q -- byte/char offset mismatch",
				want.name, truncateForMsg(got.Content), want.prefix)
		}
	}
}

// tree-sitter returns a partial tree rather than failing on a syntax error, so the flag is
// the only way a caller can decide to fall back to raw indexing.
func TestSyntaxErrorIsReportedNotSwallowed(t *testing.T) {
	dir := t.TempDir()
	abs := write(t, dir, "broken.py", "def ok():\n    return 1\n\nclass ((( :\n")

	chunks, err := File(abs, "broken.py")
	if err != nil {
		t.Fatalf("parse should not fail on a syntax error: %v", err)
	}
	if len(chunks) == 0 {
		t.Fatal("expected chunks even from a file with errors")
	}
	found := false
	for _, c := range chunks {
		if c.HadParseError {
			found = true
		}
	}
	if !found {
		t.Error("HadParseError was never set on a file with a syntax error")
	}
}

func TestExtensionMapping(t *testing.T) {
	cases := map[string]string{
		".py": "python", ".ts": "typescript", ".tsx": "tsx",
		".js": "javascript", ".jsx": "javascript", ".go": "go",
	}
	for ext, want := range cases {
		got, ok := LanguageFor(ext)
		if !ok || got != want {
			t.Errorf("LanguageFor(%q) = %q,%v; want %q", ext, got, ok, want)
		}
	}
	if _, ok := LanguageFor(".rs"); ok {
		t.Error("LanguageFor(.rs) should report unlinked: this build has 5 grammars, not 9")
	}
}

func TestUnknownExtensionYieldsNoChunks(t *testing.T) {
	dir := t.TempDir()
	abs := write(t, dir, "notes.txt", "plain text")
	chunks, err := File(abs, "notes.txt")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if len(chunks) != 0 {
		t.Errorf("expected no chunks for an unlinked extension, got %d", len(chunks))
	}
}

// A file with no extractable declarations still carries meaning; dropping it would lose
// content the Python side keeps.
func TestFileWithNoDeclarationsFallsBackToModuleChunk(t *testing.T) {
	dir := t.TempDir()
	abs := write(t, dir, "consts.py", "A = 1\nB = 2\n")
	chunks, err := File(abs, "consts.py")
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if len(chunks) != 1 || chunks[0].ChunkType != "module" {
		t.Fatalf("want one module chunk, got %+v", chunks)
	}
}

func TestLinkedReportsEveryMappedExtension(t *testing.T) {
	linked := Linked()
	if len(linked) == 0 {
		t.Fatal("Linked() must report grammars so callers never assume parity with Python")
	}
	if exts, ok := linked["tsx"]; !ok || len(exts) == 0 {
		t.Error("tsx must be reported separately from typescript")
	}
}

func keys(m map[string]Chunk) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}

func truncateForMsg(s string) string {
	if len(s) > 60 {
		return s[:60] + "..."
	}
	return s
}
