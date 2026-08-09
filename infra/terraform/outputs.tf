output "api_ipv4" {
  description = "Public IPv4 of the API droplet."
  value       = digitalocean_droplet.api.ipv4_address
}

output "api_url" {
  description = "Base URL of the API. This is the value written to Vercel's NEXT_PUBLIC_API_URL."
  value       = "http://${digitalocean_droplet.api.ipv4_address}:8000"
}

output "health_url" {
  description = "Check this first after apply; it reports database, vector store, LLM provider and GitHub API status."
  value       = "http://${digitalocean_droplet.api.ipv4_address}:8000/health"
}

output "ssh_command" {
  description = "Only works if ssh_allowed_cidrs includes your address."
  value       = "ssh root@${digitalocean_droplet.api.ipv4_address}"
}

output "data_volume" {
  description = "Block volume holding the SQLite database, Chroma store and clones."
  value = {
    name    = digitalocean_volume.data.name
    size_gb = digitalocean_volume.data.size
    mount   = local.data_mount
  }
}

output "next_steps" {
  description = "Manual follow-up that Terraform deliberately does not do."
  value       = <<-EOT
    1. cloud-init takes ~3-5 minutes after apply (docker install + image build).
       Watch it:  ssh root@${digitalocean_droplet.api.ipv4_address} 'tail -f /var/log/cloud-init-output.log'
       Then:      curl http://${digitalocean_droplet.api.ipv4_address}:8000/health

    2. REDEPLOY THE FRONTEND. NEXT_PUBLIC_API_URL is inlined by Next at build time,
       so setting the Vercel variable is not enough on its own -- the existing
       production build still has the old value baked in. Trigger a redeploy.

    3. This serves plain HTTP. The browser calling it from an https:// Vercel page will
       be blocked as mixed content. To finish properly: point a domain at the droplet
       and terminate TLS (caddy or nginx + certbot), then set NEXT_PUBLIC_API_URL to
       the https:// name. Until then, expect the frontend to fail in the browser even
       though curl works.
  EOT
}
