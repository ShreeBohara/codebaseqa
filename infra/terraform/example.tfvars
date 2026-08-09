# Copy to secrets.tfvars (gitignored) and fill in.
#   terraform plan  -var-file=secrets.tfvars
#
# Everything marked sensitive still lands in terraform.tfstate in PLAINTEXT.
# `sensitive` only hides values from CLI output. Keep state off git.

digitalocean_token = "dop_v1_..."
vercel_api_token   = "..."
# vercel_team_id   = "team_..."   # omit for a personal account

# From `doctl compute ssh-key list`. Without this you cannot reach the droplet.
ssh_key_fingerprints = ["aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99"]

# Your own address. Deliberately not 0.0.0.0/0.
ssh_allowed_cidrs = ["203.0.113.4/32"]

# --- application ---
openai_api_key = "sk-..."
# github_token = "ghp_..."        # only needed for private repositories

# Or Azure instead of public OpenAI:
# llm_provider                      = "azure_openai"
# embedding_provider                = "azure_openai"
# azure_openai_endpoint             = "https://my-resource.openai.azure.com"
# azure_openai_api_key              = "..."
# azure_openai_deployment           = "my-gpt4o-deployment"
# azure_openai_embedding_deployment = "my-embedding-deployment"

# --- sizing ---
# droplet_size   = "s-1vcpu-1gb"   # ~$6/mo; s-2vcpu-2gb (~$18) if you index large repos
# volume_size_gb = 10              # ~$1/mo; clones dominate usage
# region         = "nyc3"
