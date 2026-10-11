import React, { useState } from 'react';
import { TemplateOut } from '../types';

interface TemplateStudioProps {
  templates: TemplateOut[]; loading: boolean; error: string | null;
  onUploadTemplate: (name: string, description: string, file: File | null) => Promise<void>;
}

export const TemplateStudio: React.FC<TemplateStudioProps> = ({ templates, loading, error, onUploadTemplate }) => {
  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); if (!name.trim()) return;
    setUploading(true); setUploadError(null);
    try {
      await onUploadTemplate(name, desc, file);
      setShowModal(false); setName(''); setDesc(''); setFile(null);
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed');
    } finally { setUploading(false); }
  };

  return (
    <div className="templates-container">
      <div className="section-header">
        <div>
          <h2>Template Studio</h2>
          <p className="section-desc">Native PowerPoint design templates and layout hierarchies.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowModal(true)}>+ Import .pptx Template</button>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {loading ? (
        <div className="state-panel"><div className="spinner" /><p>Loading templates…</p></div>
      ) : templates.length === 0 ? (
        <div className="state-panel"><h3>No templates registered</h3></div>
      ) : (
        <div className="template-grid">
          {templates.map((tmpl) => (
            <div key={tmpl.id} className="card">
              <div className="card-top">
                <span className="color-swatch" style={{ backgroundColor: tmpl.theme_color || '#3b82f6' }} />
                <span className="tag">{tmpl.is_builtin === 'true' ? 'Built-in' : 'Custom'}</span>
              </div>
              <h3 className="card-title">{tmpl.name}</h3>
              <p className="section-desc">{tmpl.description || 'Standard theme'}</p>
              <div className="layout-chips">
                {tmpl.layout_names.map((l, i) => <span key={i} className="chip">{l}</span>)}
              </div>
            </div>
          ))}
        </div>
      )}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Import .pptx Template</h3>
              <button className="btn-close" onClick={() => setShowModal(false)}>&times;</button>
            </div>
            {uploadError && <div className="alert alert-error">{uploadError}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Template Name</label>
                <input type="text" className="form-control" value={name} onChange={(e) => setName(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input type="text" className="form-control" value={desc} onChange={(e) => setDesc(e.target.value)} />
              </div>
              <div className="form-group">
                <label>.pptx Template File</label>
                <input type="file" accept=".pptx" onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)} />
              </div>
              <div className="modal-footer">
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={uploading}>{uploading ? 'Importing…' : 'Import Template'}</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
