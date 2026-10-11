import {
  DeckListResponse,
  DeckOut,
  EvaluationListResponse,
  EvaluationOut,
  OIDCConfig,
  SlideOut,
  TemplateListResponse,
  TemplateOut,
  UserInfo,
} from './types';

let memoryAccessToken: string | null = null;
export const setAccessToken = (token: string | null) => { memoryAccessToken = token; };
export const getAccessToken = () => memoryAccessToken;

export const storePKCEState = (state: string, verifier: string) => {
  sessionStorage.setItem('sentinel_pkce_state', state);
  sessionStorage.setItem('sentinel_pkce_verifier', verifier);
};

export const retrievePKCEState = () => {
  const state = sessionStorage.getItem('sentinel_pkce_state');
  const verifier = sessionStorage.getItem('sentinel_pkce_verifier');
  sessionStorage.removeItem('sentinel_pkce_state');
  sessionStorage.removeItem('sentinel_pkce_verifier');
  return { state, verifier };
};

const API_BASE = '/api';

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (memoryAccessToken) headers.set('Authorization', `Bearer ${memoryAccessToken}`);
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
    } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? ({} as T) : res.json();
}

const qs = (p?: Record<string, unknown>) => {
  if (!p) return '';
  const q = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => v !== undefined && q.set(k, String(v)));
  const s = q.toString();
  return s ? `?${s}` : '';
};

export const api = {
  auth: {
    getConfig: () => request<OIDCConfig>('/auth/config'),
    getMe: () => request<UserInfo>('/auth/me'),
  },
  decks: {
    list: (p?: { skip?: number; limit?: number; source_type?: string; status?: string; search?: string }) =>
      request<DeckListResponse>(`/decks${qs(p)}`),
    get: (id: string) => request<DeckOut>(`/decks/${id}`),
    generateTopic: (b: { topic: string; slide_count?: number; template_id?: string | null }) =>
      request<DeckOut>('/decks/generate/topic', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }),
    generateDocument: (b: { text: string; slide_count?: number; template_id?: string | null }) =>
      request<DeckOut>('/decks/generate/document', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }),
    delete: (id: string) => request<void>(`/decks/${id}`, { method: 'DELETE' }),
    addSlide: (id: string, b: { slide_type: string; title: string; body_text?: string; speaker_notes?: string }) =>
      request<SlideOut>(`/decks/${id}/slides`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }),
    exportPptxUrl: (id: string) => `${API_BASE}/decks/${id}/export/pptx`,
    synthesizeNarration: (id: string, voice: string = 'narrator-en', wpm: number = 150) =>
      request<import('./types').DeckNarrationOut>(`/decks/${id}/narration/synthesize?voice=${encodeURIComponent(voice)}&words_per_minute=${wpm}`, { method: 'POST' }),
    narrationAudioUrl: (id: string, voice: string = 'narrator-en', wpm: number = 150) =>
      `${API_BASE}/decks/${id}/narration/audio?voice=${encodeURIComponent(voice)}&words_per_minute=${wpm}`,
    slideNarrationAudioUrl: (id: string, slideId: string, voice: string = 'narrator-en', wpm: number = 150) =>
      `${API_BASE}/decks/${id}/slides/${slideId}/narration/audio?voice=${encodeURIComponent(voice)}&words_per_minute=${wpm}`,
    searchSlides: (q: string, limit?: number) =>
      request<import('./types').SlideSearchResponse>(`/decks/search/slides${qs({ q, limit })}`),
  },
  evaluations: {
    list: (p?: { deck_id?: string; eval_type?: string; skip?: number; limit?: number }) =>
      request<EvaluationListResponse>(`/evaluations${qs(p)}`),
    get: (id: string) => request<EvaluationOut>(`/evaluations/${id}`),
    run: (id: string, b: { eval_type: string; model?: string; request_llm_advisory?: boolean }) =>
      request<EvaluationOut>(`/evaluations/decks/${id}/run`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(b) }),
  },
  templates: {
    list: (p?: { skip?: number; limit?: number }) => request<TemplateListResponse>(`/templates${qs(p)}`),
    get: (id: string) => request<TemplateOut>(`/templates/${id}`),
    create: (fd: FormData) => request<TemplateOut>('/templates', { method: 'POST', body: fd }),
  },
};
