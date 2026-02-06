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

  async getRepoFileContent(repoId: string, path: string): Promise<{ content: string }> {
    // Sanitize path: remove leading @/ or similar aliases that LLMs might hallucinate
    const sanitizedPath = path.replace(/^@\//, 'src/').replace(/^~\//, '');
    const res = await fetch(`${this.baseUrl}/api/repos/${repoId}/files/content?path=${encodeURIComponent(sanitizedPath)}`);
    if (!res.ok) throw new Error('Failed to fetch file content');
    return res.json();
  }

  async deleteRepo(repoId: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/api/repos/${repoId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(await res.text());
  }

  async seedDemo(): Promise<{ status: string; repo_id: string; message: string }> {
    const res = await fetch(`${this.baseUrl}/api/repos/demo/seed`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
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

  // Learning endpoints
  async getPersonas(): Promise<Persona[]> {
    const res = await fetch(`${this.baseUrl}/api/learning/personas`);
    if (!res.ok) throw new Error('Failed to fetch personas');
    return res.json();
  }

  async generateSyllabus(repoId: string, persona: string): Promise<Syllabus> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/curriculum`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ persona }),
    });
    if (!res.ok) throw new Error('Failed to generate syllabus');
    return res.json();
  }

  async generateLesson(repoId: string, lessonId: string, title: string): Promise<LessonContent> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error('Failed to generate lesson content');
    return res.json();
  }

  async generateQuiz(repoId: string, lessonId: string, contextContent: string): Promise<Quiz> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/quiz`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context_content: contextContent }),
    });
    if (!res.ok) throw new Error('Failed to generate quiz');
    return res.json();
  }

  async getDependencyGraph(repoId: string): Promise<DependencyGraph> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/graph`);
    if (!res.ok) throw new Error('Failed to generate graph');
    return res.json();
  }

  // Gamification endpoints
  async getUserStats(repoId: string): Promise<UserStats> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/stats`);
    if (!res.ok) throw new Error('Failed to fetch user stats');
    return res.json();
  }

  async getAchievements(repoId: string): Promise<Achievement[]> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/achievements`);
    if (!res.ok) throw new Error('Failed to fetch achievements');
    return res.json();
  }

  async getCompletedLessons(repoId: string): Promise<string[]> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/progress`);
    if (!res.ok) throw new Error('Failed to fetch lesson progress');
    const data = await res.json();
    return data.completed_lessons || [];
  }

  async completeLesson(repoId: string, lessonId: string, timeSpentSeconds: number): Promise<LessonCompleteResponse> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ time_spent_seconds: timeSpentSeconds }),
    });
    if (!res.ok) throw new Error('Failed to complete lesson');
    return res.json();
  }

  async submitQuizResult(repoId: string, lessonId: string, score: number): Promise<QuizResultResponse> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/quiz/result`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ score }),
    });
    if (!res.ok) throw new Error('Failed to submit quiz result');
    return res.json();
  }

  async recordGraphView(repoId: string): Promise<{ achievement_unlocked?: Achievement; already_viewed?: boolean }> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/graph/viewed`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to record graph view');
    return res.json();
  }

  // Challenge endpoints
  async generateChallenge(repoId: string, lessonId: string, challengeType: ChallengeType, context: string = ''): Promise<Challenge> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/challenge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ challenge_type: challengeType, context }),
    });
    if (!res.ok) throw new Error('Failed to generate challenge');
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
    if (!res.ok) throw new Error('Failed to validate challenge');
    return res.json();
  }

  async exportCodeTour(repoId: string, lessonId: string): Promise<CodeTour> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/lessons/${lessonId}/export/codetour`);
    if (!res.ok) throw new Error('Failed to export CodeTour');
    return res.json();
  }

  async getUserActivity(repoId: string): Promise<Record<string, number>> {
    const res = await fetch(`${this.baseUrl}/api/learning/${repoId}/activity`);
    if (!res.ok) throw new Error('Failed to load activity');
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
