# Medium Publishing Checklist (Launch-Critical)

## 1) Security Preflight

- [ ] Rotate any compromised API keys before writing/publishing.
- [ ] Confirm `.env` files are gitignored (`.env`, `.env.local`, `.env.*.local`).
- [ ] Remove secrets from any local notes/screenshots/video captures.
- [ ] Run:

```bash
bash docs/launch/medium/tools/secret_preflight.sh
```

## 2) Scope and Accuracy

- [ ] Freeze content to v1.0.0 scope from `docs/releases/v1.0.0.md`.
- [ ] Keep claims measurable and evidence-backed.
- [ ] Include "Known limitations" section.
- [ ] Ensure no feature claims exceed current shipped behavior.

## 3) Link Health and Runtime Checks

- [ ] Verify Vercel frontend URL is live.
- [ ] Verify Render backend health endpoint responds.
- [ ] Verify API docs URL works.
- [ ] Verify GitHub repo/docs/issues links.
- [ ] Run:

```bash
bash docs/launch/medium/tools/link_check.sh docs/launch/medium/ARTICLE_DRAFT.md
```

## 4) Article Quality

- [ ] Title and subtitle are outcome-focused and specific.
- [ ] Article length is in 1,600-2,000 word target.
- [ ] Every major claim has a screenshot/diagram/proof point.
- [ ] One short CLI code block only (avoid excessive code).
- [ ] Deployment vs local comparison table included.
- [ ] CTA includes live links.

## 5) Accessibility and Media

- [ ] Every image has meaningful alt text.
- [ ] Demo video is captioned or has transcript support.
- [ ] Mobile readability pass completed in Medium preview.
- [ ] Large GIFs replaced with embed video where possible.

## 6) Medium Settings

- [ ] Featured image selected from article visuals.
- [ ] Up to 5 relevant topics selected.
- [ ] Custom story link set.
- [ ] Paywall set intentionally (free recommended for launch).
- [ ] Canonical URL set only if cross-posting.

## 7) Post-Publish Distribution

- [ ] Post on LinkedIn with one problem/outcome hook.
- [ ] Post on X with short thread or summary.
- [ ] Add Medium link to GitHub profile and README launch section.
- [ ] Share in 1-2 relevant dev communities.
- [ ] Monitor 24h and 7d metrics in `METRICS_TRACKER.md`.

