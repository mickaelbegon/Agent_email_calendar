from dataclasses import dataclass
from typing import Literal

from email_parser import ParsedEmail


Category = Literal[
    "etudiant",
    "administration",
    "recherche",
    "subvention",
    "enseignement",
    "collaboration",
    "autre",
]
Urgency = Literal["basse", "normale", "haute"]
Importance = Literal["basse", "normale", "haute"]
RecommendedAction = Literal["repondre", "deleguer", "planifier", "archiver", "attendre"]


@dataclass(frozen=True)
class EmailAssessment:
    category: Category
    urgency: Urgency
    importance: Importance
    estimated_minutes: int
    recommended_action: RecommendedAction
    rationale: str


CATEGORY_KEYWORDS: list[tuple[Category, tuple[str, ...]]] = [
    ("subvention", ("subvention", "grant", "frq", "nserc", "crsng", "cihr", "irsc")),
    ("enseignement", ("cours", "classe", "examen", "devoir", "moodle", "enseignement")),
    ("etudiant", ("etudiant", "etudiante", "memoire", "these", "stage", "supervision")),
    ("recherche", ("article", "manuscrit", "experience", "donnees", "recherche", "publication")),
    ("administration", ("formulaire", "administration", "comite", "departement", "budget")),
    ("collaboration", ("collaboration", "meeting", "rencontre", "projet commun", "coauthor")),
]


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def classify_email_rules(email: ParsedEmail) -> EmailAssessment:
    text = f"{email.sender}\n{email.subject}\n{email.body}".lower()

    category: Category = "autre"
    for candidate, keywords in CATEGORY_KEYWORDS:
        if _contains_any(text, keywords):
            category = candidate
            break

    urgency: Urgency = "normale"
    if _contains_any(text, ("urgent", "aujourd'hui", "asap", "des que possible", "deadline", "echeance")):
        urgency = "haute"
    elif _contains_any(text, ("quand tu peux", "pas presse", "la semaine prochaine")):
        urgency = "basse"

    importance: Importance = "normale"
    if category in {"subvention", "recherche", "enseignement"} or urgency == "haute":
        importance = "haute"
    elif category == "autre":
        importance = "basse"

    recommended_action: RecommendedAction = "repondre"
    if _contains_any(text, ("rencontre", "meeting", "disponibilite", "rdv", "calendrier")):
        recommended_action = "planifier"
    elif _contains_any(text, ("pour information", "fyi", "aucune action")):
        recommended_action = "archiver"
    elif _contains_any(text, ("peux-tu transmettre", "deleguer", "qui peut")):
        recommended_action = "deleguer"
    elif _contains_any(text, ("attendre", "je reviens vers toi")):
        recommended_action = "attendre"

    estimated_minutes = 15
    if recommended_action == "archiver":
        estimated_minutes = 2
    elif recommended_action == "planifier":
        estimated_minutes = 30
    elif urgency == "haute" and importance == "haute":
        estimated_minutes = 60
    elif category == "subvention":
        estimated_minutes = 120

    return EmailAssessment(
        category=category,
        urgency=urgency,
        importance=importance,
        estimated_minutes=estimated_minutes,
        recommended_action=recommended_action,
        rationale="Classification locale par mots-cles; validation humaine recommandee.",
    )


def classify_email(email: ParsedEmail, llm_mode: str = "rules", openai_api_key: str = "") -> EmailAssessment:
    # The local rules path is the default and keeps the prototype usable without any API key.
    if llm_mode != "openai":
        return classify_email_rules(email)

    try:
        from openai import OpenAI
    except ModuleNotFoundError:
        return classify_email_rules(email)

    client = OpenAI(api_key=openai_api_key)
    prompt = f"""
Classe ce courriel dans une sortie JSON simple.
Categories permises: etudiant, administration, recherche, subvention, enseignement, collaboration, autre.
Urgence/importance: basse, normale, haute.
Temps permis: 2, 15, 30, 60, 120 minutes.
Actions permises: repondre, deleguer, planifier, archiver, attendre.
Ne recommande jamais d'envoyer automatiquement un courriel.

Sujet: {email.subject}
Expediteur: {email.sender}
Date: {email.date}
Corps:
{email.body[:4000]}
""".strip()

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            text={"format": {"type": "json_object"}},
        )
        import json

        data = json.loads(response.output_text)
        return EmailAssessment(
            category=data.get("category", "autre"),
            urgency=data.get("urgency", "normale"),
            importance=data.get("importance", "normale"),
            estimated_minutes=int(data.get("estimated_minutes", 15)),
            recommended_action=data.get("recommended_action", "repondre"),
            rationale=data.get("rationale", "Analyse LLM; validation humaine recommandee."),
        )
    except Exception:
        return classify_email_rules(email)

