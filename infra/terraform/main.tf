locals {
  data_mount = "/mnt/${var.name}-data"

  # The API talks to Redis over the compose network, so Redis is NOT published to the
  # internet (see the firewall below). This mirrors docker-compose.yml, where redis is
  # only reachable from the api service.
  app_env = merge(
    {
      LLM_PROVIDER       = var.llm_provider
      EMBEDDING_PROVIDER = var.embedding_provider
      DEMO_MODE          = var.demo_mode ? "true" : "false"
      SEED_DEMO          = var.demo_mode ? "true" : "false"
      # Compose bind-mounts ../data, so the app's relative paths resolve inside the
      # volume once the repo is checked out under the mount point.
      DATABASE_URL = "sqlite:///./data/codebaseqa.db"
      REDIS_URL    = "redis://redis:6379/0"
    },
    var.openai_api_key == "" ? {} : { OPENAI_API_KEY = var.openai_api_key },
    var.github_token == "" ? {} : { GITHUB_TOKEN = var.github_token },
    var.azure_openai_endpoint == "" ? {} : {
      AZURE_OPENAI_ENDPOINT             = var.azure_openai_endpoint
      AZURE_OPENAI_API_KEY              = var.azure_openai_api_key
      AZURE_OPENAI_DEPLOYMENT           = var.azure_openai_deployment
      AZURE_OPENAI_EMBEDDING_DEPLOYMENT = var.azure_openai_embedding_deployment
    },
  )
}

# Block storage for everything stateful. Separate from the droplet on purpose: the
# droplet can be destroyed and recreated without losing the index, and SQLite plus
# Chroma both need a real block device rather than a network filesystem.
resource "digitalocean_volume" "data" {
  name                    = "${var.name}-data"
  region                  = var.region
  size                    = var.volume_size_gb
  initial_filesystem_type = "ext4"
  description             = "SQLite database, Chroma vector store and cloned repositories"
}

resource "digitalocean_droplet" "api" {
  name     = "${var.name}-api"
  region   = var.region
  size     = var.droplet_size
  image    = "ubuntu-24-04-x64"
  ssh_keys = var.ssh_key_fingerprints

  monitoring = true
  ipv6       = true

  user_data = templatefile("${path.module}/cloud-init.yaml.tftpl", {
    repo_url    = var.git_repo_url
    git_ref     = var.git_ref
    data_mount  = local.data_mount
    volume_name = digitalocean_volume.data.name
    app_env     = local.app_env
  })

  tags = [var.name, "api"]

  lifecycle {
    # user_data is only read at first boot, so a change here would silently do nothing
    # unless the droplet is replaced. Making that explicit rather than surprising.
    create_before_destroy = false
  }
}

resource "digitalocean_volume_attachment" "data" {
  droplet_id = digitalocean_droplet.api.id
  volume_id  = digitalocean_volume.data.id
}

resource "digitalocean_firewall" "api" {
  name        = "${var.name}-api"
  droplet_ids = [digitalocean_droplet.api.id]

  # HTTP: the API itself.
  inbound_rule {
    protocol         = "tcp"
    port_range       = "8000"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  # SSH, restricted. Empty by default so this is a deliberate decision, not a leftover.
  dynamic "inbound_rule" {
    for_each = length(var.ssh_allowed_cidrs) > 0 ? [1] : []
    content {
      protocol         = "tcp"
      port_range       = "22"
      source_addresses = var.ssh_allowed_cidrs
    }
  }

  # Note there is deliberately no rule for 6379. docker-compose.yml publishes Redis on
  # the host, which on a public droplet would expose an unauthenticated Redis to the
  # internet; the firewall blocks it, and cloud-init also removes the port mapping.

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

resource "digitalocean_project" "codebaseqa" {
  name        = var.name
  description = "AI-powered codebase understanding and Q&A"
  purpose     = "Web Application"
  environment = "Production"

  resources = [
    digitalocean_droplet.api.urn,
    digitalocean_volume.data.urn,
  ]
}
