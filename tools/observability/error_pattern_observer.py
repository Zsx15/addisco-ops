"""
error_pattern_observer.py — Observabilité Error Pattern Memory V1 (TASK-057)

Script standalone : affiche les patterns d'erreur persistants par utilisateur.
Usage : python tools/observability/error_pattern_observer.py [user_id]
"""

import sys
import os

# Résolution du chemin projet (exécution depuis n'importe quel répertoire)
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from engine.error_pattern_memory import detect_persistent_error_patterns

_SEVERITY_ICON = {
    "critique":       "🔴",
    "chronique":      "🟠",
    "récent":         "🟡",
    "en_amelioration":"🟢",
    "stabilisé":      "⚪",
}

_RECOMMENDATION = {
    "critique": (
        "Pattern grave installé depuis longtemps avec score très bas. "
        "Cibler immédiatement ce type d'erreur."
    ),
    "chronique": (
        "Erreur récurrente ancienne toujours active. "
        "Révision régulière recommandée."
    ),
    "récent": (
        "Pattern apparu récemment. "
        "Surveiller l'évolution sur les prochaines sessions."
    ),
    "en_amelioration": (
        "Score en progression — continuer dans cette direction."
    ),
    "stabilisé": (
        "Pattern inactif depuis plusieurs semaines — considéré comme résolu."
    ),
}


def display_patterns(user_id: str = "default") -> None:
    result = detect_persistent_error_patterns(user_id)
    patterns = result["patterns"]

    print(f"\n{'═' * 60}")
    print(f"  Error Pattern Memory — Utilisateur : {user_id}")
    print(f"{'═' * 60}")

    if not patterns:
        print("  Aucun pattern d'erreur détecté (données insuffisantes).")
        print(f"{'═' * 60}\n")
        return

    active = [p for p in patterns if p["trend"] != "stabilisé"]
    inactive = [p for p in patterns if p["trend"] == "stabilisé"]

    if active:
        print(f"\n  Patterns actifs ({len(active)}) :\n")
        for p in active:
            icon = _SEVERITY_ICON.get(p["trend"], "•")
            reco = _RECOMMENDATION.get(p["trend"], "")
            print(f"  {icon}  {p['error_type']}")
            print(f"      Tendance    : {p['trend']}")
            print(f"      Occurrences : {p['count']}  |  Score moyen : {p['avg_score']:.0%}")
            print(f"      Dernière    : il y a {p['last_seen_days']:.0f} j  "
                  f"|  Première : il y a {p['first_seen_days']:.0f} j")
            print(f"      → {reco}")
            print()

    if inactive:
        print(f"  Patterns stabilisés ({len(inactive)}) :")
        for p in inactive:
            print(f"  ⚪  {p['error_type']}  "
                  f"(score: {p['avg_score']:.0%}, dernier: il y a {p['last_seen_days']:.0f} j)")
        print()

    summary_parts = []
    if result["has_critical"]:
        summary_parts.append("⚠️  ERREURS CRITIQUES DÉTECTÉES")
    if result["has_chronic"]:
        summary_parts.append("⚠️  ERREURS CHRONIQUES DÉTECTÉES")
    if summary_parts:
        print("  " + "  |  ".join(summary_parts))
    else:
        print("  ✓  Aucun pattern critique ou chronique actif.")

    print(f"\n  Types persistants injectés dans l'engine : {result['persistent_types'] or '—'}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    uid = sys.argv[1] if len(sys.argv) > 1 else "default"
    display_patterns(uid)
