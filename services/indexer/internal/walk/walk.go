// Package walk finds indexable files in a checkout.
//
// Ported from IndexingService._find_files in the Python API, with the same skip
// directories, extension set and size cap so both sides agree on what "indexable" means.
// One deliberate difference: the Python version's max-files cap did not work. Its `break`
// left only the inner filename loop, so os.walk continued into the next directory and kept
// appending -- the cap leaked by up to one directory's worth each time. Here the limit is
// enforced with fs.SkipAll, which actually stops the walk.
package walk

import (
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

// Directories never worth indexing. Mirrors SKIP_PATTERNS in indexing_service.py.
var skipDirs = map[string]struct{}{
	"node_modules": {}, "__pycache__": {}, ".git": {}, ".venv": {}, "venv": {},
	"dist": {}, "build": {}, ".next": {}, "coverage": {}, ".pytest_cache": {},
	"vendor": {}, "target": {}, ".idea": {}, ".vscode": {},
}

// Mirrors INDEXED_EXTENSIONS.
var indexedExts = map[string]struct{}{
	".py": {}, ".js": {}, ".jsx": {}, ".ts": {}, ".tsx": {},
	".java": {}, ".go": {}, ".rs": {}, ".c": {}, ".cpp": {}, ".h": {}, ".cc": {},
	".cxx": {}, ".hpp": {}, ".hh": {}, ".hxx": {}, ".ipp": {}, ".tpp": {},
	".cs": {}, ".csx": {},
	".rb": {}, ".rake": {}, ".gemspec": {}, ".php": {}, ".swift": {}, ".kt": {},
	".erb": {},
	".md":  {}, ".json": {},
}

// Mirrors INDEXED_FILENAMES: extensionless files worth indexing.
var indexedNames = map[string]struct{}{
	"gemfile": {}, "rakefile": {}, "config.ru": {},
}

type Result struct {
	// Paths relative to root, so they match CodeFile.path on the Python side.
	Paths   []string
	Skipped int
	// True when MaxFiles stopped the walk early, so the caller can report a partial
	// index rather than implying the repository was fully covered.
	Truncated bool
}

type Options struct {
	MaxFiles      int
	MaxFileSizeKB int
}

// Find returns indexable files under root.
func Find(root string, opts Options) (Result, error) {
	if opts.MaxFiles <= 0 {
		opts.MaxFiles = 5000
	}
	if opts.MaxFileSizeKB <= 0 {
		opts.MaxFileSizeKB = 500
	}
	maxBytes := int64(opts.MaxFileSizeKB) * 1024

	res := Result{Paths: make([]string, 0, 256)}

	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			// An unreadable directory is not fatal: skip it and index the rest, matching
			// the Python behaviour of swallowing per-entry OSError.
			if d != nil && d.IsDir() {
				return fs.SkipDir
			}
			return nil
		}

		if d.IsDir() {
			if _, skip := skipDirs[d.Name()]; skip {
				return fs.SkipDir
			}
			return nil
		}

		if !isIndexable(d.Name()) {
			return nil
		}

		info, statErr := d.Info()
		if statErr != nil {
			res.Skipped++
			return nil
		}
		if info.Size() > maxBytes {
			res.Skipped++
			return nil
		}

		rel, relErr := filepath.Rel(root, path)
		if relErr != nil {
			res.Skipped++
			return nil
		}
		res.Paths = append(res.Paths, filepath.ToSlash(rel))

		if len(res.Paths) >= opts.MaxFiles {
			res.Truncated = true
			return fs.SkipAll // actually stops, unlike the Python inner-loop break
		}
		return nil
	})
	if err != nil && !os.IsNotExist(err) {
		return res, err
	}
	return res, nil
}

func isIndexable(name string) bool {
	lower := strings.ToLower(name)
	if _, ok := indexedNames[lower]; ok {
		return true
	}
	_, ok := indexedExts[strings.ToLower(filepath.Ext(name))]
	return ok
}
