"""
verify_error_pattern_effect_30q.py - TASK-057B

Script de verification comportementale : session 30Q avec mesure avant/apres
de l'effet Error Pattern Memory (TASK-057).

Usage:
  python tools/testing/verify_error_pattern_effect_30q.py [options]
  python tools/testing/verify_error_pattern_effect_30q.py --dry-run
  python tools/testing/verify_error_pattern_effect_30q.py --user Guilhem --n 30 --seed 42 --no-confirm

Options:
  --user USER     Username (default: Guilhem)
  --n N           Number of questions (default: 30)
  --seed SEED     Random seed for reproducibility (default: 42)
  --no-confirm    Skip confirmation prompt before API session
  --dry-run       Simulate without API calls or DB writes (shows report structure)
"""

import argparse
import os
import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from typing import Optional

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Safe UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Constants ─────────────────────────────────────────────────────────────────
FALLBACK_USER_ID = "f8d18fb0-727f-4b39-bed7-1f660875ab09"
DEFAULT_USERNAME = "Guilhem"
DEFAULT_N        = 30
DEFAULT_SEED     = 42
N_RECENT_STATE   = 20  # window for before/after state measurement

# Response profile weights (profile, weight)
RESPONSE_PROFILES = [
    ("correct",       0.40),
    ("medium",        0.25),
    ("vague",         0.15),
    ("hors_sujet",    0.10),
    ("non_evaluable", 0.10),
]

_STATIC_RESPONSES = {
    "medium": (
        "Je pense que c'est lie au processus mentionne dans le document. "
        "Il faut respecter certaines regles et etapes mais je ne me souviens "
        "pas exactement de tous les details et de l'ordre precis a suivre."
    ),
    "vague": (
        "C'est quelque chose qui concerne la gestion et le traitement "
        "des informations dans le cadre prevu par les regles en vigueur."
    ),
    "hors_sujet": (
        "Je crois que cela concerne principalement la gestion des ressources "
        "humaines et la planification strategique du budget annuel de l'entreprise, "
        "ainsi que les relations avec les partenaires et prestataires externes."
    ),
    "non_evaluable": "je ne sais pas",
}

_DRY_CORRECTIONS = {
    "correct":       {"score": 0.85, "error_type": "correct",      "topic": "dry_run", "expected_answer": "[dry]", "correction": "[dry-run]"},
    "medium":        {"score": 0.55, "error_type": "reponse_vague", "topic": "dry_run", "expected_answer": "[dry]", "correction": "[dry-run]"},
    "vague":         {"score": 0.28, "error_type": "reponse_vague", "topic": "dry_run", "expected_answer": "[dry]", "correction": "[dry-run]"},
    "hors_sujet":    {"score": 0.10, "error_type": "hors_sujet",    "topic": "dry_run", "expected_answer": "[dry]", "correction": "[dry-run]"},
    "non_evaluable": {"score": 0.00, "error_type": "non_evaluable", "topic": "dry_run", "expected_answer": "[dry]", "correction": "[dry-run]"},
}

_FAKE_CHUNKS = [
    {
        "chunk_id":       1,
        "document_id":    1,
        "chunk_text":     "Le processus de gestion implique plusieurs etapes obligatoires a respecter.",
        "section_label":  "Section 1 (dry)",
        "document_title": "Document test",
    },
    {
        "chunk_id":       2,
        "document_id":    1,
        "chunk_text":     "Les delais de traitement sont fixes par la reglementation en vigueur dans ce domaine.",
        "section_label":  "Section 2 (dry)",
        "document_title": "Document test",
    },
]

_SEP      = "-" * 80
_SEP_THIN = "." * 80
_QTYPES   = ["question_directe", "vrai_faux", "reformulation",
             "cas_pratique", "consequence", "question_piege"]


# ── Utility ───────────────────────────────────────────────────────────────────

def _s(text: str, maxlen: int = 0) -> str:
    """Truncate and replace non-printable for safe terminal output."""
    if maxlen > 0:
        text = text[:maxlen]
    return text


def _pct(v: Optional[float]) -> str:
    return f"{v:.1%}" if v is not None else "N/A"


# ── DB / User helpers ─────────────────────────────────────────────────────────

def get_user_id(username: str) -> tuple:
    """Return (user_id, found_in_db: bool)."""
    import database as _db
    try:
        with sqlite3.connect(_db.DB_PATH) as conn:
            row = conn.execute(
                "SELECT user_id FROM users WHERE username = ? LIMIT 1",
                (username,),
            ).fetchone()
        if row:
            return row[0], True
    except Exception:
        pass
    return FALLBACK_USER_ID, False


def get_available_chunks() -> list:
    import database as _db
    with sqlite3.connect(_db.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT c.id AS chunk_id, c.chunk_text, c.document_id,
                   COALESCE(c.section_title, 'Section ' || (c.chunk_index+1)) AS section_label,
                   d.title AS document_title
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.embedding IS NOT NULL
            ORDER BY d.id, c.chunk_index
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_state(user_id: str) -> dict:
    """Capture current pedagogical state metrics."""
    import database as _db
    from engine.error_pattern_memory import detect_persistent_error_patterns

    ep = detect_persistent_error_patterns(user_id)

    with sqlite3.connect(_db.DB_PATH) as conn:
        score_rows = conn.execute(
            "SELECT score FROM attempts WHERE user_id=? AND score IS NOT NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, N_RECENT_STATE),
        ).fetchall()
        recent_scores = [float(r[0]) for r in score_rows]

        recent_rows = conn.execute(
            "SELECT error_type, pedagogy_type FROM attempts "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, N_RECENT_STATE),
        ).fetchall()

    error_dist: dict = {}
    qtype_dist: dict = {}
    for (et, pt) in recent_rows:
        if et and et not in ("", "non_evaluable"):
            error_dist[et] = error_dist.get(et, 0) + 1
        if pt:
            qtype_dist[pt] = qtype_dist.get(pt, 0) + 1

    avg = sum(recent_scores) / len(recent_scores) if recent_scores else None
    return {
        "patterns":         ep["patterns"],
        "persistent_types": ep["persistent_types"],
        "has_critical":     ep["has_critical"],
        "has_chronic":      ep["has_chronic"],
        "avg_score":        round(avg, 3) if avg is not None else None,
        "recent_scores":    recent_scores,
        "error_dist":       error_dist,
        "qtype_dist":       qtype_dist,
        "n_recent":         len(recent_scores),
    }


def _make_correct_response(chunk_text: str) -> str:
    """Build a contextually grounded 'correct' response using chunk content."""
    snippet = chunk_text[:80].strip()
    if " " in snippet:
        snippet = snippet[:snippet.rfind(" ")]
    return (
        f"Selon le texte, {snippet.lower()}. "
        "Cette procedure necessite de respecter les etapes et les conditions "
        "d'application definies dans le document source, en suivant l'ordre indique."
    )


def pick_profile(rng: random.Random) -> str:
    profiles = [p for p, _ in RESPONSE_PROFILES]
    weights  = [w for _, w in RESPONSE_PROFILES]
    return rng.choices(profiles, weights=weights, k=1)[0]


# ── Session runner ────────────────────────────────────────────────────────────

def run_session(
    user_id:                 str,
    chunks:                  list,
    n:                       int,
    seed:                    int,
    dry_run:                 bool,
    persistent_types_before: list,
) -> list:
    from ai_service import generate_question, correct_answer, _check_answer_evaluable
    from db.analytics import save_attempt

    rng     = random.Random(seed)
    results = []

    p_inj_str = ",".join(persistent_types_before) if persistent_types_before else "none"

    print()
    print(_SEP)
    print("  SESSION EN COURS")
    print(_SEP)
    print(f"  {'Q':>3}  {'type':<22}  {'profil':<14}  {'score':>5}  {'erreur':<18}  topic")
    print(_SEP_THIN)

    for i in range(n):
        q_num = i + 1
        chunk       = rng.choice(chunks)
        source_text = chunk["chunk_text"]
        document_id = chunk["document_id"]
        chunk_id_db = chunk["chunk_id"]

        t_start = time.time()

        # ── Generate question ──────────────────────────────────────────────
        if dry_run:
            question      = f"[DRY] Question #{q_num} - {chunk['section_label'][:30]}"
            chunk_ids_ret = [chunk_id_db]
            question_type = rng.choice(_QTYPES)
        else:
            try:
                question, chunk_ids_ret, question_type, _ = generate_question(
                    source_text=source_text,
                    document_id=document_id,
                    user_id=user_id,
                )
            except Exception as exc:
                print(f"  Q{q_num:02d}  ERREUR generate: {str(exc)[:50]}")
                results.append({
                    "q_num": q_num, "question_type": "?", "profile": "error",
                    "score": None, "error_type": "generation_error",
                    "topic": "", "pattern_injected": persistent_types_before,
                    "note": str(exc)[:40],
                    "chunk_id": chunk_id_db, "document_id": document_id,
                })
                continue

        # ── Build simulated answer ─────────────────────────────────────────
        profile     = pick_profile(rng)
        user_answer = (
            _make_correct_response(source_text)
            if profile == "correct"
            else _STATIC_RESPONSES[profile]
        )

        # ── Correct answer ─────────────────────────────────────────────────
        if dry_run:
            cr = dict(_DRY_CORRECTIONS[profile])
        elif profile == "non_evaluable":
            rejection = _check_answer_evaluable(user_answer)
            cr = rejection if rejection else {
                "score": 0.0, "error_type": "non_evaluable",
                "topic": "", "expected_answer": "", "correction": "",
            }
        else:
            try:
                rejection = _check_answer_evaluable(user_answer)
                cr = rejection if rejection else correct_answer(
                    question, user_answer, source_text
                )
            except Exception as exc:
                cr = {
                    "score": 0.0, "error_type": "hors_sujet",
                    "topic": "", "expected_answer": "", "correction": str(exc),
                }

        elapsed    = time.time() - t_start
        score      = float(cr.get("score", 0.0))
        error_type = str(cr.get("error_type") or "")
        topic      = str(cr.get("topic") or "")

        # ── Save attempt ───────────────────────────────────────────────────
        if not dry_run:
            try:
                save_attempt(
                    question              = question,
                    user_answer           = user_answer,
                    expected_answer       = str(cr.get("expected_answer") or ""),
                    correction            = str(cr.get("correction") or ""),
                    score                 = score,
                    response_time_seconds = elapsed,
                    error_type            = error_type,
                    topic                 = topic,
                    pedagogy_type         = question_type,
                    document_id           = document_id,
                    chunk_id              = chunk_ids_ret[0] if chunk_ids_ret else chunk_id_db,
                    user_id               = user_id,
                )
            except Exception as exc:
                print(f"  [WARN] save_attempt Q{q_num}: {exc}")

        et_disp = (error_type or "correct")[:18]
        print(
            f"  Q{q_num:02d}  {question_type:<22}  {profile:<14}  {score:5.2f}"
            f"  {et_disp:<18}  {_s(topic, 20)}"
        )

        results.append({
            "q_num":           q_num,
            "question_type":   question_type,
            "profile":         profile,
            "score":           score,
            "error_type":      error_type,
            "topic":           _s(topic, 30),
            "pattern_injected": persistent_types_before,
            "note":            f"inj={p_inj_str}",
            "chunk_id":        chunk_ids_ret[0] if chunk_ids_ret else chunk_id_db,
            "document_id":     document_id,
        })

    print(_SEP_THIN)
    return results


# ── Delta & Verdict ───────────────────────────────────────────────────────────

def compute_delta(before: dict, after: dict, results: list) -> dict:
    b_avg = before.get("avg_score")
    a_avg = after.get("avg_score")
    score_delta = (
        round(a_avg - b_avg, 3)
        if b_avg is not None and a_avg is not None
        else None
    )

    session_scores = [r["score"] for r in results if r.get("score") is not None]
    session_avg    = (
        round(sum(session_scores) / len(session_scores), 3)
        if session_scores else None
    )

    session_errors: dict = {}
    session_types:  dict = {}
    for r in results:
        et = r.get("error_type") or ""
        qt = r.get("question_type") or ""
        if et:
            session_errors[et] = session_errors.get(et, 0) + 1
        if qt:
            session_types[qt]  = session_types.get(qt, 0) + 1

    b_trends = {p["error_type"]: p["trend"] for p in before.get("patterns", [])}
    a_trends = {p["error_type"]: p["trend"] for p in after.get("patterns", [])}
    all_ets  = set(b_trends) | set(a_trends)
    trend_changes = {
        et: (b_trends.get(et, "none"), a_trends.get(et, "none"))
        for et in all_ets
        if b_trends.get(et) != a_trends.get(et)
    }

    new_critiques = [
        et for et, (bt, at) in trend_changes.items()
        if at == "critique" and bt != "critique"
    ]
    improvements = [
        et for et, (bt, at) in trend_changes.items()
        if at in ("en_amelioration", "stabilise", "stabilisé")
        and bt not in ("en_amelioration", "stabilise", "stabilisé")
    ]

    return {
        "score_delta":    score_delta,
        "before_avg":     b_avg,
        "after_avg":      a_avg,
        "session_avg":    session_avg,
        "session_errors": session_errors,
        "session_types":  session_types,
        "error_delta": {
            et: after.get("error_dist", {}).get(et, 0) - before.get("error_dist", {}).get(et, 0)
            for et in (set(before.get("error_dist", {})) | set(after.get("error_dist", {})))
        },
        "trend_changes":  trend_changes,
        "new_critiques":  new_critiques,
        "improvements":   improvements,
    }


def get_verdict(delta: dict, before: dict) -> tuple:
    reasons = []
    sd = delta.get("score_delta")

    if delta.get("new_critiques"):
        reasons.append(f"Nouveaux patterns critiques: {delta['new_critiques']}")
        return "REGRESSION", reasons
    if sd is not None and sd < -0.10:
        reasons.append(f"Score moyen en baisse de {sd:.3f}")
        return "REGRESSION", reasons

    if delta.get("improvements"):
        reasons.append(f"Patterns ameliores: {delta['improvements']}")
        return "IMPROVEMENT", reasons
    if sd is not None and sd > 0.05:
        reasons.append(f"Score moyen en hausse de +{sd:.3f}")
        return "IMPROVEMENT", reasons

    if before.get("n_recent", 0) < 5:
        reasons.append("Historique avant insuffisant pour comparaison fiable (< 5 tentatives)")
        return "INCONCLUSIVE", reasons

    reasons.append("Variation dans la marge de bruit — pas de changement significatif detecte")
    return "STABLE", reasons


# ── Report helpers ────────────────────────────────────────────────────────────

def _fmt_patterns(patterns: list) -> str:
    if not patterns:
        return "  (aucun pattern detecte)"
    lines = []
    for p in patterns:
        lines.append(
            f"  [{p['trend'].upper():<16}] {p['error_type']:<20}"
            f" n={p['count']} avg={p['avg_score']:.0%}"
            f" last={p['last_seen_days']:.0f}j ago={p['first_seen_days']:.0f}j"
        )
    return "\n".join(lines)


def _fmt_dist(d: dict, label: str) -> str:
    if not d:
        return f"  {label}: (aucune donnee)"
    items = sorted(d.items(), key=lambda x: -x[1])[:6]
    content = " | ".join(f"{k}={v}" for k, v in items)
    return f"  {label}: {content}"


# ── Full report ───────────────────────────────────────────────────────────────

def print_full_report(
    config:   dict,
    before:   dict,
    results:  list,
    after:    dict,
    delta:    dict,
    verd:     tuple,
    dry_run:  bool,
) -> None:
    verdict_str, verdict_reasons = verd

    print()
    print("=" * 80)
    print("  RAPPORT COMPLET - Error Pattern Memory Effect Verification (TASK-057B)")
    print("=" * 80)

    # ── A. CONFIG ──────────────────────────────────────────────────────────────
    print()
    print("A. CONFIG SESSION")
    print(_SEP_THIN)
    uid_short = config["user_id"][:8] + "..."
    print(f"  user       : {config['username']} ({uid_short})")
    print(f"  n          : {config['n']} questions")
    print(f"  seed       : {config['seed']}")
    print(f"  mode       : {'DRY-RUN (pas d API, pas de DB)' if dry_run else 'API REELLE + DB'}")
    print(f"  timestamp  : {config['timestamp']}")

    # ── B. AVANT ───────────────────────────────────────────────────────────────
    print()
    print("B. AVANT SESSION")
    print(_SEP_THIN)
    print(f"  Score moyen recent  : {_pct(before['avg_score'])}  (sur {before['n_recent']} tentatives)")
    active_b = [p for p in before["patterns"] if p["trend"] not in ("stabilise", "stabilisé")]
    print(f"  Patterns actifs     : {len(active_b)}")
    print(f"  Persistent types    : {before['persistent_types'] or ['(aucun)']}")
    print()
    print("  Patterns:")
    print(_fmt_patterns(before["patterns"]))
    print()
    print(_fmt_dist(before["error_dist"], "Erreurs recentes"))
    print(_fmt_dist(before["qtype_dist"], "Types de questions"))

    # ── C. PENDANT ─────────────────────────────────────────────────────────────
    print()
    print("C. PENDANT SESSION - Tableau synthetique")
    print(_SEP_THIN)
    hdr = (
        f"  {'Q':>3}  {'type':<22}  {'profil':<14}  {'score':>5}"
        f"  {'erreur':<18}  {'topic':<20}  injecte"
    )
    print(hdr)
    print("  " + "-" * 96)
    for r in results:
        score_s = f"{r['score']:5.2f}" if r.get("score") is not None else "  N/A"
        et_str  = (r.get("error_type") or "correct")[:18]
        p_inj   = ",".join(r.get("pattern_injected") or []) or "none"
        print(
            f"  Q{r['q_num']:02d}  {r['question_type']:<22}  {r['profile']:<14}"
            f"  {score_s}  {et_str:<18}  {_s(r.get('topic',''), 20):<20}  {p_inj}"
        )

    # ── D. APRES ────────────────────────────────────────────────────────────────
    print()
    print("D. APRES SESSION")
    print(_SEP_THIN)
    print(f"  Score moyen recent  : {_pct(after['avg_score'])}  (sur {after['n_recent']} tentatives)")
    active_a = [p for p in after["patterns"] if p["trend"] not in ("stabilise", "stabilisé")]
    print(f"  Patterns actifs     : {len(active_a)}")
    print(f"  Persistent types    : {after['persistent_types'] or ['(aucun)']}")
    print()
    print("  Patterns:")
    print(_fmt_patterns(after["patterns"]))
    print()
    print(_fmt_dist(after["error_dist"], "Erreurs recentes"))
    print(_fmt_dist(after["qtype_dist"], "Types de questions"))

    # ── E. DELTA ────────────────────────────────────────────────────────────────
    print()
    print("E. DELTA (apres - avant)")
    print(_SEP_THIN)

    sd = delta["score_delta"]
    if sd is not None:
        sign = "+" if sd >= 0 else ""
        print(
            f"  Score moyen     : {_pct(delta['before_avg'])} -> {_pct(delta['after_avg'])}"
            f"  (delta={sign}{sd:.3f})"
        )
    else:
        print(f"  Score moyen     : avant={_pct(delta['before_avg'])}  apres={_pct(delta['after_avg'])}")

    if delta["session_avg"] is not None:
        print(f"  Score session   : {_pct(delta['session_avg'])}  ({len(results)} questions)")

    print()
    s_err = dict(sorted(delta["session_errors"].items(), key=lambda x: -x[1]))
    s_typ = dict(sorted(delta["session_types"].items(), key=lambda x: -x[1]))
    print(f"  Session - erreurs      : {s_err}")
    print(f"  Session - types        : {s_typ}")

    print()
    if delta["trend_changes"]:
        print("  Changements de tendance patterns:")
        for et, (bt, at) in delta["trend_changes"].items():
            print(f"    {et:<20}: {bt} -> {at}")
    else:
        print("  Changements de tendance patterns : (aucun)")

    if delta["new_critiques"]:
        print(f"  ATTENTION - Nouveaux critiques  : {delta['new_critiques']}")
    if delta["improvements"]:
        print(f"  Ameliorations detectees         : {delta['improvements']}")

    # ── F. VERDICT ──────────────────────────────────────────────────────────────
    print()
    print("F. VERDICT")
    print(_SEP_THIN)
    print(f"  >> {verdict_str}")
    for reason in verdict_reasons:
        print(f"     - {reason}")

    # ── G. COPY BLOCK ───────────────────────────────────────────────────────────
    _print_copy_block(config, before, results, after, delta, verdict_str, verdict_reasons, dry_run)

    print()
    print("=" * 80)


def _print_copy_block(
    config, before, results, after, delta, verdict_str, verdict_reasons, dry_run
):
    avg_b = _pct(before["avg_score"])
    avg_a = _pct(after["avg_score"])
    sd    = delta.get("score_delta")
    sd_s  = f"{'+'if sd and sd>=0 else ''}{sd:.3f}" if sd is not None else "N/A"

    def _pats_txt(patterns):
        if not patterns:
            return "  (aucun)"
        return "\n".join(
            f"  - [{p['trend']}] {p['error_type']} n={p['count']} avg={p['avg_score']:.0%}"
            for p in patterns
        )

    trend_ch_txt = "\n".join(
        f"  - {et}: {bt} -> {at}"
        for et, (bt, at) in delta.get("trend_changes", {}).items()
    ) or "  (aucun)"

    session_rows = "\n".join(
        f"  Q{r['q_num']:02d} | {r['question_type']:<18} | {r['profile']:<14} |"
        f" {(r['score'] or 0.0):.2f} | {(r.get('error_type') or 'correct'):<18} | {_s(r.get('topic',''), 20)}"
        for r in results
        if r.get("score") is not None
    )

    s_err = dict(sorted(delta.get("session_errors", {}).items(), key=lambda x: -x[1]))
    s_typ = dict(sorted(delta.get("session_types",  {}).items(), key=lambda x: -x[1]))

    block = (
        "# TASK-057B - Error Pattern Memory Effect Analysis\n\n"
        "## Config\n"
        f"- User: {config['username']} ({config['user_id'][:8]}...)\n"
        f"- N: {config['n']} questions | Seed: {config['seed']}"
        f" | Mode: {'DRY-RUN' if dry_run else 'API REELLE'}\n"
        f"- Timestamp: {config['timestamp']}\n\n"
        "## Avant session\n"
        f"- Score moyen: {avg_b} (n={before['n_recent']})\n"
        f"- Persistent types: {before['persistent_types']}\n"
        f"- Patterns:\n{_pats_txt(before['patterns'])}\n\n"
        "## Session (distribution)\n"
        f"- Erreurs: {s_err}\n"
        f"- Types: {s_typ}\n"
        f"- Score session: {_pct(delta.get('session_avg'))}\n\n"
        "## Apres session\n"
        f"- Score moyen: {avg_a} (n={after['n_recent']})\n"
        f"- Persistent types: {after['persistent_types']}\n"
        f"- Patterns:\n{_pats_txt(after['patterns'])}\n\n"
        "## Delta\n"
        f"- Score: {avg_b} -> {avg_a} (delta={sd_s})\n"
        f"- Changements tendances:\n{trend_ch_txt}\n\n"
        f"## Session detail ({len(results)} lignes)\n"
        f"{session_rows}\n\n"
        f"## Verdict: {verdict_str}\n"
        + "\n".join(f"- {r}" for r in verdict_reasons)
        + "\n"
    )

    print()
    print("=== COPY_FOR_ANALYSIS_START ===")
    print(block)
    print("=== COPY_FOR_ANALYSIS_END ===")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "TASK-057B - Verification session 30Q avant/apres Error Pattern Memory.\n"
            "Mesure l'effet comportemental de TASK-057 sur une session reelle ou simulee."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--user",       default=DEFAULT_USERNAME,
                        help=f"Username (default: {DEFAULT_USERNAME})")
    parser.add_argument("--n",          type=int, default=DEFAULT_N,
                        help=f"Number of questions (default: {DEFAULT_N})")
    parser.add_argument("--seed",       type=int, default=DEFAULT_SEED,
                        help=f"Random seed (default: {DEFAULT_SEED})")
    parser.add_argument("--no-confirm", action="store_true",
                        help="Skip confirmation prompt before API session")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Simulate without API calls or DB writes")
    args = parser.parse_args()

    dry_run = args.dry_run

    print()
    print("=" * 80)
    print("  TASK-057B - Error Pattern Memory Effect Verification")
    print("=" * 80)
    print(f"  user     : {args.user}")
    print(f"  n        : {args.n}")
    print(f"  seed     : {args.seed}")
    print(f"  mode     : {'DRY-RUN (no API, no DB writes)' if dry_run else 'API REELLE (real API calls + DB writes)'}")
    print()

    # ── Resolve user ───────────────────────────────────────────────────────────
    user_id, found = get_user_id(args.user)
    print(f"  user_id  : {user_id}  ({'found' if found else 'fallback — not found in DB'})")

    # ── Load chunks ────────────────────────────────────────────────────────────
    print()
    print(f"  Loading chunks...", end=" ", flush=True)

    if dry_run:
        # In dry-run: try real DB first, fallback to fake chunks
        try:
            chunks = get_available_chunks()
            if not chunks:
                chunks = _FAKE_CHUNKS
                print(f"DB empty, using {len(chunks)} fake chunks (dry-run)")
            else:
                print(f"{len(chunks)} chunks from DB (dry-run, no API)")
        except Exception:
            chunks = _FAKE_CHUNKS
            print(f"DB unavailable, using {len(chunks)} fake chunks (dry-run)")
    else:
        try:
            chunks = get_available_chunks()
        except Exception as exc:
            print(f"\n  ERROR: Cannot load chunks: {exc}")
            return 1
        if not chunks:
            print("\n  ERROR: No chunks with embeddings found in DB.")
            print("         Please ingest documents and generate embeddings first.")
            return 1
        print(f"{len(chunks)} chunks available")

    # ── Confirm (real mode only) ───────────────────────────────────────────────
    if not dry_run and not args.no_confirm:
        n_api = args.n * 2  # generate + correct per question
        print()
        print(f"  This will make up to {n_api} API calls and write {args.n} attempts to DB.")
        print(f"  Estimated time: ~{args.n * 8 // 60}–{args.n * 15 // 60} minutes.")
        try:
            resp = input("  Proceed? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n  Aborted.")
            return 0
        if resp != "y":
            print("  Aborted.")
            return 0

    # ── Measure BEFORE ─────────────────────────────────────────────────────────
    print()
    print("  Measuring state BEFORE session...", end=" ", flush=True)
    try:
        before = get_state(user_id)
        print(
            f"done  "
            f"avg={_pct(before['avg_score'])}  "
            f"patterns={len(before['patterns'])}  "
            f"n_recent={before['n_recent']}"
        )
    except Exception as exc:
        print(f"ERROR: {exc}")
        before = {
            "patterns": [], "persistent_types": [], "has_critical": False,
            "has_chronic": False, "avg_score": None, "recent_scores": [],
            "error_dist": {}, "qtype_dist": {}, "n_recent": 0,
        }

    config = {
        "username":  args.user,
        "user_id":   user_id,
        "n":         args.n,
        "seed":      args.seed,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }

    # ── Run session ────────────────────────────────────────────────────────────
    t0 = time.time()
    results = run_session(
        user_id                  = user_id,
        chunks                   = chunks,
        n                        = args.n,
        seed                     = args.seed,
        dry_run                  = dry_run,
        persistent_types_before  = before["persistent_types"],
    )
    elapsed_s = time.time() - t0
    print(f"\n  Session terminee en {elapsed_s:.1f}s  ({len(results)} resultats)")

    # ── Measure AFTER ──────────────────────────────────────────────────────────
    if dry_run:
        after = dict(before)
    else:
        print("  Measuring state AFTER session...", end=" ", flush=True)
        try:
            after = get_state(user_id)
            print(
                f"done  "
                f"avg={_pct(after['avg_score'])}  "
                f"patterns={len(after['patterns'])}"
            )
        except Exception as exc:
            print(f"ERROR: {exc}")
            after = dict(before)

    # ── Compute delta & verdict ────────────────────────────────────────────────
    delta = compute_delta(before, after, results)
    verd  = get_verdict(delta, before)

    # ── Full report ────────────────────────────────────────────────────────────
    print_full_report(config, before, results, after, delta, verd, dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
