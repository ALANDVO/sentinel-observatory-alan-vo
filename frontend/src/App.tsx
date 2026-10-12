import React, { useEffect, useState } from 'react';
import { api, setAccessToken } from './api';
import { DeckOut, DeckSummary, EvaluationOut, TemplateOut, UserInfo } from './types';
import { Navbar } from './components/Navbar';
import { DeckDashboard } from './components/DeckDashboard';
import { DeckDetail } from './components/DeckDetail';
import { ObservatoryView } from './components/ObservatoryView';
import { SearchView } from './components/SearchView';
import { TemplateStudio } from './components/TemplateStudio';
import { QuickstartModal } from './components/QuickstartModal';
export const App: React.FC = () => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [tab, setTab] = useState<'decks' | 'observatory' | 'templates' | 'search'>('decks');
  const [decks, setDecks] = useState<DeckSummary[]>([]);
  const [decksLoading, setDecksLoading] = useState(true);
  const [decksErr, setDecksErr] = useState<string | null>(null);
  const [deck, setDeck] = useState<DeckOut | null>(null);
  const [filterSource, setFilterSource] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [evals, setEvals] = useState<EvaluationOut[]>([]);
  const [evalsLoading, setEvalsLoading] = useState(false);
  const [evalDeckId, setEvalDeckId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<TemplateOut[]>([]);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const [templatesErr, setTemplatesErr] = useState<string | null>(null);
  const [quickstart, setQuickstart] = useState(false);
  const loadDecks = () => { setDecksLoading(true); api.decks.list({ limit: 50 }).then(r => setDecks(r.items)).catch(e => setDecksErr(String(e))).finally(() => setDecksLoading(false)); };
  const loadTemplates = () => { setTemplatesLoading(true); api.templates.list().then(r => setTemplates(r.items)).catch(e => setTemplatesErr(String(e))).finally(() => setTemplatesLoading(false)); };
  const loadEvals = () => { setEvalsLoading(true); api.evaluations.list({ limit: 100 }).then(r => setEvals(r.items)).catch(() => {}).finally(() => setEvalsLoading(false)); };
  useEffect(() => { api.auth.getMe().then(setUser).catch(() => {}); loadDecks(); loadTemplates(); loadEvals(); }, []);
  return (
    <div className="app-root">
      <Navbar user={user} activeTab={tab} onSelectTab={t => { setTab(t); setDeck(null); }} onLogout={() => { setAccessToken(null); setUser(null); window.location.reload(); }} onOpenQuickstart={() => setQuickstart(true)} />
      <main className="content-container">
        {tab === 'decks' && (deck ? (
          <DeckDetail deck={deck} onBack={() => setDeck(null)} onAddSlide={async (id, s) => { await api.decks.addSlide(id, s); setDeck(await api.decks.get(id)); loadDecks(); }} onRunEval={dId => { setEvalDeckId(dId); setTab('observatory'); }} />
        ) : (
          <DeckDashboard decks={decks} loading={decksLoading} error={decksErr} onSelectDeck={async id => setDeck(await api.decks.get(id))} onDeleteDeck={async id => { if (confirm('Delete?')) { await api.decks.delete(id); loadDecks(); } }} onCreateTopic={async (t, c) => { const d = await api.decks.generateTopic({ topic: t, slide_count: c }); loadDecks(); setDeck(d); }} onCreateDoc={async (txt, c) => { const d = await api.decks.generateDocument({ text: txt, slide_count: c }); loadDecks(); setDeck(d); }} filterSource={filterSource} setFilterSource={setFilterSource} searchQuery={searchQuery} setSearchQuery={setSearchQuery} />
        ))}{tab === 'observatory' && <ObservatoryView decks={decks} evaluations={evals} loading={evalsLoading} selectedDeckId={evalDeckId} onSelectDeck={setEvalDeckId} onRunEval={async (id, opt) => { const res = await api.evaluations.run(id, opt); setEvals(p => [res, ...p.filter(e => e.id !== res.id)]); }} />}{tab === 'templates' && <TemplateStudio templates={templates} loading={templatesLoading} error={templatesErr} onUploadTemplate={async (n, desc, f) => { const fd = new FormData(); fd.append('name', n); if (desc) fd.append('description', desc); if (f) fd.append('file', f); await api.templates.create(fd); loadTemplates(); }} />}{tab === 'search' && <SearchView />}
      </main>
      <QuickstartModal isOpen={quickstart} onClose={() => setQuickstart(false)} onSelectPreset={async (topic, count) => { const d = await api.decks.generateTopic({ topic, slide_count: count }); loadDecks(); setDeck(d); setTab('decks'); }} />
      <footer className="app-footer"><div>Sentinel Observatory &bull; Alan Vo (<a href="mailto:alanvo@gmail.com">alanvo@gmail.com</a>) &bull; GitHub ALANDVO</div></footer>
    </div>
  );
};
