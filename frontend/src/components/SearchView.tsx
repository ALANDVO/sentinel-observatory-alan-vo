import React, { useState, useEffect } from 'react';
import { SearchResultItem, SearchFacets } from '../types';
import { api } from '../api';
const C = { deck: '#2563eb', slide: '#16a34a', evaluation: '#ea580c' };
const L = { result_type: 'Result Type', source_type: 'Source Type', slide_type: 'Slide Type', eval_type: 'Evaluation Type' };
const RC = ({ item }: { item: SearchResultItem }) => {
  const c = C[item.result_type as keyof typeof C] || '#6b7280';
  const m = item.metadata, p: string[] = [];
  if (m.source_type) p.push(`Source: ${m.source_type}`);
  if (m.status) p.push(`Status: ${m.status}`);
  if (m.slide_type) p.push(`Type: ${m.slide_type}`);
  if (m.eval_type) p.push(`Eval: ${m.eval_type}`);
  if (m.deck_id) p.push(`Deck: ${m.deck_id.slice(0, 8)}`);
  if (m.created_at) p.push(new Date(m.created_at).toLocaleDateString());
  return <div className="search-result-card" style={{ borderLeft: `4px solid ${c}` }}><div className="result-header"><span className="result-type-badge" style={{ background: c }}>{item.result_type}</span><span className="result-score">Score: {item.score.toFixed(3)}</span></div><h4 className="result-title">{item.title || '(Untitled)'}</h4><p className="result-snippet">{item.snippet}</p><div className="result-meta">{p.join(' · ')}</div></div>;
};
const FP = ({ facets, af, otf }: { facets: SearchFacets; af: Record<string, string>; otf: (f: string, v: string) => void }) => {
  if (!facets || !Object.keys(facets).length) return null;
  return <div className="facet-panel"><h4>Filters</h4>{Object.entries(facets).map(([f, cnt]) => cnt && Object.keys(cnt).length && <div key={f} className="facet-group"><div className="facet-label">{L[f as keyof typeof L] || f}</div>{Object.entries(cnt as Record<string, number>).map(([v, n]) => { const k = `${f}:${v}`; return <label key={k} className="facet-option"><input type="checkbox" checked={af[k] === v} onChange={() => otf(f, v)} /><span>{v} ({n})</span></label>; })}</div>)}</div>;
};
export const SearchView: React.FC = () => {
  const [q, setQ] = useState(''), [r, setR] = useState<SearchResultItem[]>([]), [f, setF] = useState<SearchFacets>({ result_type: {}, source_type: {}, slide_type: {}, eval_type: {} }), [t, setT] = useState(0), [ld, setLd] = useState(false), [err, setE] = useState<string | null>(null), [off, setO] = useState(0), [af, setAf] = useState<Record<string, string>>({}), LIM = 20;
  const bf = () => { const p: { q: string; limit?: number; offset?: number; source_type?: string; status?: string; deck_id?: string; slide_type?: string; eval_type?: string; author_sub?: string } = { q }; if (off) p.offset = off; Object.entries(af).forEach(([k, v]) => { const [fc] = k.split(':'); if (fc === 'source_type') p.source_type = v; else if (fc === 'status') p.status = v; else if (fc === 'deck_id') p.deck_id = v; else if (fc === 'slide_type') p.slide_type = v; else if (fc === 'eval_type') p.eval_type = v; else if (fc === 'author_sub') p.author_sub = v; }); return p; };
  const ds = async () => { if (!q.trim() || q.length < 2) { setR([]); setT(0); setF({ result_type: {}, source_type: {}, slide_type: {}, eval_type: {} }); return; } setLd(true); setE(null); try { const d = await api.search.unified(bf()); setR(d.results); setT(d.total); setF(d.facets); } catch (e: unknown) { setE(e instanceof Error ? e.message : 'Search failed'); } finally { setLd(false); } };
  useEffect(() => { ds(); }, [q, off, af]);
  const np = off + LIM < t, pp = off > 0;
  return <div className="search-view"><div className="section-header"><div><h2>Cross-Deck Search</h2><p className="section-desc">Unified search across presentations, slides, and evaluations with faceted filtering.</p></div></div><form onSubmit={e => { e.preventDefault(); setO(0); ds(); }} className="search-form"><input className="search-input-large" placeholder="Search across decks, slides, and evaluations… (min 2 characters)" value={q} onChange={e => setQ(e.target.value)} minLength={2} autoFocus /><button className="btn-primary" type="submit" disabled={ld || q.length < 2}>{ld ? 'Searching…' : 'Search'}</button></form>{err && <div className="alert alert-error">{err}</div>}<div className="search-layout"><aside className="search-sidebar"><FP facets={f} af={af} otf={otf} /></aside><main>{r.map(i => <RC key={i.id} item={i} />)}</main></div>{np || pp && <div className="pagination"><button onClick={() => setO(o => o - LIM)} disabled={!pp}>Prev</button><span>Page {Math.floor(off / LIM) + 1}</span><button onClick={() => setO(o => o + LIM)} disabled={!np}>Next</button></div>}</div>;
  function otf(f: string, v: string) { setAf(a => ({ ...a, [`${f}:${v}`]: v })); }
};