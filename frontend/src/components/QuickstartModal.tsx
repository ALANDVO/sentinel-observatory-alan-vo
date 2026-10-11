import React, { useState } from 'react';

interface QuickstartModalProps {
  isOpen: boolean; onClose: () => void;
  onSelectPreset: (topic: string, slideCount: number) => void;
}

export const PRESETS = [
  { id: 'ai-eval', title: 'AI Safety & Alignment Evaluation', topic: 'Frontier LLM Alignment & Safety Guardrails Evaluation', slides: 8, category: 'AI Research', desc: '8-slide deck with metrics.' },
  { id: 'exec-strategy', title: 'Executive AI Strategy & Roadmap', topic: 'Enterprise AI Strategy 2026: Infrastructure & ROI', slides: 6, category: 'Executive Brief', desc: '6-slide executive brief.' },
  { id: 'ml-benchmarks', title: 'ML System Performance & Benchmarks', topic: 'Distributed Deep Learning Inference Benchmarks', slides: 10, category: 'Engineering', desc: '10-slide benchmark deck.' },
];

export const QuickstartModal: React.FC<QuickstartModalProps> = ({ isOpen, onClose, onSelectPreset }) => {
  const [activeStep, setActiveStep] = useState<1 | 2 | 3>(1);
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" data-testid="quickstart-modal" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>🚀 Quickstart Onboarding & Presets</h3>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>
        <div className="tab-pills" style={{ marginBottom: '1rem' }}>
          <button className={`tab-pill ${activeStep === 1 ? 'active' : ''}`} onClick={() => setActiveStep(1)}>1. Presets</button>
          <button className={`tab-pill ${activeStep === 2 ? 'active' : ''}`} onClick={() => setActiveStep(2)}>2. Workflows</button>
          <button className={`tab-pill ${activeStep === 3 ? 'active' : ''}`} onClick={() => setActiveStep(3)}>3. Docs</button>
        </div>
        {activeStep === 1 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '.6rem' }}>
            {PRESETS.map((p) => (
              <div key={p.id} className="card" style={{ cursor: 'pointer' }} onClick={() => { onSelectPreset(p.topic, p.slides); onClose(); }}>
                <div className="card-top"><h4>{p.title}</h4><span className="tag">{p.category}</span></div>
                <p style={{ margin: '.25rem 0 0', fontSize: '.8rem', color: 'var(--muted)' }}>{p.desc}</p>
              </div>
            ))}
          </div>
        )}
        {activeStep === 2 && (
          <div style={{ fontSize: '.85rem', lineHeight: '1.5' }}>
            <h4>Capabilities</h4>
            <ul style={{ paddingLeft: '1.25rem', marginTop: '.35rem' }}>
              <li><strong>Native PPTX Deck Generation:</strong> Real shapes, tables, charts, transitions.</li>
              <li><strong>Slide Observatory:</strong> Cognitive load, brevity, data fidelity, MECE scores.</li>
              <li><strong>Audio Narration:</strong> Speech audio WAV tracks from speaker notes.</li>
              <li><strong>Template Studio:</strong> Custom .pptx template layout and theme support.</li>
            </ul>
          </div>
        )}
        {activeStep === 3 && (
          <div style={{ fontSize: '.85rem', lineHeight: '1.5' }}>
            <h4>Documentation Hub (#225)</h4>
            <ul style={{ paddingLeft: '1.25rem', marginTop: '.35rem' }}>
              <li><code>docs/quickstart.md</code>: Guided local setup, API reference.</li>
              <li><code>docs/zh/quickstart.md</code>: 中文快速上手指南与完整文档。</li>
              <li><code>README.md</code>: Architecture diagram and Keycloak OIDC guide.</li>
            </ul>
          </div>
        )}
        <div className="modal-footer"><button className="btn-secondary" onClick={onClose}>Close</button></div>
      </div>
    </div>
  );
};
