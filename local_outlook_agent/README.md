# Prototype local Outlook sans Microsoft Graph

Ce prototype aide a analyser des courriels Outlook localement, sous macOS ou Windows, sans Azure, Entra, `CLIENT_ID` ni `TENANT_ID`.

Il ne modifie rien dans Outlook:

- aucun courriel envoye automatiquement;
- aucun appel a `Mail.Send`, Graph ou Outlook Web;
- aucun courriel modifie ou supprime;
- aucun evenement calendrier cree automatiquement;
- dry-run active par defaut;
- les resultats sont ecrits dans `output/`.

## Choix techniques

### A) Outlook local

Sur macOS, l'agent utilise AppleScript avec `osascript`.

Sur Windows, l'agent utilise Outlook COM via `pywin32`. Outlook desktop doit etre installe, configure et accessible depuis la session Windows qui lance Python.

Avantages:

- ne demande pas Microsoft Graph;
- reste local sur la machine;
- peut lire des metadonnees et le contenu des messages.

Inconvenients:

- depend fortement de la version Outlook et du profil local;
- le "nouvel Outlook" peut exposer moins de possibilites que l'application Outlook desktop classique;
- macOS peut demander une permission Automatisation;
- Windows demande la dependance `pywin32`;
- pas fiable pour un agent robuste a long terme.

Le fallback fichiers reste donc important.

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

macOS ou Linux:

```bash
cd /chemin/vers/Agent_email_calendar/local_outlook_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell:

```powershell
cd C:\chemin\vers\Agent_email_calendar\local_outlook_agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
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
- charger directement les fichiers presents dans `input_emails/`;
- charger des courriels exemples pour verifier que l'interface fonctionne;
- essayer Outlook localement;
- revoir les courriels charges avant analyse;
- afficher un tableau de synthese et filtrer les resultats apres analyse;
- editer puis sauvegarder un brouillon local;
- generer `tasks.csv`;
- generer des brouillons `.txt` a valider manuellement;
- generer des fichiers `.ics` locaux si l'option est cochee.
- telecharger toutes les sorties dans un fichier `.zip`.

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

## Permissions et limites Outlook local

### macOS

Pour AppleScript, macOS peut demander l'autorisation:

`Reglages Systeme > Confidentialite et securite > Automatisation`

Autoriser Terminal, iTerm, Python ou l'application qui lance le script a controler `Microsoft Outlook`.

### Windows

Installer les dependances avec `pip install -r requirements.txt`, ce qui installe `pywin32` uniquement sous Windows.

Outlook desktop doit etre installe, ouvert ou disponible en arriere-plan, et le profil MAPI par defaut doit contenir une boite de reception.

## Tester Outlook local

```bash
python main.py --source outlook
```

Si Outlook ne retourne aucun message, le script affichera:

```text
Outlook local n'a retourne aucun courriel.
Aucun courriel trouve...
```

Dans l'interface Streamlit, c'est la raison la plus probable si aucun courriel n'apparait apres avoir clique sur `Lire Outlook localement`. Sur macOS, le nouvel Outlook peut repondre a AppleScript tout en exposant 0 message. Dans ce cas, utiliser plutot:

- `Charger exemples` pour verifier le fonctionnement;
- `Charger input_emails` apres avoir place des fichiers dans `input_emails/`;
- l'import manuel `.txt`, `.eml`, `.msg` ou `.csv`.

## Tester avec fichiers locaux

Option rapide: copier l'exemple fourni.

macOS ou Linux:

```bash
cp sample_emails/research_meeting.txt input_emails/test.txt
python main.py --source files
```

Windows PowerShell:

```powershell
Copy-Item sample_emails\research_meeting.txt input_emails\test.txt
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

Tester avec CSV:

macOS ou Linux:

```bash
cp sample_emails/sample_emails.csv input_emails/sample_emails.csv
python main.py --source files
```

Windows PowerShell:

```powershell
Copy-Item sample_emails\sample_emails.csv input_emails\sample_emails.csv
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
