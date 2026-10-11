import React, { useState } from 'react';
import { DeckSummary, SlideSearchResult } from '../types';
import { api } from '../api';

interface DeckDashboardProps {
  decks: DeckSummary[]; loading: boolean; error: string | null;
  onSelectDeck: (id: string) => void; onDeleteDeck: (id: string) => void;
  onCreateTopic: (topic: string, count: number) => Promise<void>;
  onCreateDoc: (text: string, count: number) => Promise<void>;
  filterSource: string; setFilterSource: (src: string) => void;
  searchQuery: string; setSearchQuery: (query: string) => void;
}

export const DeckDashboard: React.FC<DeckDashboardProps> = ({
  decks, loading, error, onSelectDeck, onDeleteDeck, onCreateTopic, onCreateDoc,
  filterSource, setFilterSource, searchQuery, setSearchQuery,
}) => {
  const [showModal, setShowModal] = useState(false);
  const [createMode, setCreateMode] = useState<'topic' | 'doc'>('topic');
  const [topicInput, setTopicInput] = useState('');
  const [docInput, setDocInput] = useState('');
  const [slideCount, setSlideCount] = useState(6);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [searchMode, setSearchMode] = useState<'deck' | 'slide'>('deck');
  const [slideResults, setSlideResults] = useState<SlideSearchResult[]>([]);
  const [slideSearching, setSlideSearching] = useState(false);
  const [slideSearchError, setSlideSearchError] = useState<string | null>(null);
  const [slideSearchQuery, setSlideSearchQuery] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSubmitting(true); setSubmitError(null);
    try {
      if (createMode === 'topic') {
        if (!topicInput.trim()) throw new Error('Topic is required');
        await onCreateTopic(topicInput, slideCount); setTopicInput('');
      } else {
        if (!docInput.trim()) throw new Error('Document text is required');
        await onCreateDoc(docInput, slideCount); setDocInput('');
      }
      setShowModal(false);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Creation failed');
    } finally { setSubmitting(false); }
  };

  const handleSlideSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!slideSearchQuery.trim() || slideSearchQuery.trim().length < 2) return;
    setSlideSearching(true); setSlideSearchError(null);
    try {
      const res = await api.decks.searchSlides(slideSearchQuery.trim(), 20);
      setSlideResults(res.results);
    } catch (err: unknown) {
      setSlideSearchError(err instanceof Error ? err.message : 'Search failed');
      setSlideResults([]);
    } finally { setSlideSearching(false); }
  };

  const filtered = decks.filter((d) => d.title.toLowerCase().includes(searchQuery.toLowerCase()) && (!filterSource || d.source_type === filterSource));

  return (
    <div className="dashboard-container">
      <div className="section-header">
        <div>
          <h2>Presentation Decks</h2>
          <p className="section-desc">Structured content generation with native layouts and metrics.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>+ New Presentation</button>
      </div>
      <div className="filter-bar">
        <div className="tab-pills" style={{ marginBottom: 0 }}>
          <button type="button" className={`tab-pill ${searchMode === 'deck' ? 'active' : ''}`} onClick={() => setSearchMode('deck')}>Deck Filter</button>
          <button type="button" className={`tab-pill ${searchMode === 'slide' ? 'active' : ''}`} onClick={() => setSearchMode('slide')}>Slide Content Search</button>
        </div>
        {searchMode === 'deck' ? (
          <>
            <input type="text" className="search-input" placeholder="Filter by deck title…" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
            <select className="select-input" value={filterSource} onChange={(e) => setFilterSource(e.target.value)}>
              <option value="">All Source Types</option>
              <option value="topic">Topic-driven</option>
              <option value="document">Document-driven</option>
            </select>
          </>
        ) : (
          <form onSubmit={handleSlideSearch} style={{ display: 'flex', gap: '.5rem', flex: 1 }}>
            <input type="text" className="search-input" placeholder="Search across slide content, notes, titles…" value={slideSearchQuery} onChange={(e) => setSlideSearchQuery(e.target.value)} minLength={2} required />
            <button type="submit" className="btn-secondary" disabled={slideSearching}>{slideSearching ? 'Searching…' : 'Search'}</button>
          </form>
        )}
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {searchMode === 'slide' ? (
        <div>
          {slideSearchError && <div className="alert alert-error">{slideSearchError}</div>}
          {slideResults.length === 0 && !slideSearching && slideSearchQuery && (
            <div className="state-panel"><h3>No slide matches found</h3><p>Try a different query or search within a specific deck.</p></div>
          )}
          {slideResults.length > 0 && (
            <div className="deck-grid">
              {slideResults.map((r) => (
                <div key={`${r.deck_id}-${r.slide_id}`} className="deck-card" onClick={() => onSelectDeck(r.deck_id)} style={{ cursor: 'pointer' }}>
                  <div className="card-top">
                    <span className="tag">{r.slide_type}</span>
                    {r.match_fields.map((f) => <span key={f} className="tag status-tag">{f}</span>)}
                  </div>
                  <h3 className="card-title">{r.title || '(Untitled Slide)'}</h3>
                  <p style={{ fontSize: '.85rem', color: '#555', margin: '.25rem 0', fontStyle: 'italic' }}>{r.deck_title} · slide {r.position + 1}</p>
                  {r.snippet && <p style={{ fontSize: '.8rem', color: '#333', margin: '.25rem 0' }}>{r.snippet}</p>}
                  <div className="card-actions" onClick={(e) => e.stopPropagation()}>
                    <button className="btn-secondary btn-sm" onClick={() => onSelectDeck(r.deck_id)}>Open Deck</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : loading ? (
        <div className="state-panel"><div className="spinner" /><p>Loading presentations…</p></div>
      ) : filtered.length === 0 ? (
        <div className="state-panel">
          <h3>No presentations found</h3>
          <p>Create a presentation from a research topic or document.</p>
          <button className="btn-secondary" onClick={() => setShowModal(true)}>Create First Deck</button>
        </div>
      ) : (
        <div className="deck-grid">
          {filtered.map((d) => (
            <div key={d.id} className="deck-card" onClick={() => onSelectDeck(d.id)}>
              <div className="card-top">
                <span className="tag">{d.source_type}</span>
                <span className="tag status-tag">{d.status}</span>
              </div>
              <h3 className="card-title">{d.title}</h3>
              <div className="card-meta">
                <span>{d.slide_count} slides</span>
                <span>• {new Date(d.created_at).toLocaleDateString()}</span>
              </div>
              <div className="card-actions" onClick={(e) => e.stopPropagation()}>
                <button className="btn-secondary btn-sm" onClick={() => onSelectDeck(d.id)}>Open</button>
                <button className="btn-danger btn-sm" onClick={() => onDeleteDeck(d.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create New Presentation</h3>
              <button className="btn-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            {submitError && <div className="alert alert-error">{submitError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="tab-pills" style={{ marginBottom: '.75rem' }}>
                <button type="button" className={`tab-pill ${createMode === 'topic' ? 'active' : ''}`} onClick={() => setCreateMode('topic')}>From Research Topic</button>
                <button type="button" className={`tab-pill ${createMode === 'doc' ? 'active' : ''}`} onClick={() => setCreateMode('doc')}>From Freeform Document</button>
              </div>
              {createMode === 'topic' ? (
                <div className="form-group">
                  <label>Topic / Prompt</label>
                  <textarea className="form-control" rows={3} placeholder="e.g. Distributed Consensus" value={topicInput} onChange={(e) => setTopicInput(e.target.value)} required />
                </div>
              ) : (
                <div className="form-group">
                  <label>Source Document Text</label>
                  <textarea className="form-control" rows={5} placeholder="Paste document content…" value={docInput} onChange={(e) => setDocInput(e.target.value)} required />
                </div>
              )}
              <div className="form-group">
                <label>Target Slide Count ({slideCount})</label>
                <input type="range" min={3} max={20} value={slideCount} onChange={(e) => setSlideCount(Number(e.target.value))} className="w-full" />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={submitting}>{submitting ? 'Generating…' : 'Generate Presentation'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
