import React, { useState } from 'react';
import { DeckSummary, EvaluationOut, EvaluationComparisonResponse } from '../types';
import { api } from '../api';

const BASE = '/api';
const evalExportJson = (id: string) => `${BASE}/evaluations/${id}/export/json`;
const evalExportMarkdown = (id: string) => `${BASE}/evaluations/${id}/export/markdown`;

interface Props { decks: DeckSummary[]; evaluations: EvaluationOut[]; loading: boolean; selectedDeckId: string | null; onSelectDeck: (id: string) => void; onRunEval: (id: string, opt: { eval_type: string; request_llm_advisory: boolean }) => Promise<void>; }

const GS = (v: number | null) => v == null ? <span className="tag">N/A</span> : (() => { const p = Math.round(v * 100); return <span className={`score-badge ${v >= 0.8 ? 'badge-good' : v >= 0.6 ? 'badge-med' : 'badge-low'}`}>{p}%</span>; })();


export const ObservatoryView: React.FC<Props> = ({ decks, evaluations, loading, selectedDeckId, onSelectDeck, onRunEval }) => {
  const [et, setEt] = useState('full'), [rl, setRl] = useState(false), [ru, setRu] = useState(false), [re, setRe] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'single' | 'compare'>('single');
  const [selectedEvalIds, setSelectedEvalIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<EvaluationComparisonResponse | null>(null);
  const [compLoading, setCompLoading] = useState(false);
  const [compError, setCompError] = useState<string | null>(null);
  const aid = selectedDeckId || (decks[0]?.id ?? null);
  const le = evaluations.find(e => e.deck_id === aid) || null;
  const hr = async () => { if (!aid) return; setRu(true); setRe(null); try { await onRunEval(aid, { eval_type: et, request_llm_advisory: rl }); } catch (err: unknown) { setRe(err instanceof Error ? err.message : 'Evaluation run failed'); } finally { setRu(false); } };
  const hc = async () => { if (selectedEvalIds.length < 2) { setCompError('Select at least 2 evaluations to compare'); return; } setCompLoading(true); setCompError(null); setComparison(null); try { const data = await api.evaluations.compare(selectedEvalIds); setComparison(data); } catch (err: unknown) { setCompError(err instanceof Error ? err.message : 'Comparison failed'); } finally { setCompLoading(false); } };
  const toggleEval = (eid: string) => { setSelectedEvalIds(prev => prev.includes(eid) ? prev.filter(x => x !== eid) : [...prev, eid]); };
  return (
    <div className="observatory-container">
      <div className="section-header"><div><h2>Slide-Intelligence Observatory</h2><p className="section-desc">Cognitive load benchmarking, numeric claim verification, and attribution diagnostics.</p></div></div>
      <div className="observatory-controls card">
        <div className="control-group"><label>Mode</label><select className="select-input" value={viewMode} onChange={e => setViewMode(e.target.value as 'single' | 'compare')}>
          <option value="single">Single Evaluation</option>
          <option value="compare">Compare Evaluations</option>
        </select></div>
        {viewMode === 'single' && (
          <>
            <div className="control-group"><label>Target Presentation</label><select className="select-input" value={aid || ''} onChange={e => onSelectDeck(e.target.value)}>{decks.map(d => <option key={d.id} value={d.id}>{d.title} ({d.slide_count} slides)</option>)}</select></div>
            <div className="control-group"><label>Evaluation Type</label><select className="select-input" value={et} onChange={e => setEt(e.target.value)}><option value="full">Full Multi-Metric Evaluation</option><option value="cognitive_load">Cognitive Load</option><option value="data_fidelity">Data Fidelity</option><option value="attribution">Attribution Guard</option><option value="prompt_audit">Prompt & Locale Audit</option></select></div>
            <label style={{ fontSize: '.8rem' }}><input type="checkbox" checked={rl} onChange={e => setRl(e.target.checked)} /> Include LLM Advisory</label>
            <button className="btn-primary" onClick={hr} disabled={ru || !aid}>{ru ? 'Evaluating…' : 'Execute Evaluation'}</button>
          </>
        )}
        {viewMode === 'compare' && (
          <>
            <div className="control-group"><label>Select Evaluations to Compare (2-10)</label><div style={{ display: 'flex', flexWrap: 'wrap', gap: '.5rem' }}>
              {evaluations.map(e => (
                <label key={e.id} style={{ display: 'flex', alignItems: 'center', gap: '.3rem', padding: '.3rem .6rem', border: '1px solid var(--border)', borderRadius: '4px', background: selectedEvalIds.includes(e.id) ? 'var(--primary-bg)' : 'transparent', cursor: 'pointer' }}>
                  <input type="checkbox" checked={selectedEvalIds.includes(e.id)} onChange={() => toggleEval(e.id)} />
                  <span style={{ fontSize: '.85rem' }}>{e.id.slice(0,8)} ({e.eval_type}) - Deck: {e.deck_id.slice(0,8)}</span>
                  {e.overall_cognitive_score != null && <span className="tag" style={{ fontSize: '.7rem' }}>{Math.round(e.overall_cognitive_score * 100)}%</span>}
                </label>
              ))}
            </div></div>
            <button className="btn-primary" onClick={hc} disabled={compLoading || selectedEvalIds.length < 2}>{compLoading ? 'Comparing…' : 'Run Comparison'}</button>
          </>
        )}
      </div>
      {re && <div className="alert alert-error">{re}</div>}
      {compError && <div className="alert alert-error">{compError}</div>}
      {loading ? <div className="state-panel"><div className="spinner" /><p>Analyzing metrics…</p></div> : viewMode === 'single' ? !le ? <div className="state-panel"><h3>No evaluation records yet</h3><p>Run an evaluation to see results.</p></div> : (
        <div>
          <div className="metrics-grid">
            <div className="metric-card"><span className="metric-label">Overall Cognitive Score</span><div>{GS(le.overall_cognitive_score)}</div></div>
            <div className="metric-card"><span className="metric-label">Information Density</span><div>{GS(le.information_density_score)}</div></div>
            <div className="metric-card"><span className="metric-label">Readability Grade</span><div className="metric-val">{le.readability_grade ? `Grade ${le.readability_grade.toFixed(1)}` : 'N/A'}</div></div>
            <div className="metric-card"><span className="metric-label">Attribution Guard</span><div className="metric-val"><span className={`tag ${le.attribution_pass === 'pass' ? 'badge-good' : 'badge-low'}`}>{le.attribution_pass?.toUpperCase() || 'PASS'}</span></div></div>
            {le.prompt_audit_pass && <div className="metric-card"><span className="metric-label">Prompt & Locale Audit</span><div className="metric-val"><span className={`tag ${le.prompt_audit_pass === 'pass' ? 'badge-good' : 'badge-low'}`}>{le.prompt_audit_pass === 'pass' ? 'AUDIT OK' : 'AUDIT FAIL'}</span></div></div>}
          </div>
          <div className="card" style={{ marginTop: '1rem' }}>
            <div className="section-header"><h4>Export Evaluation Report</h4></div>
            <div className="card-actions">
              <a className="btn-secondary" href={evalExportJson(le.id)} download={`evaluation-${le.eval_type}-${le.id.slice(0,8)}.json`}>📄 Download JSON</a>
              <a className="btn-secondary" href={evalExportMarkdown(le.id)} download={`evaluation-${le.eval_type}-${le.id.slice(0,8)}.md`}>📝 Download Markdown</a>
            </div>
          </div>
          {le.llm_advisory && <div className="advisory-box"><h4>🤖 Advisory Insights ({le.llm_provider_used})</h4><p>{le.llm_advisory}</p></div>}
        </div>
      ) : comparison ? (
        <div>
          <div className="metrics-grid" style={{ marginBottom: '1rem' }}>
            {Object.entries(comparison.comparison).map(([key, m]) => (
              <div key={key} className="metric-card">
                <span className="metric-label">{m.label}</span>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '.3rem' }}>
                  {Object.entries(m.values).map(([eid, val]) => (
                    <div key={eid} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '.85rem' }}>
                      <span>{eid.slice(0,8)}</span>
                      <span style={{ fontWeight: 600, color: eid === m.best.id ? 'var(--success)' : eid === m.worst.id ? 'var(--danger)' : 'inherit' }}>
                        {key === 'readability_grade' ? `Grade ${val.toFixed(1)}` : `${Math.round(val * 100)}%`}
                      </span>
                    </div>
                  ))}
                  <div style={{ fontSize: '.7rem', color: 'var(--muted)' }}>Spread: {m.spread.toFixed(3)}</div>
                </div>
              </div>
            ))}
          </div>
          <div className="card" style={{ marginTop: '1rem' }}>
            <div className="section-header"><h4>Export Comparison Report</h4></div>
            <div className="card-actions">
              <a className="btn-secondary" href={api.evaluations.exportComparisonMarkdown(selectedEvalIds)} download={`evaluation_comparison_${selectedEvalIds[0].slice(0,8)}_et_al.md`}>📝 Download Markdown</a>
            </div>
          </div>
        </div>
      ) : (
        <div className="state-panel"><h3>No evaluations to compare</h3><p>Run evaluations on decks first, then select 2-10 to compare.</p></div>
      )}
    </div>
  );
};