"""
curriculum_engine.py — Curriculum Engine V1 (TASK-058)

Phase 1 : OBSERVATION ONLY.
N'influence pas generate_question() directement — usage observer/tests uniquement.

Organise les prochaines etapes pedagogiques selon :
  - patterns d'erreurs persistants  (engine.error_pattern_memory)
  - maitrise par skill + graphe     (db.skills + engine.skill_graph)
  - besoin de revision espacee      (db.chunks.get_revision_suggestion)
  - performance recente
  - variete pedagogique (rotation max 2x consecutif)

Fonctions publiques :
  compute_learning_priority(...)         -> float  [pure]
  build_learning_queue(user_id)          -> list[dict]
  select_next_learning_step(user_id)     -> Optional[dict]
  recommend_revision_focus(user_id)      -> dict
  get_curriculum_recommendation(user_id) -> dict  [observer/tests only]
"""

import sqlite3
from typing import Optional

from engine.thresholds import (
    MASTERY_MASTERED,
    ADAPTIVE_FORCE_EASY,
    ADAPTIVE_ALLOW_HARD,
)
from engine.question_type import QUESTION_TYPES
from engine.skill_graph import (
    SKILL_GRAPH,
    get_blocking,
    get_level,
    get_session_order,
    is_ready,
)
from engine.skill_engine import classify_skill_mastery


# ── Mappings deterministes ────────────────────────────────────────────────────

# Erreur → type recommande (mastery normale)
_ERROR_TO_QTYPE: dict[str, str] = {
    "reponse_vague":    "reformulation",
    "hors_sujet":       "question_directe",
    "oubli_etape":      "cas_pratique",
    "confusion_notion": "vrai_faux",
    "erreur_ordre":     "consequence",
}

# Erreur → type recommande (Fragile — version plus accessible)
_ERROR_TO_QTYPE_FRAGILE: dict[str, str] = {
    "reponse_vague":    "question_directe",
    "hors_sujet":       "question_directe",
    "oubli_etape":      "vrai_faux",
    "confusion_notion": "vrai_faux",
    "erreur_ordre":     "question_directe",
}

# Erreur → skill cible a travailler
_ERROR_TO_SKILL: dict[str, str] = {
    "reponse_vague":    "synthese_reformulation",
    "hors_sujet":       "identification_concepts",
    "oubli_etape":      "comprehension_procedure",
    "confusion_notion": "identification_concepts",
    "erreur_ordre":     "comprehension_procedure",
}

# Skill → types de questions preferes (ordre de preference)
_SKILL_TO_QTYPES: dict[str, list] = {
    "memorisation_faits":       ["question_directe", "vrai_faux"],
    "identification_concepts":  ["question_directe", "vrai_faux"],
    "comprehension_procedure":  ["cas_pratique", "question_directe"],
    "application_regles":       ["cas_pratique", "consequence"],
    "analyse_causale":          ["consequence", "cas_pratique"],
    "resolution_problemes":     ["cas_pratique", "question_piege"],
    "prise_decision":           ["question_piege", "cas_pratique"],
    "evaluation_critique":      ["question_piege", "vrai_faux"],
    "synthese_reformulation":   ["reformulation", "question_directe"],
    "conformite_reglementaire": ["cas_pratique", "vrai_faux"],
}

# Poids de priorite par tendance
_TREND_WEIGHT: dict[str, float] = {
    "critique":        +0.25,
    "chronique":       +0.18,
    "récent":          +0.08,
    "en_amelioration": -0.05,
    "stabilisé":       -0.20,
}

# Poids de priorite par classe de maitrise
_MASTERY_WEIGHT: dict[str, float] = {
    "Fragile":  +0.22,
    "En cours": +0.05,
    "Acquis":   -0.18,
}

# Nombre de dependants directs dans SKILL_GRAPH (pre-calcule, immuable)
_SKILL_DEPENDENTS_COUNT: dict[str, int] = {
    slug: sum(1 for prereqs in SKILL_GRAPH.values() if slug in prereqs)
    for slug in SKILL_GRAPH
}

_EXCLUDED_ERRORS = frozenset({"non_evaluable", "correct", ""})


# ── Fonctions pures ───────────────────────────────────────────────────────────

def compute_learning_priority(
    mastery_class:  Optional[str]   = None,
    error_trend:    Optional[str]   = None,
    recent_avg:     Optional[float] = None,
    needs_revision: bool             = False,
    is_blocking:    bool             = False,
) -> float:
    """
    Score de priorite pedagogique : 0.0 (bas) -> 1.0 (critique).

    Facteurs appliques dans l'ordre decroissant d'importance :
    1. Prerequis bloquant dans skill_graph  (+0.20)
    2. Pattern d'erreur (critique +0.25, chronique +0.18, recent +0.08)
    3. Maitrise Fragile (+0.22) / Acquis (-0.18)
    4. Performance recente faible < 0.40   (+0.12)
    5. Revision espacee due                (+0.15)
    """
    score = 0.50
    score += _MASTERY_WEIGHT.get(mastery_class or "", 0.0)
    score += _TREND_WEIGHT.get(error_trend or "", 0.0)
    if recent_avg is not None:
        if recent_avg < ADAPTIVE_FORCE_EASY:
            score += 0.12
        elif recent_avg >= MASTERY_MASTERED:
            score -= 0.10
    if needs_revision:
        score += 0.15
    if is_blocking:
        score += 0.20
    return max(0.0, min(1.0, round(score, 3)))


def _pick_question_type(
    error_type:    Optional[str],
    skill_slug:    Optional[str],
    mastery_class: Optional[str],
    used_types:    list,
) -> str:
    """
    Selectionne le type de question le plus adapte.

    Priorite : erreur dominante > skill cible > generique.
    Rotation  : si les 2 dernieres utilisations sont identiques,
                ce type est sature et evite.

    used_types est ordonne du plus recent au plus ancien (DESC).
    """
    if error_type and error_type not in _EXCLUDED_ERRORS:
        primary = (
            _ERROR_TO_QTYPE_FRAGILE.get(error_type, "question_directe")
            if mastery_class == "Fragile"
            else _ERROR_TO_QTYPE.get(error_type, "question_directe")
        )
        candidates = [primary] + [t for t in QUESTION_TYPES if t != primary]
    elif skill_slug:
        preferred  = _SKILL_TO_QTYPES.get(skill_slug, ["question_directe"])
        candidates = list(preferred) + [t for t in QUESTION_TYPES if t not in preferred]
    else:
        candidates = list(QUESTION_TYPES)

    # Type sature si les 2 plus recents sont identiques
    saturated: Optional[str] = None
    if len(used_types) >= 2 and used_types[0] == used_types[1]:
        saturated = used_types[0]

    for qt in candidates:
        if qt != saturated:
            return qt
    return candidates[0]


def _classify_difficulty(
    mastery_class: Optional[str],
    recent_avg:    Optional[float] = None,
) -> str:
    """Cible de difficulte : easy | medium | hard."""
    if recent_avg is not None and recent_avg < ADAPTIVE_FORCE_EASY:
        return "easy"
    if mastery_class == "Fragile":
        return "easy"
    if mastery_class in ("En cours", "En consolidation"):
        return "medium"
    if mastery_class in ("Acquis", "Maîtrisé"):
        if recent_avg is None or recent_avg >= ADAPTIVE_ALLOW_HARD:
            return "hard"
        return "medium"
    return "medium"


# ── Collecte de contexte DB (non-bloquant) ────────────────────────────────────

def _gather_context(user_id: str) -> dict:
    """Collecte le contexte utilisateur. Chaque appel DB est isole dans try/except."""
    import database as _db
    from engine.error_pattern_memory import detect_persistent_error_patterns

    ctx: dict = {
        "skill_rows":       [],
        "mastery_map":      {},
        "patterns":         [],
        "persistent_types": [],
        "revision":         None,
        "recent_avg":       None,
        "used_types":       [],  # plus recent en premier (DESC)
    }

    try:
        from db.skills import get_user_skill_mastery
        ctx["skill_rows"]  = get_user_skill_mastery(user_id)
        ctx["mastery_map"] = {r["slug"]: float(r["mastery_score"]) for r in ctx["skill_rows"]}
    except Exception:
        pass

    try:
        ep = detect_persistent_error_patterns(user_id)
        ctx["patterns"]        = ep.get("patterns", [])
        ctx["persistent_types"] = ep.get("persistent_types", [])
    except Exception:
        pass

    try:
        from db.chunks import get_revision_suggestion
        ctx["revision"] = get_revision_suggestion(user_id)
    except Exception:
        pass

    try:
        with sqlite3.connect(_db.DB_PATH) as conn:
            score_rows = conn.execute(
                "SELECT score FROM attempts WHERE user_id=? AND score IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 10",
                (user_id,),
            ).fetchall()
            type_rows = conn.execute(
                "SELECT pedagogy_type FROM attempts WHERE user_id=? "
                "AND pedagogy_type IS NOT NULL "
                "ORDER BY created_at DESC LIMIT 5",
                (user_id,),
            ).fetchall()
        conn.close()
        scores = [float(r[0]) for r in score_rows]
        ctx["recent_avg"]  = round(sum(scores) / len(scores), 3) if scores else None
        ctx["used_types"]  = [r[0] for r in type_rows]
    except Exception:
        pass

    return ctx


# ── Fonctions publiques ───────────────────────────────────────────────────────

def build_learning_queue(user_id: str = "default", max_items: int = 10) -> list:
    """
    Construit une queue pedagogique ordonnee par priorite.

    Trois sources (par ordre de priorite naturelle) :
      1. Patterns d'erreurs persistants  (critique > chronique > recent)
      2. Maitrise par skill via session_order du graphe
      3. Suggestion de revision espacee

    Chaque item : {priority, target_skill, question_type, difficulty, reason, source, context}
    """
    ctx = _gather_context(user_id)

    mastery_map = ctx["mastery_map"]
    skill_rows  = ctx["skill_rows"]
    patterns    = ctx["patterns"]
    revision    = ctx["revision"]
    recent_avg  = ctx["recent_avg"]
    used_types  = ctx["used_types"]
    skill_data  = {r["slug"]: r for r in skill_rows}

    items: list = []

    # ── Source 1 : Patterns d'erreurs ─────────────────────────────────────
    for p in patterns:
        if p["trend"] not in ("critique", "chronique", "récent"):
            continue

        et          = p["error_type"]
        target      = _ERROR_TO_SKILL.get(et, "identification_concepts")
        skill_score = mastery_map.get(target, 0.0)
        skill_n     = skill_data.get(target, {}).get("attempts_count", 0) if skill_data.get(target) else 0
        mcls        = classify_skill_mastery(skill_score, skill_n)
        n_deps      = _SKILL_DEPENDENTS_COUNT.get(target, 0)
        is_block    = n_deps > 0 and skill_score < MASTERY_MASTERED

        qt   = _pick_question_type(et, target, mcls, used_types)
        diff = _classify_difficulty(mcls, recent_avg)
        pri  = compute_learning_priority(
            mastery_class = mcls,
            error_trend   = p["trend"],
            recent_avg    = recent_avg,
            is_blocking   = is_block,
        )

        parts = [f"pattern {p['trend']} '{et}'"]
        if mcls == "Fragile":
            parts.append(f"skill '{target}' fragile ({skill_score:.0%})")
        if is_block:
            parts.append(f"debloque {n_deps} skill(s)")
        parts.append(f"-> {qt} ({diff})")

        items.append({
            "priority":      pri,
            "target_skill":  target,
            "question_type": qt,
            "difficulty":    diff,
            "reason":        " + ".join(parts),
            "source":        "error_pattern",
            "context": {
                "error_type":    et,
                "trend":         p["trend"],
                "count":         p["count"],
                "avg_score":     p["avg_score"],
                "skill_mastery": mcls,
            },
        })

    # ── Source 2 : Maitrise skills (session_order graphe) ─────────────────
    session_order = get_session_order(mastery_map)

    for slug in session_order[:8]:
        score  = mastery_map.get(slug, 0.0)
        n_att  = skill_data.get(slug, {}).get("attempts_count", 0) if skill_data.get(slug) else 0
        mcls   = classify_skill_mastery(score, n_att)

        if mcls == "Acquis":
            continue

        ready           = is_ready(slug, mastery_map)
        blocking_prereqs = get_blocking(slug, mastery_map)
        n_deps          = _SKILL_DEPENDENTS_COUNT.get(slug, 0)
        is_block        = n_deps > 0 and score < MASTERY_MASTERED
        level           = get_level(slug)

        qt   = _pick_question_type(None, slug, mcls, used_types)
        diff = _classify_difficulty(mcls, recent_avg)
        pri  = compute_learning_priority(
            mastery_class  = mcls,
            recent_avg     = recent_avg,
            needs_revision = (n_att >= 3 and score < 0.60),
            is_blocking    = is_block,
        )
        if not ready:
            pri = max(0.0, round(pri - 0.08, 3))

        parts = [f"skill {mcls.lower()} '{slug}' (lvl {level})"]
        if not ready and blocking_prereqs:
            parts.append(f"prereqs manquants: {blocking_prereqs}")
        if is_block:
            parts.append(f"debloque {n_deps} skill(s) avances")
        parts.append(f"-> {qt} ({diff})")

        items.append({
            "priority":      pri,
            "target_skill":  slug,
            "question_type": qt,
            "difficulty":    diff,
            "reason":        " + ".join(parts),
            "source":        "skill_mastery",
            "context": {
                "mastery_score":    round(score, 3),
                "mastery_class":    mcls,
                "attempts_count":   n_att,
                "level":            level,
                "ready":            ready,
                "blocking_prereqs": blocking_prereqs,
                "blocks_others":    is_block,
            },
        })

    # ── Source 3 : Revision espacee ───────────────────────────────────────
    if revision:
        rev_score = float(revision.get("avg_score") or 0.0)
        rev_n     = int(revision.get("attempts_count") or 0)
        rev_mcls  = classify_skill_mastery(rev_score, rev_n)
        qt        = _pick_question_type(None, None, rev_mcls, used_types)
        diff      = _classify_difficulty(rev_mcls, recent_avg)
        pri       = compute_learning_priority(
            mastery_class  = rev_mcls,
            recent_avg     = recent_avg,
            needs_revision = True,
        )
        items.append({
            "priority":      pri,
            "target_skill":  "general",
            "question_type": qt,
            "difficulty":    diff,
            "reason": (
                f"revision espacee due — chunk {revision['chunk_id']}"
                f" '{revision.get('section_label', '')[:30]}'"
                f" score {rev_score:.0%} ({rev_n} tentatives)"
            ),
            "source":        "revision",
            "context": {
                "chunk_id":       revision["chunk_id"],
                "document_id":    revision.get("document_id"),
                "section_label":  revision.get("section_label", ""),
                "document_title": revision.get("document_title", ""),
                "avg_score":      rev_score,
                "attempts_count": rev_n,
            },
        })

    # ── Fallback si vide ──────────────────────────────────────────────────
    if not items:
        diff = _classify_difficulty(None, recent_avg)
        items.append({
            "priority":      0.50,
            "target_skill":  "identification_concepts",
            "question_type": "question_directe",
            "difficulty":    diff,
            "reason":        "fallback — aucun historique disponible -> fondations",
            "source":        "fallback",
            "context":       {"recent_avg": recent_avg},
        })

    # ── Tri par priorite ──────────────────────────────────────────────────
    items.sort(key=lambda x: -x["priority"])

    # ── Rotation : eviter meme type 2x consecutif ─────────────────────────
    if len(used_types) >= 2 and used_types[0] == used_types[1]:
        overused = used_types[0]
        promoted = [it for it in items if it["question_type"] != overused]
        demoted  = [it for it in items if it["question_type"] == overused]
        items    = promoted + demoted
        if demoted and promoted:
            demoted[0]["reason"] += f" [rotation: '{overused}' sature]"

    # ── Deduplication (meme type + meme skill) ────────────────────────────
    seen: set = set()
    out: list = []
    for it in items:
        key = (it["question_type"], it["target_skill"])
        if key not in seen:
            seen.add(key)
            out.append(it)

    return out[:max_items]


def select_next_learning_step(user_id: str = "default") -> Optional[dict]:
    """Meilleure etape pedagogique suivante (premier element de la queue)."""
    queue = build_learning_queue(user_id, max_items=1)
    return queue[0] if queue else None


def recommend_revision_focus(user_id: str = "default") -> dict:
    """
    Synthese des priorites de revision.

    Retourne :
      fragile_skills   : list de slugs fragiles
      active_patterns  : patterns actifs (critique/chronique/recent)
      revision_due     : chunk a reviser ou None
      avg_score        : score moyen recent
      confidence       : high/medium/low (selon volume de donnees)
    """
    ctx = _gather_context(user_id)

    mastery_map = ctx["mastery_map"]
    skill_rows  = ctx["skill_rows"]
    patterns    = ctx["patterns"]

    fragile_skills = [
        r["slug"]
        for r in skill_rows
        if classify_skill_mastery(float(r["mastery_score"]), int(r["attempts_count"])) == "Fragile"
    ]

    active_patterns = [
        p for p in patterns
        if p["trend"] in ("critique", "chronique", "récent")
    ]

    n_total = sum(int(r.get("attempts_count") or 0) for r in skill_rows)
    if n_total >= 20:
        confidence = "high"
    elif n_total >= 5:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "fragile_skills":   fragile_skills,
        "active_patterns":  active_patterns,
        "revision_due":     ctx["revision"],
        "avg_score":        ctx["recent_avg"],
        "confidence":       confidence,
        "n_attempts_total": n_total,
    }


def get_curriculum_recommendation(user_id: str = "default") -> dict:
    """
    Rapport complet de curriculum.

    Phase 1 : OBSERVATION ONLY — non branche dans generate_question().
    Usage : observer CLI et tests uniquement.

    Retourne :
      user_id, next_step, queue (max 10), focus
    """
    queue     = build_learning_queue(user_id)
    next_step = queue[0] if queue else None
    focus     = recommend_revision_focus(user_id)
    return {
        "user_id":   user_id,
        "next_step": next_step,
        "queue":     queue,
        "focus":     focus,
    }
