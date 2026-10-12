import React, { useState } from 'react';
import { DeckSummary, EvaluationOut, EvaluationComparisonResponse } from '../types';
import { api } from '../api';
const BASE = '/api', evalExportJson = (id: string) => `${BASE}/evaluations/${id}/export/json`, evalExportMarkdown = (id: string) => `${BASE}/evaluations/${id}/export/markdown`;
interface Props { decks: DeckSummary[]; evaluations: EvaluationOut[]; loading: boolean; selectedDeckId: string | null; onSelectDeck: (id: string) => void; onRunEval: (id: string, opt: { eval_type: string; request_llm_advisory: boolean }) => Promise<void>; }
const GS = (v: number | null) => v == null ? <span className="tag">N/A</span> : <span className={`score-badge ${v >= 0.8 ? 'badge-good' : v >= 0.6 ? 'badge-med' : 'badge-low'}`}>{Math.round(v * 100)}%</span>;
export const ObservatoryView: React.FC<Props> = ({ decks, evaluations, loading, selectedDeckId, onSelectDeck, onRunEval }) => {
  const [et, setEt] = useState('full'), [rl, setRl] = useState(false), [ru, setRu] = useState(false), [re, setRe] = useState<string | null>(null);
  const [vm, setVm] = useState<'single' | 'compare'>('single');
  const [sel, setSel] = useState<string[]>([]);
  const [comp, setComp] = useState<EvaluationComparisonResponse | null>(null);
  const [cl, setCl] = useState(false), [ce, setCe] = useState<string | null>(null);
  const aid = selectedDeckId || (decks[0]?.id ?? null);
  const le = evaluations.find(e => e.deck_id === aid) || null;
  const hr = async () => { if (!aid) return; setRu(true); setRe(null); try { await onRunEval(aid, { eval_type: et, request_llm_advisory: rl }); } catch (err: unknown) { setRe(err instanceof Error ? err.message : 'Evaluation run failed'); } finally { setRu(false); } };
  const hc = async () => { if (sel.length < 2) { setCe('Select at least 2 evaluations to compare'); return; } setCl(true); setCe(null); setComp(null); try { setComp(await api.evaluations.compare(sel)); } catch (err: unknown) { setCe(err instanceof Error ? err.message : 'Comparison failed'); } finally { setCl(false); } };
  const tog = (eid: string) => setSel(p => p.includes(eid) ? p.filter(x => x !== eid) : [...p, eid]);
  return (
    <div className="observatory-container">
      <div className="section-header"><div><h2>Slide-Intelligence Observatory</h2><p className="section-desc">Cognitive load benchmarking, numeric claim verification, and attribution diagnostics.</p></div></div>
      <div className="observatory-controls card">
        <div className="control-group"><label>Mode</label><select className="select-input" value={vm} onChange={e => setVm(e.target.value as 'single' | 'compare')}>
          <option value="single">Single Evaluation</option>
          <option value="compare">Compare Evaluations</option>
        </select></div>
        {vm === 'single' && (
          <>
            <div className="control-group"><label>Target Presentation</label><select className="select-input" value={aid || ''} onChange={e => onSelectDeck(e.target.value)}>{decks.map(d => <option key={d.id} value={d.id}>{d.title} ({d.slide_count} slides)</option>)}</select></div>
            <div className="control-group"><label>Evaluation Type</label><select className="select-input" value={et} onChange={e => setEt(e.target.value)}><option value="full">Full Multi-Metric Evaluation</option><option value="cognitive_load">Cognitive Load</option><option value="data_fidelity">Data Fidelity</option><option value="attribution">Attribution Guard</option><option value="prompt_audit">Prompt & Locale Audit</option></select></div>
            <label className="fs-8"><input type="checkbox" checked={rl} onChange={e => setRl(e.target.checked)} /> Include LLM Advisory</label>
            <button className="btn-primary" onClick={hr} disabled={ru || !aid}>{ru ? 'Evaluating…' : 'Execute Evaluation'}</button>
          </>
        )}
        {vm === 'compare' && (
          <>
            <div className="control-group"><label>Select Evaluations to Compare (2-10)</label><div className="flex-wrap">
              {evaluations.map(e => (
                <label key={e.id} className={`pill ${sel.includes(e.id) ? 'pill-active' : ''}`}>
                  <input type="checkbox" checked={sel.includes(e.id)} onChange={() => tog(e.id)} />
                  <span className="fs-85">{e.id.slice(0,8)} ({e.eval_type}) - Deck: {e.deck_id.slice(0,8)}</span>
                  {e.overall_cognitive_score != null && <span className="tag fs-7">{Math.round(e.overall_cognitive_score * 100)}%</span>}
                </label>
              ))}
            </div></div>
            <button className="btn-primary" onClick={hc} disabled={cl || sel.length < 2}>{cl ? 'Comparing…' : 'Run Comparison'}</button>
          </>
        )}
      </div>
      {re && <div className="alert alert-error">{re}</div>}
      {ce && <div className="alert alert-error">{ce}</div>}
      {loading ? <div className="state-panel"><div className="spinner" /><p>Analyzing metrics…</p></div> : vm === 'single' ? !le ? <div className="state-panel"><h3>No evaluation records yet</h3><p>Run an evaluation to see results.</p></div> : (
        <div>
          <div className="metrics-grid">
            <div className="metric-card"><span className="metric-label">Overall Cognitive Score</span><div>{GS(le.overall_cognitive_score)}</div></div>
            <div className="metric-card"><span className="metric-label">Information Density</span><div>{GS(le.information_density_score)}</div></div>
            <div className="metric-card"><span className="metric-label">Readability Grade</span><div className="metric-val">{le.readability_grade ? `Grade ${le.readability_grade.toFixed(1)}` : 'N/A'}</div></div>
            <div className="metric-card"><span className="metric-label">Attribution Guard</span><div className="metric-val"><span className={`tag ${le.attribution_pass === 'pass' ? 'badge-good' : 'badge-low'}`}>{le.attribution_pass?.toUpperCase() || 'PASS'}</span></div></div>
            {le.prompt_audit_pass && <div className="metric-card"><span className="metric-label">Prompt & Locale Audit</span><div className="metric-val"><span className={`tag ${le.prompt_audit_pass === 'pass' ? 'badge-good' : 'badge-low'}`}>{le.prompt_audit_pass === 'pass' ? 'AUDIT OK' : 'AUDIT FAIL'}</span></div></div>}
          </div>
          <div className="card mt-1">
            <div className="section-header"><h4>Export Evaluation Report</h4></div>
            <div className="card-actions">
              <a className="btn-secondary" href={evalExportJson(le.id)} download={`evaluation-${le.eval_type}-${le.id.slice(0,8)}.json`}>📄 Download JSON</a>
              <a className="btn-secondary" href={evalExportMarkdown(le.id)} download={`evaluation-${le.eval_type}-${le.id.slice(0,8)}.md`}>📝 Download Markdown</a>
            </div>
          </div>
          {le.llm_advisory && <div className="advisory-box"><h4>🤖 Advisory Insights ({le.llm_provider_used})</h4><p>{le.llm_advisory}</p></div>}
        </div>
      ) : comp ? (
        <div>
          <div className="metrics-grid mb-1">
            {Object.entries(comp.comparison).map(([key, m]) => (
              <div key={key} className="metric-card">
                <span className="metric-label">{m.label}</span>
                <div className="flex-col">
                  {Object.entries(m.values).map(([eid, val]) => (
                    <div key={eid} className="flex-between fs-85">
                      <span>{eid.slice(0,8)}</span>
                      <span className={`fw-6 ${eid === m.best.id ? 'text-success' : eid === m.worst.id ? 'text-danger' : 'text-inherit'}`}>
                        {key === 'readability_grade' ? `Grade ${val.toFixed(1)}` : `${Math.round(val * 100)}%`}
                      </span>
                    </div>
                  ))}
                  <div className="fs-7 text-muted">Spread: {m.spread.toFixed(3)}</div>
                </div>
              </div>
            ))}
          </div>
          <div className="card mt-1">
            <div className="section-header"><h4>Export Comparison Report</h4></div>
            <div className="card-actions">
              <a className="btn-secondary" href={api.evaluations.exportComparisonMarkdown(sel)} download={`evaluation_comparison_{sel[0].slice(0,8)}_et_al.md`}>📝 Download Markdown</a>
            </div>
          </div>
        </div>
      ) : (
        <div className="state-panel"><h3>No evaluations to compare</h3><p>Run evaluations on decks first, then select 2-10 to compare.</p></div>
      )}
    </div>
  );
};