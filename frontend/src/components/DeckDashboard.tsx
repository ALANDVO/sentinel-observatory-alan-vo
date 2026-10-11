import React, { useState } from 'react';
import { DeckSummary, SlideSearchResult } from '../types';
import { api } from '../api';
interface Props {
  decks: DeckSummary[]; loading: boolean; error: string | null;
  onSelectDeck: (id: string) => void; onDeleteDeck: (id: string) => void;
  onCreateTopic: (t: string, c: number) => Promise<void>;
  onCreateDoc: (d: string, c: number) => Promise<void>;
  filterSource: string; setFilterSource: (s: string) => void;
  searchQuery: string; setSearchQuery: (q: string) => void;
}
const Card = ({ title, tag1, tag2, sub, snip, onOpen, onDel }: { title: string; tag1: string; tag2?: string | string[]; sub?: string; snip?: string | null; onOpen: () => void; onDel?: () => void }) => (
  <div className="deck-card" onClick={onOpen} style={{ cursor: 'pointer' }}>
    <div className="card-top"><span className="tag">{tag1}</span>{Array.isArray(tag2) ? tag2.map(t => <span key={t} className="tag">{t}</span>) : tag2 && <span className="tag">{tag2}</span>}</div>
    <h3 className="card-title">{title}</h3>
    {sub && <div className="card-meta"><span>{sub}</span></div>}
    {snip && <p style={{ fontSize: '.8rem', color: '#333', margin: '.25rem 0' }}>{snip}</p>}
    {onDel && <div className="card-actions" onClick={e => e.stopPropagation()}><button className="btn-danger btn-sm" onClick={onDel}>Delete</button></div>}
  </div>
);
export const DeckDashboard: React.FC<Props> = ({
  decks, loading, error, onSelectDeck, onDeleteDeck, onCreateTopic, onCreateDoc,
  filterSource, setFilterSource, searchQuery, setSearchQuery,
}) => {
  const [modal, setModal] = useState(false), [mode, setMode] = useState<'topic' | 'doc'>('topic');
  const [topic, setTopic] = useState(''), [doc, setDoc] = useState(''), [count, setCount] = useState(6);
  const [submitting, setSubmitting] = useState(false), [submitErr, setSubmitErr] = useState<string | null>(null);
  const [searchMode, setSearchMode] = useState<'deck' | 'slide'>('deck'), [results, setResults] = useState<SlideSearchResult[]>([]);
  const [searching, setSearching] = useState(false), [searchErr, setSearchErr] = useState<string | null>(null), [slideQ, setSlideQ] = useState('');
  const submitCreate = async (e: React.FormEvent) => {
    e.preventDefault(); setSubmitting(true); setSubmitErr(null);
    try {
      if (mode === 'topic') { if (topic.trim().length < 3) throw new Error('Topic must be ≥ 3 characters'); await onCreateTopic(topic.trim(), count); }
      else { if (doc.trim().length < 10) throw new Error('Document must be ≥ 10 characters'); await onCreateDoc(doc.trim(), count); }
      setModal(false); setTopic(''); setDoc('');
    } catch (err: unknown) { setSubmitErr(err instanceof Error ? err.message : 'Creation failed'); }
    finally { setSubmitting(false); }
  };
  const searchSlides = async (e: React.FormEvent) => {
    e.preventDefault(); if (slideQ.trim().length < 2) return; setSearching(true); setSearchErr(null); setResults([]);
    try { const res = await api.decks.searchSlides(slideQ.trim(), 50); setResults(res.results); }
    catch (err: unknown) { setSearchErr(err instanceof Error ? err.message : 'Search failed'); }
    finally { setSearching(false); }
  };
  const filtered = decks.filter(d => d.title.toLowerCase().includes(searchQuery.toLowerCase()) && (!filterSource || d.source_type === filterSource));
  return (
    <div className="dashboard-container">
      <div className="section-header"><div><h2>Presentation Decks</h2><p className="section-desc">Structured content generation with native layouts and metrics.</p></div><button className="btn-primary" onClick={() => setModal(true)}>+ New Presentation</button></div>
      <div className="filter-bar"><div className="tab-pills" style={{ marginBottom: 0 }}>
        <button className={`tab-pill ${searchMode === 'deck' ? 'active' : ''}`} onClick={() => setSearchMode('deck')}>Deck Filter</button>
        <button className={`tab-pill ${searchMode === 'slide' ? 'active' : ''}`} onClick={() => setSearchMode('slide')}>Slide Content Search</button></div>
        {searchMode === 'deck' ? (
          <> <input className="search-input" placeholder="Filter by deck title…" value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
            <select className="select-input" value={filterSource} onChange={e => setFilterSource(e.target.value)}><option value="">All Source Types</option><option value="topic">Topic-driven</option><option value="document">Document-driven</option></select>
          </>
        ) : (
          <form onSubmit={searchSlides} style={{ display: 'flex', gap: '.5rem', flex: 1 }}>
            <input className="search-input" placeholder="Search across slide content, notes, titles…" value={slideQ} onChange={e => setSlideQ(e.target.value)} minLength={2} required />
            <button className="btn-secondary" disabled={searching} type="submit">{searching ? 'Searching…' : 'Search'}</button></form>
        )}
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {searchMode === 'slide' ? (
        <div>{searchErr && <div className="alert alert-error">{searchErr}</div>}
          {!results.length && !searching && slideQ && <div className="state-panel"><h3>No slide matches found</h3><p>Try a different query or search within a specific deck.</p></div>}
          {results.length > 0 && <div className="deck-grid">{results.map(r => <Card key={`${r.deck_id}-${r.slide_id}`} title={r.title || '(Untitled Slide)'} tag1={r.slide_type} tag2={r.match_fields} sub={`${r.deck_title} · slide ${r.position + 1}`} snip={r.snippet} onOpen={() => onSelectDeck(r.deck_id)} />)}</div>}
        </div>
      ) : loading ? <div className="state-panel"><div className="spinner" /><p>Loading presentations…</p></div> : filtered.length === 0 ? (
        <div className="state-panel"><h3>No presentations found</h3><p>Create a presentation from a research topic or document.</p><button className="btn-secondary" onClick={() => setModal(true)}>Create First Deck</button></div>
      ) : <div className="deck-grid">{filtered.map(d => <Card key={d.id} title={d.title} tag1={d.source_type} tag2={d.status} sub={`${d.slide_count} slides • ${new Date(d.created_at).toLocaleDateString()}`} onOpen={() => onSelectDeck(d.id)} onDel={() => onDeleteDeck(d.id)} />)}</div>}
      {modal && <div className="modal-overlay" onClick={() => setModal(false)}><div className="modal-dialog" onClick={e => e.stopPropagation()}>
        <div className="modal-header"><h3>Create New Presentation</h3><button className="btn-close" onClick={() => setModal(false)}>&times;</button></div>
        {submitErr && <div className="alert alert-error">{submitErr}</div>}
        <form onSubmit={submitCreate}>
          <div className="tab-pills" style={{ marginBottom: '.75rem' }}><button className={`tab-pill ${mode === 'topic' ? 'active' : ''}`} onClick={() => setMode('topic')}>From Research Topic</button><button className={`tab-pill ${mode === 'doc' ? 'active' : ''}`} onClick={() => setMode('doc')}>From Freeform Document</button></div>
          <div className="form-group"><label>{mode === 'topic' ? 'Topic / Prompt' : 'Source Document Text'}</label><textarea className="form-control" rows={mode === 'topic' ? 3 : 5} placeholder={mode === 'topic' ? 'e.g. Distributed Consensus' : 'Paste document content…'} value={mode === 'topic' ? topic : doc} onChange={e => mode === 'topic' ? setTopic(e.target.value) : setDoc(e.target.value)} required /></div>
          <div className="form-group"><label>Target Slide Count ({count})</label><input type="range" min={3} max={20} value={count} onChange={e => setCount(Number(e.target.value))} className="w-full" /></div>
          <div className="modal-footer"><button className="btn-secondary" type="button" onClick={() => setModal(false)}>Cancel</button><button className="btn-primary" type="submit" disabled={submitting}>{submitting ? 'Generating…' : 'Generate Presentation'}</button></div>
        </form></div></div>}
    </div>
  );
};