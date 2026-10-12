import {
  DeckListResponse, DeckOut, DeckNarrationOut, EvaluationListResponse, EvaluationOut,
  OIDCConfig, SlideOut, TemplateListResponse, TemplateOut, UserInfo,
  SearchResponse,
} from './types';
let _token: string | null = null;
export const setAccessToken = (t: string | null) => { _token = t; };
export const getAccessToken = () => _token;
export const storePKCEState = (s: string, v: string) => { sessionStorage.setItem('sentinel_pkce_state', s); sessionStorage.setItem('sentinel_pkce_verifier', v); };
export const retrievePKCEState = () => {
  const s = sessionStorage.getItem('sentinel_pkce_state'), v = sessionStorage.getItem('sentinel_pkce_verifier');
  sessionStorage.removeItem('sentinel_pkce_state'); sessionStorage.removeItem('sentinel_pkce_verifier');
  return { state: s, verifier: v };
};
const BASE = '/api';
async function req<T>(path: string, opt: RequestInit = {}): Promise<T> {
  const headers = new Headers(opt.headers || {});
  if (_token) headers.set('Authorization', `Bearer ${_token}`);
  const res = await fetch(`${BASE}${path}`, { ...opt, headers });
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { const err = await res.json(); if (err.detail) msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail); } catch {}
    throw new Error(msg);
  }
  return res.status === 204 ? ({} as T) : res.json();
}
const qs = (p?: Record<string, unknown>) => {
  if (!p) return '';
  const q = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => v !== undefined && q.set(k, String(v)));
  return q.size ? `?${q}` : '';
};
const jpost = (path: string, body: unknown) => req(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
const _nUrl = (p: string, v: string, w: number) => `${BASE}${p}?voice=${encodeURIComponent(v)}&words_per_minute=${w}`;
export const api = {
  auth: {
    getConfig: () => req<OIDCConfig>('/auth/config'),
    getMe: () => req<UserInfo>('/auth/me'),
  },
  decks: {
    list: (p?: { skip?: number; limit?: number; source_type?: string; status?: string; search?: string }) => req<DeckListResponse>(`/decks${qs(p)}`),
    get: (id: string) => req<DeckOut>(`/decks/${id}`),
    generateTopic: (b: { topic: string; slide_count?: number; template_id?: string | null }) => jpost('/decks/generate/topic', b) as Promise<DeckOut>,
    generateDocument: (b: { text: string; slide_count?: number; template_id?: string | null }) => jpost('/decks/generate/document', b) as Promise<DeckOut>,
    delete: (id: string) => req<void>(`/decks/${id}`, { method: 'DELETE' }),
    addSlide: (id: string, b: { slide_type: string; title: string; body_text?: string; speaker_notes?: string }) => jpost(`/decks/${id}/slides`, b) as Promise<SlideOut>,
    exportPptxUrl: (id: string) => `${BASE}/decks/${id}/export/pptx`,
    synthesizeNarration: (id: string, v = 'narrator-en', w = 150) => req<DeckNarrationOut>(`/decks/${id}/narration/synthesize?voice=${encodeURIComponent(v)}&words_per_minute=${w}`, { method: 'POST' }),
    narrationAudioUrl: (id: string, v = 'narrator-en', w = 150) => _nUrl(`/decks/${id}/narration/audio`, v, w),
    slideNarrationAudioUrl: (id: string, sId: string, v = 'narrator-en', w = 150) => _nUrl(`/decks/${id}/slides/${sId}/narration/audio`, v, w),
  },
  search: {
    unified: (params: { q: string; limit?: number; offset?: number; source_type?: string; status?: string; deck_id?: string; slide_type?: string; eval_type?: string; author_sub?: string }) => req<SearchResponse>(`/search${qs(params)}`),
  },
  evaluations: {
    list: (p?: { deck_id?: string; eval_type?: string; skip?: number; limit?: number }) => req<EvaluationListResponse>(`/evaluations${qs(p)}`),
    get: (id: string) => req<EvaluationOut>(`/evaluations/${id}`),
    run: (id: string, b: { eval_type: string; model?: string; request_llm_advisory?: boolean }) => jpost(`/evaluations/decks/${id}/run`, b) as Promise<EvaluationOut>,
    exportJson: (id: string) => `${BASE}/evaluations/${id}/export/json`,
    exportMarkdown: (id: string) => `${BASE}/evaluations/${id}/export/markdown`,
  },
  templates: {
    list: (p?: { skip?: number; limit?: number }) => req<TemplateListResponse>(`/templates${qs(p)}`),
    get: (id: string) => req<TemplateOut>(`/templates/${id}`),
    create: (fd: FormData) => req<TemplateOut>('/templates', { method: 'POST', body: fd }),
  },
};
