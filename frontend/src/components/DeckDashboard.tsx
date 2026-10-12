import React, { useState } from 'react';
import { DeckSummary } from '../types';
import { api } from '../api';
interface Props { decks: DeckSummary[]; loading: boolean; error: string | null; onSelectDeck: (id: string) => void; onDeleteDeck: (id: string) => void; onCreateTopic: (t: string, c: number) => Promise<void>; onCreateDoc: (d: string, c: number) => Promise<void>; filterSource: string; setFilterSource: (s: string) => void; searchQuery: string; setSearchQuery: (q: string) => void; }
const Card = ({ t, t1, t2, s, sn, oo, od }: { t: string; t1: string; t2?: string | string[]; s?: string; sn?: string | null; oo: () => void; od?: () => void }) => (
  <div className="deck-card" onClick={oo} style={{ cursor: 'pointer' }}>
    <div className="card-top"><span className="tag">{t1}</span>{Array.isArray(t2) ? t2.map(x => <span key={x} className="tag">{x}</span>) : t2 && <span className="tag">{t2}</span>}</div>
    <h3 className="card-title">{t}</h3>
    {s && <div className="card-meta"><span>{s}</span></div>}
    {sn && <p style={{ fontSize: '.8rem', color: '#333', margin: '.25rem 0' }}>{sn}</p>}
    {od && <div className="card-actions" onClick={e => e.stopPropagation()}><button className="btn-danger btn-sm" onClick={od}>Delete</button></div>}
  </div>
);
export const DeckDashboard: React.FC<Props> = ({
  decks, loading, error, onSelectDeck, onDeleteDeck, onCreateTopic, onCreateDoc,
  filterSource, setFilterSource, searchQuery, setSearchQuery,
}) => {
  const [mo, setMo] = useState(false), [md, setMd] = useState<'topic' | 'doc'>('topic');
  const [tp, setTp] = useState(''), [dc, setDc] = useState(''), [ct, setCt] = useState(6);
  const [sb, setSb] = useState(false), [se, setSe] = useState<string | null>(null);
  const sc = async (e: React.FormEvent) => { e.preventDefault(); setSb(true); setSe(null); try { if (md === 'topic') { if (tp.trim().length < 3) throw new Error('Topic must be ≥ 3 characters'); await onCreateTopic(tp.trim(), ct); } else { if (dc.trim().length < 10) throw new Error('Document must be ≥ 10 characters'); await onCreateDoc(dc.trim(), ct); } setMo(false); setTp(''); setDc(''); } catch (err: unknown) { setSe(err instanceof Error ? err.message : 'Creation failed'); } finally { setSb(false); } };
  const fd = decks.filter(d => d.title.toLowerCase().includes(searchQuery.toLowerCase()) && (!filterSource || d.source_type === filterSource));
  return (
    <div className="dashboard-container">
      <div className="section-header"><div><h2>Presentation Decks</h2><p className="section-desc">Structured content generation with native layouts and metrics.</p></div><button className="btn-primary" onClick={() => setMo(true)}>+ New Presentation</button></div>
      <div className="filter-bar"><input className="search-input" placeholder="Filter by deck title…" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} /><select className="select-input" value={filterSource} onChange={e => setFilterSource(e.target.value)}><option value="">All Source Types</option><option value="topic">Topic-driven</option><option value="document">Document-driven</option></select></div>
      {error && <div className="alert alert-error">{error}</div>}
      {loading ? <div className="state-panel"><div className="spinner" /><p>Loading presentations…</p></div> : fd.length === 0 ? (
        <div className="state-panel"><h3>No presentations found</h3><p>Create a presentation from a research topic or document.</p><button className="btn-secondary" onClick={() => setMo(true)}>Create First Deck</button></div>
      ) : <div className="deck-grid">{fd.map(d => <Card key={d.id} t={d.title} t1={d.source_type} t2={d.status} s={`${d.slide_count} slides • ${new Date(d.created_at).toLocaleDateString()}`} oo={() => onSelectDeck(d.id)} od={() => onDeleteDeck(d.id)} />)}</div>}
      {mo && <div className="modal-overlay" onClick={() => setMo(false)}><div className="modal-dialog" onClick={e => e.stopPropagation()}>
        <div className="modal-header"><h3>Create New Presentation</h3><button className="btn-close" onClick={() => setMo(false)}>&times;</button></div>
        {se && <div className="alert alert-error">{se}</div>}
        <form onSubmit={sc}>
          <div className="tab-pills" style={{ marginBottom: '.75rem' }}><button className={`tab-pill ${md === 'topic' ? 'active' : ''}`} onClick={() => setMd('topic')}>From Research Topic</button><button className={`tab-pill ${md === 'doc' ? 'active' : ''}`} onClick={() => setMd('doc')}>From Freeform Document</button></div>
          <div className="form-group"><label>{md === 'topic' ? 'Topic / Prompt' : 'Source Document Text'}</label><textarea className="form-control" rows={md === 'topic' ? 3 : 5} placeholder={md === 'topic' ? 'e.g. Distributed Consensus' : 'Paste document content…'} value={md === 'topic' ? tp : dc} onChange={e => md === 'topic' ? setTp(e.target.value) : setDc(e.target.value)} required /></div>
          <div className="form-group"><label>Target Slide Count ({ct})</label><input type="range" min={3} max={20} value={ct} onChange={e => setCt(Number(e.target.value))} className="w-full" /></div>
          <div className="modal-footer"><button className="btn-secondary" type="button" onClick={() => setMo(false)}>Cancel</button><button className="btn-primary" type="submit" disabled={sb}>{sb ? 'Generating…' : 'Generate Presentation'}</button></div>
        </form></div></div>}
    </div>
  );
};