import io, json, math, re, struct, sys, wave
from dataclasses import dataclass, field
from typing import Any
@dataclass
class SlideNarration:
    slide_id: str; position: int; transcript: str; word_count: int
    duration_seconds: float; audio_bytes: bytes = field(repr=False, default=b"")
    words_per_minute: int = 150
@dataclass
class DeckNarration:
    deck_id: str; voice: str; total_duration_seconds: float; total_words: int
    slides: list[SlideNarration]; audio_bytes: bytes = field(repr=False, default=b"")
    words_per_minute: int = 150
class AudioNarrationService:
    VF = {"narrator-exec": 160.0, "narrator-tech": 190.0, "narrator-calm": 140.0, "narrator-en": 175.0}
    @classmethod
    def get_available_voices(cls) -> list[str]: return list(cls.VF.keys())
    @classmethod
    def is_supported_voice(cls, v: str) -> bool: return v in cls.VF
    def _clean(self, text: str | None = None, fallback_title: str | None = None) -> str:
        raw = (text or "").strip() or (f"Slide: {fallback_title.strip()}." if fallback_title else "")
        if not raw: return "No notes provided for this slide."
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", raw)
        return " ".join(re.sub(r"[*_~`#>]", " ", cleaned).split()) or "No notes provided for this slide."
    def synth(self, transcript: str, voice: str = "narrator-en", sample_rate: int = 16000, words_per_minute: int = 150) -> tuple[bytes, float]:
        wpm, words = max(80, min(300, words_per_minute)), transcript.split()
        dur = max(1.5, round((max(1, len(words)) / wpm) * 60.0, 2))
        f0 = self.VF.get(voice, 175.0)
        ns = int(sample_rate * dur)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sample_rate)
            data = bytearray()
            for i in range(ns):
                t = i / sample_rate
                f = f0 * (1.0 + 0.15 * math.sin(2 * math.pi * 3.5 * t))
                env = min(1.0, t * 10.0) * min(1.0, (dur - t) * 10.0)
                data.extend(struct.pack("<h", max(-32767, min(32767, int(12000 * env * (0.6 * math.sin(2 * math.pi * f * t) + 0.3 * math.sin(2 * math.pi * f * 2.8 * t)))))))
            wf.writeframes(data)
        return buf.getvalue(), dur
    def synthesize_slide(self, slide_id: str, position: int, speaker_notes: str | None, title: str | None = None, voice: str = "narrator-en", words_per_minute: int = 150) -> SlideNarration:
        tr = self._clean(speaker_notes, title)
        b, dur = self.synth(tr, voice, words_per_minute=words_per_minute)
        return SlideNarration(slide_id, position, tr, len(tr.split()), dur, b, words_per_minute=words_per_minute)
    def synthesize_deck(self, deck_id: str, slides: list[dict[str, Any]], voice: str = "narrator-en", words_per_minute: int = 150) -> DeckNarration:
        narrs = [self.synthesize_slide(str(s.get("id", f"pos_{s.get('position', 0)}")), int(s.get("position", 0)), s.get("speaker_notes"), s.get("title"), voice, words_per_minute=words_per_minute) for s in sorted(slides, key=lambda x: x.get("position", 0))]
        sr, tot_words, tot_dur = 16000, sum(n.word_count for n in narrs), sum(n.duration_seconds for n in narrs)
        merged = io.BytesIO()
        with wave.open(merged, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr)
            for sn in narrs:
                with wave.open(io.BytesIO(sn.audio_bytes), "rb") as r: wf.writeframes(r.readframes(r.getnframes()))
                wf.writeframes(b"\x00\x00" * int(sr * 0.4))
                tot_dur += 0.4
        return DeckNarration(deck_id, voice, round(tot_dur, 2), tot_words, narrs, merged.getvalue(), words_per_minute=words_per_minute)
    synthesize_wav_pcm = synth
    _clean_transcript = _clean
def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description="Sentinel Observatory Audio Narration Synthesis CLI")
    p.add_argument("--text", help="Text or transcript to synthesize into WAV audio")
    p.add_argument("--voice", default="narrator-en", choices=AudioNarrationService.get_available_voices(), help="Voice profile")
    p.add_argument("--wpm", type=int, default=150, help="Speech pace in words per minute (80-300)")
    p.add_argument("--out", help="Optional output filepath for synthesized .wav")
    p.add_argument("--json", action="store_true", help="Output diagnostic JSON payload")
    args = p.parse_args(argv)
    if not args.text or not args.text.strip(): sys.stderr.write("[AudioNarration] ERROR: --text must be non-empty.\n"); return 1
    if not (80 <= args.wpm <= 300): sys.stderr.write(f"[AudioNarration] ERROR: --wpm must be between 80 and 300 (got {args.wpm}).\n"); return 1
    raw, dur = AudioNarrationService().synth(args.text, voice=args.voice, words_per_minute=args.wpm)
    wc = len(args.text.split())
    if args.out:
        with open(args.out, "wb") as fh: fh.write(raw)
    info = {"voice": args.voice, "words_per_minute": args.wpm, "word_count": wc, "duration_seconds": dur, "sample_rate": 16000, "audio_bytes_length": len(raw), "status": "ok"}
    if args.json: sys.stdout.write(json.dumps(info, indent=2) + "\n")
    else: sys.stdout.write(f"[AudioNarration] PASS: Synthesized {dur}s ({wc} words @ {args.wpm} wpm, voice={args.voice}, bytes={len(raw)}).\n")
    return 0
if __name__ == "__main__": sys.exit(main())