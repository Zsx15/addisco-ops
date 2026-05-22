"""
verify_curriculum_engine_20q.py -- TASK-058B

Script de verification comportementale : session 20Q avec mesure de l'alignement
entre les recommandations Curriculum Engine V1 et ce que generate_question() produit.

Objectif Phase 1 (observation) : quantifier le GAP entre curriculum recommande
et session reelle. Ce gap justifie TASK-059 (integration runtime).

Metriques cles :
  - Alignement type_question   : % questions generees qui matchent les types curriculum
  - Couverture skills cibles   : % des skills recommandes touches dans la session
  - Score sur skills prioritaires vs non-prioritaires
  - Verdict : ALIGNED / PARTIAL / MISALIGNED

Usage :
  python tools/testing/verify_curriculum_engine_20q.py [options]
  python tools/testing/verify_curriculum_engine_20q.py --dry-run
  python tools/testing/verify_curriculum_engine_20q.py --user Guilhem --n 20 --seed 42 --no-confirm
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

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Constants ─────────────────────────────────────────────────────────────────
FALLBACK_USER_ID = "f8d18fb0-727f-4b39-bed7-1f660875ab09"
DEFAULT_USERNAME = "Guilhem"
DEFAULT_N        = 20
DEFAULT_SEED     = 42
N_RECENT_STATE   = 20

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
    "correct":       {"score": 0.85, "error_type": "correct",       "topic": "dry_run"},
    "medium":        {"score": 0.55, "error_type": "reponse_vague",  "topic": "dry_run"},
    "vague":         {"score": 0.28, "error_type": "reponse_vague",  "topic": "dry_run"},
    "hors_sujet":    {"score": 0.10, "error_type": "hors_sujet",     "topic": "dry_run"},
    "non_evaluable": {"score": 0.00, "error_type": "non_evaluable",  "topic": "dry_run"},
}

_FAKE_CHUNKS = [
    {
        "chunk_id": 1, "document_id": 1,
        "chunk_text": "Le processus de gestion implique plusieurs etapes obligatoires.",
        "section_label": "Section 1 (dry)", "document_title": "Document test",
    },
    {
        "chunk_id": 2, "document_id": 1,
        "chunk_text": "Les delais de traitement sont fixes par la reglementation en vigueur.",
        "section_label": "Section 2 (dry)", "document_title": "Document test",
    },
]

_QTYPES = ["question_directe", "vrai_faux", "reformulation",
           "cas_pratique", "consequence", "question_piege"]

_SEP      = "-" * 80
_SEP_THIN = "." * 80

# Seuils pour le verdict alignement
ALIGNED_THRESHOLD  = 0.50   # >= 50% alignement type -> ALIGNED
PARTIAL_THRESHOLD  = 0.25   # 25-50% -> PARTIAL
                            # < 25%  -> MISALIGNED (attendu Phase 1)


# ── Utilities ─────────────────────────────────────────────────────────────────

def _pct(v: Optional[float]) -> str:
    return f"{v:.1%}" if v is not None else "N/A"


def _s(text: str, maxlen: int = 0) -> str:
    if maxlen > 0:
        text = str(text)[:maxlen]
    return str(text)


# ── DB / User helpers ─────────────────────────────────────────────────────────

def get_user_id(username: str) -> tuple:
    import database as _db
    try:
        with sqlite3.connect(_db.DB_PATH) as conn:
            row = conn.execute(
                "SELECT id FROM users WHERE username = ? LIMIT 1", (username,)
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


# ── Curriculum state capture ──────────────────────────────────────────────────

def get_curriculum_state(user_id: str) -> dict:
    """Capture l'etat curriculum complet (recommandations + focus)."""
    from engine.curriculum_engine import get_curriculum_recommendation
    rec = get_curriculum_recommendation(user_id)

    queue    = rec.get("queue", [])
    focus    = rec.get("focus", {})
    nxt      = rec.get("next_step")

    # Types recommandes (par ordre de priorite)
    recommended_types  = [it["question_type"] for it in queue]
    recommended_skills = [it["target_skill"]  for it in queue]
    top3_types_set     = set(recommended_types[:3])

    return {
        "queue":             queue,
        "next_step":         nxt,
        "recommended_types": recommended_types,
        "recommended_skills":recommended_skills,
        "top3_types_set":    top3_types_set,
        "focus":             focus,
        "confidence":        focus.get("confidence", "low"),
        "fragile_skills":    focus.get("fragile_skills", []),
        "active_patterns":   focus.get("active_patterns", []),
    }


def get_recent_scores_state(user_id: str) -> dict:
    """Score moyen recent + distribution types."""
    import database as _db
    try:
        with sqlite3.connect(_db.DB_PATH) as conn:
            score_rows = conn.execute(
                "SELECT score FROM attempts WHERE user_id=? AND score IS NOT NULL "
                "ORDER BY created_at DESC LIMIT ?",
                (user_id, N_RECENT_STATE),
            ).fetchall()
            type_rows = conn.execute(
                "SELECT pedagogy_type, COUNT(*) as cnt FROM attempts "
                "WHERE user_id=? AND pedagogy_type IS NOT NULL "
                "GROUP BY pedagogy_type ORDER BY cnt DESC LIMIT 10",
                (user_id,),
            ).fetchall()
    except Exception:
        return {"avg_score": None, "n_recent": 0, "type_dist": {}}

    scores = [float(r[0]) for r in score_rows]
    avg    = round(sum(scores) / len(scores), 3) if scores else None
    return {
        "avg_score": avg,
        "n_recent":  len(scores),
        "type_dist": {r[0]: r[1] for r in type_rows},
    }


# ── Response helpers ──────────────────────────────────────────────────────────

def _make_correct_response(chunk_text: str) -> str:
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
    user_id:     str,
    chunks:      list,
    n:           int,
    seed:        int,
    dry_run:     bool,
    curr_before: dict,
) -> list:
    from ai_service import generate_question, correct_answer, _check_answer_evaluable
    from db.analytics import save_attempt

    rng     = random.Random(seed)
    results = []

    rec_types_str = ",".join(curr_before["recommended_types"][:3]) or "none"

    print()
    print(_SEP)
    print("  SESSION EN COURS")
    print(f"  Types curriculum recommandes (top 3) : {rec_types_str}")
    print(_SEP)
    print(f"  {'Q':>3}  {'type_genere':<22}  {'match_curr':>10}  {'profil':<14}  {'score':>5}  erreur")
    print(_SEP_THIN)

    for i in range(n):
        q_num   = i + 1
        chunk   = rng.choice(chunks)
        src_txt = chunk["chunk_text"]
        doc_id  = chunk["document_id"]
        ck_id   = chunk["chunk_id"]

        t_start = time.time()

        # ── Generate question ──────────────────────────────────────────────
        if dry_run:
            question      = f"[DRY] Question #{q_num} - {chunk['section_label'][:30]}"
            chunk_ids_ret = [ck_id]
            question_type = rng.choice(_QTYPES)
        else:
            try:
                question, chunk_ids_ret, question_type, _ = generate_question(
                    source_text=src_txt,
                    document_id=doc_id,
                    user_id=user_id,
                )
            except Exception as exc:
                print(f"  Q{q_num:02d}  ERREUR generate: {str(exc)[:50]}")
                results.append({
                    "q_num": q_num, "question_type": "?", "profile": "error",
                    "score": None, "error_type": "generation_error",
                    "topic": "", "match_curriculum": False, "chunk_id": ck_id,
                })
                continue

        # Type match curriculum (top 3 recommandes)
        match_curr = question_type in curr_before["top3_types_set"]

        # ── Build simulated answer ─────────────────────────────────────────
        profile     = pick_profile(rng)
        user_answer = (
            _make_correct_response(src_txt)
            if profile == "correct"
            else _STATIC_RESPONSES[profile]
        )

        # ── Correct answer ─────────────────────────────────────────────────
        if dry_run:
            cr = dict(_DRY_CORRECTIONS[profile])
        elif profile == "non_evaluable":
            rejection = _check_answer_evaluable(user_answer)
            cr = rejection if rejection else {
                "score": 0.0, "error_type": "non_evaluable", "topic": "",
                "expected_answer": "", "correction": "",
            }
        else:
            try:
                rejection = _check_answer_evaluable(user_answer)
                cr = rejection if rejection else correct_answer(question, user_answer, src_txt)
            except Exception as exc:
                cr = {"score": 0.0, "error_type": "hors_sujet",
                      "topic": "", "expected_answer": "", "correction": str(exc)}

        elapsed    = time.time() - t_start
        score      = float(cr.get("score") or 0.0)
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
                    document_id           = doc_id,
                    chunk_id              = chunk_ids_ret[0] if chunk_ids_ret else ck_id,
                    user_id               = user_id,
                )
            except Exception as exc:
                print(f"  [WARN] save_attempt Q{q_num}: {exc}")

        match_s = "[MATCH]" if match_curr else "      "
        et_disp = (error_type or "correct")[:18]
        print(
            f"  Q{q_num:02d}  {question_type:<22}  {match_s:>10}  {profile:<14}"
            f"  {score:5.2f}  {et_disp}"
        )

        results.append({
            "q_num":            q_num,
            "question_type":    question_type,
            "profile":          profile,
            "score":            score,
            "error_type":       error_type,
            "topic":            _s(topic, 30),
            "match_curriculum": match_curr,
            "chunk_id":         chunk_ids_ret[0] if chunk_ids_ret else ck_id,
            "document_id":      doc_id,
        })

    print(_SEP_THIN)
    return results


# ── Analyse alignement ────────────────────────────────────────────────────────

def compute_alignment(curr_before: dict, results: list) -> dict:
    """Calcule les metriques d'alignement curriculum vs session reelle."""
    valid      = [r for r in results if r.get("score") is not None and r.get("question_type") != "?"]
    n_valid    = len(valid)
    n_match    = sum(1 for r in valid if r.get("match_curriculum"))
    align_rate = round(n_match / n_valid, 3) if n_valid else None

    # Types generes vs recommandes
    generated_types: dict = {}
    for r in valid:
        qt = r["question_type"]
        generated_types[qt] = generated_types.get(qt, 0) + 1

    rec_types  = curr_before["recommended_types"]
    rec_skills = curr_before["recommended_skills"]
    top3_types = curr_before["top3_types_set"]

    # Score moyen : questions alignees vs non-alignees
    scores_match    = [r["score"] for r in valid if r.get("match_curriculum")]
    scores_no_match = [r["score"] for r in valid if not r.get("match_curriculum")]
    avg_match    = round(sum(scores_match)    / len(scores_match),    3) if scores_match    else None
    avg_no_match = round(sum(scores_no_match) / len(scores_no_match), 3) if scores_no_match else None

    # Score sur types recommandes top 1 (next_step)
    next_type  = curr_before["next_step"]["question_type"] if curr_before["next_step"] else None
    next_skill = curr_before["next_step"]["target_skill"]  if curr_before["next_step"] else None
    scores_next_type = [r["score"] for r in valid if r.get("question_type") == next_type]
    avg_next_type    = round(sum(scores_next_type) / len(scores_next_type), 3) if scores_next_type else None

    # Couverture : quels types recommandes ont ete generes ?
    gen_types_set    = set(generated_types.keys())
    covered_rec      = top3_types & gen_types_set
    coverage_rate    = round(len(covered_rec) / len(top3_types), 3) if top3_types else None

    # Types manquants dans la session
    missing_rec_types = sorted(top3_types - gen_types_set)
    extra_types       = sorted(gen_types_set - set(rec_types[:6]))

    return {
        "n_valid":           n_valid,
        "n_match":           n_match,
        "align_rate":        align_rate,       # % questions matchant top3 curriculum
        "coverage_rate":     coverage_rate,    # % types top3 curricum generes
        "generated_types":   generated_types,
        "recommended_types": rec_types[:6],
        "top3_types_set":    sorted(top3_types),
        "covered_rec":       sorted(covered_rec),
        "missing_rec_types": missing_rec_types,
        "extra_types":       extra_types,
        "avg_match":         avg_match,
        "avg_no_match":      avg_no_match,
        "avg_next_type":     avg_next_type,
        "next_type":         next_type,
        "next_skill":        next_skill,
        "session_avg":       round(sum(r["score"] for r in valid) / n_valid, 3) if valid else None,
    }


def get_verdict(alignment: dict, curr_before: dict) -> tuple:
    """
    ALIGNED   : >= 50% types generes dans top3 curriculum
    PARTIAL   : 25-50%
    MISALIGNED: < 25% (attendu Phase 1 -- observation seulement)
    """
    rate    = alignment.get("align_rate")
    reasons = []

    next_type  = alignment.get("next_type")
    next_skill = alignment.get("next_skill")
    if next_type:
        reasons.append(
            f"Curriculum recommande '{next_type}' sur skill '{next_skill}' "
            f"(priorite {curr_before['next_step']['priority']:.3f})"
        )

    conf = curr_before.get("confidence", "low")
    reasons.append(f"Confiance curriculum : {conf.upper()}")

    if rate is None:
        return "INCONCLUSIVE", reasons + ["Aucune donnee de session valide"]

    n_match  = alignment["n_match"]
    n_valid  = alignment["n_valid"]
    covered  = alignment["covered_rec"]
    missing  = alignment["missing_rec_types"]

    reasons.append(f"Alignement type : {n_match}/{n_valid} questions ({_pct(rate)})")
    if covered:
        reasons.append(f"Types recommandes couverts : {covered}")
    if missing:
        reasons.append(f"Types recommandes absents de la session : {missing}")

    am    = alignment.get("avg_match")
    anm   = alignment.get("avg_no_match")
    if am is not None and anm is not None:
        delta_score = round(am - anm, 3)
        sign = "+" if delta_score >= 0 else ""
        reasons.append(
            f"Score moyen types alignes vs non-alignes : "
            f"{_pct(am)} vs {_pct(anm)} (delta={sign}{delta_score:.3f})"
        )

    if rate >= ALIGNED_THRESHOLD:
        return "ALIGNED", reasons
    if rate >= PARTIAL_THRESHOLD:
        return "PARTIAL", reasons

    reasons.append(
        "GAP CONFIRME : generate_question() ne suit pas le curriculum "
        "(attendu Phase 1). Justifie TASK-059."
    )
    return "MISALIGNED", reasons


# ── Report helpers ────────────────────────────────────────────────────────────

def _fmt_queue(queue: list, max_items: int = 5) -> str:
    if not queue:
        return "  (queue vide)"
    lines = []
    for i, it in enumerate(queue[:max_items], 1):
        src_map = {"error_pattern": "[ERR]", "skill_mastery": "[SKL]",
                   "revision": "[REV]", "fallback": "[---]"}
        src = src_map.get(it["source"], "[?]")
        lines.append(
            f"  {i:2d}. {src} [{it['priority']:.3f}]  {it['question_type']:<22}"
            f"  skill: {it['target_skill']}"
        )
        lines.append(f"       {it['reason'][:70]}")
    if len(queue) > max_items:
        lines.append(f"  ... +{len(queue) - max_items} item(s)")
    return "\n".join(lines)


# ── Full report ───────────────────────────────────────────────────────────────

def print_full_report(
    config:       dict,
    curr_before:  dict,
    scores_before:dict,
    results:      list,
    curr_after:   dict,
    scores_after: dict,
    alignment:    dict,
    verd:         tuple,
    dry_run:      bool,
) -> None:
    verdict_str, verdict_reasons = verd

    print()
    print("=" * 80)
    print("  RAPPORT COMPLET - Curriculum Engine V1 Alignment Verification (TASK-058B)")
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

    # ── B. CURRICULUM AVANT ────────────────────────────────────────────────────
    print()
    print("B. CURRICULUM AVANT SESSION")
    print(_SEP_THIN)
    nxt = curr_before.get("next_step")
    if nxt:
        print(f"  Prochaine etape recommandee :")
        print(f"    source    : {nxt['source']}")
        print(f"    skill     : {nxt['target_skill']}")
        print(f"    type      : {nxt['question_type']}")
        print(f"    priorite  : {nxt['priority']:.3f}")
        print(f"    raison    : {nxt['reason'][:70]}")
    print()
    print(f"  Top 3 types recommandes : {sorted(curr_before['top3_types_set'])}")
    print(f"  Confiance curriculum    : {curr_before['confidence'].upper()}")
    print(f"  Score recent            : {_pct(scores_before['avg_score'])} (n={scores_before['n_recent']})")
    print()
    print(f"  Queue pedagogique ({len(curr_before['queue'])} items) :")
    print(_fmt_queue(curr_before["queue"]))

    if curr_before["active_patterns"]:
        print()
        print(f"  Patterns actifs ({len(curr_before['active_patterns'])}) :")
        for p in curr_before["active_patterns"]:
            print(f"    [{p['trend'].upper():<14}] {p['error_type']}")

    if curr_before["fragile_skills"]:
        print()
        print(f"  Skills fragiles : {curr_before['fragile_skills']}")

    # ── C. SESSION ─────────────────────────────────────────────────────────────
    print()
    print("C. SESSION - Tableau")
    print(_SEP_THIN)
    top3s = sorted(curr_before["top3_types_set"])
    print(f"  Types curriculum top3 : {top3s}")
    print(f"  {'Q':>3}  {'type_genere':<22}  {'match':>6}  {'profil':<14}  {'score':>5}  erreur")
    print("  " + "-" * 74)
    for r in results:
        score_s = f"{r['score']:5.2f}" if r.get("score") is not None else "  N/A"
        match_s = "[OK]  " if r.get("match_curriculum") else "      "
        et_str  = (r.get("error_type") or "correct")[:18]
        print(
            f"  Q{r['q_num']:02d}  {r['question_type']:<22}  {match_s:>6}  "
            f"{r['profile']:<14}  {score_s}  {et_str}"
        )

    # ── D. ALIGNEMENT ──────────────────────────────────────────────────────────
    print()
    print("D. ALIGNEMENT CURRICULUM vs SESSION")
    print(_SEP_THIN)

    ar = alignment.get("align_rate")
    cr = alignment.get("coverage_rate")
    print(f"  Alignement type (match top3) : {alignment['n_match']}/{alignment['n_valid']}"
          f"  ({_pct(ar)})")
    print(f"  Couverture types curriculum  : {_pct(cr)}"
          f"  ({alignment['covered_rec']} / top3={alignment['top3_types_set']})")

    print()
    gen_sorted = dict(sorted(alignment["generated_types"].items(), key=lambda x: -x[1]))
    print(f"  Types generes         : {gen_sorted}")
    print(f"  Types recommandes     : {alignment['recommended_types']}")
    print(f"  Manquants recommandes : {alignment['missing_rec_types'] or '(aucun)'}")
    print(f"  Hors-curriculum       : {alignment['extra_types'] or '(aucun)'}")

    print()
    am  = alignment.get("avg_match")
    anm = alignment.get("avg_no_match")
    ssa = alignment.get("session_avg")
    ant = alignment.get("avg_next_type")
    print(f"  Score session global              : {_pct(ssa)}")
    if am is not None:
        print(f"  Score types alignes curriculum    : {_pct(am)}")
    if anm is not None:
        print(f"  Score types hors curriculum       : {_pct(anm)}")
    if ant is not None:
        print(f"  Score type top1 '{alignment['next_type']}' : {_pct(ant)}")

    # ── E. CURRICULUM APRES ────────────────────────────────────────────────────
    print()
    print("E. CURRICULUM APRES SESSION (evolution des recommandations)")
    print(_SEP_THIN)

    nxt_a = curr_after.get("next_step")
    nxt_b = curr_before.get("next_step")
    if nxt_a and nxt_b:
        same_skill = nxt_a["target_skill"] == nxt_b["target_skill"]
        same_type  = nxt_a["question_type"] == nxt_b["question_type"]
        changed    = not (same_skill and same_type)
        print(f"  Prochaine etape : ", end="")
        if changed:
            print(f"CHANGEE  ({nxt_b['target_skill']}/{nxt_b['question_type']}"
                  f" -> {nxt_a['target_skill']}/{nxt_a['question_type']})")
        else:
            print(f"STABLE   ({nxt_a['target_skill']}/{nxt_a['question_type']})")

    print(f"  Score recent apres : {_pct(scores_after['avg_score'])} (n={scores_after['n_recent']})")

    delta_score = None
    if scores_before["avg_score"] is not None and scores_after["avg_score"] is not None:
        delta_score = round(scores_after["avg_score"] - scores_before["avg_score"], 3)
        sign = "+" if delta_score >= 0 else ""
        print(f"  Delta score global : {sign}{delta_score:.3f}")

    # ── F. VERDICT ─────────────────────────────────────────────────────────────
    print()
    print("F. VERDICT")
    print(_SEP_THIN)
    print(f"  >> {verdict_str}")
    for reason in verdict_reasons:
        print(f"     - {reason}")

    if verdict_str == "MISALIGNED":
        print()
        print("  INTERPRETATION Phase 1 :")
        print("  Le gap mesure confirme que generate_question() fonctionne")
        print("  independamment du curriculum. TASK-059 (integration runtime)")
        print("  est necesssaire pour que les recommandations soient effectives.")

    # ── G. COPY BLOCK ──────────────────────────────────────────────────────────
    _print_copy_block(
        config, curr_before, scores_before, results,
        curr_after, scores_after, alignment,
        verdict_str, verdict_reasons, dry_run, delta_score,
    )

    print()
    print("=" * 80)


def _print_copy_block(
    config, curr_before, scores_before, results,
    curr_after, scores_after, alignment,
    verdict_str, verdict_reasons, dry_run, delta_score,
):
    nxt = curr_before.get("next_step")
    nxt_s = (
        f"{nxt['question_type']} sur '{nxt['target_skill']}' (prio={nxt['priority']:.3f})"
        if nxt else "(aucune)"
    )

    session_rows = "\n".join(
        f"  Q{r['q_num']:02d} | {r['question_type']:<18} | {'MATCH' if r.get('match_curriculum') else '    '}"
        f" | {r['profile']:<14} | {(r['score'] or 0.0):.2f} | {r.get('error_type', '') or 'correct'}"
        for r in results if r.get("score") is not None
    )

    gen_sorted = dict(sorted(alignment.get("generated_types", {}).items(), key=lambda x: -x[1]))

    ds = f"{'+' if delta_score and delta_score >= 0 else ''}{delta_score:.3f}" if delta_score is not None else "N/A"

    block = (
        "# TASK-058B - Curriculum Engine V1 Alignment Analysis\n\n"
        "## Config\n"
        f"- User: {config['username']} ({config['user_id'][:8]}...)\n"
        f"- N: {config['n']} questions | Seed: {config['seed']}"
        f" | Mode: {'DRY-RUN' if dry_run else 'API REELLE'}\n"
        f"- Timestamp: {config['timestamp']}\n\n"
        "## Curriculum AVANT\n"
        f"- Prochaine etape: {nxt_s}\n"
        f"- Top3 types recommandes: {sorted(curr_before['top3_types_set'])}\n"
        f"- Confiance: {curr_before['confidence'].upper()}\n"
        f"- Score recent avant: {_pct(scores_before['avg_score'])} (n={scores_before['n_recent']})\n"
        f"- Fragile skills: {curr_before['fragile_skills'] or '(aucun)'}\n"
        f"- Patterns actifs: {[p['error_type'] for p in curr_before['active_patterns']] or ['(aucun)']}\n\n"
        "## Alignement\n"
        f"- Taux alignement: {_pct(alignment.get('align_rate'))} ({alignment['n_match']}/{alignment['n_valid']})\n"
        f"- Couverture types curriculum: {_pct(alignment.get('coverage_rate'))}\n"
        f"- Types generes: {gen_sorted}\n"
        f"- Types manquants (recommandes): {alignment.get('missing_rec_types', [])}\n"
        f"- Score types alignes: {_pct(alignment.get('avg_match'))}\n"
        f"- Score types hors-curriculum: {_pct(alignment.get('avg_no_match'))}\n\n"
        "## Session APRES\n"
        f"- Score recent apres: {_pct(scores_after['avg_score'])} (n={scores_after['n_recent']})\n"
        f"- Delta score global: {ds}\n\n"
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
            "TASK-058B - Verification alignement Curriculum Engine V1.\n"
            "Mesure le gap entre recommandations curriculum et session reelle.\n"
            "Phase 1 = observation : MISALIGNED attendu, justifie TASK-059."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--user",       default=DEFAULT_USERNAME)
    parser.add_argument("--n",          type=int, default=DEFAULT_N)
    parser.add_argument("--seed",       type=int, default=DEFAULT_SEED)
    parser.add_argument("--no-confirm", action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()

    dry_run = args.dry_run

    print()
    print("=" * 80)
    print("  TASK-058B - Curriculum Engine V1 Alignment Verification")
    print("=" * 80)
    print(f"  user  : {args.user}")
    print(f"  n     : {args.n}")
    print(f"  seed  : {args.seed}")
    print(f"  mode  : {'DRY-RUN' if dry_run else 'API REELLE + DB'}")
    print()

    # ── Resolve user ───────────────────────────────────────────────────────────
    user_id, found = get_user_id(args.user)
    print(f"  user_id : {user_id}  ({'found' if found else 'fallback'})")

    # ── Load chunks ────────────────────────────────────────────────────────────
    print(f"\n  Loading chunks...", end=" ", flush=True)
    if dry_run:
        chunks = _FAKE_CHUNKS
        print(f"{len(chunks)} fake chunks (dry-run)")
    else:
        try:
            chunks = get_available_chunks()
            print(f"{len(chunks)} chunks avec embeddings")
            if not chunks:
                print("  ATTENTION : aucun chunk disponible — fallback dry-run")
                chunks = _FAKE_CHUNKS
                dry_run = True
        except Exception as exc:
            print(f"ERREUR : {exc} — fallback dry-run")
            chunks  = _FAKE_CHUNKS
            dry_run = True

    # ── State AVANT ────────────────────────────────────────────────────────────
    print(f"\n  Computing curriculum state AVANT...", end=" ", flush=True)
    try:
        curr_before   = get_curriculum_state(user_id)
        scores_before = get_recent_scores_state(user_id)
        print("OK")
    except Exception as exc:
        print(f"ERREUR : {exc}")
        curr_before   = {
            "queue": [], "next_step": None, "recommended_types": [],
            "recommended_skills": [], "top3_types_set": set(),
            "focus": {}, "confidence": "low", "fragile_skills": [], "active_patterns": [],
        }
        scores_before = {"avg_score": None, "n_recent": 0, "type_dist": {}}

    n_queue = len(curr_before["queue"])
    nxt = curr_before.get("next_step")
    if nxt:
        print(f"  Prochaine etape : '{nxt['question_type']}' sur '{nxt['target_skill']}'  prio={nxt['priority']:.3f}")
    print(f"  Queue : {n_queue} items  |  Top3 types : {sorted(curr_before['top3_types_set'])}")
    print(f"  Score avant : {_pct(scores_before['avg_score'])}")

    # ── Confirmation ───────────────────────────────────────────────────────────
    if not dry_run and not args.no_confirm:
        print()
        print(f"  Lancer {args.n} questions avec API reelle ? [o/N] ", end="", flush=True)
        rep = input().strip().lower()
        if rep not in ("o", "oui", "y", "yes"):
            print("  Annule.")
            return

    config = {
        "username":  args.user,
        "user_id":   user_id,
        "n":         args.n,
        "seed":      args.seed,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

    # ── Session ────────────────────────────────────────────────────────────────
    results = run_session(
        user_id     = user_id,
        chunks      = chunks,
        n           = args.n,
        seed        = args.seed,
        dry_run     = dry_run,
        curr_before = curr_before,
    )

    # ── State APRES ────────────────────────────────────────────────────────────
    print(f"\n  Computing curriculum state APRES...", end=" ", flush=True)
    try:
        curr_after   = get_curriculum_state(user_id)
        scores_after = get_recent_scores_state(user_id)
        print("OK")
    except Exception as exc:
        print(f"ERREUR : {exc}")
        curr_after   = curr_before
        scores_after = scores_before

    # ── Analyse ────────────────────────────────────────────────────────────────
    alignment = compute_alignment(curr_before, results)
    verd      = get_verdict(alignment, curr_before)

    print_full_report(
        config        = config,
        curr_before   = curr_before,
        scores_before = scores_before,
        results       = results,
        curr_after    = curr_after,
        scores_after  = scores_after,
        alignment     = alignment,
        verd          = verd,
        dry_run       = dry_run,
    )


if __name__ == "__main__":
    main()
