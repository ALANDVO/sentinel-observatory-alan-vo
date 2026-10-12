import React, { useState } from 'react';
import { DeckSummary, EvaluationOut } from '../types';

interface Props { decks: DeckSummary[]; evaluations: EvaluationOut[]; loading: boolean; selectedDeckId: string | null; onSelectDeck: (id: string) => void; onRunEval: (id: string, opt: { eval_type: string; request_llm_advisory: boolean }) => Promise<void>; }

const GS = (v: number | null) => v == null ? <span className="tag">N/A</span> : (() => { const p = Math.round(v * 100); return <span className={`score-badge ${v >= 0.8 ? 'badge-good' : v >= 0.6 ? 'badge-med' : 'badge-low'}`}>{p}%</span>; })();

export const ObservatoryView: React.FC<Props> = ({ decks, evaluations, loading, selectedDeckId, onSelectDeck, onRunEval }) => {
  const [et, setEt] = useState('full'), [rl, setRl] = useState(false), [ru, setRu] = useState(false), [re, setRe] = useState<string | null>(null);
  const aid = selectedDeckId || (decks[0]?.id ?? null);
  const le = evaluations.find(e => e.deck_id === aid) || null;
  const hr = async () => { if (!aid) return; setRu(true); setRe(null); try { await onRunEval(aid, { eval_type: et, request_llm_advisory: rl }); } catch (err: unknown) { setRe(err instanceof Error ? err.message : 'Evaluation run failed'); } finally { setRu(false); } };
  return (
    <div className="observatory-container">
      <div className="section-header"><div><h2>Slide-Intelligence Observatory</h2><p className="section-desc">Cognitive load benchmarking, numeric claim verification, and attribution diagnostics.</p></div></div>
      <div className="observatory-controls card">
        <div className="control-group"><label>Target Presentation</label><select className="select-input" value={aid || ''} onChange={e => onSelectDeck(e.target.value)}>{decks.map(d => <option key={d.id} value={d.id}>{d.title} ({d.slide_count} slides)</option>)}</select></div>
        <div className="control-group"><label>Mode</label><select className="select-input" value={et} onChange={e => setEt(e.target.value)}><option value="full">Full Multi-Metric Evaluation</option><option value="cognitive_load">Cognitive Load</option><option value="data_fidelity">Data Fidelity</option><option value="attribution">Attribution Guard</option><option value="prompt_audit">Prompt & Locale Audit</option></select></div>
        <label style={{ fontSize: '.8rem' }}><input type="checkbox" checked={rl} onChange={e => setRl(e.target.checked)} /> Include LLM Advisory</label>
        <button className="btn-primary" onClick={hr} disabled={ru || !aid}>{ru ? 'Evaluating…' : 'Execute Evaluation'}</button>
      </div>
      {re && <div className="alert alert-error">{re}</div>}
      {loading ? <div className="state-panel"><div className="spinner" /><p>Analyzing metrics…</p></div> : !le ? <div className="state-panel"><h3>No evaluation records yet</h3></div> : (
        <div>
          <div className="metrics-grid">
            <div className="metric-card"><span className="metric-label">Overall Cognitive Score</span><div>{GS(le.overall_cognitive_score)}</div></div>
            <div className="metric-card"><span className="metric-label">Information Density</span><div>{GS(le.information_density_score)}</div></div>
            <div className="metric-card"><span className="metric-label">Readability Grade</span><div className="metric-val">{le.readability_grade ? `Grade ${le.readability_grade.toFixed(1)}` : 'N/A'}</div></div>
            <div className="metric-card"><span className="metric-label">Attribution Guard</span><div className="metric-val"><span className={`tag ${le.attribution_pass === 'pass' ? 'badge-good' : 'badge-low'}`}>{le.attribution_pass?.toUpperCase() || 'PASS'}</span></div></div>
            {le.prompt_audit_pass && <div className="metric-card"><span className="metric-label">Prompt & Locale Audit</span><div className="metric-val"><span className={`tag ${le.prompt_audit_pass === 'pass' ? 'badge-good' : 'badge-low'}`}>{le.prompt_audit_pass === 'pass' ? 'AUDIT OK' : 'AUDIT FAIL'}</span></div></div>}
          </div>
          {le.llm_advisory && <div className="advisory-box"><h4>🤖 Advisory Insights ({le.llm_provider_used})</h4><p>{le.llm_advisory}</p></div>}
        </div>
      )}
    </div>
  );
};