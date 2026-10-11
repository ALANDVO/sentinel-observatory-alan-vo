"""Audio narration synthesis engine for slide speaker notes.

Generates valid RIFF/WAVE PCM audio for individual slides and presentations.
Runs offline and deterministically without external services.
"""
from __future__ import annotations

import io
import math
import re
import struct
import wave
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SlideNarration:
    slide_id: str
    position: int
    transcript: str
    word_count: int
    duration_seconds: float
    audio_bytes: bytes = field(repr=False, default=b"")


@dataclass
class DeckNarration:
    deck_id: str
    voice: str
    total_duration_seconds: float
    total_words: int
    slides: list[SlideNarration]
    audio_bytes: bytes = field(repr=False, default=b"")


class AudioNarrationService:
    VOICE_FREQS = {"narrator-exec": 160.0, "narrator-tech": 190.0, "narrator-calm": 140.0, "narrator-en": 175.0}

    def _clean_transcript(self, text: str | None, fallback_title: str | None = None) -> str:
        raw = (text or "").strip() or (f"Slide: {fallback_title.strip()}." if fallback_title else "")
        return re.sub(r"\s+", " ", raw) or "No notes provided for this slide."

    def synthesize_wav_pcm(self, transcript: str, voice: str = "narrator-en", sample_rate: int = 16000, words_per_minute: int = 150) -> tuple[bytes, float]:
        words = [w for w in re.split(r"\s+", transcript) if w]
        duration = max(1.5, round((max(1, len(words)) / words_per_minute) * 60.0, 2))
        base_freq = self.VOICE_FREQS.get(voice, 170.0)
        num_samples = int(sample_rate * duration)

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                f0 = base_freq * (1.0 + 0.15 * math.sin(2 * math.pi * 3.5 * t))
                env = min(1.0, t * 10.0) * min(1.0, (duration - t) * 10.0)
                tone = 0.6 * math.sin(2 * math.pi * f0 * t) + 0.3 * math.sin(2 * math.pi * f0 * 2.8 * t)
                sample = max(-32767, min(32767, int(12000 * env * tone)))
                data.extend(struct.pack("<h", sample))
            wf.writeframes(data)
        return buf.getvalue(), duration

    def synthesize_slide(self, slide_id: str, position: int, speaker_notes: str | None, title: str | None = None, voice: str = "narrator-en") -> SlideNarration:
        tr = self._clean_transcript(speaker_notes, title)
        audio_bytes, dur = self.synthesize_wav_pcm(tr, voice=voice)
        words = [w for w in re.split(r"\s+", tr) if w]
        return SlideNarration(slide_id=slide_id, position=position, transcript=tr, word_count=len(words), duration_seconds=dur, audio_bytes=audio_bytes)

    def synthesize_deck(self, deck_id: str, slides: list[dict[str, Any]], voice: str = "narrator-en") -> DeckNarration:
        narrations = []
        tot_words = 0
        tot_dur = 0.0
        for s in sorted(slides, key=lambda x: x.get("position", 0)):
            sn = self.synthesize_slide(str(s.get("id", f"pos_{s.get('position', 0)}")), int(s.get("position", 0)), s.get("speaker_notes"), s.get("title"), voice=voice)
            narrations.append(sn)
            tot_words += sn.word_count
            tot_dur += sn.duration_seconds

        sr = 16000
        merged = io.BytesIO()
        with wave.open(merged, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            for sn in narrations:
                with wave.open(io.BytesIO(sn.audio_bytes), "rb") as r:
                    wf.writeframes(r.readframes(r.getnframes()))
                wf.writeframes(b"\x00\x00" * int(sr * 0.4))
                tot_dur += 0.4

        return DeckNarration(deck_id=deck_id, voice=voice, total_duration_seconds=round(tot_dur, 2), total_words=tot_words, slides=narrations, audio_bytes=merged.getvalue())
