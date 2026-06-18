# Prototype local Outlook sans Microsoft Graph

Ce prototype macOS aide a analyser des courriels Outlook sans Azure, Entra, `CLIENT_ID` ni `TENANT_ID`.

Il ne modifie rien dans Outlook:

- aucun courriel envoye automatiquement;
- aucun appel a `Mail.Send`, Graph ou Outlook Web;
- aucun courriel modifie ou supprime;
- aucun evenement calendrier cree automatiquement;
- dry-run active par defaut;
- les resultats sont ecrits dans `output/`.

## Choix techniques

### A) Outlook macOS + AppleScript

Avantages:

- ne demande pas Microsoft Graph;
- reste local sur le Mac;
- peut lire des metadonnees et parfois le contenu des messages.

Inconvenients:

- depend fortement de la version Outlook macOS;
- le "nouvel Outlook" expose parfois 0 message a AppleScript;
- macOS demande une permission Automatisation;
- pas fiable pour un agent robuste a long terme.

Test local effectue: Outlook repond a AppleScript, mais `messages of inbox` retourne 0 message dans cette configuration. Le fallback fichiers est donc important.

### B) Export manuel `.eml`, `.msg` ou `.txt`

Avantages:

- fiable et controlable;
- aucun acces Azure/Graph;
- parfait pour tester l'agent et les regles.

Inconvenients:

- demande une exportation manuelle;
- pas de synchronisation automatique.

### C) CSV de courriels copie-colle

Avantages:

- tres simple pour prototyper;
- utile si les exports Outlook sont difficiles.

Inconvenients:

- moins naturel pour conserver le corps complet du message;
- demande de copier-coller les champs.

Cette option est implementee. Colonnes reconnues:

- `sender`, `from` ou `expediteur`;
- `subject` ou `sujet`;
- `date`, `received` ou `recu`;
- `body`, `contenu` ou `message`.

### D) Automatisation navigateur

A eviter sauf dernier recours.

Inconvenients:

- fragile;
- potentiellement contraire aux politiques institutionnelles;
- risque de casser avec les changements Outlook Web;
- moins propre que l'export manuel ou l'accord IT.

## Installation

```bash
cd /Users/mickaelbegon/Documents/Agent_email_calendar/local_outlook_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Interface Streamlit

Lancer l'interface locale:

```bash
streamlit run app.py
```

Puis ouvrir l'URL affichee par Streamlit, habituellement:

```text
http://localhost:8501
```

L'interface permet:

- importer des fichiers `.txt`, `.eml`, `.msg` ou `.csv`;
- essayer Outlook AppleScript localement;
- revoir les courriels charges avant analyse;
- generer `tasks.csv`;
- generer des brouillons `.txt` a valider manuellement;
- generer des fichiers `.ics` locaux si l'option est cochee.

Elle ne contient aucun bouton d'envoi de courriel.

Le mode par defaut est sans LLM:

```env
LLM_MODE=rules
DRY_RUN=true
CREATE_ICS=false
```

Pour tester avec OpenAI:

```env
LLM_MODE=openai
OPENAI_API_KEY=sk-...
```

## Permissions macOS

Pour AppleScript, macOS peut demander l'autorisation:

`Reglages Systeme > Confidentialite et securite > Automatisation`

Autoriser Terminal, iTerm, Python ou l'application qui lance le script a controler `Microsoft Outlook`.

Outlook doit etre installe et ouvert.

## Tester Outlook AppleScript

```bash
python main.py --source outlook
```

Si Outlook ne retourne aucun message, le script affichera:

```text
Outlook AppleScript n'a retourne aucun courriel.
Aucun courriel trouve...
```

## Tester avec fichiers locaux

Option rapide: copier l'exemple fourni.

```bash
cp sample_emails/research_meeting.txt input_emails/test.txt
python main.py --source files
```

Ou creer un fichier dans `input_emails/test.txt`:

```text
From: personne@example.com
Subject: Rencontre projet de recherche
Date: 2026-06-17

Bonjour,
Peux-tu me proposer une disponibilite pour discuter du projet de recherche?
Merci.
```

Puis lancer:

```bash
python main.py --source files
```

Tester avec CSV:

```bash
cp sample_emails/sample_emails.csv input_emails/sample_emails.csv
python main.py --source files
```

Ou laisser le mode auto essayer Outlook puis les fichiers:

```bash
python main.py
```

## Sortie attendue

```text
Analyse de 1 courriel(s). Dry-run: True
- Rencontre projet de recherche | recherche | normale | 30 min | planifier

Resultats ecrits dans: output
- Taches: output/tasks.csv
- Brouillons: output/drafts
- Fichiers ICS: desactives (CREATE_ICS=false)
```

Le dossier `output/` contient:

- `tasks.csv`: taches structurees;
- `drafts/`: brouillons texte a relire;
- `calendar_blocks/`: fichiers `.ics` si `CREATE_ICS=true`.

## Generer des fichiers `.ics`

Modifier `.env`:

```env
CREATE_ICS=true
```

Puis relancer:

```bash
python main.py --source files
```

Les `.ics` sont seulement des fichiers locaux. Il faut les ouvrir/importer manuellement pour creer un bloc calendrier.

## Tests

```bash
python -m unittest discover -s tests
```

Les tests n'appellent ni Outlook, ni OpenAI, ni Microsoft Graph.
