import React, { useState } from 'react';
import { DeckSummary, EvaluationOut } from '../types';

interface ObservatoryViewProps {
  decks: DeckSummary[];
  evaluations: EvaluationOut[];
  loading: boolean;
  selectedDeckId: string | null;
  onSelectDeck: (deckId: string) => void;
  onRunEval: (deckId: string, options: { eval_type: string; request_llm_advisory: boolean }) => Promise<void>;
}

export const ObservatoryView: React.FC<ObservatoryViewProps> = ({
  decks, evaluations, loading, selectedDeckId, onSelectDeck, onRunEval,
}) => {
  const [evalType, setEvalType] = useState('full');
  const [requestLlm, setRequestLlm] = useState(false);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  const activeDeckId = selectedDeckId || (decks.length > 0 ? decks[0].id : null);
  const deckEvals = evaluations.filter((e) => e.deck_id === activeDeckId);
  const latestEval = deckEvals[0] || null;

  const handleRun = async () => {
    if (!activeDeckId) return;
    setRunning(true);
    setRunError(null);
    try {
      await onRunEval(activeDeckId, { eval_type: evalType, request_llm_advisory: requestLlm });
    } catch (err: unknown) {
      setRunError(err instanceof Error ? err.message : 'Evaluation run failed');
    } finally {
      setRunning(false);
    }
  };

  const getScore = (val: number | null) => {
    if (val === null || val === undefined) return <span className="tag">N/A</span>;
    const p = Math.round(val * 100);
    const cls = val >= 0.8 ? 'badge-good' : val >= 0.6 ? 'badge-med' : 'badge-low';
    return <span className={`score-badge ${cls}`}>{p}%</span>;
  };

  return (
    <div className="observatory-container">
      <div className="section-header">
        <div>
          <h2>Slide-Intelligence Observatory</h2>
          <p className="section-desc">Cognitive load benchmarking, numeric claim verification, and attribution diagnostics.</p>
        </div>
      </div>

      <div className="observatory-controls card">
        <div className="control-group">
          <label>Target Presentation</label>
          <select className="select-input" value={activeDeckId || ''} onChange={(e) => onSelectDeck(e.target.value)}>
            {decks.map((d) => (
              <option key={d.id} value={d.id}>{d.title} ({d.slide_count} slides)</option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label>Mode</label>
          <select className="select-input" value={evalType} onChange={(e) => setEvalType(e.target.value)}>
            <option value="full">Full Multi-Metric Evaluation</option>
            <option value="cognitive_load">Cognitive Load</option>
            <option value="data_fidelity">Data Fidelity</option>
            <option value="attribution">Attribution Guard</option>
          </select>
        </div>

        <label style={{ fontSize: '.8rem' }}>
          <input type="checkbox" checked={requestLlm} onChange={(e) => setRequestLlm(e.target.checked)} /> Include LLM Advisory
        </label>

        <button className="btn-primary" onClick={handleRun} disabled={running || !activeDeckId}>
          {running ? 'Evaluating…' : 'Execute Evaluation'}
        </button>
      </div>

      {runError && <div className="alert alert-error">{runError}</div>}

      {loading ? (
        <div className="state-panel"><div className="spinner" /><p>Analyzing metrics…</p></div>
      ) : !latestEval ? (
        <div className="state-panel"><h3>No evaluation records yet</h3></div>
      ) : (
        <div>
          <div className="metrics-grid">
            <div className="metric-card"><span className="metric-label">Overall Cognitive Score</span><div>{getScore(latestEval.overall_cognitive_score)}</div></div>
            <div className="metric-card"><span className="metric-label">Information Density</span><div>{getScore(latestEval.information_density_score)}</div></div>
            <div className="metric-card"><span className="metric-label">Readability Grade</span><div className="metric-val">{latestEval.readability_grade ? `Grade ${latestEval.readability_grade.toFixed(1)}` : 'N/A'}</div></div>
            <div className="metric-card"><span className="metric-label">Attribution Guard</span><div className="metric-val"><span className={`tag ${latestEval.attribution_pass === 'pass' ? 'badge-good' : 'badge-low'}`}>{latestEval.attribution_pass?.toUpperCase() || 'PASS'}</span></div></div>
          </div>
          {latestEval.llm_advisory && (
            <div className="advisory-box" style={{ marginTop: '1rem', padding: '1rem', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
              <h4>🤖 Advisory Insights ({latestEval.llm_provider_used})</h4>
              <p style={{ fontSize: '.9rem', color: '#334155' }}>{latestEval.llm_advisory}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
