import React, { useState } from 'react';
import { DeckOut, DeckNarrationOut } from '../types';
import { api } from '../api';

interface Props {
  deck: DeckOut; onBack: () => void;
  onAddSlide: (id: string, s: { slide_type: string; title: string; body_text: string; speaker_notes: string }) => Promise<void>;
  onRunEval: (id: string) => void;
}

const VOICES = [['narrator-en', 'Default Narrator'], ['narrator-exec', 'Executive Voice'], ['narrator-tech', 'Technical Voice'], ['narrator-calm', 'Calm Voice']];
const WPMS = [[120, 'Deliberate (120 WPM)'], [150, 'Standard (150 WPM)'], [180, 'Brisk (180 WPM)'], [210, 'Fast (210 WPM)']] as const;
const TYPES = [['content', 'Content with Bullets'], ['kpi', 'Key Metric / KPI'], ['table', 'Data Table'], ['conclusion', 'Summary / Conclusion']];

export const DeckDetail: React.FC<Props> = ({ deck, onBack, onAddSlide, onRunEval }) => {
  const [slideIdx, setSlideIdx] = useState(0), [showAdd, setShowAdd] = useState(false);
  const [title, setTitle] = useState(''), [body, setBody] = useState(''), [notes, setNotes] = useState(''), [type, setType] = useState('content');
  const [adding, setAdding] = useState(false), [voice, setVoice] = useState('narrator-en'), [wpm, setWpm] = useState(150), [synth, setSynth] = useState(false);
  const [narration, setNarration] = useState<DeckNarrationOut | null>(null), [audioTs, setAudioTs] = useState(Date.now());
  const slides = deck.slides || [], cur = slides[slideIdx];

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault(); setAdding(true);
    try {
      await onAddSlide(deck.id, { slide_type: type, title, body_text: body, speaker_notes: notes });
      setShowAdd(false); setTitle(''); setBody(''); setNotes(''); setSlideIdx(slides.length);
    } finally { setAdding(false); }
  };

  const handleSynth = async () => {
    setSynth(true);
    try { setNarration(await api.decks.synthesizeNarration(deck.id, voice, wpm)); setAudioTs(Date.now()); }
    finally { setSynth(false); }
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
        <div className="card-meta"><span className="tag">{deck.source_type}</span><span className="tag status-tag">{deck.status}</span><span className="tag">{slides.length} slides</span></div>
      </div>
      <div className="detail-layout">
        <aside className="slide-list-sidebar">
          <div className="sidebar-header"><h4>Slides ({slides.length})</h4><button className="btn-link" onClick={() => setShowAdd(true)}>+ Add Slide</button></div>
          <div className="slide-thumbnails">
            {slides.map((s, idx) => (
              <div key={s.id} className={`slide-thumb-card ${idx === slideIdx ? 'active' : ''}`} onClick={() => setSlideIdx(idx)}>
                <div>#{s.position}</div>
                <div><div style={{ fontSize: '.85rem', fontWeight: 600 }}>{s.title || `Slide ${s.position}`}</div><span className="tag">{s.slide_type}</span></div>
              </div>
            ))}
          </div>
        </aside>
        <main>
          {cur ? (
            <div>
              <div className="slide-canvas">
                <span className="tag">{cur.slide_type.toUpperCase()}</span>
                <h3 style={{ marginTop: '.5rem', fontSize: '1.2rem' }}>{cur.title}</h3>
                {cur.body_text && <div className="canvas-bullets" style={{ marginTop: '1rem' }}>{cur.body_text.split('\n').map((l, i) => <div key={i}>• {l}</div>)}</div>}
              </div>
              <div className="speaker-notes-panel">
                <h4>🎙️ Speaker Notes</h4>
                <p style={{ marginTop: '.3rem', fontSize: '.9rem', color: 'var(--muted)' }}>{cur.speaker_notes || 'No speaker notes.'}</p>
              </div>
              <div className="speaker-notes-panel" style={{ marginTop: '1rem' }} data-testid="narration-panel">
                <div className="section-header">
                  <h4>🎧 Audio Narration</h4>
                  <div className="card-actions">
                    <select aria-label="Narration Voice" className="form-control select-sm" value={voice} onChange={(e) => setVoice(e.target.value)}>{VOICES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                    <select aria-label="Narration Pace" data-testid="narration-wpm-select" className="form-control select-sm" value={wpm} onChange={(e) => setWpm(Number(e.target.value))}>{WPMS.map(([p, l]) => <option key={p} value={p}>{l}</option>)}</select>
                    <button className="btn-primary btn-sm" onClick={handleSynth} disabled={synth}>{synth ? 'Synthesizing…' : 'Synthesize Audio'}</button>
                  </div>
                </div>
                <div style={{ marginTop: '.75rem' }}>
                  <p style={{ fontSize: '.85rem', color: 'var(--muted)', marginBottom: '.5rem' }}>Deck Narration Audio (RIFF/WAVE PCM track):</p>
                  <audio data-testid="deck-audio-player" controls className="audio-player" src={`${api.decks.narrationAudioUrl(deck.id, voice, wpm)}&t=${audioTs}`} />
                  <div className="card-actions">
                    <a className="btn-secondary btn-sm" href={api.decks.narrationAudioUrl(deck.id, voice, wpm)} download={`${deck.title.replace(/\s+/g, '_')}_narration.wav`}>⬇️ Download Deck Audio (.wav)</a>
                    {narration && <span className="tag tag-info">Synthesized: {narration.total_duration_seconds}s ({narration.total_words} words @ {wpm} wpm)</span>}
                  </div>
                </div>
              </div>
            </div>
          ) : <div className="state-panel"><p>No slides.</p></div>}
        </main>
      </div>
      {showAdd && (
        <div className="modal-overlay" onClick={() => setShowAdd(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header"><h3>Add New Slide</h3><button className="btn-close" onClick={() => setShowAdd(false)}>&times;</button></div>
            <form onSubmit={handleAdd}>
              <div className="form-group"><label>Type</label><select className="form-control" value={type} onChange={(e) => setType(e.target.value)}>{TYPES.map(([t, l]) => <option key={t} value={t}>{l}</option>)}</select></div>
              <div className="form-group"><label>Title</label><input type="text" className="form-control" value={title} onChange={(e) => setTitle(e.target.value)} required /></div>
              <div className="form-group"><label>Body Bullets</label><textarea className="form-control" rows={3} value={body} onChange={(e) => setBody(e.target.value)} /></div>
              <div className="form-group"><label>Speaker Notes</label><textarea className="form-control" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} /></div>
              <div className="modal-footer"><button type="button" className="btn-secondary" onClick={() => setShowAdd(false)}>Cancel</button><button type="submit" className="btn-primary" disabled={adding}>{adding ? 'Adding…' : 'Add Slide'}</button></div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
