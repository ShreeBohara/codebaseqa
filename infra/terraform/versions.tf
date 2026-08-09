terraform {
  required_version = ">= 1.6.0"

  required_providers {
    # Pinned deliberately. Both of these ship multiple releases per month, and an
    # unpinned provider means `terraform init` on a different day can produce a
    # different plan for identical code.
    #
    # Provider choice note: the obvious host here was Fly.io, but its Terraform
    # provider is not maintained -- fly-apps/fly is still 0.0.23, last published
    # 2023-06-22, and the community fork (andrewbaxter/fly) last shipped 2024-10-28.
    # digitalocean/digitalocean is a partner provider with ~13M downloads that was
    # updated within the last week, and a Droplet gives a real block device, which
    # SQLite and Chroma both require.
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.99"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "~> 5.10"
    }
  }
}

provider "digitalocean" {
  # Reads DIGITALOCEAN_TOKEN from the environment. Never put the token in a .tf file.
  token = var.digitalocean_token
}

provider "vercel" {
  # Reads VERCEL_API_TOKEN from the environment.
  api_token = var.vercel_api_token
  team      = var.vercel_team_id
}
