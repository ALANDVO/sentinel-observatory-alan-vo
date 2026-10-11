import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Navbar } from '../components/Navbar';
import { DeckDashboard } from '../components/DeckDashboard';
import { ObservatoryView } from '../components/ObservatoryView';
import { TemplateStudio } from '../components/TemplateStudio';
import { DeckSummary, EvaluationOut, TemplateOut, UserInfo } from '../types';

describe('Navbar Component', () => {
  it('renders branding and user role tags', () => {
    const mockUser: UserInfo = {
      sub: 'user-123',
      email: 'analyst@sentinel.local',
      preferred_username: 'analyst',
      roles: ['operator'],
      demo: true,
    };
    render(
      <Navbar
        user={mockUser}
        activeTab="decks"
        onSelectTab={vi.fn()}
        onLogout={vi.fn()}
      />
    );

    expect(screen.getByText('Sentinel Observatory')).toBeInTheDocument();
    expect(screen.getByText('Alan Vo | AI & Machine Learning')).toBeInTheDocument();
    expect(screen.getByText('analyst')).toBeInTheDocument();
    expect(screen.getByText('Demo Mode')).toBeInTheDocument();
    expect(screen.getByText('Operator')).toBeInTheDocument();
  });
});

describe('DeckDashboard Component', () => {
  it('renders presentations, search filter, and triggers create modal', () => {
    const sampleDecks: DeckSummary[] = [
      {
        id: 'deck-1',
        title: 'Neural Architecture Search Overview',
        source_type: 'topic',
        status: 'draft',
        slide_count: 6,
        created_at: new Date().toISOString(),
      },
    ];

    render(
      <DeckDashboard
        decks={sampleDecks}
        loading={false}
        error={null}
        onSelectDeck={vi.fn()}
        onDeleteDeck={vi.fn()}
        onCreateTopic={vi.fn()}
        onCreateDoc={vi.fn()}
        filterSource=""
        setFilterSource={vi.fn()}
        searchQuery=""
        setSearchQuery={vi.fn()}
      />
    );

    expect(screen.getByText('Neural Architecture Search Overview')).toBeInTheDocument();
    expect(screen.getByText('+ New Presentation')).toBeInTheDocument();

    // Clicking New Presentation opens modal
    fireEvent.click(screen.getByText('+ New Presentation'));
    expect(screen.getByText('Create New Presentation')).toBeInTheDocument();
    expect(screen.getByText('From Research Topic')).toBeInTheDocument();
  });

  it('renders empty state when no presentations match', () => {
    render(
      <DeckDashboard
        decks={[]}
        loading={false}
        error={null}
        onSelectDeck={vi.fn()}
        onDeleteDeck={vi.fn()}
        onCreateTopic={vi.fn()}
        onCreateDoc={vi.fn()}
        filterSource=""
        setFilterSource={vi.fn()}
        searchQuery=""
        setSearchQuery={vi.fn()}
      />
    );

    expect(screen.getByText('No presentations found')).toBeInTheDocument();
    expect(screen.getByText('Create First Deck')).toBeInTheDocument();
  });
});

describe('ObservatoryView Component', () => {
  it('renders cognitive metrics, score badges, and attribution guard status', () => {
    const sampleDecks: DeckSummary[] = [
      {
        id: 'deck-1',
        title: 'Deep Learning Safety',
        source_type: 'topic',
        status: 'compiled',
        slide_count: 5,
        created_at: new Date().toISOString(),
      },
    ];

    const sampleEval: EvaluationOut = {
      id: 'eval-1',
      deck_id: 'deck-1',
      eval_type: 'full',
      overall_cognitive_score: 0.88,
      information_density_score: 0.82,
      bullet_brevity_score: 0.9,
      hierarchy_balance_score: 0.85,
      readability_grade: 8.5,
      mece_alignment_score: 0.95,
      numeric_claims_found: 3,
      claims_verified: 3,
      data_fidelity_precision: 1.0,
      data_fidelity_recall: 1.0,
      attribution_pass: 'pass',
      attribution_diagnostics: [],
      prompt_audit_pass: 'pass',
      prompt_audit_findings: [],
      llm_advisory: null,
      llm_provider_used: null,
      raw_result: { observations: ['Balanced information density across all 5 slides.'] },
      created_at: new Date().toISOString(),
    };

    render(
      <ObservatoryView
        decks={sampleDecks}
        evaluations={[sampleEval]}
        loading={false}
        selectedDeckId="deck-1"
        onSelectDeck={vi.fn()}
        onRunEval={vi.fn()}
      />
    );

    expect(screen.getByText('Slide-Intelligence Observatory')).toBeInTheDocument();
    expect(screen.getByText('Overall Cognitive Score')).toBeInTheDocument();
    expect(screen.getByText('88%')).toBeInTheDocument();
    expect(screen.getByText('Grade 8.5')).toBeInTheDocument();
    expect(screen.getByText('PASS')).toBeInTheDocument();
  });
});

describe('TemplateStudio Component', () => {
  it('renders templates and layout options', () => {
    const sampleTemplates: TemplateOut[] = [
      {
        id: 't-1',
        name: 'Executive Minimalist',
        description: 'Clean modern layout',
        theme_color: '#2563eb',
        slide_count: 10,
        layout_names: ['Title', 'Bullets', 'Two-Column', 'KPI Grid'],
        placeholder_map: {},
        is_builtin: 'true',
        created_at: new Date().toISOString(),
      },
    ];

    render(
      <TemplateStudio
        templates={sampleTemplates}
        loading={false}
        error={null}
        onUploadTemplate={vi.fn()}
      />
    );

    expect(screen.getByText('Template Studio')).toBeInTheDocument();
    expect(screen.getByText('Executive Minimalist')).toBeInTheDocument();
    expect(screen.getByText('KPI Grid')).toBeInTheDocument();
  });
});
