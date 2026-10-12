"""Shared logic: storage, pattern analysis, wording guardrails, approval.
Learner IDs should be pseudonyms (e.g. 'L-0042'), never names."""
import os, re, json, sqlite3, time

DB = os.environ.get("LP_DB", os.path.join(os.path.dirname(os.path.abspath(__file__)), "learner.db"))
KINDS = {"quiz", "project", "teacher_note"}
ATL = {"", "Thinking", "Research", "Communication", "Social", "Self-management"}
MIN_SOURCES, MIN_TERMS = 3, 2          # evidence floor: tune with teachers

SCHEMA = """
CREATE TABLE IF NOT EXISTS evidence(
  id INTEGER PRIMARY KEY, learner TEXT, term TEXT, subject TEXT, kind TEXT,
  score REAL, atl TEXT, note TEXT, teacher TEXT,
  status TEXT DEFAULT 'pending', created REAL);
CREATE TABLE IF NOT EXISTS proposals(
  id INTEGER PRIMARY KEY, learner TEXT, evidence_ids TEXT, diff TEXT,
  wording TEXT, model TEXT, status TEXT DEFAULT 'pending',
  decided_by TEXT, decided_at REAL, reason TEXT, created REAL);
"""

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.executescript(SCHEMA); return c

def rows(c, learner, statuses):
    q = ",".join("?" * len(statuses))
    return [dict(r) for r in c.execute(
        f"SELECT * FROM evidence WHERE learner=? AND status IN ({q}) ORDER BY term,id",
        (learner, *statuses))]

def _slope(p):
    if len(p) < 2: return 0.0
    mx = sum(x for x, _ in p) / len(p); my = sum(y for _, y in p) / len(p)
    den = sum((x - mx) ** 2 for x, _ in p)
    return sum((x - mx) * (y - my) for x, y in p) / den if den else 0.0

def analyze(rs):
    terms = sorted({r["term"] for r in rs}); idx = {t: i for i, t in enumerate(terms)}
    out = {}
    for s in sorted({r["subject"] for r in rs}):
        es = [r for r in rs if r["subject"] == s]
        sc = [r for r in es if r["score"] is not None]
        by = {}
        for r in sc: by.setdefault(r["term"], []).append(r["score"])
        pts = [(idx[t], sum(v) / len(v)) for t, v in by.items()]
        mean = sum(r["score"] for r in sc) / len(sc) if sc else None
        nt = len({r["term"] for r in es})
        enough = len(es) >= MIN_SOURCES and nt >= MIN_TERMS
        if not enough: level = "not enough evidence yet"
        elif mean is None: level = "observed in notes only"
        elif mean >= 70: level = "emerging strength"
        elif mean < 55: level = "may need support"
        else: level = "developing"
        sl = _slope(pts)
        trend = "" if not enough or len(pts) < 2 else ("rising" if sl > 2 else "falling" if sl < -2 else "steady")
        item = {"level": level, "trend": trend, "sources": len(es), "terms": nt,
                "average": None if mean is None else round(mean),
                "evidence_ids": [f"E{r['id']}" for r in es]}
        if level == "may need support":
            item["check_first"] = ["attendance in those terms", "language of instruction",
                                   "sight/hearing", "circumstances at home or school"]
        out[s] = item
    return out

def atl_summary(rs):
    d = {}
    for r in rs:
        if r["atl"]: d.setdefault(r["atl"], []).append(f"E{r['id']}")
    return d

BANNED = [r"\bshould (become|be a|study|choose|take|pursue)", r"\bmust\b", r"\bwill (be|become)\b",
          r"\bdestined\b", r"\bnot (suited|cut out)\b", r"\bcannot\b", r"\bbest career\b",
          r"\bideal career\b", r"\byou need to\b", r"\bnever\b", r"\bonly option\b", r"\bgenius\b",
          r"\blow ability\b", r"\bweak learner\b", r"\bslow learner\b"]

def lint_wording(text, valid_ids):
    """Guardrail between any model and the teacher. Returns list of problems."""
    probs = []
    if not text or len(text) > 1200: probs.append("wording must be 1-1200 characters")
    cited = {int(x) for x in re.findall(r"\[E(\d+)\]", text or "")}
    if not cited: probs.append("cite sources like [E12] for every claim")
    bad = cited - valid_ids
    if bad: probs.append("cites unknown evidence: " + ", ".join(f"E{i}" for i in sorted(bad)))
    for p in BANNED:
        m = re.search(p, text or "", re.I)
        if m: probs.append(f"prescriptive/labelling phrase '{m.group(0)}': describe evidence and pose questions instead")
    if "?" not in (text or ""): probs.append("include at least one open question for the learner or family")
    return probs

def diff(before, after):
    d = {}
    for s, a in after.items():
        b = before.get(s)
        if b != a:
            d[s] = {"before": None if not b else {k: b[k] for k in ("level", "sources", "average", "trend")},
                    "after": {k: a[k] for k in ("level", "sources", "average", "trend")}}
    return d

def approve(pid, by, ok=True, reason="", discard_evidence=False):
    """Called ONLY by the teacher CLI. Not exposed as an MCP tool, by design."""
    c = conn()
    p = c.execute("SELECT * FROM proposals WHERE id=?", (pid,)).fetchone()
    if not p or p["status"] != "pending": raise ValueError("no such pending proposal")
    ids = json.loads(p["evidence_ids"])
    with c:
        c.execute("UPDATE proposals SET status=?,decided_by=?,decided_at=?,reason=? WHERE id=?",
                  ("approved" if ok else "rejected", by, time.time(), reason, pid))
        mark = "approved" if ok else ("discarded" if discard_evidence else None)
        if mark:
            c.executemany("UPDATE evidence SET status=? WHERE id=?", [(mark, i) for i in ids])
