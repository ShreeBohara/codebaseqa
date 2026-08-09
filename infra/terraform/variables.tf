variable "digitalocean_token" {
  description = "DigitalOcean API token with read/write scope. Set via TF_VAR_digitalocean_token or DIGITALOCEAN_TOKEN."
  type        = string
  sensitive   = true
}

variable "vercel_api_token" {
  description = "Vercel API token, used only to set the frontend's NEXT_PUBLIC_API_URL."
  type        = string
  sensitive   = true
}

variable "vercel_team_id" {
  description = "Vercel team id. Leave null for a personal account."
  type        = string
  default     = null
}

variable "vercel_project_name" {
  description = "Name of the existing Vercel project serving apps/web."
  type        = string
  default     = "codebaseqa-web"
}

variable "name" {
  description = "Name prefix for created resources."
  type        = string
  default     = "codebaseqa"
}

variable "region" {
  description = "DigitalOcean region slug. Must be one that supports block storage volumes."
  type        = string
  default     = "nyc3"
}

variable "droplet_size" {
  description = <<-EOT
    Droplet slug. s-1vcpu-1gb (~$6/mo) is enough to serve the API, but indexing is
    CPU-bound and single-threaded per repo, so s-2vcpu-2gb (~$18/mo) is noticeably
    better if you index anything large. Chroma plus the API sit around 400-600MB.
  EOT
  type        = string
  default     = "s-1vcpu-1gb"
}

variable "volume_size_gb" {
  description = <<-EOT
    Block volume for /mnt/codebaseqa-data. Holds the SQLite database, the Chroma
    directory and every cloned repository -- clones dominate. 10GB (~$1/mo) is a
    reasonable start; a single large monorepo clone can be 1-2GB.
  EOT
  type        = number
  default     = 10
}

variable "ssh_key_fingerprints" {
  description = <<-EOT
    Fingerprints of DigitalOcean SSH keys to install on the droplet. Get them with
    `doctl compute ssh-key list`. Without at least one you cannot reach the box, since
    password auth is disabled below.
  EOT
  type        = list(string)
}

variable "ssh_allowed_cidrs" {
  description = <<-EOT
    Who may reach port 22. Defaults to nothing -- set your own address explicitly,
    e.g. ["203.0.113.4/32"]. Deliberately not 0.0.0.0/0.
  EOT
  type        = list(string)
  default     = []
}

variable "git_repo_url" {
  description = "Repository cloned onto the droplet by cloud-init to obtain docker-compose.yml."
  type        = string
  default     = "https://github.com/ShreeBohara/codebaseqa.git"
}

variable "git_ref" {
  description = "Branch or tag to deploy."
  type        = string
  default     = "main"
}

# --- application configuration -------------------------------------------------
# These are written to docker/.env on the droplet, which is where compose reads
# ${VAR} interpolation from.

variable "llm_provider" {
  description = "openai | azure_openai | anthropic | ollama"
  type        = string
  default     = "openai"
}

variable "embedding_provider" {
  description = "openai | azure_openai | ollama"
  type        = string
  default     = "openai"
}

variable "openai_api_key" {
  description = "Required when llm_provider or embedding_provider is openai."
  type        = string
  default     = ""
  sensitive   = true
}

variable "azure_openai_endpoint" {
  description = "e.g. https://my-resource.openai.azure.com"
  type        = string
  default     = ""
}

variable "azure_openai_api_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "azure_openai_deployment" {
  description = "Azure chat deployment name (Azure sends this where a model id normally goes)."
  type        = string
  default     = ""
}

variable "azure_openai_embedding_deployment" {
  type    = string
  default = ""
}

variable "github_token" {
  description = "Optional. Required only to clone private repositories."
  type        = string
  default     = ""
  sensitive   = true
}

variable "demo_mode" {
  description = "Pin the deployment to a single featured repository."
  type        = bool
  default     = true
}
