# Indexer service (Go + gRPC)

Walk-and-parse stage extracted from the Python API, streaming results over gRPC.

## Why this exists — and why it is *not* about speed

The obvious claim ("rewrote the parser in Go for performance") is false, and it was
measured on this repository before any Go was written:

```
files parsed    : 900
sequential      : 1115.3 ms   (1.00x)
ThreadPool(4)   : 1092.5 ms   (1.02x)   <- threads give nothing
ProcessPool(4)  :  393.3 ms   (2.84x)
```

`py-tree-sitter` never releases the GIL, so threads are ~1.0x — which also means the
obvious `anyio.to_thread` fix would not have worked. Only ~41% of the parse phase is
actually C, so a perfect native rewrite ceilings around **2.4x**, *below* the 2.84x that
`ProcessPoolExecutor` on the existing Python already delivers for about half a day's work.

The real reason is a **process and failure boundary**. `repos.py` runs indexing by spinning
a new event loop inside an anyio threadpool thread and blocking it for minutes, in the same
process that serves chat. This moves that CPU-bound, GIL-bound, minutes-long stage behind
an explicit typed contract.

Server streaming is why gRPC rather than one large response: progress becomes part of the
contract instead of shared mutable state — the same bug class that made the SSE progress
bar show only 0% or 100%.

## Binding choice

Uses the **official** `tree-sitter/go-tree-sitter`. Not `smacker/go-tree-sitter`, which is
the trap: it has roughly twice the stars (562 vs 288) and outranks the official binding in
search results, but was last pushed **2024-08-27** with 42 open issues and no deprecation
notice.

## Two bugs not repeated here

Both were found and fixed in the Python parser; this implementation gets them right from
the start, and there are tests for each.

- **`.tsx` uses `LanguageTSX()`**, not `LanguageTypescript()`. The plain TypeScript grammar
  cannot parse JSX and returns a tree full of ERROR nodes for every `.tsx` file.
- **Chunk text comes from `node.Utf8Text(source)`** over the source *bytes*. tree-sitter
  offsets are byte offsets; slicing a decoded string with them corrupts every chunk after
  the first multi-byte character.

`had_parse_error` is on the wire because tree-sitter does not fail on a syntax error — it
returns a partial tree. Without that flag the Python caller cannot decide to fall back to
raw indexing.

## Build and run

```bash
cd services/indexer
CGO_ENABLED=1 go build -o bin/indexer .
./bin/indexer -addr :50051
```

`CGO_ENABLED=1` is mandatory: every grammar is cgo. That means a C toolchain in any builder
image, no `scratch` base, and a slower uncached build than the all-wheels Python image.

## Grammar scope, stated rather than implied

This build links **5** grammars (python, javascript, typescript, tsx, go) against the
Python side's 9. Each grammar is a separate generated `parser.c`, so each one costs build
time and binary size. `Health()` reports exactly what is linked so the caller never has to
assume parity:

```
linked grammars: {'go': ['.go'], 'javascript': ['.js', '.jsx'],
                  'python': ['.py'], 'tsx': ['.tsx'], 'typescript': ['.ts']}
```

## One fixed bug in the port

The Python `_find_files` max-files cap did not work: its `break` left only the inner
filename loop, so `os.walk` continued into the next directory and kept appending. The Go
walker uses `fs.SkipAll`, which actually stops, and reports `Truncated` so a partial index
is not mistaken for full coverage.

## Verified end to end

Go server running, Python client streaming, against this repository's `apps/api/src`:

```
health: True v0.1.0
progress events : 5
chunk batches   : 3
chunks received : 509
summary         : walked=59 parsed=58 chunks=509 errors=0 99ms
chunk kinds     : {'module': 17, 'class': 121, 'function': 109, 'method': 262}
example         : class 'Level' in api/graphql/schema.py L47-53
```

Correctness cases:

```
tsx         function  'Widget'          had_parse_error=False
function  'after_unicode' L2-3  content starts: 'def after_unicode(x):'
class     'Café'         L4-6  content starts: 'class Café:'
method    'método'       L5-6  content starts: 'def método(self):'
```

## Not done

The service is **not wired into the indexing pipeline** — `IndexingService` still uses the
Python parser, and `IndexerClient` is opt-in. Doing that swap needs a decision this PR does
not make: the service must be co-located with the API on the shared volume, because clones
live under `./data/repos/<owner>/<name>` and a Fly/EBS-style volume attaches to exactly one
machine. There is also no CI job for Go yet (`ci.yml` has Python 3.11 and Node 20 only, no
cgo toolchain, no grammar-compile caching, no cross-language contract test).
