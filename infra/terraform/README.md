# Infrastructure

Terraform for the one thing this project did not have: **a deployed API**.

`apps/web` has been live on Vercel, but `apps/web/src/lib/api-client.ts:1` reads

```ts
process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

and nothing ever set that variable, so the deployed frontend fell back to localhost and
could not reach a backend. `docker/docker-compose.yml` was the only deployment artifact
and it is a local-development file. This module provisions the host, the block volume
the app's state requires, and wires `NEXT_PUBLIC_API_URL` from the host's address —
so one stack's output feeds the other's input.

## What it creates

| Resource | Why | Cost |
|---|---|---|
| `digitalocean_droplet` | Runs `docker/docker-compose.yml` via cloud-init | ~$6/mo (`s-1vcpu-1gb`) |
| `digitalocean_volume` | SQLite DB + Chroma + cloned repos need a **real block device** | ~$1/mo (10GB) |
| `digitalocean_volume_attachment` | Attaches it | — |
| `digitalocean_firewall` | Opens 8000, restricts 22, **blocks 6379** | free |
| `digitalocean_project` | Groups the resources | free |
| `vercel_project_environment_variable` | Sets `NEXT_PUBLIC_API_URL` from the droplet IP | free |

Roughly **$7/month** at the defaults.

## Why DigitalOcean and not Fly

Fly is the better-known choice for this shape of app, and it was the original plan. Its
**Terraform provider is not maintained**:

| Provider | Latest | Published | Tier |
|---|---|---|---|
| `fly-apps/fly` | 0.0.23 | 2023-06-22 | partner, abandoned |
| `andrewbaxter/fly` (fork) | 0.1.18 | 2024-10-28 | community |
| `digitalocean/digitalocean` | 2.99.1 | 2026-08-06 | partner, 13.3M downloads |

Managing Fly through a provider stuck on 0.0.23 for three years would undermine the
point of using Terraform at all. A Droplet also gives a plain block device, which is
what SQLite and Chroma actually need — Azure Container Apps was rejected for the same
reason (no block-device volume type; only Azure Files over SMB/NFS, which is exactly the
configuration `sqlite.org/howtocorrupt.html` §2.1 warns about).

## Usage

```bash
cp example.tfvars secrets.tfvars     # then fill it in
terraform init
terraform plan  -var-file=secrets.tfvars
terraform apply -var-file=secrets.tfvars
```

Then, in order:

1. **Wait ~3–5 min.** cloud-init installs Docker and builds the images.
   ```bash
   ssh root@$(terraform output -raw api_ipv4) 'tail -f /var/log/cloud-init-output.log'
   curl "$(terraform output -raw health_url)"
   ```
2. **Redeploy the frontend.** `NEXT_PUBLIC_API_URL` is inlined by Next at *build* time,
   so setting the Vercel variable does not affect the existing production build.
3. **Add TLS before expecting the browser to work** — see below.

## Known limitations, stated rather than discovered later

- **Plain HTTP.** The droplet serves `http://IP:8000`. A browser on an `https://`
  Vercel page will block that as mixed content, so `curl` will work while the site does
  not. Finishing properly means pointing a domain at the droplet, terminating TLS
  (Caddy, or nginx + certbot), and setting `NEXT_PUBLIC_API_URL` to the `https://` name.
- **Single instance, and it must stay that way.** `apps/api/src/main.py` runs
  `init_db` + `run_pending_migrations` unguarded on every startup, and Chroma holds a
  process-local client. Two replicas would race the `ALTER TABLE`s. Nothing here
  autoscales, and that is deliberate.
- **Local state, single operator.** No remote backend, no locking, no workspaces. Fine
  for one person; not a team setup, and not claimed as one.
- **`terraform.tfstate` holds every secret in plaintext.** `sensitive = true` only
  redacts CLI output. `.gitignore` in this directory covers state, tfvars and plan
  files — check it is in place before your first `apply`.
- **cloud-init runs once.** Editing `cloud-init.yaml.tftpl` shows a `user_data` diff but
  changes nothing on a running droplet; it must be replaced. To redeploy the app instead,
  `ssh` in and run `/usr/local/bin/codebaseqa-up`.
- **Not applied.** This configuration is `terraform validate`-clean against
  digitalocean 2.99.1 and vercel 5.10.0, but it has never been run against real
  accounts — no `plan` or `apply` has executed, because that requires live credentials
  and creates billable resources.

## Redis exposure

`docker/docker-compose.yml` publishes Redis on `6379` for local development. On a
public droplet that would be an unauthenticated Redis facing the internet. Two
independent controls prevent it: the DO firewall has no inbound rule for 6379, and
`ufw` on the host allows only 22 and 8000. The API reaches Redis over the compose
network, which is unaffected.
