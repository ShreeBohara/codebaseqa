# Medium Launch Pack (CodebaseQA)

This folder contains a complete, execution-ready package for publishing your first Medium launch article for CodebaseQA.

## What's Included

- `ARTICLE_DRAFT.md`: flagship article draft (target 1,600-2,000 words)
- `INPUTS_REQUIRED.md`: exact details to fill before final publish
- `MEDIUM_METADATA.md`: title/subtitle/slug/topics/paywall (paste-ready)
- `ASSET_MANIFEST.md`: image/video/GIF inventory with alt text
- `PUBLISHING_CHECKLIST.md`: preflight, QA, Medium settings, and distribution checklist
- `STEP_BY_STEP_PUBLISH.md`: exact beginner-friendly publish steps (terminal + Medium UI)
- `METRICS_TRACKER.md`: 24h and 7d launch KPI tracker
- `MEDIA_CAPTURE_GUIDE.md`: detailed screenshot/video/GIF capture instructions
- `SECURITY_PRELAUNCH.md`: key rotation and secret-hygiene checklist
- `diagrams/`: architecture and deployment visuals (PNG + Mermaid sources)
- `tools/`: link checker and secret preflight scripts

## Fast Start

1. Fill placeholders in `INPUTS_REQUIRED.md`.
2. Update placeholders in `ARTICLE_DRAFT.md`.
3. Run preflight checks:

```bash
bash docs/launch/medium/tools/secret_preflight.sh
bash docs/launch/medium/tools/link_check.sh docs/launch/medium/ARTICLE_DRAFT.md
```

4. Upload images from `docs/launch/medium/diagrams/` and `docs/media/screenshots/` into Medium.
5. Walk through `PUBLISHING_CHECKLIST.md` top-to-bottom.

## Non-Negotiables Before Publish

- Rotate any compromised API keys.
- Never show `.env` values in screenshots/video.
- Keep article scope aligned to `docs/releases/v1.0.0.md`.
- Include known limitations for accuracy and trust.
