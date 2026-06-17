from openai import OpenAI

from models import EmailAgendaAnalysis


SYSTEM_PROMPT = (
    "Tu es un assistant d'agenda prudent. Tu analyses des courriels Outlook pour "
    "detecter des demandes liees a l'agenda. Tu dois produire une sortie structuree. "
    "Tu ne dois jamais recommander d'envoyer automatiquement un courriel ni de "
    "modifier automatiquement un calendrier."
)


class EmailAgendaAnalyzerError(RuntimeError):
    pass


class EmailAgendaAnalyzer:
    def __init__(self, api_key: str, model: str = "gpt-4.1-mini") -> None:
        if not api_key:
            raise EmailAgendaAnalyzerError("OPENAI_API_KEY est manquante.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def analyze(
        self,
        *,
        subject: str,
        sender: str,
        body_preview: str,
        body_text: str,
    ) -> EmailAgendaAnalysis:
        if not (body_preview or body_text or subject):
            raise EmailAgendaAnalyzerError("Courriel vide: aucun sujet ni contenu exploitable.")

        user_prompt = f"""
Analyse ce courriel Outlook.

Contraintes:
- Ne pas inventer de date, heure ou periode si elles ne sont pas explicites.
- Estimer le temps necessaire pour chaque tache d'agenda ou de travail personnel.
- Utiliser duration_minutes=30 seulement si le message implique clairement une rencontre
  et ne donne pas de duree explicite.
- Pour du travail personnel, renseigner is_personal_work=true et estimated_effort_minutes.
- Ne pas proposer de bloc de travail personnel de plus de 120 minutes; si la tache semble
  plus longue, le dire dans recommended_next_step avec une validation humaine.
- Si le courriel vient de France metropolitaine ou mentionne la France, utiliser
  requested_timezone="Europe/Paris" pour les heures demandees.
- Si le courriel vient de l'ile de la Reunion ou mentionne La Reunion, utiliser
  requested_timezone="Indian/Reunion" pour les heures demandees.
- Quand un fuseau source est detecte, indiquer local_time_equivalent si possible.
- Renseigner les ambiguities lorsque l'information est incomplete.
- recommended_next_step doit toujours demander une validation humaine.
- Ne jamais recommander d'envoi automatique ni de modification automatique du calendrier.

Sujet: {subject or "(sans sujet)"}
Expediteur: {sender or "(inconnu)"}
Apercu: {body_preview or "(vide)"}
Corps:
{body_text or "(vide)"}
""".strip()

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=EmailAgendaAnalysis,
            )
        except Exception as exc:
            raise EmailAgendaAnalyzerError(f"Erreur OpenAI pendant l'analyse: {exc}") from exc

        parsed = completion.choices[0].message.parsed
        if not isinstance(parsed, EmailAgendaAnalysis):
            raise EmailAgendaAnalyzerError("Réponse OpenAI invalide: structure Pydantic absente.")
        return parsed
