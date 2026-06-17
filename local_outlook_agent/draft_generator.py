from email_parser import ParsedEmail
from classifier import EmailAssessment


def generate_draft(email: ParsedEmail, assessment: EmailAssessment) -> str:
    if assessment.recommended_action == "attendre":
        body = (
            "Bonjour,\n\n"
            "Merci pour votre message. Je prends note et je reviendrai vers vous lorsque "
            "j'aurai les elements necessaires.\n\n"
            "Cordialement,"
        )
    elif assessment.recommended_action == "deleguer":
        body = (
            "Bonjour,\n\n"
            "Merci pour votre message. Je pense que cette demande devrait etre traitee "
            "avec la personne ou l'equipe la mieux placee. Je vais verifier a qui la "
            "transmettre avant de repondre officiellement.\n\n"
            "Cordialement,"
        )
    elif assessment.recommended_action == "planifier":
        body = (
            "Bonjour,\n\n"
            "Merci pour votre message. Je peux proposer quelques disponibilites, mais je "
            "vais d'abord verifier mon calendrier afin de confirmer un creneau approprie.\n\n"
            "Cordialement,"
        )
    elif assessment.recommended_action == "archiver":
        body = (
            "Bonjour,\n\n"
            "Merci pour l'information. Bien recu.\n\n"
            "Cordialement,"
        )
    else:
        body = (
            "Bonjour,\n\n"
            "Merci pour votre message. Je vais regarder cela et vous revenir avec une "
            "reponse plus complete.\n\n"
            "Cordialement,"
        )

    return (
        f"Objet: Re: {email.subject}\n"
        f"A: {email.sender}\n\n"
        f"{body}\n\n"
        "---\n"
        "Brouillon genere localement. A relire et valider manuellement. "
        "Aucun courriel n'a ete envoye.\n"
    )

