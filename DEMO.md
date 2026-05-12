# Guide de démonstration — IA Révision Métier

Scénario de présentation jury. Durée estimée : 8 à 12 minutes.

---

## Avant la démo

- [ ] `streamlit run app.py` lancé dans le terminal
- [ ] Navigateur ouvert sur `http://localhost:8501`
- [ ] Clé API OpenAI présente dans `.env`
- [ ] Base de données fraîche (ou plusieurs tentatives déjà effectuées pour alimenter le Dashboard)

> **Conseil :** effectuer 4 à 6 tentatives à l'avance sur le document de démo pour que le Dashboard soit déjà peuplé au moment de la présentation. Cela rend la démonstration plus lisible.

---

## Étape 1 — Présentation de l'application

**Action :** montrer la page d'accueil, les 4 onglets visibles.

**Script :**
> "Cette application transforme n'importe quel document métier en entraînement actif. Elle génère des questions, corrige les réponses, et suit la progression de l'agent section par section. Tout fonctionne localement, sans infrastructure lourde — SQLite et l'API OpenAI suffisent."

---

## Étape 2 — Le document de démonstration (onglet Documents)

**Action :** cliquer sur l'onglet **Documents** → dérouler l'expander du document de démo.

**Ce que le jury voit :** titre, type (TXT), nombre de sections, aperçu du texte.

**Script :**
> "Un document de procédure fictive SNCF est préchargé automatiquement au premier lancement — l'application est démontrable immédiatement, sans import préalable. Ici, 5 sections ont été détectées et indexées automatiquement."

---

## Étape 3 — Sélection du document et génération d'une question (onglet Entraînement)

**Action :** dans l'expander du document, cliquer **"Utiliser ce document pour l'entraînement"** → aller dans l'onglet **Entraînement** → cliquer **"Générer une question"**.

**Ce que le jury voit :** une question générée par l'IA, dont le type est choisi par rotation (cas pratique, vrai/faux, reformulation…).

**Script :**
> "L'IA sélectionne la section la plus pertinente par similarité vectorielle, puis choisit un type de question parmi six — directe, cas pratique, vrai/faux, piège, reformulation, conséquence — en évitant de répéter le même type deux fois de suite sur la même section."

---

## Étape 4 — Réponse et correction

**Action :** saisir une réponse (correcte ou volontairement incomplète) → cliquer **"Valider ma réponse"**.

**Ce que le jury voit :** score en %, type d'erreur identifié, correction détaillée, réponse attendue.

**Script :**
> "La correction est générée par le LLM : elle identifie le type d'erreur — oubli d'étape, confusion de notion, réponse vague — et produit une correction pédagogique ciblée. Le score et l'erreur sont enregistrés en base pour alimenter le suivi."

> **Variante :** répondre volontairement de façon incomplète pour montrer le bloc d'erreur rouge et la correction détaillée.

---

## Étape 5 — Dashboard pédagogique (onglet Dashboard)

**Action :** cliquer sur l'onglet **Dashboard**.

**Ce que le jury voit :** métriques globales, évolution des scores, graphiques par notion, et — en bas — le tableau **"Progression par section"**.

**Script :**
> "Après quelques tentatives, le Dashboard identifie automatiquement les sections fragiles, en consolidation ou maîtrisées. Chaque section a une date de prochaine révision calculée selon son niveau — 1 jour pour une section fragile, 3 jours pour une section en consolidation, 7 jours pour une section maîtrisée."

**Pointer :**
- Colonne **Maîtrise** (Fragile / En consolidation / Maîtrisé)
- Colonne **Statut révision** (En retard / Aujourd'hui / Dans N jour(s))
- Liste **Priorités de révision** avec indicateur de retard

---

## Étape 6 — La boucle pédagogique se ferme (retour dans Entraînement)

**Action :** retourner dans l'onglet **Entraînement**.

**Ce que le jury voit :** bloc "Révision suggérée" en haut de l'onglet — section prioritaire, score actuel, ancienneté, bouton "Réviser ce chunk →".

**Script :**
> "La boucle est fermée : le système identifie la section la plus urgente à réviser et la propose directement dans l'onglet Entraînement, sans que l'agent ait besoin de consulter le Dashboard. Un clic suffit pour charger la section et générer une nouvelle question."

---

## Étape 7 — Robustesse sans API (optionnel si le jury pose la question)

**Script :**
> "Si la clé API est absente ou indisponible, l'application bascule automatiquement en mode texte brut. Les questions sont générées sur le texte collé manuellement, sans RAG ni embeddings. Le Dashboard et la répétition espacée restent fonctionnels sur les tentatives existantes. L'application ne plante jamais."

---

## Points clés à retenir pour le jury

| Dimension | Ce que l'application fait |
|---|---|
| Pédagogie | 6 types de questions en rotation, correction ciblée par type d'erreur |
| Mémoire | Répétition espacée par section, date de révision dynamique |
| Robustesse | Fallback texte brut si API indisponible, seed idempotente au démarrage |
| Architecture | SQLite local, zéro dépendance externe hors OpenAI, réinitialisation triviale |
| Extensibilité | Tout document TXT ou PDF importable, sections détectées automatiquement |
