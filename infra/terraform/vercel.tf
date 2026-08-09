# The whole point of this file: apps/web/src/lib/api-client.ts:1 reads
#
#     process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
#
# and Next inlines that at BUILD time. So the Vercel-deployed frontend was falling back
# to localhost and could never reach a backend. Setting the variable here, from the
# droplet's address, is what actually connects the two halves of the system.
#
# Because it is inlined at build time, changing it requires a redeploy -- setting the
# variable alone is not enough. See the note in outputs.tf.

data "vercel_project" "web" {
  name = var.vercel_project_name
}

resource "vercel_project_environment_variable" "api_url" {
  project_id = data.vercel_project.web.id
  key        = "NEXT_PUBLIC_API_URL"
  value      = "http://${digitalocean_droplet.api.ipv4_address}:8000"
  target     = ["production", "preview"]
  # Explicitly not sensitive: NEXT_PUBLIC_* is inlined into the client bundle by Next,
  # so it is public by construction. Marking it sensitive would imply otherwise.
  sensitive = false
}
