# tools/qa — Tests de robustesse pédagogique

Scripts de validation QA du moteur pédagogique. Exécuter depuis la racine du projet.

## Scripts disponibles

### test_robustesse_100q.py

Simule 100 cycles question/correction/sauvegarde pour valider la stabilité du moteur.

```bash
# Mode rapide (0 appel API, < 5 s)
python tools/qa/test_robustesse_100q.py --mock --no-confirm

# Mode mock avec profil faible
python tools/qa/test_robustesse_100q.py --mock --profile weak --no-confirm

# Mode corpus — couvre tous les chunks
python tools/qa/test_robustesse_100q.py --mock --scope corpus --n 300 --no-confirm

# Nettoyage des données de test
python tools/qa/test_robustesse_100q.py --cleanup

# Mode API réel (~200 appels OpenAI, 5–15 min, coût réel)
python tools/qa/test_robustesse_100q.py
```

**Verdict final :** `GO SAFE` | `GO WITH WARNING` | `FAILED`

**Isolation :** toutes les données sont écrites sous l'utilisateur `test_100_questions` — les vrais utilisateurs et documents ne sont pas modifiés.
