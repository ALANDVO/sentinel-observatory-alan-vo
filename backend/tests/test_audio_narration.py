"""Tests for the Audio Narration synthesis engine, CLI, and API endpoints."""
from __future__ import annotations
import io, json, struct, tempfile, wave
import pytest
from fastapi.testclient import TestClient

from backend.app.services.audio_narration import (
    AudioNarrationService,
    SlideNarration,
    DeckNarration,
    main as narration_cli_main,
)

@pytest.fixture
def narration_service():
    return AudioNarrationService()

def test_synthesize_wav_pcm_header_and_structure(narration_service: AudioNarrationService):
    transcript = "Welcome to the presentation on distributed machine learning systems."
    audio_bytes, duration = narration_service.synthesize_wav_pcm(transcript, voice="narrator-en", sample_rate=16000, words_per_minute=150)
    assert len(audio_bytes) > 44
    assert audio_bytes[:4] == b"RIFF"
    assert audio_bytes[8:12] == b"WAVE"
    assert duration > 1.0

    buf = io.BytesIO(audio_bytes)
    with wave.open(buf, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000
        nframes = wf.getnframes()
        assert nframes > 0
        expected_frames = int(16000 * duration)
        assert abs(nframes - expected_frames) <= 1

def test_synthesize_wav_pcm_pace_variation(narration_service: AudioNarrationService):
    text = "Detailed technical explanation of transformer attention mechanism and key value cache."
    _, slow_dur = narration_service.synthesize_wav_pcm(text, words_per_minute=100)
    _, fast_dur = narration_service.synthesize_wav_pcm(text, words_per_minute=200)
    assert slow_dur > fast_dur

def test_synthesize_voices(narration_service: AudioNarrationService):
    voices = AudioNarrationService.get_available_voices()
    assert "narrator-en" in voices
    assert "narrator-exec" in voices
    assert "narrator-tech" in voices
    assert "narrator-calm" in voices

    for v in voices:
        b, d = narration_service.synthesize_wav_pcm("Slide speaker notes test.", voice=v)
        assert len(b) > 100
        assert d >= 1.5

def test_clean_transcript_markdown_and_fallbacks(narration_service: AudioNarrationService):
    dirty = "## Important Points\n* Use **RLHF** with [reward models](https://example.com/rm) and `PPO`."
    cleaned = narration_service._clean_transcript(dirty)
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "`" not in cleaned
    assert "https://example.com" not in cleaned
    assert "reward models" in cleaned

    empty_fallback = narration_service._clean_transcript(None, fallback_title="Architecture Overview")
    assert "Slide: Architecture Overview." in empty_fallback

    none_fallback = narration_service._clean_transcript("", None)
    assert none_fallback == "No notes provided for this slide."

def test_synthesize_slide(narration_service: AudioNarrationService):
    sn = narration_service.synthesize_slide("slide-1", 1, "Speaker notes for slide 1.", title="Overview", voice="narrator-exec", words_per_minute=160)
    assert isinstance(sn, SlideNarration)
    assert sn.slide_id == "slide-1"
    assert sn.position == 1
    assert sn.words_per_minute == 160
    assert sn.word_count > 0
    assert len(sn.audio_bytes) > 0

def test_synthesize_deck(narration_service: AudioNarrationService):
    slides = [
        {"id": "s1", "position": 0, "title": "Intro", "speaker_notes": "Welcome to the talk."},
        {"id": "s2", "position": 1, "title": "Data", "speaker_notes": "Here is the dataset analysis."},
    ]
    deck_narr = narration_service.synthesize_deck("deck-100", slides, voice="narrator-calm", words_per_minute=140)
    assert isinstance(deck_narr, DeckNarration)
    assert deck_narr.deck_id == "deck-100"
    assert deck_narr.voice == "narrator-calm"
    assert deck_narr.words_per_minute == 140
    assert len(deck_narr.slides) == 2
    assert deck_narr.total_duration_seconds > sum(s.duration_seconds for s in deck_narr.slides)
    assert len(deck_narr.audio_bytes) > 0

def test_deck_narration_api_endpoints(client: TestClient):
    create_resp = client.post("/api/decks/generate/topic", json={"topic": "Audio Narration Deep Dive", "slide_count": 4})
    assert create_resp.status_code == 201
    deck_id = create_resp.json()["id"]
    slides = create_resp.json()["slides"]
    assert len(slides) >= 3
    slide_id = slides[0]["id"]

    synth_resp = client.post(f"/api/decks/{deck_id}/narration/synthesize?voice=narrator-exec&words_per_minute=160")
    assert synth_resp.status_code == 200
    data = synth_resp.json()
    assert data["deck_id"] == deck_id
    assert data["voice"] == "narrator-exec"
    assert data["words_per_minute"] == 160
    assert data["total_duration_seconds"] > 0
    assert len(data["slides"]) == len(slides)

    deck_audio_resp = client.get(f"/api/decks/{deck_id}/narration/audio?voice=narrator-exec&words_per_minute=160")
    assert deck_audio_resp.status_code == 200
    assert "audio/wav" in deck_audio_resp.headers["content-type"]
    assert deck_audio_resp.content[:4] == b"RIFF"

    slide_audio_resp = client.get(f"/api/decks/{deck_id}/slides/{slide_id}/narration/audio?voice=narrator-exec&words_per_minute=160")
    assert slide_audio_resp.status_code == 200
    assert "audio/wav" in slide_audio_resp.headers["content-type"]
    assert slide_audio_resp.content[:4] == b"RIFF"

def test_deck_narration_api_404_errors(client: TestClient):
    resp = client.post("/api/decks/00000000-0000-0000-0000-000000000000/narration/synthesize")
    assert resp.status_code == 404

    resp = client.get("/api/decks/00000000-0000-0000-0000-000000000000/narration/audio")
    assert resp.status_code == 404

def test_narration_cli_interface():
    res = narration_cli_main(["--text", "Automated speech test for CLI execution.", "--voice", "narrator-tech", "--wpm", "175", "--json"])
    assert res == 0

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        out_path = tf.name
    res = narration_cli_main(["--text", "Saving audio to disk test.", "--voice", "narrator-en", "--wpm", "150", "--out", out_path])
    assert res == 0
    with open(out_path, "rb") as fh:
        raw = fh.read()
    assert raw[:4] == b"RIFF"

def test_narration_cli_fail_closed():
    res_empty = narration_cli_main(["--text", "   "])
    assert res_empty == 1

    res_bad_wpm = narration_cli_main(["--text", "Hello", "--wpm", "50"])
    assert res_bad_wpm == 1
