package walk

import (
	"fmt"
	"os"
	"path/filepath"
	"testing"
)

func seed(t *testing.T, dir string, files map[string]string) {
	t.Helper()
	for name, body := range files {
		p := filepath.Join(dir, name)
		if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
	}
}

func TestSkipsExcludedDirectories(t *testing.T) {
	dir := t.TempDir()
	seed(t, dir, map[string]string{
		"src/app.ts":                "x",
		"node_modules/pkg/index.js": "x",
		".git/config":               "x",
		"dist/bundle.js":            "x",
		".venv/lib/mod.py":          "x",
	})

	got, err := Find(dir, Options{})
	if err != nil {
		t.Fatal(err)
	}
	if len(got.Paths) != 1 || got.Paths[0] != "src/app.ts" {
		t.Errorf("paths = %v, want only src/app.ts", got.Paths)
	}
}

// The Python original's cap did not work: its `break` left only the inner filename loop,
// so os.walk continued into the next directory and kept appending. This is the regression
// test for that class of bug.
func TestMaxFilesActuallyStopsTheWalk(t *testing.T) {
	dir := t.TempDir()
	files := map[string]string{}
	for d := 0; d < 5; d++ {
		for f := 0; f < 10; f++ {
			files[fmt.Sprintf("d%d/f%d.py", d, f)] = "x"
		}
	}
	seed(t, dir, files)

	got, err := Find(dir, Options{MaxFiles: 12})
	if err != nil {
		t.Fatal(err)
	}
	if len(got.Paths) > 12 {
		t.Errorf("found %d files with MaxFiles=12: the cap leaked", len(got.Paths))
	}
	if !got.Truncated {
		t.Error("Truncated must be set, or a partial index looks like full coverage")
	}
}

func TestTruncatedIsFalseWhenEverythingFits(t *testing.T) {
	dir := t.TempDir()
	seed(t, dir, map[string]string{"a.py": "x", "b.py": "x"})
	got, err := Find(dir, Options{MaxFiles: 100})
	if err != nil {
		t.Fatal(err)
	}
	if got.Truncated {
		t.Error("Truncated set despite the walk completing")
	}
}

func TestSkipsOversizeFiles(t *testing.T) {
	dir := t.TempDir()
	big := make([]byte, 3*1024)
	for i := range big {
		big[i] = 'x'
	}
	seed(t, dir, map[string]string{"small.py": "x"})
	if err := os.WriteFile(filepath.Join(dir, "big.py"), big, 0o644); err != nil {
		t.Fatal(err)
	}

	got, err := Find(dir, Options{MaxFileSizeKB: 2})
	if err != nil {
		t.Fatal(err)
	}
	if len(got.Paths) != 1 || got.Paths[0] != "small.py" {
		t.Errorf("paths = %v, want only small.py", got.Paths)
	}
	if got.Skipped != 1 {
		t.Errorf("Skipped = %d, want 1", got.Skipped)
	}
}

func TestIndexesExtensionlessKnownFilenames(t *testing.T) {
	dir := t.TempDir()
	seed(t, dir, map[string]string{
		"Gemfile": "x", "Rakefile": "x", "config.ru": "x", "LICENSE": "x",
	})
	got, err := Find(dir, Options{})
	if err != nil {
		t.Fatal(err)
	}
	if len(got.Paths) != 3 {
		t.Errorf("paths = %v, want the three known Ruby filenames and not LICENSE", got.Paths)
	}
}

func TestPathsAreRelativeAndSlashSeparated(t *testing.T) {
	dir := t.TempDir()
	seed(t, dir, map[string]string{"a/b/c.py": "x"})
	got, err := Find(dir, Options{})
	if err != nil {
		t.Fatal(err)
	}
	// Must match CodeFile.path on the Python side, which is repo-relative with forward
	// slashes regardless of platform.
	if len(got.Paths) != 1 || got.Paths[0] != "a/b/c.py" {
		t.Errorf("paths = %v, want [a/b/c.py]", got.Paths)
	}
}

func TestMissingRootIsNotAPanic(t *testing.T) {
	if _, err := Find(filepath.Join(t.TempDir(), "nope"), Options{}); err != nil {
		t.Errorf("a missing root should return empty, not error: %v", err)
	}
}
