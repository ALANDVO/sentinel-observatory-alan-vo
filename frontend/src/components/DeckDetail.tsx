import React, { useState } from 'react';
import { DeckOut, DeckNarrationOut } from '../types';
import { api } from '../api';
interface Props { deck: DeckOut; onBack: () => void; onAddSlide: (id: string, s: { slide_type: string; title: string; body_text: string; speaker_notes: string }) => Promise<void>; onRunEval: (id: string) => void; }
const V = [['narrator-en', 'Default Narrator'], ['narrator-exec', 'Executive Voice'], ['narrator-tech', 'Technical Voice'], ['narrator-calm', 'Calm Voice']] as const;
const W = [[120, 'Deliberate (120 WPM)'], [150, 'Standard (150 WPM)'], [180, 'Brisk (180 WPM)'], [210, 'Fast (210 WPM)']] as const;
const T = [['content', 'Content with Bullets'], ['kpi', 'Key Metric / KPI'], ['table', 'Data Table'], ['conclusion', 'Summary / Conclusion']] as const;
export const DeckDetail: React.FC<Props> = ({ deck, onBack, onAddSlide, onRunEval }) => {
  const [si, setSi] = useState(0), [sa, setSa] = useState(false);
  const [tl, setTl] = useState(''), [bd, setBd] = useState(''), [nt, setNt] = useState(''), [tp, setTp] = useState('content');
  const [ad, setAd] = useState(false), [vc, setVc] = useState('narrator-en'), [wp, setWp] = useState(150), [sy, setSy] = useState(false);
  const [nr, setNr] = useState<DeckNarrationOut | null>(null);
  const sl = deck.slides || [], cu = sl[si];
  const ha = async (e: React.FormEvent) => { e.preventDefault(); setAd(true); try { await onAddSlide(deck.id, { slide_type: tp, title: tl, body_text: bd, speaker_notes: nt }); setSa(false); setTl(''); setBd(''); setNt(''); setSi(sl.length); } finally { setAd(false); } };
  const hs = async () => { setSy(true); try { setNr(await api.decks.synthesizeNarration(deck.id, vc, wp)); } finally { setSy(false); } };
  const sc = cu ? (
    <div>
      <div className="slide-canvas"><span className="tag">{cu.slide_type.toUpperCase()}</span><h3 style={{ marginTop: '.5rem', fontSize: '1.2rem' }}>{cu.title}</h3>{cu.body_text && <div className="canvas-bullets" style={{ marginTop: '1rem' }}>{cu.body_text.split('\n').map((l, i) => <div key={i}>• {l}</div>)}</div>}</div>
      <div className="speaker-notes-panel"><h4>🎙️ Speaker Notes</h4><p style={{ marginTop: '.3rem', fontSize: '.9rem', color: 'var(--muted)' }}>{cu.speaker_notes || 'No speaker notes.'}</p></div>
      <div className="speaker-notes-panel" style={{ marginTop: '1rem' }} data-testid="narration-panel">
        <div className="section-header"><h4>🎧 Audio Narration</h4></div>
        <div className="card-actions">
          <select aria-label="Voice" className="form-control select-sm" value={vc} onChange={e => setVc(e.target.value)}>{V.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
          <select aria-label="Pace" data-testid="narration-wpm-select" className="form-control select-sm" value={wp} onChange={e => setWp(Number(e.target.value))}>{W.map(([p, l]) => <option key={p} value={p}>{l}</option>)}</select>
          <button className="btn-primary btn-sm" onClick={hs} disabled={sy}>{sy ? 'Synthesizing…' : 'Synthesize Audio'}</button>
        </div>
        <div style={{ marginTop: '.5rem' }}>{nr && <div className="audio-playback"><div className="card-actions"><audio controls src={api.decks.narrationAudioUrl(deck.id, vc, wp)} style={{ width: '100%' }}></audio><a className="btn-secondary btn-sm" href={api.decks.narrationAudioUrl(deck.id, vc, wp)} download={`${deck.title}-narration.wav`}>Download</a></div><span className="tag tag-info">Synthesized: {nr.total_duration_seconds}s ({nr.total_words} words @ {wp} wpm)</span></div>}</div>
      </div>
    </div>
  ) : <div className="state-panel"><p>No slides.</p></div>;
  return (
    <div className="deck-detail-container">
      <div className="detail-top-bar"><button className="btn-secondary btn-sm" onClick={onBack}>&larr; Back</button><div className="detail-actions"><button className="btn-secondary" onClick={() => onRunEval(deck.id)}>🔍 Observatory</button><button className="btn-primary" onClick={() => window.open(api.decks.exportPptxUrl(deck.id), '_blank')}>💾 Export .pptx</button></div></div>
      <div className="detail-header" style={{ margin: '1rem 0' }}><h2>{deck.title}</h2><div className="card-meta"><span className="tag">{deck.source_type}</span><span className="tag status-tag">{deck.status}</span><span className="tag">{sl.length} slides</span></div></div>
      <div className="detail-layout"><aside className="slide-list-sidebar"><div className="sidebar-header"><h4>Slides ({sl.length})</h4><button className="btn-link" onClick={() => setSa(true)}>+ Add Slide</button></div><div className="slide-thumbnails">{sl.map((s, idx) => (<div key={s.id} className={`slide-thumb-card ${idx === si ? 'active' : ''}`} onClick={() => setSi(idx)}><div>#{s.position}</div><div><div style={{ fontSize: '.85rem', fontWeight: 600 }}>{s.title || `Slide ${s.position}`}</div><span className="tag">{s.slide_type}</span></div></div>))}</div></aside><main>{sc}</main></div>
      {sa && <div className="modal-overlay" onClick={() => setSa(false)}><div className="modal-dialog" onClick={e => e.stopPropagation()}><div className="modal-header"><h3>Add New Slide</h3><button className="btn-close" onClick={() => setSa(false)}>&times;</button></div><form onSubmit={ha}><div className="form-group"><label>Type</label><select className="form-control" value={tp} onChange={e => setTp(e.target.value)}>{T.map(([t, l]) => <option key={t} value={t}>{l}</option>)}</select></div><div className="form-group"><label>Title</label><input type="text" className="form-control" value={tl} onChange={e => setTl(e.target.value)} required /></div><div className="form-group"><label>Body Bullets</label><textarea className="form-control" value={bd} onChange={e => setBd(e.target.value)} /></div><div className="form-group"><label>Speaker Notes</label><textarea className="form-control" value={nt} onChange={e => setNt(e.target.value)} /></div><div className="modal-footer"><button className="btn-secondary" type="button" onClick={() => setSa(false)}>Cancel</button><button className="btn-primary" type="submit" disabled={ad}>{ad ? 'Adding…' : 'Add Slide'}</button></div></form></div></div>}
    </div>
  );
};