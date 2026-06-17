# Prototype Python d'agent Outlook Agenda

Ce prototype local lit les courriels recents Outlook via Microsoft Graph, les analyse avec OpenAI en sortie structuree Pydantic, consulte les disponibilites du calendrier et affiche jusqu'a 3 creneaux possibles dans la console.

Il estime aussi le temps necessaire pour les demandes detectees. Les propositions respectent la plage `08:30-17:30`, evitent les week-ends et plafonnent les blocs de travail personnel a `2h` par defaut.

## Securite

Par defaut, l'application est strictement en lecture seule:

- aucun courriel envoye;
- aucun evenement cree, modifie ou supprime;
- aucune permission `Mail.Send`;
- aucune permission `Calendars.ReadWrite`.

Une phase optionnelle de creation de brouillon est disponible avec `ENABLE_DRAFT_CREATION=true`. Elle ajoute la permission `Mail.ReadWrite` et cree uniquement un brouillon relisible. Elle n'envoie jamais le courriel.

## Configuration Microsoft Entra ID

1. Creez une App Registration dans Microsoft Entra ID.
2. Notez le `TENANT_ID` et le `CLIENT_ID`.
3. Activez le public client flow / device code flow si necessaire.
4. Ajoutez les permissions deleguees Microsoft Graph:
   - `User.Read`
   - `Mail.Read`
   - `Calendars.Read`
   - `MailboxSettings.Read`
5. Pour la phase brouillon optionnelle seulement, ajoutez aussi:
   - `Mail.ReadWrite`

## Installation

```bash
cd outlook_agenda_agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Fichier `.env`

Copiez `.env.example` vers `.env`, puis renseignez les valeurs:

```env
TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
OPENAI_API_KEY=sk-...
TIMEZONE=America/Montreal
ENABLE_DRAFT_CREATION=false
PERSONAL_WORK_MAX_BLOCK_MINUTES=120
```

`PERSONAL_WORK_MAX_BLOCK_MINUTES` limite la duree d'un bloc propose pour une tache personnelle. La valeur par defaut est `120` minutes.

## Regles de planification

- aucun creneau avant `08:30` ni apres `17:30`;
- aucun creneau le samedi ou le dimanche;
- les taches personnelles sont proposees en blocs de `120` minutes maximum;
- si un courriel vient de France metropolitaine, le fuseau source attendu est `Europe/Paris`;
- si un courriel vient de l'ile de La Reunion, le fuseau source attendu est `Indian/Reunion`;
- le prototype affiche les hypotheses et demande toujours une validation humaine.

## Execution

```bash
python main.py
```

Au premier lancement, suivez le device code flow affiche dans la console.

## Tests

Les tests unitaires ne font aucun appel reel a Microsoft Graph ni a OpenAI.

```bash
python -m unittest discover -s tests
```
