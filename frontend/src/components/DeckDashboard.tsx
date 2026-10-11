import React, { useState } from 'react';
import { DeckSummary } from '../types';

interface DeckDashboardProps {
  decks: DeckSummary[];
  loading: boolean;
  error: string | null;
  onSelectDeck: (id: string) => void;
  onDeleteDeck: (id: string) => void;
  onCreateTopic: (topic: string, count: number) => Promise<void>;
  onCreateDoc: (text: string, count: number) => Promise<void>;
  filterSource: string;
  setFilterSource: (src: string) => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (createMode === 'topic') {
        if (!topicInput.trim()) throw new Error('Topic is required');
        await onCreateTopic(topicInput, slideCount);
        setTopicInput('');
      } else {
        if (!docInput.trim()) throw new Error('Document text is required');
        await onCreateDoc(docInput, slideCount);
        setDocInput('');
      }
      setShowModal(false);
    } catch (err: unknown) {
      setSubmitError(err instanceof Error ? err.message : 'Creation failed');
    } finally { setSubmitting(false); }
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
        <input type="text" className="search-input" placeholder="Search presentations…" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} />
        <select className="select-input" value={filterSource} onChange={(e) => setFilterSource(e.target.value)}>
          <option value="">All Source Types</option>
          <option value="topic">Topic-driven</option>
          <option value="document">Document-driven</option>
        </select>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {loading ? (
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
              <h3 className="card-title" style={{ margin: '.5rem 0' }}>{d.title}</h3>
              <div className="card-meta" style={{ fontSize: '.8rem', color: 'var(--muted)' }}>
                <span>{d.slide_count} slides</span>
                <span>• {new Date(d.created_at).toLocaleDateString()}</span>
              </div>
              <div className="card-actions" style={{ marginTop: '.75rem' }} onClick={(e) => e.stopPropagation()}>
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
                  <textarea className="form-control" rows={3} placeholder="e.g. Distributed Consensus in Modern Storage Systems" value={topicInput} onChange={(e) => setTopicInput(e.target.value)} required />
                </div>
              ) : (
                <div className="form-group">
                  <label>Source Document Text</label>
                  <textarea className="form-control" rows={5} placeholder="Paste document content…" value={docInput} onChange={(e) => setDocInput(e.target.value)} required />
                </div>
              )}
              <div className="form-group">
                <label>Target Slide Count ({slideCount})</label>
                <input type="range" min={3} max={20} value={slideCount} onChange={(e) => setSlideCount(Number(e.target.value))} style={{ width: '100%' }} />
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
