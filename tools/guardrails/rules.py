# Guardrails V1 — Seuils et constantes d'audit

# Seuils taille fichiers (lignes)
FILE_WARN_LINES = 800
FILE_CRITICAL_LINES = 1200

# Seuils taille fonctions (lignes)
FUNC_WARN_LINES = 80
FUNC_CRITICAL_LINES = 120

# Répertoires exclus du scan récursif
EXCLUDED_DIRS = frozenset({"backups", "__pycache__", ".pytest_cache", ".git"})

# Fichiers exclus de la vérification secrets (valeurs d'env légitimes)
SECRETS_EXCLUDED_FILES = frozenset({".env", ".env.example", ".gitignore", "docker-compose.yml"})

# Patterns secrets potentiellement hardcodés (regex)
# Filtrage en amont : lignes avec os.getenv / os.environ sont exemptées
SECRET_PATTERNS = [
    r'OPENAI_API_KEY\s*=\s*["\'][^"\']{5,}["\']',
    r'(?i)(?:password|passwd)\s*=\s*["\'][^"\']{3,}["\']',
    r'(?i)(?<!["\'])\btoken\s*=\s*["\'][^"\']{5,}["\']',
    r'(?i)(?<!["\'])\bsecret\s*=\s*["\'][^"\']{5,}["\']',
]

# Fichiers runtime critiques — ne doivent pas importer depuis tools/
RUNTIME_CRITICAL = frozenset({
    "app.py",
    "database.py",
    "ai_service.py",
    "document_service.py",
    "rag_service.py",
    "adaptive_engine.py",
    "auth_service.py",
})
