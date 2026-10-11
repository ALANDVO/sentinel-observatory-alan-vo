"""Tests for template service: registration, layout scanning, placeholder mapping, builtin seeding."""
from __future__ import annotations

import io
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.database import Base
from backend.app.services.template_service import TemplateService


@pytest.fixture(scope="function")
def db():
    """In-memory SQLite database for template tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def svc():
    return TemplateService()


def _make_minimal_pptx_bytes() -> bytes:
    """Generate a minimal valid .pptx file in memory."""
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    prs.slide_width = Inches(13.33)
    prs.slide_height = Inches(7.5)
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def test_seed_builtin_templates_creates_three(svc: TemplateService, db):
    svc.seed_builtin_templates(db)
    templates, total = svc.list_templates(db)
    assert total == 3
    names = {t.name for t in templates}
    assert "Executive Brief" in names
    assert "Research Report" in names
    assert "Data Dashboard" in names


def test_seed_builtin_templates_idempotent(svc: TemplateService, db):
    """Calling seed twice should not create duplicates."""
    svc.seed_builtin_templates(db)
    svc.seed_builtin_templates(db)
    templates, total = svc.list_templates(db)
    assert total == 3


def test_create_template_without_pptx(svc: TemplateService, db):
    t = svc.create_template(db, "Text Only Template", "No PPTX provided", "user-123")
    assert t.id is not None
    assert t.name == "Text Only Template"
    assert t.is_builtin == "false"


def test_create_template_with_pptx_scans_layouts(svc: TemplateService, db, tmp_path):
    """Creating a template from a .pptx file should scan layouts and placeholder maps."""
    pptx_bytes = _make_minimal_pptx_bytes()
    svc.TEMPLATES_DIR = str(tmp_path)
    t = svc.create_template(db, "Scanned Template", "Auto-scanned layouts", "user-456", pptx_bytes=pptx_bytes)
    assert t.id is not None
    assert isinstance(t.layout_names, list)
    # A default Presentation has 11 slide layouts
    assert len(t.layout_names) >= 1
    assert isinstance(t.placeholder_map, dict)


def test_get_template_returns_correct_record(svc: TemplateService, db):
    svc.seed_builtin_templates(db)
    templates, _ = svc.list_templates(db)
    first = templates[0]
    fetched = svc.get_template(db, first.id)
    assert fetched is not None
    assert fetched.id == first.id
    assert fetched.name == first.name


def test_get_template_returns_none_for_missing_id(svc: TemplateService, db):
    result = svc.get_template(db, "00000000-0000-0000-0000-000000000000")
    assert result is None


def test_delete_template_removes_from_db(svc: TemplateService, db):
    svc.seed_builtin_templates(db)
    templates, total = svc.list_templates(db)
    assert total == 3
    to_delete = templates[0]
    deleted = svc.delete_template(db, to_delete.id)
    assert deleted is True
    _, new_total = svc.list_templates(db)
    assert new_total == 2


def test_delete_nonexistent_template_returns_false(svc: TemplateService, db):
    result = svc.delete_template(db, "00000000-0000-0000-0000-000000000099")
    assert result is False


def test_list_templates_pagination(svc: TemplateService, db):
    svc.seed_builtin_templates(db)
    page1, total = svc.list_templates(db, skip=0, limit=2)
    assert len(page1) == 2
    assert total == 3
    page2, _ = svc.list_templates(db, skip=2, limit=2)
    assert len(page2) == 1


def test_template_theme_color_stored(svc: TemplateService, db):
    svc.seed_builtin_templates(db)
    templates, _ = svc.list_templates(db)
    exec_brief = next((t for t in templates if t.name == "Executive Brief"), None)
    assert exec_brief is not None
    assert exec_brief.theme_color == "#1A1A2E"


def test_template_invalid_pptx_raises_value_error(svc: TemplateService, db, tmp_path):
    svc.TEMPLATES_DIR = str(tmp_path)
    bad_bytes = b"not a pptx file at all"
    with pytest.raises(ValueError, match="Failed to parse PPTX template"):
        svc.create_template(db, "Bad Template", "Bad file", "user-789", pptx_bytes=bad_bytes)
