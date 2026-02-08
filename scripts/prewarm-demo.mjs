const API_URL = process.env.PREWARM_API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const MAX_WAIT_MS = Number.parseInt(process.env.PREWARM_MAX_WAIT_MS || '180000', 10);
const POLL_MS = 3000;

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  const text = await res.text();
  let payload;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { raw: text };
  }

  if (!res.ok) {
    const detail = payload?.detail?.message || payload?.detail || payload?.raw || res.statusText;
    throw new Error(`${res.status} ${detail}`);
  }

  return payload;
}

async function ensureDemoRepoId() {
  const startedAt = Date.now();

  try {
    await fetchJson(`${API_URL}/api/repos/demo/seed`, { method: 'POST' });
  } catch (error) {
    console.warn(`[prewarm] seed request returned warning: ${error.message}`);
  }

  while (Date.now() - startedAt < MAX_WAIT_MS) {
    const platform = await fetchJson(`${API_URL}/api/platform/config`);
    if (platform.demo_repo_id) {
      const repo = await fetchJson(`${API_URL}/api/repos/${platform.demo_repo_id}`);
      if (repo.status === 'completed') {
        return platform.demo_repo_id;
      }
      console.log(`[prewarm] waiting for demo repo indexing (${repo.status})...`);
    } else {
      console.log('[prewarm] waiting for demo repo id...');
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_MS));
  }

  throw new Error(`Timed out waiting for demo repo readiness after ${MAX_WAIT_MS}ms`);
}

async function prewarmChat(repoId) {
  const session = await fetchJson(`${API_URL}/api/chat/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_id: repoId }),
  });

  const res = await fetch(`${API_URL}/api/chat/sessions/${session.id}/messages`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: 'Give a concise architecture overview of this repository.' }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`chat prewarm failed: ${res.status} ${text}`);
  }

  const reader = res.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let done = false;
  while (!done) {
    const chunk = await reader.read();
    done = chunk.done;
    decoder.decode(chunk.value || new Uint8Array(), { stream: !done });
  }
}

async function run() {
  console.log(`[prewarm] using API ${API_URL}`);

  const repoId = await ensureDemoRepoId();
  console.log(`[prewarm] demo repository ready: ${repoId}`);

  await fetchJson(`${API_URL}/api/learning/${repoId}/curriculum`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ persona: 'new_hire' }),
  });
  console.log('[prewarm] curriculum generated');

  await fetchJson(`${API_URL}/api/learning/${repoId}/graph`);
  console.log('[prewarm] dependency graph generated');

  await prewarmChat(repoId);
  console.log('[prewarm] chat response generated');

  console.log('[prewarm] done');
}

run().catch((error) => {
  console.error('[prewarm] failed:', error.message);
  process.exit(1);
});
