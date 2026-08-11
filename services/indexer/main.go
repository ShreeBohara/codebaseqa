// Command indexer serves the walk-and-parse stage over gRPC.
//
// See proto/indexer.proto for why this is a separate process. In short: not for parse
// speed (measured, a native rewrite ceilings around 2.4x while ProcessPoolExecutor on the
// existing Python already gives 2.84x), but to move a CPU-bound, GIL-bound, minutes-long
// stage out of the process that serves chat, behind a typed streaming contract.
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"path/filepath"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"

	"github.com/ShreeBohara/codebaseqa/services/indexer/gen"
	"github.com/ShreeBohara/codebaseqa/services/indexer/internal/parse"
	"github.com/ShreeBohara/codebaseqa/services/indexer/internal/walk"
)

const version = "0.1.0"

// Default chunks per ChunkBatch. Batching matters: one message per chunk spends more time
// in framing than in parsing on a large repository.
const defaultBatchSize = 200

// Progress is emitted at most this often. Without throttling a fast walk floods the
// stream with one event per file, which is the noise the Python SSE endpoint used to send
// every second.
const progressEvery = 25

type server struct {
	gen.UnimplementedIndexerServer
}

func (s *server) Health(_ context.Context, _ *gen.HealthRequest) (*gen.HealthResponse, error) {
	var parsers []*gen.ParserInfo
	for lang, exts := range parse.Linked() {
		parsers = append(parsers, &gen.ParserInfo{Language: lang, Extensions: exts})
	}
	return &gen.HealthResponse{Ok: true, Version: version, Parsers: parsers}, nil
}

func (s *server) IndexRepo(req *gen.IndexRequest, stream gen.Indexer_IndexRepoServer) error {
	started := time.Now()

	root := req.GetRootPath()
	if root == "" {
		return sendFailed(stream, "root_path is required", "")
	}
	info, err := os.Stat(root)
	if err != nil || !info.IsDir() {
		// A missing checkout is the single most likely caller mistake, so it gets a
		// specific message rather than a generic failure.
		return sendFailed(stream, fmt.Sprintf("root_path is not a readable directory: %s", root), root)
	}

	batchSize := int(req.GetBatchSize())
	if batchSize <= 0 {
		batchSize = defaultBatchSize
	}

	if err := send(stream, &gen.IndexEvent{
		Event: &gen.IndexEvent_Progress{Progress: &gen.Progress{Stage: "walking", Percent: 0}},
	}); err != nil {
		return err
	}

	found, err := walk.Find(root, walk.Options{
		MaxFiles:      int(req.GetMaxFiles()),
		MaxFileSizeKB: int(req.GetMaxFileSizeKb()),
	})
	if err != nil {
		return sendFailed(stream, fmt.Sprintf("walk failed: %v", err), root)
	}

	total := len(found.Paths)
	if found.Truncated {
		// Say so rather than letting the caller assume full coverage.
		log.Printf("walk truncated at max_files=%d for %s", total, root)
	}

	var (
		batch         []*gen.Chunk
		parsed        int
		emitted       int
		withErrors    int
		skippedParses int
	)

	flush := func() error {
		if len(batch) == 0 {
			return nil
		}
		if err := send(stream, &gen.IndexEvent{
			Event: &gen.IndexEvent_Chunks{Chunks: &gen.ChunkBatch{Chunks: batch}},
		}); err != nil {
			return err
		}
		emitted += len(batch)
		batch = batch[:0]
		return nil
	}

	for i, rel := range found.Paths {
		// Honour client cancellation: without this, a cancelled request keeps parsing a
		// whole repository for a stream nobody is reading.
		if err := stream.Context().Err(); err != nil {
			return err
		}

		chunks, perr := parse.File(filepath.Join(root, rel), rel)
		if perr != nil {
			// One unreadable or unparseable file must not fail the whole index; the
			// Python caller falls back to raw indexing for these.
			skippedParses++
			continue
		}
		if len(chunks) > 0 {
			parsed++
			if chunks[0].HadParseError {
				withErrors++
			}
		}
		for _, c := range chunks {
			batch = append(batch, &gen.Chunk{
				FilePath: c.FilePath, Language: c.Language, ChunkType: c.ChunkType,
				Name: c.Name, Content: c.Content,
				StartLine: c.StartLine, EndLine: c.EndLine,
				HadParseError: c.HadParseError,
			})
			if len(batch) >= batchSize {
				if err := flush(); err != nil {
					return err
				}
			}
		}

		if i%progressEvery == 0 || i == total-1 {
			if err := send(stream, &gen.IndexEvent{
				Event: &gen.IndexEvent_Progress{Progress: &gen.Progress{
					Stage: "parsing", CurrentPath: rel,
					FilesProcessed: uint32(i + 1), TotalFiles: uint32(total),
					Percent: float64(i+1) / float64(max(total, 1)) * 100,
				}},
			}); err != nil {
				return err
			}
		}
	}

	if err := flush(); err != nil {
		return err
	}

	return send(stream, &gen.IndexEvent{
		Event: &gen.IndexEvent_Completed{Completed: &gen.Completed{
			FilesWalked:     uint32(total),
			FilesParsed:     uint32(parsed),
			FilesSkipped:    uint32(found.Skipped + skippedParses),
			ChunksEmitted:   uint32(emitted),
			FilesWithErrors: uint32(withErrors),
			DurationMs:      time.Since(started).Milliseconds(),
		}},
	})
}

func send(stream gen.Indexer_IndexRepoServer, ev *gen.IndexEvent) error {
	return stream.Send(ev)
}

func sendFailed(stream gen.Indexer_IndexRepoServer, msg, path string) error {
	// Delivered as a stream event rather than a gRPC error status so the caller sees it
	// in the same channel as progress, and a partially useful stream still terminates
	// cleanly.
	return send(stream, &gen.IndexEvent{
		Event: &gen.IndexEvent_Failed{Failed: &gen.Failed{Message: msg, Path: path}},
	})
}

func max(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func main() {
	addr := flag.String("addr", ":50051", "listen address")
	flag.Parse()

	lis, err := net.Listen("tcp", *addr)
	if err != nil {
		log.Fatalf("listen %s: %v", *addr, err)
	}

	grpcServer := grpc.NewServer()
	gen.RegisterIndexerServer(grpcServer, &server{})

	// Standard grpc health service, so a Kubernetes probe can use grpc_health_probe
	// rather than needing an HTTP sidecar.
	hs := health.NewServer()
	hs.SetServingStatus("", healthpb.HealthCheckResponse_SERVING)
	healthpb.RegisterHealthServer(grpcServer, hs)

	// Reflection so grpcurl works against a running instance without the .proto.
	reflection.Register(grpcServer)

	log.Printf("indexer %s listening on %s", version, *addr)
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("serve: %v", err)
	}
}
