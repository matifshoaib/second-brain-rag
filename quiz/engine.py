"""
engine.py - Second Brain Drill: active-recall engine over the RAG corpus.

Turns every note in chunks.jsonl into a spaced-repetition card, writes
questions from the note's own text with the local model, grades free-text
answers against key points drawn from that same text, and schedules the
next review (SM-2 style). Every note enters rotation, spread evenly across
vaults, so the drill eventually checks you on everything.

Standard library only (sqlite3, json, urllib) - no new dependencies.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

DAY = 86400.0
MIN_NOTE_CHARS = 600            # notes shorter than this are stubs, not drillable
WINDOW_CHARS = 5500             # source text handed to the model per question
SKIP_TITLE_RE = re.compile(
    r"(^|[\s_-])(index|moc|map[\s_-]of[\s_-]content|readme|template|vault[\s_-]meta)($|[\s_-])",
    re.I,
)
# vault scaffolding, build logs and personal plans - not knowledge to be tested on
SKIP_PATH_RE = re.compile(
    r"/00-MOC/|/00-Vault-Meta/|BUILD-TRACKER|\(archive\)|🏠|Homelab|Exam-Strategy|Day-of-Exam",
    re.I,
)
THINK_RE = re.compile(r"<think>.*?</think>", re.S)

VERDICTS = ("again", "hard", "good", "easy")

# How each question type is framed. The how-layer types only fire on notes
# that carry the matching how-layer field.
QTYPE_GUIDE = {
    "recall": "Ask them to explain a central concept, mechanism or distinction from the SOURCE in their own words.",
    "apply": "Pose a short, realistic scenario (2-3 sentences) and ask what they would do or conclude using the SOURCE's concepts.",
    "compare": "Ask them to compare two related concepts, patterns or options in the SOURCE: how they differ and when each one wins.",
    "misconception": "State a plausible but WRONG claim about the SOURCE's subject and ask them to judge it and correct it with reasoning. The claim itself goes in the question.",
    "elicit": "Ask what they must elicit from stakeholders on this topic - the things stakeholders will not volunteer - and why each matters.",
    "specify": "Ask them to state the concrete requirement, control or acceptance criterion this topic becomes, with measurable terms where the SOURCE gives them.",
    "design": "Ask about the design decision or trade-off this topic forces: the options, what each costs, and when each is the right call.",
    "regulatory": "Ask which supervisory expectation or regulatory anchor applies and how it shapes the requirement or the design.",
}
QTYPE_LABEL = {
    "recall": "Explain", "apply": "Apply", "compare": "Compare",
    "misconception": "Spot the error", "elicit": "Elicit", "specify": "Specify",
    "design": "Design", "regulatory": "Regulatory",
}
HOW_FIELD_FOR = {"elicit": "elicit", "specify": "specify", "design": "design", "regulatory": "dsib"}

QUESTION_PROMPT = """/no_think
You are a demanding examiner drilling a senior Business Systems Analyst and solutions architect who works in Canadian banking and payments. Write ONE question of type "{label}" that tests the SOURCE below.

Rules:
- The question must be answerable from the SOURCE alone. Never require facts that are not in it.
- Test understanding, not trivia. Never ask about note titles, tags, file names, section numbers or exact wording.
- It must not be answerable with a bare yes/no.
- Institution-neutral: never name a specific bank.
- {guide}

Return JSON only:
{{"question": "<the question>",
  "key_points": ["<3 to 6 short, atomic, checkable statements an excellent answer must contain, each grounded in the SOURCE>"],
  "model_answer": "<a concise expert answer, 80-180 words, grounded in the SOURCE>",
  "difficulty": "core" or "stretch"}}

SOURCE (note: {title} | vault: {vault})
<<<
{context}
>>>"""

GRADE_PROMPT = """/no_think
You are grading a senior professional's free-text answer against key points taken from their own notes.
Be rigorous but fair: credit meaning, not wording - different phrasing and synonyms count. Do not credit a point the answer does not actually make. Flag any statement that contradicts the SOURCE.

QUESTION:
{question}

KEY POINTS:
{points}

SOURCE:
<<<
{context}
>>>

ANSWER:
<<<
{answer}
>>>

Return JSON only:
{{"points": [{{"i": <key point number>, "hit": "yes" | "partial" | "no", "note": "<one short reason>"}}],
  "errors": ["<each factual error or contradiction in the answer; empty list if none>"],
  "feedback": "<2-4 sentences: what was strong, what was missing, and how to think about it>"}}"""


# ----------------------------------------------------------------------------
# Corpus
# ----------------------------------------------------------------------------

@dataclass
class Note:
    path: str
    title: str
    vault: str
    sections: list = field(default_factory=list)   # [(section_index, section, text)]
    how: dict = field(default_factory=dict)        # elicit/specify/design/dsib
    chars: int = 0

    @property
    def pretty_title(self) -> str:
        t = re.sub(r"^[0-9]{1,3}[A-Za-z]?[-_. ]+", "", self.title)
        t = t.replace("_", " ").replace("-", " ").strip()
        return re.sub(r"\s+", " ", t) or self.title

    def windows(self) -> list[str]:
        """Contiguous runs of sections, each at most WINDOW_CHARS, so repeat
        reviews of a long note walk through different parts of it."""
        out, buf = [], ""
        for _, sec, text in sorted(self.sections, key=lambda s: s[0]):
            piece = text.strip()
            if not piece:
                continue
            if buf and len(buf) + len(piece) > WINDOW_CHARS:
                out.append(buf)
                buf = ""
            buf = (buf + "\n\n" + piece).strip() if buf else piece[:WINDOW_CHARS]
        if buf:
            out.append(buf)
        return out or [""]

    def how_text(self) -> str:
        names = (("elicit", "Elicit"), ("specify", "Specify"), ("design", "Design"), ("dsib", "D-SIB Hook"))
        return "\n".join(f"{label}: {self.how[k]}" for k, label in names if self.how.get(k))


def load_corpus(chunks_path: str) -> dict[str, Note]:
    notes: dict[str, Note] = {}
    with open(chunks_path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            c = json.loads(line)
            p = c.get("note_path")
            if not p:
                continue
            n = notes.get(p)
            if n is None:
                n = notes[p] = Note(path=p, title=c.get("note_title") or p.rsplit("/", 1)[-1],
                                    vault=c.get("vault") or p.split("/", 1)[0])
            if not n.how:
                for k in ("elicit", "specify", "design", "dsib"):
                    v = c.get(f"bsa_{k}")
                    if v:
                        n.how[k] = v
            if c.get("chunk_type") == "how_layer":
                continue
            text = c.get("text") or ""
            n.sections.append((c.get("section_index", 0), c.get("section", ""), text))
            n.chars += len(text)
    return {p: n for p, n in notes.items() if drillable(n)}


def drillable(n: Note) -> bool:
    if n.chars < MIN_NOTE_CHARS or SKIP_PATH_RE.search(n.path):
        return False
    return not SKIP_TITLE_RE.search(n.pretty_title) and not SKIP_TITLE_RE.search(n.title)


# ----------------------------------------------------------------------------
# Scheduling (SM-2 variant)
# ----------------------------------------------------------------------------

def schedule(card: dict, verdict: str, now: float) -> dict:
    """Return the new scheduling state for a card after a verdict."""
    ease = card.get("ease") or 2.5
    ivl = card.get("interval") or 0.0
    reps = card.get("reps") or 0
    lapses = card.get("lapses") or 0

    if verdict == "again":
        if reps > 0:
            lapses += 1
        reps, ivl, ease = 0, 0.0, max(1.3, ease - 0.2)
        due = now + 10 * 60          # comes back later in this session
        status = "learning"
    else:
        if verdict == "hard":
            ivl = 0.5 if reps == 0 else max(1.0, ivl * 1.2) if ivl >= 1 else 1.0
            ease = max(1.3, ease - 0.15)
        elif verdict == "good":
            ivl = 1.0 if reps == 0 else 3.0 if reps == 1 else max(ivl + 1, ivl * ease)
        else:  # easy
            ivl = 4.0 if reps == 0 else max(ivl + 1, ivl * ease * 1.3)
            ease += 0.15
        reps += 1
        ivl = min(ivl, 365.0)
        if ivl >= 3:
            ivl *= random.uniform(0.95, 1.05)   # spread the load
        due = now + ivl * DAY
        status = "review"
    return {"ease": round(ease, 3), "interval": round(ivl, 3), "reps": reps,
            "lapses": lapses, "due": due, "status": status}


def verdict_for(score: int) -> str:
    return "again" if score < 40 else "hard" if score < 65 else "good" if score < 85 else "easy"


def interval_label(days: float) -> str:
    if days <= 0:
        return "10 min"
    if days < 1:
        return f"{max(1, round(days * 24))} h"
    if days < 30:
        return f"{round(days)} d"
    if days < 365:
        return f"{round(days / 30.4)} mo"
    return f"{round(days / 365, 1)} y"


def local_day_start(now: float) -> float:
    lt = time.localtime(now)
    return time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1))


# ----------------------------------------------------------------------------
# Local model
# ----------------------------------------------------------------------------

class LLMError(RuntimeError):
    pass


def parse_json(text: str) -> dict:
    text = THINK_RE.sub("", text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


class Ollama:
    def __init__(self, url: str, model: str, timeout: float = 300.0):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._gate = threading.Lock()     # one generation at a time on a 16GB Mac

    def json(self, prompt: str, temperature: float = 0.4, tries: int = 2) -> dict:
        body = json.dumps({
            "model": self.model, "prompt": prompt, "stream": False,
            "format": "json", "think": False, "keep_alive": "30m",
            "options": {"num_ctx": 8192, "num_predict": 1400, "temperature": temperature},
        }).encode()
        last = None
        for _ in range(tries):
            req = urllib.request.Request(f"{self.url}/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
            try:
                with self._gate, urllib.request.urlopen(req, timeout=self.timeout) as r:
                    out = json.loads(r.read().decode())
                return parse_json(out.get("response", ""))
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                raise LLMError(f"Ollama unreachable at {self.url} ({e.__class__.__name__}). Is Ollama running?") from e
            except (json.JSONDecodeError, ValueError) as e:
                last = e
        raise LLMError(f"Model returned unparseable output ({last})")

    def ping(self) -> bool:
        try:
            with urllib.request.urlopen(f"{self.url}/api/tags", timeout=3):
                return True
        except Exception:
            return False


# ----------------------------------------------------------------------------
# Drill
# ----------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS cards(
  note_path TEXT PRIMARY KEY, vault TEXT, title TEXT,
  status TEXT DEFAULT 'new', due REAL, interval REAL DEFAULT 0, ease REAL DEFAULT 2.5,
  reps INTEGER DEFAULT 0, lapses INTEGER DEFAULT 0, last_score INTEGER,
  last_review REAL, introduced REAL, active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS questions(
  id INTEGER PRIMARY KEY, note_path TEXT, qtype TEXT, win INTEGER,
  question TEXT, key_points TEXT, model_answer TEXT, difficulty TEXT,
  created REAL, asked INTEGER DEFAULT 0, retired INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS reviews(
  id INTEGER PRIMARY KEY, note_path TEXT, question_id INTEGER, answer TEXT,
  score INTEGER, verdict TEXT, auto_verdict TEXT, feedback TEXT, points TEXT,
  errors TEXT, prev_state TEXT, at REAL);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS ix_cards_due ON cards(status, due);
CREATE INDEX IF NOT EXISTS ix_q_note ON questions(note_path, asked, retired);
CREATE INDEX IF NOT EXISTS ix_r_at ON reviews(at);
"""

CARD_COLS = ("note_path", "vault", "title", "status", "due", "interval", "ease",
             "reps", "lapses", "last_score", "last_review", "introduced", "active")


class Drill:
    def __init__(self, db_path: str, chunks_path: str, llm: Ollama):
        self.db_path = db_path
        self.chunks_path = chunks_path
        self.llm = llm
        self.lock = threading.RLock()
        self.note_locks: dict[str, threading.Lock] = {}
        self.inflight: set[str] = set()
        self._tl = threading.local()
        self.conn.executescript(SCHEMA)
        self.notes: dict[str, Note] = {}
        self.reload()

    @property
    def conn(self) -> sqlite3.Connection:
        """One connection per thread (request threads + prefetch thread), WAL so
        readers never block on the writer. Writes are still serialized by self.lock."""
        c = getattr(self._tl, "c", None)
        if c is None:
            c = sqlite3.connect(self.db_path, timeout=30)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            self._tl.c = c
        return c

    # ---------- corpus sync ----------
    def reload(self) -> dict:
        notes = load_corpus(self.chunks_path)
        with self.lock:
            existing = {r["note_path"] for r in self.conn.execute("SELECT note_path FROM cards")}
            added = 0
            for p, n in notes.items():
                if p not in existing:
                    self.conn.execute("INSERT INTO cards(note_path, vault, title) VALUES(?,?,?)",
                                      (p, n.vault, n.pretty_title))
                    added += 1
                else:
                    self.conn.execute("UPDATE cards SET vault=?, title=?, active=1 WHERE note_path=?",
                                      (n.vault, n.pretty_title, p))
            gone = existing - set(notes)
            for p in gone:
                self.conn.execute("UPDATE cards SET active=0 WHERE note_path=?", (p,))
            self.conn.commit()
            self.notes = notes
        return {"notes": len(notes), "added": added, "retired": len(gone)}

    # ---------- settings ----------
    def setting(self, key: str, default):
        r = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return type(default)(r["value"]) if r else default

    def set_setting(self, key: str, value) -> None:
        with self.lock:
            self.conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)", (key, str(value)))
            self.conn.commit()

    @property
    def new_per_day(self) -> int:
        return self.setting("new_per_day", 25)

    # ---------- queue ----------
    def _card(self, note_path: str) -> dict | None:
        r = self.conn.execute("SELECT * FROM cards WHERE note_path=?", (note_path,)).fetchone()
        return dict(r) if r else None

    def new_today(self, now: float) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM cards WHERE introduced >= ?",
                                 (local_day_start(now),)).fetchone()[0]

    def upcoming(self, vault: str | None = None, extra: bool = False, n: int = 1,
                 exclude: set | None = None, now: float | None = None) -> list[str]:
        """Next n note_paths to drill: due reviews first, then new notes spread
        across vaults (least-covered vault first) up to the daily new limit."""
        now = now or time.time()
        exclude = set(exclude or ())
        out: list[str] = []
        vf, args = ("AND vault=?", [vault]) if vault else ("", [])
        with self.lock:
            for r in self.conn.execute(
                f"SELECT note_path FROM cards WHERE active=1 AND status!='new' AND due<=? {vf} ORDER BY due",
                [now, *args]):
                if r["note_path"] not in exclude and r["note_path"] in self.notes:
                    out.append(r["note_path"])
                    if len(out) >= n:
                        return out
            budget = (10 ** 6 if extra else self.new_per_day - self.new_today(now)) - 0
            if budget > 0:
                cov = {row["vault"]: (row["intro"] / row["total"]) for row in self.conn.execute(
                    f"SELECT vault, COUNT(*) total, SUM(status!='new') intro FROM cards WHERE active=1 {vf} GROUP BY vault",
                    args)}
                rows = self.conn.execute(
                    f"SELECT note_path, vault FROM cards WHERE active=1 AND status='new' "
                    f"AND (due IS NULL OR due<=?) {vf} ORDER BY note_path", [now, *args]).fetchall()
                by_vault: dict[str, list[str]] = {}
                for r in rows:
                    if r["note_path"] not in exclude and r["note_path"] in self.notes:
                        by_vault.setdefault(r["vault"], []).append(r["note_path"])
                taken = {v: 0 for v in by_vault}
                while len(out) < n and budget > 0 and any(by_vault.values()):
                    # least-covered vault first, so every vault keeps moving
                    v = min((v for v in by_vault if by_vault[v]),
                            key=lambda v: (cov.get(v, 0) + taken[v] / max(1, len(rows)), v))
                    out.append(by_vault[v].pop(0))
                    taken[v] += 1
                    budget -= 1
            if not out:
                # nothing due: pull the soonest relearn card forward rather than idle
                r = self.conn.execute(
                    f"SELECT note_path FROM cards WHERE active=1 AND status='learning' AND due<=? {vf} ORDER BY due LIMIT 1",
                    [now + 20 * 60, *args]).fetchone()
                if r and r["note_path"] not in exclude:
                    out.append(r["note_path"])
        return out

    # ---------- questions ----------
    def _qtype_for(self, note: Note, card: dict) -> tuple[str, int]:
        types = ["recall", "apply", "compare", "misconception"]
        types += [t for t, f in HOW_FIELD_FOR.items() if note.how.get(f)]
        seed = int(hashlib.sha1(note.path.encode()).hexdigest(), 16)
        rng = random.Random(seed)
        rng.shuffle(types)
        if "recall" in types:            # first exposure always builds the foundation
            types.remove("recall")
            types.insert(0, "recall")
        asked = self.conn.execute("SELECT COUNT(*) FROM questions WHERE note_path=? AND asked=1",
                                  (note.path,)).fetchone()[0]
        qtype = types[asked % len(types)]
        wins = note.windows()
        win = (seed + asked) % len(wins)
        return qtype, win

    def _context(self, note: Note, qtype: str, win: int) -> str:
        wins = note.windows()
        body = wins[win % len(wins)]
        if qtype in HOW_FIELD_FOR and note.how:
            return (note.how_text() + "\n\n" + body)[: WINDOW_CHARS + 1200]
        return body

    def pending_question(self, note_path: str) -> dict | None:
        r = self.conn.execute(
            "SELECT * FROM questions WHERE note_path=? AND asked=0 AND retired=0 ORDER BY id DESC LIMIT 1",
            (note_path,)).fetchone()
        return dict(r) if r else None

    def ensure_question(self, note_path: str) -> dict:
        """Return the pending question for a note, generating one if needed.
        Safe to call from the prefetch thread and a request at the same time."""
        lock = self.note_locks.setdefault(note_path, threading.Lock())
        with lock:
            q = self.pending_question(note_path)
            if q:
                return q
            note = self.notes[note_path]
            card = self._card(note_path) or {}
            qtype, win = self._qtype_for(note, card)
            self.inflight.add(note_path)
            try:
                q = self._generate(note, qtype, win)
            finally:
                self.inflight.discard(note_path)
            with self.lock:
                cur = self.conn.execute(
                    "INSERT INTO questions(note_path, qtype, win, question, key_points, model_answer, difficulty, created) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (note_path, qtype, win, q["question"], json.dumps(q["key_points"]),
                     q["model_answer"], q["difficulty"], time.time()))
                self.conn.commit()
            return self.pending_question(note_path) or {**q, "id": cur.lastrowid}

    def _generate(self, note: Note, qtype: str, win: int) -> dict:
        prompt = QUESTION_PROMPT.format(label=QTYPE_LABEL[qtype], guide=QTYPE_GUIDE[qtype],
                                        title=note.pretty_title, vault=note.vault,
                                        context=self._context(note, qtype, win))
        for attempt in range(2):
            d = self.llm.json(prompt, temperature=0.5 + 0.2 * attempt)
            question = str(d.get("question") or "").strip()
            kps = [str(k).strip() for k in (d.get("key_points") or []) if str(k).strip()]
            if len(question) > 15 and len(kps) >= 2:
                return {"question": question, "key_points": kps[:6],
                        "model_answer": str(d.get("model_answer") or "").strip(),
                        "difficulty": "stretch" if str(d.get("difficulty")).lower() == "stretch" else "core"}
        raise LLMError("The model did not produce a usable question for this note.")

    # ---------- grading ----------
    def grade(self, question_id: int, answer: str, idk: bool = False) -> dict:
        q = self.conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        if not q:
            raise KeyError("question not found")
        q = dict(q)
        note = self.notes.get(q["note_path"])
        kps = json.loads(q["key_points"])
        answer = (answer or "").strip()

        if idk or len(answer) < 3:
            points = [{"text": k, "hit": "no", "note": ""} for k in kps]
            errors, feedback, score = [], "No answer given - read the model answer and the key points, then this note comes back in 10 minutes.", 0
        else:
            ctx = self._context(note, q["qtype"], q["win"]) if note else ""
            d = self.llm.json(GRADE_PROMPT.format(
                question=q["question"], points="\n".join(f"{i}. {k}" for i, k in enumerate(kps, 1)),
                context=ctx, answer=answer[:4000]), temperature=0.1)
            marks = {}
            for p in d.get("points") or []:
                try:
                    marks[int(p.get("i"))] = p
                except (TypeError, ValueError):
                    continue
            points = []
            for i, k in enumerate(kps, 1):
                p = marks.get(i, {})
                hit = str(p.get("hit", "no")).lower()
                hit = "yes" if hit in ("yes", "true", "hit") else "partial" if hit.startswith("part") else "no"
                points.append({"text": k, "hit": hit, "note": str(p.get("note") or "").strip()})
            errors = [str(e).strip() for e in (d.get("errors") or []) if str(e).strip()]
            feedback = str(d.get("feedback") or "").strip()
            # score is computed here, not trusted from the model
            got = sum(1.0 if p["hit"] == "yes" else 0.5 if p["hit"] == "partial" else 0.0 for p in points)
            score = round(100 * got / max(1, len(points))) - 12 * min(len(errors), 2)
            score = max(0, min(100, score))

        verdict = verdict_for(score)
        now = time.time()
        with self.lock:
            card = self._card(q["note_path"])
            prev = {k: card.get(k) for k in CARD_COLS}
            new = schedule(card, verdict, now)
            self._apply(q["note_path"], new, score, now, first=card["status"] == "new")
            self.conn.execute("UPDATE questions SET asked=1 WHERE id=?", (question_id,))
            cur = self.conn.execute(
                "INSERT INTO reviews(note_path, question_id, answer, score, verdict, auto_verdict, feedback, points, errors, prev_state, at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (q["note_path"], question_id, answer, score, verdict, verdict, feedback,
                 json.dumps(points), json.dumps(errors), json.dumps(prev), now))
            self.conn.commit()
        return {"review_id": cur.lastrowid, "score": score, "verdict": verdict, "points": points,
                "errors": errors, "feedback": feedback, "model_answer": q["model_answer"],
                "options": self.verdict_options(prev, now), "source": self.source(q["note_path"])}

    def _apply(self, note_path: str, new: dict, score: int, now: float, first: bool) -> None:
        self.conn.execute(
            "UPDATE cards SET status=?, due=?, interval=?, ease=?, reps=?, lapses=?, last_score=?, last_review=?, "
            "introduced=COALESCE(introduced, ?) WHERE note_path=?",
            (new["status"], new["due"], new["interval"], new["ease"], new["reps"], new["lapses"],
             score, now, now if first else None, note_path))

    def verdict_options(self, prev: dict, now: float) -> dict:
        """Next-interval label for each verdict, computed from the pre-review state."""
        random.seed(0)
        out = {v: interval_label(schedule(prev, v, now)["interval"]) for v in VERDICTS}
        random.seed()
        return out

    def override(self, review_id: int, verdict: str) -> dict:
        if verdict not in VERDICTS:
            raise ValueError("bad verdict")
        with self.lock:
            r = self.conn.execute("SELECT * FROM reviews WHERE id=?", (review_id,)).fetchone()
            if not r:
                raise KeyError("review not found")
            prev = json.loads(r["prev_state"])
            new = schedule(prev, verdict, r["at"])
            self.conn.execute(
                "UPDATE cards SET status=?, due=?, interval=?, ease=?, reps=?, lapses=?, "
                "introduced=COALESCE(?, introduced) WHERE note_path=?",
                (new["status"], new["due"], new["interval"], new["ease"], new["reps"], new["lapses"],
                 prev.get("introduced") or r["at"], r["note_path"]))
            self.conn.execute("UPDATE reviews SET verdict=? WHERE id=?", (verdict, review_id))
            self.conn.commit()
        return {"verdict": verdict, "next": interval_label(new["interval"])}

    def skip(self, question_id: int, bad: bool) -> None:
        with self.lock:
            q = self.conn.execute("SELECT note_path FROM questions WHERE id=?", (question_id,)).fetchone()
            if not q:
                return
            if bad:   # throw the question away; the note stays where it is in the queue
                self.conn.execute("UPDATE questions SET retired=1 WHERE id=?", (question_id,))
            else:     # keep the question, push the note back a few hours
                self.conn.execute("UPDATE cards SET due=? WHERE note_path=?",
                                  (time.time() + 4 * 3600, q["note_path"]))
            self.conn.commit()

    # ---------- presentation ----------
    def source(self, note_path: str) -> dict:
        n = self.notes.get(note_path)
        if not n:
            return {"path": note_path}
        return {"path": n.path, "title": n.pretty_title, "vault": n.vault, "how": n.how}

    def card_view(self, note_path: str, q: dict, now: float | None = None) -> dict:
        now = now or time.time()
        card = self._card(note_path)
        n = self.notes[note_path]
        status = card["status"]
        label = "New" if status == "new" else "Relearn" if status == "learning" else "Review"
        return {
            "note_path": note_path, "vault": n.vault, "title": n.pretty_title, "status": label,
            "reps": card["reps"], "lapses": card["lapses"], "last_score": card["last_score"],
            "question": {"id": q["id"], "text": q["question"], "qtype": q["qtype"],
                         "label": QTYPE_LABEL.get(q["qtype"], q["qtype"]), "difficulty": q["difficulty"]},
        }

    def stats(self, vault: str | None = None, now: float | None = None) -> dict:
        now = now or time.time()
        day0 = local_day_start(now)
        vf, args = ("AND vault=?", [vault]) if vault else ("", [])
        c = self.conn
        tot = c.execute(f"SELECT COUNT(*) FROM cards WHERE active=1 {vf}", args).fetchone()[0]
        intro = c.execute(f"SELECT COUNT(*) FROM cards WHERE active=1 AND status!='new' {vf}", args).fetchone()[0]
        mastered = c.execute(f"SELECT COUNT(*) FROM cards WHERE active=1 AND interval>=21 {vf}", args).fetchone()[0]
        due = c.execute(f"SELECT COUNT(*) FROM cards WHERE active=1 AND status!='new' AND due<=? {vf}", [now, *args]).fetchone()[0]
        reviewed_today = c.execute("SELECT COUNT(*) FROM reviews WHERE at>=?", (day0,)).fetchone()[0]
        avg = c.execute("SELECT AVG(score) FROM (SELECT score FROM reviews ORDER BY at DESC LIMIT 50)").fetchone()[0]

        days = {local_day_start(r[0]) for r in c.execute("SELECT at FROM reviews WHERE at>=?", (now - 400 * DAY,))}
        streak, d = 0, day0 if day0 in days else day0 - DAY
        while d in days:
            streak += 1
            d = local_day_start(d - 3600)
        forecast = []
        for i in range(7):
            start = day0 + i * DAY
            end = start + DAY
            lo = -1e18 if i == 0 else start
            forecast.append(c.execute(
                f"SELECT COUNT(*) FROM cards WHERE active=1 AND status!='new' AND due>=? AND due<? {vf}",
                [lo, end, *args]).fetchone()[0])

        vaults = [dict(r) for r in c.execute(
            "SELECT vault, COUNT(*) total, SUM(status!='new') introduced, SUM(interval>=21) mastered, "
            "SUM(status!='new' AND due<=?) due, ROUND(AVG(last_score)) avg_score "
            "FROM cards WHERE active=1 GROUP BY vault ORDER BY vault", (now,))]
        weakest = [dict(r) for r in c.execute(
            f"SELECT note_path, vault, title, last_score, lapses FROM cards WHERE active=1 AND status!='new' {vf} "
            "ORDER BY lapses DESC, last_score ASC LIMIT 8", args)]
        remaining = tot - intro
        return {
            "total": tot, "introduced": intro, "mastered": mastered, "due": due,
            "coverage": round(100 * intro / tot, 1) if tot else 0,
            "mastery": round(100 * mastered / tot, 1) if tot else 0,
            "reviewed_today": reviewed_today, "new_today": self.new_today(now),
            "new_per_day": self.new_per_day, "avg_score": round(avg) if avg is not None else None,
            "streak": streak, "forecast": forecast, "vaults": vaults, "weakest": weakest,
            "eta_days": -(-remaining // max(1, self.new_per_day)) if remaining else 0,
        }
