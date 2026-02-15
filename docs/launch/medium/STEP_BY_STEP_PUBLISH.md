# Step-by-Step: Publish Your Medium Article (No Guesswork)

Follow this exactly from your terminal + Medium editor.

## Step 0) Open the right folder

1. Open terminal.
2. Run:

```bash
cd /Users/shree/Desktop/codebaseqa
```

3. Confirm files exist:

```bash
ls /Users/shree/Desktop/codebaseqa/docs/launch/medium
```

You should see `ARTICLE_DRAFT.md`, `MEDIUM_METADATA.md`, and `PUBLISHING_CHECKLIST.md`.

## Step 1) Quick safety checks (2 commands)

Run:

```bash
bash /Users/shree/Desktop/codebaseqa/docs/launch/medium/tools/secret_preflight.sh
bash /Users/shree/Desktop/codebaseqa/docs/launch/medium/tools/link_check.sh /Users/shree/Desktop/codebaseqa/docs/launch/medium/ARTICLE_DRAFT.md
```

What success looks like:

- Secret script says `Secret preflight passed.`
- Link script returns `OK HTTP ...` for links (or tells you exactly which link failed)

If a link fails, fix it in:

`/Users/shree/Desktop/codebaseqa/docs/launch/medium/ARTICLE_DRAFT.md`

## Step 2) Open the draft and metadata

Open these files side by side:

- `/Users/shree/Desktop/codebaseqa/docs/launch/medium/ARTICLE_DRAFT.md`
- `/Users/shree/Desktop/codebaseqa/docs/launch/medium/MEDIUM_METADATA.md`

You will copy from these into Medium.

## Step 3) Open Medium and start a new story

1. Go to [https://medium.com/new-story](https://medium.com/new-story)
2. Paste the title from `MEDIUM_METADATA.md`.
3. Paste the subtitle from `MEDIUM_METADATA.md`.
4. Paste article body from `ARTICLE_DRAFT.md`.

## Step 4) Add images in correct order

In Medium, replace local image links by uploading files directly.

Use this order:

1. `/Users/shree/Desktop/codebaseqa/docs/launch/medium/diagrams/hero-cover.png`
2. `/Users/shree/Desktop/codebaseqa/docs/media/screenshots/02_RepoPage.png`
3. `/Users/shree/Desktop/codebaseqa/docs/media/screenshots/03_ChatPage.png`
4. `/Users/shree/Desktop/codebaseqa/docs/launch/medium/diagrams/architecture-container.png`
5. `/Users/shree/Desktop/codebaseqa/docs/media/screenshots/04_AuthChat.png`
6. `/Users/shree/Desktop/codebaseqa/docs/media/screenshots/07_LearnPage.png`
7. `/Users/shree/Desktop/codebaseqa/docs/media/screenshots/08_FullStackTrackl.png`
8. `/Users/shree/Desktop/codebaseqa/docs/media/screenshots/09_InsideLearn.png`
9. `/Users/shree/Desktop/codebaseqa/docs/media/screenshots/05_Graph.png`
10. `/Users/shree/Desktop/codebaseqa/docs/media/screenshots/06_grpahDepth.png`
11. `/Users/shree/Desktop/codebaseqa/docs/launch/medium/diagrams/deployment-vs-local.png`
12. `/Users/shree/Desktop/codebaseqa/docs/launch/medium/diagrams/cta-card.png`

## Step 5) Embed your demo video

1. In Medium editor, add a new line under "60-90 Second Demo".
2. Paste only this URL:

`https://www.youtube.com/watch?v=nM8-2t4xr9A`

3. Wait 2-3 seconds for embed preview.

## Step 6) Configure publish settings (important)

Click `Publish` -> `Schedule/Publish settings` and set:

1. Topics (exactly these 5):
   - Software Engineering
   - Artificial Intelligence
   - Open Source
   - Developer Tools
   - Programming
2. Story slug:
   - `how-i-built-codebaseqa-to-cut-codebase-onboarding-time`
3. Paywall:
   - `No paywall / Public`
4. Canonical:
   - leave empty (unless cross-posting)
5. Featured image:
   - use the uploaded `hero-cover.png`

## Step 7) Final QA before pressing Publish

Use this mini pass:

1. Confirm links open:
   - `https://codebaseqa-web.vercel.app/`
   - `https://codebaseqa-api.onrender.com/docs`
   - `https://codebaseqa-api.onrender.com/health`
   - `https://github.com/ShreeBohara/codebaseqa`
2. Confirm no placeholder text remains (`PASTE_...` should not exist).
3. Preview on mobile in Medium preview mode.
4. Confirm all images render and are readable.

## Step 8) Publish

1. Click `Publish now`.
2. Copy the final Medium URL.
3. Paste it into:

`/Users/shree/Desktop/codebaseqa/docs/launch/medium/METRICS_TRACKER.md`

## Step 9) Post-launch (same day)

1. Use copy from:
   - `/Users/shree/Desktop/codebaseqa/docs/launch/medium/DISTRIBUTION_COPY.md`
2. Post on LinkedIn and X.
3. Add Medium link to GitHub README/profile.
4. Track 24h metrics in `METRICS_TRACKER.md`.

## If You Get Stuck

- Content questions: edit `ARTICLE_DRAFT.md`
- Metadata questions: check `MEDIUM_METADATA.md`
- Missing image: see `ASSET_MANIFEST.md`
- Safety checks: run scripts in `tools/`
