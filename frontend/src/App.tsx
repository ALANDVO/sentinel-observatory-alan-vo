import React, { useEffect, useState } from 'react';
import { api, setAccessToken } from './api';
import { DeckOut, DeckSummary, EvaluationOut, TemplateOut, UserInfo } from './types';
import { Navbar } from './components/Navbar';
import { DeckDashboard } from './components/DeckDashboard';
import { DeckDetail } from './components/DeckDetail';
import { ObservatoryView } from './components/ObservatoryView';
import { TemplateStudio } from './components/TemplateStudio';
import { QuickstartModal } from './components/QuickstartModal';

export const App: React.FC = () => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [activeTab, setActiveTab] = useState<'decks' | 'observatory' | 'templates'>('decks');
  const [decks, setDecks] = useState<DeckSummary[]>([]);
  const [decksLoading, setDecksLoading] = useState(true);
  const [decksError, setDecksError] = useState<string | null>(null);
  const [selectedDeck, setSelectedDeck] = useState<DeckOut | null>(null);
  const [filterSource, setFilterSource] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [evaluations, setEvaluations] = useState<EvaluationOut[]>([]);
  const [evalsLoading, setEvalsLoading] = useState(false);
  const [selectedEvalDeckId, setSelectedEvalDeckId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateOut[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [templatesError, setTemplatesError] = useState<string | null>(null);
  const [showQuickstart, setShowQuickstart] = useState(false);

  const loadDecks = () => {
    setDecksLoading(true);
    api.decks.list({ limit: 50 }).then((r) => setDecks(r.items)).catch((e) => setDecksError(String(e))).finally(() => setDecksLoading(false));
  };
  const loadTemplates = () => {
    setTemplatesLoading(true);
    api.templates.list().then((r) => setTemplates(r.items)).catch((e) => setTemplatesError(String(e))).finally(() => setTemplatesLoading(false));
  };
  const loadEvals = () => {
    setEvalsLoading(true);
    api.evaluations.list({ limit: 100 }).then((r) => setEvaluations(r.items)).catch(() => {}).finally(() => setEvalsLoading(false));
  };

  useEffect(() => {
    api.auth.getMe().then(setUser).catch(() => {});
    loadDecks();
    loadTemplates();
    loadEvals();
  }, []);

  return (
    <div className="app-root">
      <Navbar
        user={user}
        activeTab={activeTab}
        onSelectTab={(t) => { setActiveTab(t); setSelectedDeck(null); }}
        onLogout={() => { setAccessToken(null); setUser(null); window.location.reload(); }}
        onOpenQuickstart={() => setShowQuickstart(true)}
      />
      <main className="content-container">
        {activeTab === 'decks' && (
          selectedDeck ? (
            <DeckDetail
              deck={selectedDeck}
              onBack={() => setSelectedDeck(null)}
              onAddSlide={async (id, s) => { await api.decks.addSlide(id, s); setSelectedDeck(await api.decks.get(id)); loadDecks(); }}
              onRunEval={(dId) => { setSelectedEvalDeckId(dId); setActiveTab('observatory'); }}
            />
          ) : (
            <DeckDashboard
              decks={decks}
              loading={decksLoading}
              error={decksError}
              onSelectDeck={async (id) => setSelectedDeck(await api.decks.get(id))}
              onDeleteDeck={async (id) => { if (confirm('Delete?')) { await api.decks.delete(id); loadDecks(); } }}
              onCreateTopic={async (t, c) => { const d = await api.decks.generateTopic({ topic: t, slide_count: c }); loadDecks(); setSelectedDeck(d); }}
              onCreateDoc={async (txt, c) => { const d = await api.decks.generateDocument({ text: txt, slide_count: c }); loadDecks(); setSelectedDeck(d); }}
              filterSource={filterSource}
              setFilterSource={setFilterSource}
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
            />
          )
        )}
        {activeTab === 'observatory' && (
          <ObservatoryView
            decks={decks}
            evaluations={evaluations}
            loading={evalsLoading}
            selectedDeckId={selectedEvalDeckId}
            onSelectDeck={setSelectedEvalDeckId}
            onRunEval={async (id, opt) => {
              const res = await api.evaluations.run(id, opt);
              setEvaluations((prev) => [res, ...prev.filter((e) => e.id !== res.id)]);
            }}
          />
        )}
        {activeTab === 'templates' && (
          <TemplateStudio
            templates={templates}
            loading={templatesLoading}
            error={templatesError}
            onUploadTemplate={async (n, desc, f) => {
              const fd = new FormData();
              fd.append('name', n);
              if (desc) fd.append('description', desc);
              if (f) fd.append('file', f);
              await api.templates.create(fd);
              loadTemplates();
            }}
          />
        )}
      </main>
      <QuickstartModal
        isOpen={showQuickstart}
        onClose={() => setShowQuickstart(false)}
        onSelectPreset={async (topic, count) => {
          const d = await api.decks.generateTopic({ topic, slide_count: count });
          loadDecks();
          setSelectedDeck(d);
          setActiveTab('decks');
        }}
      />
      <footer className="app-footer">
        <div>Sentinel Observatory &bull; Alan Vo (<a href="mailto:alanvo@gmail.com">alanvo@gmail.com</a>) &bull; GitHub ALANDVO</div>
      </footer>
    </div>
  );
};
