const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Types
export interface Repository {
  id: string;
  github_url: string;
  github_owner: string;
  github_name: string;
  status: 'pending' | 'cloning' | 'parsing' | 'embedding' | 'completed' | 'failed';
  description?: string;
  primary_language?: string;
  languages: string[];
  total_files: number;
  total_chunks: number;
  last_indexed_at?: string;
  created_at: string;
}

export interface ChatSession {
  id: string;
  repo_id: string;
  title?: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  retrieved_chunks?: Array<{ id: string; file: string }>;
  created_at: string;
}

export interface StreamingChunk {
  type: 'content' | 'sources' | 'done' | 'error';
  content?: string;
  sources?: Array<{
    file: string;
    content: string;
    start_line: number;
    end_line: number;
    score: number;
  }>;
  error?: string;
}

export interface SearchResult {
  chunk_id: string;
  file_path: string;
  content: string;
  chunk_type: string;
  score: number;
  start_line: number;
  end_line: number;
}

// API Client
class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_URL;
  }

  // Repository endpoints
  async createRepo(githubUrl: string, branch?: string): Promise<Repository> {
    const res = await fetch(`${this.baseUrl}/api/repos/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ github_url: githubUrl, branch }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async listRepos(): Promise<{ repositories: Repository[]; total: number }> {
    const res = await fetch(`${this.baseUrl}/api/repos/`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async getRepo(repoId: string): Promise<Repository> {
    const res = await fetch(`${this.baseUrl}/api/repos/${repoId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async deleteRepo(repoId: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/repos/${repoId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(await res.text());
  }

  // Chat endpoints
  async createSession(repoId: string): Promise<{ id: string }> {
    const res = await fetch(`${this.baseUrl}/api/chat/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_id: repoId }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async getSession(sessionId: string): Promise<ChatSession> {
    const res = await fetch(`${this.baseUrl}/api/chat/sessions/${sessionId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async *streamChat(sessionId: string, content: string): AsyncGenerator<StreamingChunk> {
    const res = await fetch(`${this.baseUrl}/api/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

    const reader = res.body?.getReader();
    const decoder = new TextDecoder();

    if (!reader) {
      throw new Error('No response body');
    }

    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            yield data as StreamingChunk;
          } catch {
            // Skip invalid JSON
          }
        }
      }
    }
  }

  // Search endpoint
  async search(repoId: string, query: string, limit = 10): Promise<{ results: SearchResult[] }> {
    const res = await fetch(`${this.baseUrl}/api/search/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_id: repoId, query, limit }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
}

export const api = new ApiClient();
