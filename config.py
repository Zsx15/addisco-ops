"""
config.py — Référence documentaire des constantes ADDISCO OPS.

DOCUMENTATION UNIQUEMENT — CE FICHIER N'EST PAS IMPORTÉ.
Les modules conservent leurs propres définitions.

Consolidation prévue en Phase 13 (SQLAlchemy) : les constantes seront
centralisées ici et importées depuis chaque module.

Pour modifier une constante : chercher sa définition dans le module source.
"""
import os
from pathlib import Path

# ── Chemins ───────────────────────────────────────────────────────────────────
# Source : database.py
DB_PATH = Path(os.getenv("DB_PATH", "database.db"))

# ── Modèles OpenAI ────────────────────────────────────────────────────────────
# Source : ai_service.py
LLM_MODEL        = "gpt-4o-mini"
EMBEDDING_MODEL  = "text-embedding-3-small"
EMBEDDING_DIMS   = 1536

# ── RAG ───────────────────────────────────────────────────────────────────────
# Source : ai_service.py
RAG_TOP_K           = 3
TEXT_MAX_CHARS      = 6_000
EMBEDDING_MAX_CHARS = 24_000

# ── Répétition espacée ────────────────────────────────────────────────────────
# Source : database.py
REVIEW_INTERVALS = {
    "Fragile":          1,
    "En consolidation": 3,
    "Maîtrisé":         7,
}

# ── Types de questions ────────────────────────────────────────────────────────
# Source : ai_service.py
QUESTION_TYPES = [
    "question_directe",
    "cas_pratique",
    "vrai_faux",
    "question_piege",
    "reformulation",
    "consequence",
]
