from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import or_
from backend.app.models.deck import Deck, Slide
from backend.app.models.evaluation import Evaluation
from backend.app.models.audit import AuditLog
@dataclass
class R: result_type: str; id: str; title: str; snippet: str; score: float; metadata: dict = field(default_factory=dict)
def d(x: R): return {"result_type": x.result_type, "id": x.id, "title": x.title, "snippet": x.snippet, "score": round(x.score, 3), "metadata": x.metadata}
@dataclass
class SR: query: str; total: int; results: list[R]; facets: dict = field(default_factory=dict)
class SS:
    TB, BB, SL = 3.0, 1.5, 200
    T = re.compile(r"[a-z0-9]+")
    def k(self, t): return self.T.findall(t.lower())
    def rel(self, q, ti, bo):
        if not q: return 0.0
        tt, bt = set(self.k(ti)), set(self.k(bo))
        if not tt and not bt: return 0.0
        tm, bm = sum(1 for x in q if x in tt), sum(1 for x in q if x in bt)
        return min(1.0, (tm*self.TB + bm*self.BB)/(self.TB+self.BB))
    def snip(self, q, tx):
        if not tx or not q: return tx[:self.SL] if tx else ""
        lt = tx.lower()
        for t in q:
            i = lt.find(t)
            if i >= 0:
                s, e = max(0, i-self.SL//2), min(len(tx), i+self.SL//2)
                sn = tx[s:e]
                if s: sn = "..."+sn
                if e < len(tx): sn += "..."
                return sn
        return tx[:self.SL]
    def sk(self, x): return (-x.score, x.metadata.get("created_at") or "")
    def _s(self, db, M, q, fs, fl, lim, off, rt, tf, bf, mf):
        qt = self.k(q)
        if not qt: return [], 0
        qy = db.query(M)
        for k, v in fl.items():
            if v is not None: qy = qy.filter(getattr(M, k)==v)
        cs = []
        for t in qt:
            lk = f"%{t}%"
            cs.append(or_(*(getattr(M, f).ilike(lk) for f in fs)))
        if cs: qy = qy.filter(or_(*cs))
        tot = qy.count()
        rs = []
        for o in qy.all():
            ti, bo = getattr(o, tf) or "", getattr(o, bf) or ""
            sc = self.rel(qt, ti, bo)
            if sc <= 0: continue
            md = {}
            if mf:
                for k, a in mf.items():
                    v = getattr(o, a, None)
                    if hasattr(v, "isoformat"): v = v.isoformat()
                    md[k] = v
            rs.append(R(rt, o.id, ti, self.snip(qt, bo), sc, md))
        rs.sort(key=self.sk)
        return rs[off:off+lim], tot
    def sa(self, db, q, limit=20, offset=0, f=None):
        f = f or {}
        d = {"Deck": (["title", "topic", "source_text"], "deck", "title", "source_text", {"source_type": "source_type", "status": "status", "slide_count": "slide_count", "created_at": "created_at"}),
             "Slide": (["title", "body_text", "speaker_notes"], "slide", "title", "body_text", {"deck_id": "deck_id", "position": "position", "slide_type": "slide_type"}),
             "Evaluation": (["eval_type", "llm_advisory"], "evaluation", "eval_type", "llm_advisory", {"deck_id": "deck_id", "eval_type": "eval_type", "overall_cognitive_score": "overall_cognitive_score", "data_fidelity_precision": "data_fidelity_precision", "created_at": "created_at"})}
        fl = [f.get("source_type"), f.get("status"), f.get("author_sub")], [f.get("deck_id"), f.get("slide_type")], [f.get("deck_id"), f.get("eval_type")]
        ar = []; tot = 0
        for idx, (M, (fs, rt, tf, bf, mf)) in enumerate(zip([Deck, Slide, Evaluation], d.values())):
            r, t = self._s(db, M, q, fs, dict(zip(["source_type","status","author_sub"] if idx==0 else ["deck_id","slide_type"] if idx==1 else ["deck_id","eval_type"], fl[idx])), limit*2, 0, rt, tf, bf, mf)
            ar.extend(r); tot += t
        ar.sort(key=lambda x: -x.score)
        ft = {"result_type":{}, "source_type":{}, "slide_type":{}, "eval_type":{}}
        for r in ar:
            ft["result_type"][r.result_type] = ft["result_type"].get(r.result_type, 0) + 1
            if r.result_type == "deck": ft["source_type"][r.metadata.get("source_type","?")] = ft["source_type"].get(r.metadata.get("source_type","?"), 0) + 1
            elif r.result_type == "slide": ft["slide_type"][r.metadata.get("slide_type","?")] = ft["slide_type"].get(r.metadata.get("slide_type","?"), 0) + 1
            elif r.result_type == "evaluation": ft["eval_type"][r.metadata.get("eval_type","?")] = ft["eval_type"].get(r.metadata.get("eval_type","?"), 0) + 1
        return SR(q, tot, ar[offset:offset+limit], ft)
    search_all = lambda s, db, q, limit=20, offset=0, f=None: s.sa(db, q, limit, offset, f)
    get_index_stats = lambda s, db: {"decks": db.query(Deck).count(), "slides": db.query(Slide).count(), "evaluations": db.query(Evaluation).count(), "audit_logs": db.query(AuditLog).count()}
