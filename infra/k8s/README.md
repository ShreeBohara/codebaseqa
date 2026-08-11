# Kubernetes

Manifests for the API, validated on [kind](https://kind.sigs.k8s.io/). Everything below
was actually run — the pod reaches `1/1 Running`, serves traffic on a NodePort, and its
volume survives pod deletion.

## What this does and does not give you

Of the capabilities kubernetes.io lists, this workload can genuinely use two: **storage
orchestration** and **self-healing restarts**.

It does **not** give you horizontal scaling, and the manifests say `replicas: 1` on
purpose. Two reasons, both properties of the application rather than of these files:

1. **SQLite.** `DATABASE_URL` is a file on the volume. A `ReadWriteOnce` PVC attaches to
   one node, and concurrent writers to a single SQLite file are the configuration
   `sqlite.org/howtocorrupt.html` warns about.
2. **ChromaDB is embedded.** `chroma_store.py` holds a process-local persistent client
   over the same directory, so two pods would be two independent writers to one on-disk
   index.

Startup *is* now safe to run concurrently — the `ALTER TABLE` migrations were changed from
check-then-act to idempotent, so a second replica no longer dies on `duplicate column
name`. But safe startup is not safe operation. Scaling past 1 means moving to Postgres and
a server-mode vector store.

Writing these manifests is what surfaced both constraints, plus two real bugs (see below).

## Run it

```bash
kind create cluster --config infra/k8s/kind-cluster.yaml
docker build -f docker/Dockerfile.api -t codebaseqa-api:kind .
kind load docker-image codebaseqa-api:kind --name codebaseqa

# Real credentials out of band, so they never enter git:
kubectl create secret generic codebaseqa-secrets \
  --from-literal=OPENAI_API_KEY=sk-... \
  --from-literal=GITHUB_TOKEN=

kubectl apply -k infra/k8s/
kubectl rollout status statefulset/codebaseqa-api
curl http://localhost:30080/api/platform/config
```

`secret.yaml` is a **template with empty values**. It exists so `kubectl kustomize`
resolves in a bare cluster; do not put real keys in it.

## Decisions worth knowing

**`imagePullPolicy: Never`.** The image is built locally and side-loaded with `kind load`.
With `IfNotPresent` or `Always`, the kubelet would try a registry and fail on a tag that
only exists in the node's containerd.

**The readiness probe is not `/api/health`.** That endpoint reports `degraded` whenever
*any* dependency is unreachable, including the LLM provider — a third party. Gating
readiness on it would pull the pod out of service because OpenAI had a bad minute, and in
a cluster with no key it would never become ready at all. Readiness instead hits
`/api/platform/config`, which touches only the local database, and answers the question
the kubelet actually needs: is this process serving HTTP?

**`fsGroup: 10001`.** This is what makes the mounted PVC writable by the non-root user —
the kubelet chowns the volume to that GID. Without it the pod starts and then fails on the
first SQLite write, which is a much worse failure than not starting.

**`runAsNonRoot: true`.** The image now creates uid 10001 and sets `USER`. This makes the
kubelet refuse the pod if that ever regresses.

**Not deployed here:** Redis and Neo4j. The ConfigMap disables both, and the in-memory
fallbacks cover them. Add them as their own StatefulSets if you want them in-cluster.

**kind, not AKS.** kind is a Kubernetes SIG project and costs nothing. AKS's cheapest sane
node (`Standard_B2s`) is roughly $30/month to run something pinned to one replica.

## Two bugs this found

Neither was visible from reading the code, and neither would have been caught by the test
suite.

**The image ran as root.** Confirmed by inspecting the built image (`id -u` → 0). Under
docker-compose that meant root-owned files in the developer's working tree via the
`../data` bind mount; in Kubernetes it made `runAsNonRoot` unsatisfiable. Fixed in
`docker/Dockerfile.api`.

**The API could not start without a provider key.** The pod went into
`CrashLoopBackOff` with `openai.OpenAIError: Missing credentials`, because the lifespan
builds the vector store eagerly and the OpenAI SDK raises at *construction*, not first
use. Three consequences: the pod crash-loops instead of reporting itself unhealthy, you
cannot deploy first and add credentials afterwards, and `/api/health` can never report
`llm_provider unreachable` because the process never boots far enough to serve it. Vector
store initialization is now non-fatal — endpoints that need embeddings still fail
per-request with a clear error, and the rest keep working:

```json
{ "status": "degraded",
  "checks": { "database": "ok",
              "vector_store": "error: Missing credentials...",
              "llm_provider": "error: Missing credentials..." } }
```

## Verified

| Check | Result |
|---|---|
| `kubectl kustomize` | 5 resources render |
| Rollout | `codebaseqa-api-0  1/1  Running  0 restarts` |
| NodePort from host | `curl localhost:30080/api/platform/config` returns JSON |
| `/health` with no key | `degraded` with a specific reason, process stays up |
| Migrations at startup | applied, including `ix_code_dependencies_repo` |
| PVC | `Bound`, 5Gi, RWO |
| Non-root write | uid 10001 writes `/app/data` via `fsGroup` |
| Persistence | marker file and `codebaseqa.db` survive `kubectl delete pod` |
| Concurrent startup | 6 simultaneous migration runs, 0 failures |

## Not verified

The web frontend is not deployed here — these manifests cover the API only. Nothing has
been run on a managed cluster (AKS/EKS/GKE); a cloud `StorageClass` and `LoadBalancer`
would replace kind's `standard` class and the NodePort.
