#!/usr/bin/env python
"""
simulate_adaptive_training.py — TASK-073
Simulation contrôlée pour tester et nourrir le moteur adaptatif.

Deux modes :
  --mode mock  (défaut) — aucun appel API, cohérence pipeline
  --mode api            — vrais appels API, nourrit réellement le moteur

Usage :
  python tools/testing/simulate_adaptive_training.py --user Guilhem --n 20 --mode mock
  python tools/testing/simulate_adaptive_training.py --user Guilhem --n 50 --mode api --seed 42
"""
from __future__ import annotations

import argparse
import logging
import random
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Encodage Windows ──────────────────────────────────────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Racine du projet ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.WARNING)

# ── Imports projet ────────────────────────────────────────────────────────────
import database as _db
from db.analytics import save_attempt, get_attempts_count, get_score_evolution
from db.profile import compute_and_save_learning_profile
from db.runtime_metrics import get_metrics_summary
from db.skills import get_user_skill_mastery, update_user_skill_mastery
from engine.curriculum_engine import get_curriculum_recommendation
from engine.error_pattern_memory import detect_persistent_error_patterns

# ── Constantes ────────────────────────────────────────────────────────────────
SEP  = "─" * 70
SEP2 = "━" * 70

API_PAUSE_S    = 1.2
RECALC_EVERY   = 10

QUESTION_TYPES = [
    "question_directe", "cas_pratique", "vrai_faux",
    "question_piege", "reformulation", "consequence",
]

# (profil, poids, (score_min, score_max), error_type)
RESPONSE_PROFILES: list[tuple] = [
    ("correct",       0.35, (0.85, 1.00), "correct"),
    ("partielle",     0.25, (0.55, 0.75), "reponse_vague"),
    ("vague",         0.15, (0.30, 0.50), "reponse_vague"),
    ("oubli_etape",   0.10, (0.35, 0.55), "oubli_etape"),
    ("hors_sujet",    0.10, (0.05, 0.20), "hors_sujet"),
    ("non_evaluable", 0.05, (None, None),  "non_evaluable"),
]

_PROFILE_NAMES   = [p[0] for p in RESPONSE_PROFILES]
_PROFILE_WEIGHTS = [p[1] for p in RESPONSE_PROFILES]

MOCK_ANSWERS = {
    "correct":       "La procédure décrite implique plusieurs étapes clés que j'ai bien comprises et que j'applique conformément aux directives.",
    "partielle":     "Il faut vérifier les éléments principaux et s'assurer de la conformité, mais certains détails m'échappent.",
    "vague":         "C'est lié aux règles générales et aux bonnes pratiques habituelles.",
    "oubli_etape":   "On commence par l'analyse puis on passe directement à la validation finale.",
    "hors_sujet":    "Cela dépend des circonstances et du contexte général de l'organisation.",
    "non_evaluable": "?",
}

MOCK_CORRECTIONS = {
    "correct":       "Réponse complète et précise, toutes les étapes sont correctement identifiées.",
    "partielle":     "La réponse est partiellement correcte mais manque de précision sur certains points clés.",
    "vague":         "La réponse est trop vague et ne cite pas les éléments spécifiques du texte.",
    "oubli_etape":   "Une étape intermédiaire essentielle a été omise dans la réponse.",
    "hors_sujet":    "La réponse ne répond pas à la question posée et sort du contexte du texte.",
    "non_evaluable": "Réponse non évaluable.",
}


# ── Helpers DB ────────────────────────────────────────────────────────────────

def _get_user_id(username: str) -> Optional[str]:
    try:
        conn = sqlite3.connect(_db.DB_PATH)
        row = conn.execute(
            "SELECT user_id FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception as exc:
        print(f"[ERREUR] _get_user_id: {exc}")
        return None


def _get_exploitable_chunks(min_len: int = 150, limit: int = 200) -> list[dict]:
    try:
        conn = sqlite3.connect(_db.DB_PATH)
        rows = conn.execute(
            """SELECT c.id, c.document_id, c.chunk_text, d.title
               FROM chunks c JOIN documents d ON c.document_id = d.id
               WHERE c.chunk_text IS NOT NULL AND length(c.chunk_text) >= ?
               ORDER BY RANDOM() LIMIT ?""",
            (min_len, limit),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "document_id": r[1], "chunk_text": r[2], "doc_title": r[3]}
            for r in rows
        ]
    except Exception as exc:
        print(f"[ERREUR] _get_exploitable_chunks: {exc}")
        return []


def _avg_score_recent(user_id: str, n: int = 20) -> Optional[float]:
    try:
        df = get_score_evolution(limit=n, user_id=user_id)
        if df is None or df.empty:
            return None
        return float(df["score"].mean())
    except Exception:
        return None


def _fragile_skills(user_id: str) -> list[str]:
    try:
        skills = get_user_skill_mastery(user_id)
        return [
            s["slug"] for s in (skills or [])
            if s.get("mastery_score", 1.0) < 0.50
        ]
    except Exception:
        return []


# ── Snapshot état ─────────────────────────────────────────────────────────────

def _snapshot(user_id: str, run_ts: str) -> dict:
    avg = _avg_score_recent(user_id)
    pat = detect_persistent_error_patterns(user_id)
    cur = get_curriculum_recommendation(user_id)
    rm  = get_metrics_summary(hours=1)
    fragile = _fragile_skills(user_id)
    n_att = get_attempts_count(user_id)
    return {
        "ts":           run_ts,
        "n_attempts":   n_att,
        "avg_score":    avg,
        "patterns":     pat.get("patterns", {}),
        "has_critical": pat.get("has_critical", False),
        "has_chronic":  pat.get("has_chronic", False),
        "persistent":   pat.get("persistent_types", []),
        "fragile_skills": fragile,
        "curriculum_next_qtype": (cur.get("next_step") or {}).get("question_type"),
        "curriculum_priority":   (cur.get("next_step") or {}).get("priority", 0.0),
        "rm_total_calls":        rm.get("total_calls", 0),
        "rm_fallback_rate":      rm.get("fallback_rate", 0.0),
        "rm_avg_latency":        rm.get("avg_latency_ms", 0.0),
        "rm_cost":               rm.get("estimated_cost_total", 0.0),
    }


# ── Mock question ──────────────────────────────────────────────────────────────

def _mock_question(chunk: dict, q_type: str) -> str:
    preview = chunk["chunk_text"][:120].replace("\n", " ").strip()
    templates = {
        "question_directe": f"Que signifie exactement : « {preview[:80]}… » ?",
        "cas_pratique":     f"Dans un contexte opérationnel, comment appliquer : « {preview[:60]}… » ?",
        "vrai_faux":        f"Affirmation : « {preview[:80]}… » — est-ce correct ? Justifiez.",
        "question_piege":   f"Est-il exact que « {preview[:70]}… » s'applique sans condition ?",
        "reformulation":    f"Reformulez avec vos propres mots ce passage : « {preview[:80]}… »",
        "consequence":      f"Quelles sont les conséquences si « {preview[:70]}… » n'est pas respecté ?",
    }
    return templates.get(q_type, f"Expliquez : « {preview[:100]}… »")


def _mock_correction(profile: str, q_type: str, chunk: dict) -> dict:
    p = next(row for row in RESPONSE_PROFILES if row[0] == profile)
    score_min, score_max = p[2]
    error_type = p[3]

    if score_min is None:
        score = None
    else:
        score = round(random.uniform(score_min, score_max), 2)

    return {
        "score":           score,
        "expected_answer": chunk["chunk_text"][:200],
        "correction":      MOCK_CORRECTIONS[profile],
        "error_type":      error_type,
        "topic":           chunk["doc_title"][:40] if chunk.get("doc_title") else "inconnu",
    }


def _pick_profile(rng: random.Random) -> str:
    return rng.choices(_PROFILE_NAMES, weights=_PROFILE_WEIGHTS, k=1)[0]


# ── Session principale ────────────────────────────────────────────────────────

def run_session(
    user_id: str,
    username: str,
    n: int,
    mode: str,
    seed: int,
    chunks: list[dict],
) -> tuple[list[dict], int]:
    """
    Retourne (log_entries, n_saved).
    Chaque entry : dict avec tous les champs de la session.
    """
    rng = random.Random(seed)
    log: list[dict] = []
    n_saved = 0

    if mode == "api":
        from ai_service import generate_question, correct_answer

    for i in range(n):
        entry: dict = {"idx": i + 1}
        chunk = rng.choice(chunks)
        profile = _pick_profile(rng)
        entry["profile"] = profile
        entry["doc_id"]  = chunk["document_id"]
        entry["chunk_id"] = chunk["id"]

        # ── Génération question ───────────────────────────────────────────
        t0 = time.monotonic()
        fallback = False
        q_type = rng.choice(QUESTION_TYPES)

        if mode == "mock":
            question = _mock_question(chunk, q_type)
            entry["latency_ms"] = round((time.monotonic() - t0) * 1000)
        else:
            try:
                question, chunk_ids, q_type, rag_chunks = generate_question(
                    source_text=chunk["chunk_text"][:500],
                    document_id=chunk["document_id"],
                    user_id=user_id,
                )
                if rag_chunks:
                    chunk   = {**chunk, **{
                        "id":          rag_chunks[0].get("id", chunk["id"]),
                        "document_id": rag_chunks[0].get("document_id", chunk["document_id"]),
                        "chunk_text":  rag_chunks[0].get("chunk_text", chunk["chunk_text"]),
                    }}
                    entry["chunk_id"] = chunk["id"]
                    entry["doc_id"]   = chunk["document_id"]
                entry["latency_ms"] = round((time.monotonic() - t0) * 1000)
            except Exception as exc:
                entry["error"] = f"generate: {exc}"
                entry["latency_ms"] = round((time.monotonic() - t0) * 1000)
                fallback = True
                question = _mock_question(chunk, q_type)

        entry["question_type"] = q_type

        # Alignement curriculum
        try:
            rec = get_curriculum_recommendation(user_id)
            cur_qtype = (rec.get("next_step") or {}).get("question_type")
            entry["curriculum_match"] = (cur_qtype == q_type) if cur_qtype else None
        except Exception:
            entry["curriculum_match"] = None

        # ── Correction ────────────────────────────────────────────────────
        answer_text = MOCK_ANSWERS[profile]

        t1 = time.monotonic()
        if mode == "mock" or profile == "non_evaluable":
            result = _mock_correction(profile, q_type, chunk)
            corr_latency = round((time.monotonic() - t1) * 1000)
        else:
            try:
                result = correct_answer(question, answer_text, chunk["chunk_text"][:2000])
                corr_latency = round((time.monotonic() - t1) * 1000)
            except Exception as exc:
                result = _mock_correction(profile, q_type, chunk)
                corr_latency = 0
                entry.setdefault("error", f"correct: {exc}")
                fallback = True

        score      = result.get("score")
        error_type = result.get("error_type", "hors_sujet")
        topic      = result.get("topic", "")
        correction = result.get("correction", "")
        expected   = result.get("expected_answer", "")

        entry["score"]      = score
        entry["error_type"] = error_type
        entry["fallback"]   = fallback
        entry["latency_ms"] = entry.get("latency_ms", 0) + corr_latency

        # ── Sauvegarde attempt ────────────────────────────────────────────
        try:
            save_attempt(
                question              = question,
                user_answer           = answer_text,
                expected_answer       = expected,
                correction            = correction,
                score                 = score,
                response_time_seconds = entry["latency_ms"] / 1000,
                error_type            = error_type if score is not None else None,
                topic                 = topic,
                pedagogy_type         = q_type,
                document_id           = entry["doc_id"],
                chunk_id              = entry["chunk_id"],
                user_id               = user_id,
            )
            n_saved += 1
            entry["saved"] = True
        except Exception as exc:
            entry["saved"] = False
            entry["error"] = str(exc)

        log.append(entry)

        # ── Recalcul périodique ───────────────────────────────────────────
        if (i + 1) % RECALC_EVERY == 0:
            try:
                update_user_skill_mastery(user_id)
                compute_and_save_learning_profile(user_id)
                detect_persistent_error_patterns(user_id)
            except Exception as exc:
                pass  # non-bloquant

        # Pause API
        if mode == "api":
            time.sleep(API_PAUSE_S)

        # Affichage progression
        score_str  = f"{score:.2f}" if score is not None else "N/E"
        match_str  = "✓" if entry["curriculum_match"] else ("~" if entry["curriculum_match"] is None else "✗")
        fb_str     = "FB" if fallback else "  "
        saved_str  = "✓" if entry["saved"] else "✗"
        lat_str    = f"{entry['latency_ms']:>5}ms"
        print(
            f"  Q{i+1:>02} | doc={entry['doc_id']} | {q_type:<20} | "
            f"{profile:<12} | score={score_str} | {error_type:<15} | "
            f"cur={match_str} | {fb_str} | {lat_str} | saved={saved_str}"
        )

    # Recalcul final
    try:
        update_user_skill_mastery(user_id)
        compute_and_save_learning_profile(user_id)
        detect_persistent_error_patterns(user_id)
    except Exception:
        pass

    return log, n_saved


# ── Affichage sections ────────────────────────────────────────────────────────

def _print_snapshot(label: str, s: dict) -> None:
    print(f"\n{SEP}")
    print(f"  {label}")
    print(SEP)
    avg = s["avg_score"]
    print(f"  Tentatives totales    : {s['n_attempts']}")
    print(f"  Score moyen récent    : {avg:.3f}" if avg is not None else "  Score moyen récent    : —")
    print(f"  Skills fragiles       : {', '.join(s['fragile_skills']) or 'aucun'}")
    print(f"  Patterns persistants  : {', '.join(s['persistent']) or 'aucun'}")
    print(f"  Critique              : {'OUI' if s['has_critical'] else 'non'} | Chronique : {'OUI' if s['has_chronic'] else 'non'}")
    print(f"  Curriculum next       : {s['curriculum_next_qtype'] or '—'} (priorité {s['curriculum_priority']:.2f})")
    print(f"  Runtime 1h — appels   : {s['rm_total_calls']} | fallback : {s['rm_fallback_rate']:.1f}% | latence : {s['rm_avg_latency']:.0f}ms | coût : ${s['rm_cost']:.6f}")


def _print_delta(before: dict, after: dict, log: list[dict], n_saved: int) -> dict:
    print(f"\n{SEP}")
    print("  E. DELTA")
    print(SEP)

    avg_b  = before["avg_score"] or 0.0
    avg_a  = after["avg_score"]  or 0.0
    d_score = avg_a - avg_b

    sign = "+" if d_score >= 0 else ""
    print(f"  Score moyen           : {avg_b:.3f} → {avg_a:.3f}  ({sign}{d_score:.3f})")

    # Distribution error_type
    et_counts: Counter = Counter()
    for e in log:
        if e.get("error_type"):
            et_counts[e["error_type"]] += 1
    non_ev = sum(1 for e in log if e.get("score") is None)
    for et, cnt in sorted(et_counts.items(), key=lambda x: -x[1]):
        print(f"  {et:<20}  {cnt:>3} fois")
    print(f"  non_evaluable         : {non_ev}")

    # Fallback
    fb_count  = sum(1 for e in log if e.get("fallback"))
    fb_pct    = round(fb_count / len(log) * 100, 1) if log else 0
    fb_before = before["rm_fallback_rate"]
    fb_after  = after["rm_fallback_rate"]
    print(f"  Fallback              : {fb_count}/{len(log)} ({fb_pct}%) | runtime delta : {fb_before:.1f}% → {fb_after:.1f}%")

    # Coût et latence
    cost_delta = after["rm_cost"] - before["rm_cost"]
    lat_a      = after["rm_avg_latency"]
    latencies  = [e["latency_ms"] for e in log if e.get("latency_ms")]
    avg_lat    = round(sum(latencies) / len(latencies)) if latencies else 0
    print(f"  Coût session estimé   : ${cost_delta:.6f}")
    print(f"  Latence moy. session  : {avg_lat} ms")

    # Curriculum alignment
    matches     = [e for e in log if e.get("curriculum_match") is True]
    mismatches  = [e for e in log if e.get("curriculum_match") is False]
    n_defined   = len(matches) + len(mismatches)
    align_pct   = round(len(matches) / n_defined * 100, 1) if n_defined else 0
    print(f"  Curriculum alignment  : {len(matches)}/{n_defined} ({align_pct}%)")

    # Skills
    b_frag = set(before["fragile_skills"])
    a_frag = set(after["fragile_skills"])
    new_fragile   = a_frag - b_frag
    fixed_fragile = b_frag - a_frag
    if new_fragile:
        print(f"  Skills dégradés       : {', '.join(new_fragile)}")
    if fixed_fragile:
        print(f"  Skills améliorés      : {', '.join(fixed_fragile)}")

    return {
        "d_score":    d_score,
        "fb_pct":     fb_pct,
        "n_saved":    n_saved,
        "n_total":    len(log),
        "align_pct":  align_pct,
        "cost_delta": cost_delta,
        "avg_lat":    avg_lat,
        "et_counts":  dict(et_counts),
        "non_ev":     non_ev,
        "new_fragile": list(new_fragile),
    }


def _verdict(delta: dict, n: int) -> str:
    fails: list[str] = []
    warnings: list[str] = []

    # FAILED
    if delta["n_saved"] == 0:
        fails.append("Aucun attempt sauvegardé")
    if delta["n_saved"] < n * 0.5:
        fails.append(f"Trop peu d'attempts sauvegardés ({delta['n_saved']}/{n})")

    # WARNING
    if delta["d_score"] < -0.15:
        warnings.append(f"Score en forte baisse ({delta['d_score']:+.3f})")
    if delta["fb_pct"] > 20:
        warnings.append(f"Fallback élevé ({delta['fb_pct']}%)")
    dominant_type_count = max(delta["et_counts"].values(), default=0)
    dominant_pct = dominant_type_count / n * 100 if n else 0
    if dominant_pct > 70:
        warnings.append(f"Un seul error_type domine ({dominant_pct:.0f}%)")
    if delta["new_fragile"]:
        warnings.append(f"Nouveaux skills fragiles : {', '.join(delta['new_fragile'])}")

    if fails:
        verdict = "FAILED"
    elif warnings:
        verdict = "WARNING"
    else:
        verdict = "COHERENT"

    print(f"\n{SEP2}")
    print(f"  F. VERDICT : {verdict}")
    if fails:
        for f in fails:
            print(f"     FAILED  · {f}")
    if warnings:
        for w in warnings:
            print(f"     WARNING · {w}")
    if verdict == "COHERENT":
        print("     Pipeline complet sans anomalie détectée.")
    print(SEP2)

    return verdict


def _copy_block(
    username: str, mode: str, n: int, seed: int,
    before: dict, after: dict, delta: dict, verdict: str,
    log: list[dict],
) -> str:
    lines: list[str] = []
    lines.append("=== COPY_FOR_ANALYSIS_START ===")
    lines.append(f"# Rapport simulation ADDISCO OPS — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- User    : {username}")
    lines.append(f"- Mode    : {mode}")
    lines.append(f"- N       : {n} entrées | seed={seed}")
    lines.append(f"- Verdict : **{verdict}**")
    lines.append("")
    lines.append("## État AVANT")
    avg_b = before["avg_score"]
    lines.append(f"- Score moyen  : {avg_b:.3f}" if avg_b else "- Score moyen  : —")
    lines.append(f"- Fragile      : {', '.join(before['fragile_skills']) or 'aucun'}")
    lines.append(f"- Persistants  : {', '.join(before['persistent']) or 'aucun'}")
    lines.append(f"- Curriculum   : {before['curriculum_next_qtype'] or '—'}")
    lines.append("")
    lines.append("## Delta session")
    sign = "+" if delta["d_score"] >= 0 else ""
    lines.append(f"- Score        : {sign}{delta['d_score']:.3f}")
    lines.append(f"- Saved        : {delta['n_saved']}/{delta['n_total']}")
    lines.append(f"- Fallback     : {delta['fb_pct']}%")
    lines.append(f"- Alignment    : {delta['align_pct']}%")
    lines.append(f"- Coût         : ${delta['cost_delta']:.6f}")
    lines.append(f"- Latence moy  : {delta['avg_lat']} ms")
    lines.append(f"- non_evaluable: {delta['non_ev']}")
    lines.append("")
    lines.append("## Distribution error_type")
    for et, cnt in sorted(delta["et_counts"].items(), key=lambda x: -x[1]):
        lines.append(f"- {et}: {cnt}")
    lines.append("")
    lines.append("## État APRÈS")
    avg_a = after["avg_score"]
    lines.append(f"- Score moyen  : {avg_a:.3f}" if avg_a else "- Score moyen  : —")
    lines.append(f"- Fragile      : {', '.join(after['fragile_skills']) or 'aucun'}")
    lines.append(f"- Persistants  : {', '.join(after['persistent']) or 'aucun'}")
    lines.append(f"- Curriculum   : {after['curriculum_next_qtype'] or '—'}")
    lines.append("")
    lines.append("## Tableau session (10 premiers)")
    lines.append("| Q | doc | qtype | profil | score | error_type | cur | latency |")
    lines.append("|---|-----|-------|--------|-------|------------|-----|---------|")
    for e in log[:10]:
        sc = f"{e['score']:.2f}" if e.get("score") is not None else "N/E"
        cm = "✓" if e.get("curriculum_match") else ("~" if e.get("curriculum_match") is None else "✗")
        lines.append(
            f"| Q{e['idx']:02} | {e['doc_id']} | {e.get('question_type','?')[:18]} | "
            f"{e['profile']:<12} | {sc} | {e.get('error_type','?')[:14]} | {cm} | {e.get('latency_ms',0)}ms |"
        )
    lines.append("=== COPY_FOR_ANALYSIS_END ===")
    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Simulation adaptative ADDISCO OPS")
    parser.add_argument("--user",       default="Guilhem",  help="Username cible")
    parser.add_argument("--n",          type=int, default=20, help="Nombre d'entrées")
    parser.add_argument("--mode",       choices=["mock", "api"], default="mock")
    parser.add_argument("--seed",       type=int, default=42,   help="Seed random")
    parser.add_argument("--no-confirm", action="store_true",    help="Passer la confirmation API")
    args = parser.parse_args()

    # ── A. CONFIG ─────────────────────────────────────────────────────────────
    print(f"\n{SEP2}")
    print("  ADDISCO OPS — Simulation Adaptative (TASK-073)")
    print(SEP2)
    print(f"  Utilisateur   : {args.user}")
    print(f"  Mode          : {args.mode.upper()}")
    print(f"  Entrées       : {args.n}")
    print(f"  Seed          : {args.seed}")
    print(f"  API réelle    : {'OUI' if args.mode == 'api' else 'non'}")
    print(f"  DB            : {_db.DB_PATH}")

    if args.mode == "api" and not args.no_confirm:
        print(f"\n  Vrais appels API OpenAI — coût estimé ~{args.n * 2} appels.")
        rep = input("  Confirmer ? [oui/N] : ").strip().lower()
        if rep not in ("oui", "o", "yes", "y"):
            print("  Annulé.")
            sys.exit(0)

    # Résolution user
    _db.init_db()
    user_id = _get_user_id(args.user)
    if not user_id:
        print(f"\n  [ERREUR] Utilisateur '{args.user}' introuvable en base.")
        sys.exit(1)

    chunks = _get_exploitable_chunks()
    if not chunks:
        print("\n  [ERREUR] Aucun chunk exploitable trouvé.")
        sys.exit(1)
    print(f"  Chunks dispo  : {len(chunks)}")

    # ── B. AVANT ──────────────────────────────────────────────────────────────
    run_ts = datetime.now(timezone.utc).isoformat()
    before = _snapshot(user_id, run_ts)
    _print_snapshot("B. ÉTAT AVANT", before)

    # ── C. SESSION ────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  C. SESSION ({args.n} entrées — mode {args.mode.upper()})")
    print(SEP)
    print(
        f"  {'Q':>3} | {'doc':>3} | {'question_type':<20} | "
        f"{'profil':<12} | {'score':>5} | {'error_type':<15} | "
        f"{'cur':>3} | {'fb':>2} | {'latence':>7} | saved"
    )
    print("  " + "·" * 98)

    random.seed(args.seed)
    log, n_saved = run_session(
        user_id=user_id,
        username=args.user,
        n=args.n,
        mode=args.mode,
        seed=args.seed,
        chunks=chunks,
    )

    # ── D. APRÈS ──────────────────────────────────────────────────────────────
    after = _snapshot(user_id, datetime.now(timezone.utc).isoformat())
    _print_snapshot("D. ÉTAT APRÈS", after)

    # ── E. DELTA + F. VERDICT ─────────────────────────────────────────────────
    delta = _print_delta(before, after, log, n_saved)
    verdict = _verdict(delta, args.n)

    # ── G. COPY BLOCK ─────────────────────────────────────────────────────────
    block = _copy_block(
        username=args.user, mode=args.mode, n=args.n, seed=args.seed,
        before=before, after=after, delta=delta, verdict=verdict, log=log,
    )
    print(f"\n{block}\n")


if __name__ == "__main__":
    main()
