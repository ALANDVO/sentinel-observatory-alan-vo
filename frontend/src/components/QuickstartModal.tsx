import React, { useState } from 'react';
interface Props {
  isOpen: boolean; onClose: () => void;
  onSelectPreset: (topic: string, slideCount: number) => void;
}
export const PRESETS = [
  { id: 'ai-eval', title: 'AI Safety & Alignment Evaluation', topic: 'Frontier LLM Alignment & Safety Guardrails Evaluation', slides: 8, category: 'AI Research', desc: '8-slide deck with metrics.' },
  { id: 'exec-strategy', title: 'Executive AI Strategy & Roadmap', topic: 'Enterprise AI Strategy 2026: Infrastructure & ROI', slides: 6, category: 'Executive Brief', desc: '6-slide executive brief.' },
  { id: 'ml-benchmarks', title: 'ML System Performance & Benchmarks', topic: 'Distributed Deep Learning Inference Benchmarks', slides: 10, category: 'Engineering', desc: '10-slide benchmark deck.' },
];
export const QuickstartModal: React.FC<Props> = ({ isOpen, onClose, onSelectPreset }) => {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  if (!isOpen) return null;
  return (
    <div className="modal-overlay" data-testid="quickstart-modal" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header"><h3>🚀 Quickstart Onboarding & Presets</h3><button className="btn-close" onClick={onClose}>&times;</button></div>
        <div className="tab-pills" style={{ marginBottom: '1rem' }}>
          {(['1. Presets', '2. Workflows', '3. Docs'] as const).map((l, i) => (
            <button key={l} className={`tab-pill ${step === i + 1 ? 'active' : ''}`} onClick={() => setStep((i + 1) as 1 | 2 | 3)}>{l}</button>
          ))}
        </div>
        {step === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.6rem' }}>
            {PRESETS.map((p) => (
              <div key={p.id} className="card" style={{ cursor: 'pointer' }} onClick={() => { onSelectPreset(p.topic, p.slides); onClose(); }}>
                <div className="card-top"><h4>{p.title}</h4><span className="tag">{p.category}</span></div>
                <p style={{ margin: '.25rem 0 0', fontSize: '.8rem', color: 'var(--muted)' }}>{p.desc}</p>
              </div>
            ))}
          </div>
        )}
        {step === 2 && (
          <div style={{ fontSize: '.85rem' }}>
            <h4>Capabilities</h4>
            <p style={{ marginTop: '.35rem', color: 'var(--muted)' }}>Native PPTX generation, slide observatory metrics, audio narration, and template studio.</p>
          </div>
        )}
        {step === 3 && (
          <div style={{ fontSize: '.85rem' }}>
            <h4>Documentation Hub</h4>
            <p style={{ marginTop: '.35rem', color: 'var(--muted)' }}>Refer to docs/quickstart.md, docs/zh/quickstart.md, and README.md for setup.</p>
          </div>
        )}
        <div className="modal-footer"><button className="btn-secondary" onClick={onClose}>Close</button></div>
      </div>
    </div>
  );
};