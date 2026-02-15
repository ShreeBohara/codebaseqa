# Security Prelaunch Guide (Before Publishing)

## 1) Rotate Potentially Exposed Keys

If any API key has ever appeared in local files, screenshots, terminal logs, or chat history, treat it as compromised.

Minimum actions:

1. Create a new provider key (OpenAI/Anthropic/etc.).
2. Update your runtime environment with the new key.
3. Revoke the old key.
4. Re-test app health endpoints.

## 2) Validate Ignore Rules

Current `.gitignore` should include:

- `.env`
- `.env.local`
- `.env.*.local`

Confirm with:

```bash
rg -n "^\\.env|^\\.env\\.local|^\\.env\\.\\*\\.local" .gitignore
```

## 3) Scan Workspace for Secret Patterns

Run:

```bash
bash docs/launch/medium/tools/secret_preflight.sh
```

If scan fails, fix and rerun until it passes.

## 4) Capture Hygiene

- Do not record terminal sessions containing env exports.
- Do not show deployment dashboards with secret values.
- Do not paste secret values into Medium drafts.

## 5) Final Gate

Publish only if:

- secret scan passes
- links resolve
- no sensitive data appears in images/video/text

