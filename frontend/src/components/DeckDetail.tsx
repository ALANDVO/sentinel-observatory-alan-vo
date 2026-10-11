import React, { useState } from 'react';
import { DeckOut, DeckNarrationOut } from '../types';
import { api } from '../api';

interface DeckDetailProps {
  deck: DeckOut;
  onBack: () => void;
  onAddSlide: (deckId: string, slide: { slide_type: string; title: string; body_text: string; speaker_notes: string }) => Promise<void>;
  onRunEval: (deckId: string) => void;
}

export const DeckDetail: React.FC<DeckDetailProps> = ({ deck, onBack, onAddSlide, onRunEval }) => {
  const [selectedSlideIndex, setSelectedSlideIndex] = useState(0);
  const [showAddSlide, setShowAddSlide] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newBody, setNewBody] = useState('');
  const [newNotes, setNewNotes] = useState('');
  const [newType, setNewType] = useState('content');
  const [adding, setAdding] = useState(false);
  const [voice, setVoice] = useState('narrator-en');
  const [synthesizing, setSynthesizing] = useState(false);
  const [narrationData, setNarrationData] = useState<DeckNarrationOut | null>(null);
  const [audioTimestamp, setAudioTimestamp] = useState<number>(Date.now());

  const slides = deck.slides || [];
  const currentSlide = slides[selectedSlideIndex];

  const handleCreateSlide = async (e: React.FormEvent) => {
    e.preventDefault();
    setAdding(true);
    try {
      await onAddSlide(deck.id, { slide_type: newType, title: newTitle, body_text: newBody, speaker_notes: newNotes });
      setShowAddSlide(false);
      setNewTitle(''); setNewBody(''); setNewNotes('');
      setSelectedSlideIndex(slides.length);
    } finally { setAdding(false); }
  };

  const handleSynthesizeNarration = async () => {
    setSynthesizing(true);
    try {
      const res = await api.decks.synthesizeNarration(deck.id, voice);
      setNarrationData(res);
      setAudioTimestamp(Date.now());
    } finally { setSynthesizing(false); }
  };

  return (
    <div className="deck-detail-container">
      <div className="detail-top-bar">
        <button className="btn-secondary btn-sm" onClick={onBack}>&larr; Back to Presentations</button>
        <div className="detail-actions">
          <button className="btn-secondary" onClick={() => onRunEval(deck.id)}>🔍 Run Slide Observatory</button>
          <button className="btn-primary" onClick={() => window.open(api.decks.exportPptxUrl(deck.id), '_blank')}>💾 Export Native .pptx</button>
        </div>
      </div>
      <div className="detail-header" style={{ margin: '1rem 0' }}>
        <h2>{deck.title}</h2>
        <div className="card-meta">
          <span className="tag">{deck.source_type}</span>
          <span className="tag status-tag">{deck.status}</span>
          <span className="tag">{slides.length} slides</span>
        </div>
      </div>
      <div className="detail-layout">
        <aside className="slide-list-sidebar">
          <div className="sidebar-header">
            <h4>Slides ({slides.length})</h4>
            <button className="btn-link" onClick={() => setShowAddSlide(true)}>+ Add Slide</button>
          </div>
          <div className="slide-thumbnails">
            {slides.map((s, idx) => (
              <div key={s.id} className={`slide-thumb-card ${idx === selectedSlideIndex ? 'active' : ''}`} onClick={() => setSelectedSlideIndex(idx)}>
                <div>#{s.position}</div>
                <div>
                  <div style={{ fontSize: '.85rem', fontWeight: 600 }}>{s.title || `Slide ${s.position}`}</div>
                  <span className="tag">{s.slide_type}</span>
                </div>
              </div>
            ))}
          </div>
        </aside>
        <main>
          {currentSlide ? (
            <div>
              <div className="slide-canvas">
                <span className="tag">{currentSlide.slide_type.toUpperCase()}</span>
                <h3 style={{ marginTop: '.5rem', fontSize: '1.2rem' }}>{currentSlide.title}</h3>
                {currentSlide.body_text && (
                  <div className="canvas-bullets" style={{ marginTop: '1rem' }}>
                    {currentSlide.body_text.split('\n').map((l, i) => <div key={i}>• {l}</div>)}
                  </div>
                )}
              </div>
              <div className="speaker-notes-panel">
                <h4>🎙️ Speaker Notes</h4>
                <p style={{ marginTop: '.3rem', fontSize: '.9rem', color: 'var(--muted)' }}>{currentSlide.speaker_notes || 'No speaker notes.'}</p>
              </div>
              <div className="speaker-notes-panel" style={{ marginTop: '1rem' }} data-testid="narration-panel">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <h4>🎧 Audio Narration</h4>
                  <div style={{ display: 'flex', gap: '.5rem', alignItems: 'center' }}>
                    <select className="form-control" style={{ width: 'auto', padding: '.25rem .5rem', fontSize: '.85rem' }} value={voice} onChange={(e) => setVoice(e.target.value)}>
                      <option value="narrator-en">Default Narrator</option>
                      <option value="narrator-exec">Executive Voice</option>
                      <option value="narrator-tech">Technical Voice</option>
                      <option value="narrator-calm">Calm Voice</option>
                    </select>
                    <button className="btn-primary btn-sm" onClick={handleSynthesizeNarration} disabled={synthesizing}>
                      {synthesizing ? 'Synthesizing…' : 'Synthesize Audio'}
                    </button>
                  </div>
                </div>
                <div style={{ marginTop: '.75rem' }}>
                  <p style={{ fontSize: '.85rem', color: 'var(--muted)', marginBottom: '.5rem' }}>Deck Narration Audio (RIFF/WAVE PCM track):</p>
                  <audio data-testid="deck-audio-player" controls style={{ width: '100%', marginBottom: '.5rem' }} src={`${api.decks.narrationAudioUrl(deck.id, voice)}&t=${audioTimestamp}`} />
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <a className="btn-secondary btn-sm" href={api.decks.narrationAudioUrl(deck.id, voice)} download={`${deck.title.replace(/\s+/g, '_')}_narration.wav`}>⬇️ Download Deck Audio (.wav)</a>
                    {narrationData && <span className="tag" style={{ background: '#e0f2fe', color: '#0369a1' }}>Synthesized: {narrationData.total_duration_seconds}s ({narrationData.total_words} words)</span>}
                  </div>
                </div>
              </div>
            </div>
          ) : <div className="state-panel"><p>No slides.</p></div>}
        </main>
      </div>
      {showAddSlide && (
        <div className="modal-overlay" onClick={() => setShowAddSlide(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add New Slide</h3>
              <button className="btn-close" onClick={() => setShowAddSlide(false)}>&times;</button>
            </div>
            <form onSubmit={handleCreateSlide}>
              <div className="form-group">
                <label>Type</label>
                <select className="form-control" value={newType} onChange={(e) => setNewType(e.target.value)}>
                  <option value="content">Content with Bullets</option>
                  <option value="kpi">Key Metric / KPI</option>
                  <option value="table">Data Table</option>
                  <option value="conclusion">Summary / Conclusion</option>
                </select>
              </div>
              <div className="form-group">
                <label>Title</label>
                <input type="text" className="form-control" value={newTitle} onChange={(e) => setNewTitle(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Body Bullets</label>
                <textarea className="form-control" rows={3} value={newBody} onChange={(e) => setNewBody(e.target.value)} />
              </div>
              <div className="form-group">
                <label>Speaker Notes</label>
                <textarea className="form-control" rows={2} value={newNotes} onChange={(e) => setNewNotes(e.target.value)} />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowAddSlide(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={adding}>{adding ? 'Adding…' : 'Add Slide'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
