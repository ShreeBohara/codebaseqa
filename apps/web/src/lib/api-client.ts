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

// Learning Types
export interface Persona {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface Lesson {
  id: string;
  title: string;
  description: string;
  type: 'concept' | 'code_tour' | 'quiz';
  estimated_minutes: number;
}

export interface Module {
  title: string;
  description: string;
  lessons: Lesson[];
}

export interface Syllabus {
  repo_id: string;
  persona: string;
  title: string;
  description: string;
  modules: Module[];
}

export interface CodeReference {
  file_path: string;
  start_line: number;
  end_line: number;
  content?: string;
  description: string;
}

export interface LessonContent {
  id: string;
  title: string;
  content_markdown: string;
  code_references: CodeReference[];
  diagram_mermaid?: string;
}

export interface CodeTour {
  title: string;
  steps: Array<{
    file: string;
    line: number;
    description: string;
    title?: string;
  }>;
}

// API Client
// Quiz Types
export interface Question {
  id: string;
  text: string;
  options: string[];
  correct_option_index: number;
  explanation: string;
}

export interface Quiz {
  lesson_id: string;
  questions: Question[];
}

// Gamification Types
export interface LevelInfo {
  level: number;
  title: string;
  icon: string;
  current_xp: number;
  xp_for_next_level: number;
  xp_progress: number;
}

export interface StreakInfo {
  current: number;
  longest: number;
  active_today: boolean;
}

export interface UserStats {
  total_xp: number;
  level: LevelInfo;
  streak: StreakInfo;
  lessons_completed: number;
  quizzes_passed: number;
  challenges_completed: number;
  perfect_quizzes: number;
}

export interface Achievement {
  key: string;
  name: string;
  description: string;
  icon: string;
  category: string;
  xp_reward: number;
  requirement?: number;
  unlocked: boolean;
}

export interface XPGain {
  amount: number;
  reason: string;
  bonus?: number;
  bonus_reason?: string;
}

export interface LessonCompleteResponse {
  xp_gained: XPGain;
  stats: UserStats;
}

export interface QuizResultResponse {
  xp_gained: XPGain;
  stats: UserStats;
  is_pass: boolean;
  is_perfect: boolean;
}

// Challenge Types
export type ChallengeType = 'bug_hunt' | 'code_trace' | 'fill_blank';

export interface BugHuntChallengeData {
  description: string;
  code_snippet: string;
  bug_line: number;
  bug_description: string;
  hint: string;
}

export interface CodeTraceChallengeData {
  description: string;
  code_snippet: string;
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export interface FillBlankChallengeData {
  description: string;
  code_with_blanks: string;
  blanks: Array<{ id: string; answer: string; options: string[] }>;
}

export type ChallengeData = BugHuntChallengeData | CodeTraceChallengeData | FillBlankChallengeData;

export interface Challenge<TData extends ChallengeData = ChallengeData> {
  id: string;
  lesson_id: string;
  challenge_type: ChallengeType;
  data: TData;
  completed: boolean;
  used_hint: boolean;
}

export interface FillBlankValidationItem {
  id: string;
  correct: boolean;
  correct_answer: string;
  user_answer: string;
}

export interface ChallengeResult {
  correct: boolean;
  explanation?: string;
  correct_answer?: string;
  correct_line?: number;
  correct_index?: number;
  results?: FillBlankValidationItem[];
  xp_earned?: number;
  xp_gained?: XPGain;
  stats?: UserStats;
}

export interface PlatformConfig {
  demo_mode: boolean;
  demo_repo_id?: string | null;
  demo_repo_full_name: string;
  demo_repo_url: string;
  demo_banner_text: string;
  allow_public_imports: boolean;
  busy_mode: boolean;
}

export class ApiError extends Error {
  status: number;
  code?: string;
  retryAfterSeconds?: number;

  constructor(message: string, status: number, code?: string, retryAfterSeconds?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

class ApiClient {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_URL;
  }

  private async toApiError(res: Response, fallbackMessage: string): Promise<ApiError> {
    const retryAfterHeader = res.headers.get('Retry-After');
    const retryAfter = retryAfterHeader ? Number.parseInt(retryAfterHeader, 10) : undefined;

    try {
      const payload = await res.json();
      if (payload?.detail && typeof payload.detail === 'object') {
        return new ApiError(
          payload.detail.message || fallbackMessage,
          res.status,
          payload.detail.code,
          payload.detail.retry_after_seconds ?? retryAfter,
        );
      }

      if (payload?.detail && typeof payload.detail === 'string') {
        return new ApiError(payload.detail, res.status, undefined, retryAfter);
      }
    } catch {
      // Fall back to text parsing below.
    }

    try {
      const text = await res.text();
      const clean = text.trim();
      return new ApiError(clean || fallbackMessage, res.status, undefined, retryAfter);
    } catch {
      return new ApiError(fallbackMessage, res.status, undefined, retryAfter);
    }
  }

  private async ensureOk(res: Response, fallbackMessage: string): Promise<void> {
    if (!res.ok) {
      throw await this.toApiError(res, fallbackMessage);
    }
  }

  // Repository endpoints
  async createRepo(githubUrl: string, branch?: string): Promise<Repository> {
    const res = await fetch(`${this.baseUrl}/api/repos/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ github_url: githubUrl, branch }),
    });
    await this.ensureOk(res, 'Failed to import repository');
    return res.json();
  }

  async listRepos(): Promise<{ repositories: Repository[]; total: number }> {
    const res = await fetch(`${this.baseUrl}/api/repos/`);
    await this.ensureOk(res, 'Failed to fetch repositories');
    return res.json();
  }

  async getRepo(repoId: string): Promise<Repository> {
    const res = await fetch(`${this.baseUrl}/api/repos/${repoId}`);
    await this.ensureOk(res, 'Failed to fetch repository');
    return res.json();
  }

  async getRepoFileContent(repoId: string, path: string): Promise<{ content: string }> {
    // Sanitize path: remove leading @/ or similar aliases that LLMs might hallucinate
    const sanitizedPath = path.replace(/^@\//, 'src/').replace(/^~\//, '');
    const res = await fetch(`${this.baseUrl}/api/repos/${repoId}/files/content?path=${encodeURIComponent(sanitizedPath)}`);
    await this.ensureOk(res, 'Failed to fetch file content');
    return res.json();
  }

  async deleteRepo(repoId: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/repos/${repoId}`, {
      method: 'DELETE',
    });
    await this.ensureOk(res, 'Failed to delete repository');
  }

  async seedDemo(): Promise<{ status: string; repo_id: string; message: string }> {
    const res = await fetch(`${this.baseUrl}/api/repos/demo/seed`, {
      method: 'POST',
    });
    await this.ensureOk(res, 'Failed to seed demo repository');
    return res.json();
  }

  async getPlatformConfig(): Promise<PlatformConfig> {
    const res = await fetch(`${this.baseUrl}/api/platform/config`);
    await this.ensureOk(res, 'Failed to load platform configuration');
    return res.json();
  }

  // Chat endpoints
  async createSession(repoId: string): Promise<{ id: string }> {
    const res = await fetch(`${this.baseUrl}/api/chat/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_id: repoId }),
    });
    await this.ensureOk(res, 'Failed to create chat session');
    return res.json();
  }

  async getSession(sessionId: string): Promise<ChatSession> {
    const res = await fetch(`${this.baseUrl}/api/chat/sessions/${sessionId}`);
    await this.ensureOk(res, 'Failed to fetch chat session');
    return res.json();
  }

  async *streamChat(sessionId: string, content: string): AsyncGenerator<StreamingChunk> {
    const res = await fetch(`${this.baseUrl}/api/chat/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    });

    await this.ensureOk(res, 'Failed to send chat message');

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
    await this.ensureOk(res, 'Search request failed');
    return res.json();
  }

  // Learning endpoints
  async getPersonas(): Promise<Persona[]> {
    const res = await fetch(`${this.baseUrl}/api/learning/personas`);
    await this.ensureOk(res, 'Failed to fetch personas');
    return res.json();
  }

  async generateSyllabus(repoId: string, persona: string): Promise<Syllabus> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/curriculum`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ persona }),
    });
    await this.ensureOk(res, 'Failed to generate syllabus');
    return res.json();
  }

  async generateLesson(repoId: string, lessonId: string, title: string): Promise<LessonContent> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    await this.ensureOk(res, 'Failed to generate lesson content');
    return res.json();
  }

  async generateQuiz(repoId: string, lessonId: string, contextContent: string): Promise<Quiz> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/quiz`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context_content: contextContent }),
    });
    await this.ensureOk(res, 'Failed to generate quiz');
    return res.json();
  }

  async getDependencyGraph(repoId: string): Promise<DependencyGraph> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/graph`);
    await this.ensureOk(res, 'Failed to generate graph');
    return res.json();
  }

  // Gamification endpoints
  async getUserStats(repoId: string): Promise<UserStats> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/stats`);
    await this.ensureOk(res, 'Failed to fetch user stats');
    return res.json();
  }

  async getAchievements(repoId: string): Promise<Achievement[]> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/achievements`);
    await this.ensureOk(res, 'Failed to fetch achievements');
    return res.json();
  }

  async getCompletedLessons(repoId: string): Promise<string[]> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/progress`);
    await this.ensureOk(res, 'Failed to fetch lesson progress');
    const data = await res.json();
    return data.completed_lessons || [];
  }

  async completeLesson(repoId: string, lessonId: string, timeSpentSeconds: number): Promise<LessonCompleteResponse> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ time_spent_seconds: timeSpentSeconds }),
    });
    await this.ensureOk(res, 'Failed to complete lesson');
    return res.json();
  }

  async submitQuizResult(repoId: string, lessonId: string, score: number): Promise<QuizResultResponse> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/quiz/result`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ score }),
    });
    await this.ensureOk(res, 'Failed to submit quiz result');
    return res.json();
  }

  async recordGraphView(repoId: string): Promise<{ achievement_unlocked?: Achievement; already_viewed?: boolean }> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/graph/viewed`, {
      method: 'POST',
    });
    await this.ensureOk(res, 'Failed to record graph view');
    return res.json();
  }

  // Challenge endpoints
  async generateChallenge(repoId: string, lessonId: string, challengeType: ChallengeType, context: string = ''): Promise<Challenge> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/challenge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ challenge_type: challengeType, context }),
    });
    await this.ensureOk(res, 'Failed to generate challenge');
    return res.json();
  }

  async validateChallenge(
    repoId: string,
    challengeType: ChallengeType,
    challenge: Challenge,
    answer: number | string[],
    usedHint = false
  ): Promise<ChallengeResult> {
    const endpoint = `${this.baseUrl}/api/learning/${repoId}/challenges/validate/${challengeType}`;
    const body = challengeType === 'bug_hunt'
      ? { challenge, selected_line: answer, used_hint: usedHint }
      : challengeType === 'code_trace'
        ? { challenge, selected_index: answer, used_hint: usedHint }
        : { challenge, answers: answer, used_hint: usedHint };

    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    await this.ensureOk(res, 'Failed to validate challenge');
    return res.json();
  }

  async exportCodeTour(repoId: string, lessonId: string): Promise<CodeTour> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/export/codetour`);
    await this.ensureOk(res, 'Failed to export CodeTour');
    return res.json();
  }

  async getUserActivity(repoId: string): Promise<Record<string, number>> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/activity`);
    await this.ensureOk(res, 'Failed to load activity');
    return res.json();
  }
}

// Graph Types
export interface GraphNode {
  id: string;
  label: string;
  type: string;
  description: string;
  group?: string;
  importance?: number;
  loc?: number;
  exports?: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  type?: string;
  weight?: number;
}

export interface DependencyGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export const api = new ApiClient();
