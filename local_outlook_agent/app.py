import tempfile
from pathlib import Path

import streamlit as st

from config import load_config
from email_parser import ParsedEmail, parse_csv, parse_email_file
from outlook_applescript import OutlookAppleScriptError, fetch_recent_emails
from processor import process_emails


def _parse_uploaded_files(uploaded_files, limit: int) -> list[ParsedEmail]:
    emails: list[ParsedEmail] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for uploaded_file in uploaded_files:
            if len(emails) >= limit:
                break
            path = tmp_dir / uploaded_file.name
            path.write_bytes(uploaded_file.getvalue())

            if path.suffix.lower() == ".csv":
                for parsed in parse_csv(path):
                    if len(emails) >= limit:
                        break
                    emails.append(parsed)
            else:
                emails.append(parse_email_file(path))
    return emails


def _task_rows(processed_items):
    rows = []
    for item in processed_items:
        rows.append(
            {
                "sujet": item.email.subject,
                "expediteur": item.email.sender,
                "categorie": item.assessment.category,
                "urgence": item.assessment.urgency,
                "importance": item.assessment.importance,
                "minutes": item.assessment.estimated_minutes,
                "action": item.assessment.recommended_action,
                "debut suggere": item.task.suggested_start,
                "fin suggeree": item.task.suggested_end,
            }
        )
    return rows


def main() -> None:
    st.set_page_config(page_title="Assistant local courriels Outlook", layout="wide")

    config = load_config()

    st.title("Assistant local courriels Outlook")
    st.caption("Prototype local sans Microsoft Graph, sans Azure, sans envoi de courriels.")
    st.warning(
        "Mode securite: cette app ne peut pas envoyer de courriel. "
        "Elle cree seulement des brouillons texte, un tasks.csv et des fichiers .ics optionnels.",
    )

    with st.sidebar:
        st.header("Parametres")
        source = st.radio(
            "Source",
            ["Fichiers importes", "Outlook AppleScript"],
            help="Outlook peut retourner 0 message selon la version macOS. Les fichiers sont le chemin le plus fiable.",
        )
        max_emails = st.number_input("Nombre max de courriels", min_value=1, max_value=50, value=config.max_emails)
        timezone = st.text_input("Fuseau horaire", value=config.timezone)
        output_dir = Path(st.text_input("Dossier de sortie", value=str(config.output_dir)))
        create_ics = st.checkbox("Creer des fichiers .ics locaux", value=config.create_ics)
        llm_mode = st.selectbox("Analyse", ["rules", "openai"], index=0 if config.llm_mode == "rules" else 1)
        openai_api_key = config.openai_api_key
        if llm_mode == "openai":
            openai_api_key = st.text_input(
                "OPENAI_API_KEY",
                value=config.openai_api_key,
                type="password",
                help="Optionnel. Les regles locales restent disponibles sans cle.",
            )
        max_block = st.number_input(
            "Bloc personnel max (minutes)",
            min_value=30,
            max_value=240,
            value=config.personal_work_max_block_minutes,
            step=30,
        )

    if "loaded_emails" not in st.session_state:
        st.session_state.loaded_emails = []
    if "loaded_source" not in st.session_state:
        st.session_state.loaded_source = source
    if st.session_state.loaded_source != source:
        st.session_state.loaded_emails = []
        st.session_state.loaded_source = source

    emails: list[ParsedEmail] = []
    if source == "Fichiers importes":
        uploaded_files = st.file_uploader(
            "Importer des courriels",
            type=["txt", "eml", "msg", "csv"],
            accept_multiple_files=True,
            help="CSV accepte: sender/from/expediteur, subject/sujet, date/received/recu, body/contenu/message.",
        )
        if uploaded_files:
            try:
                emails = _parse_uploaded_files(uploaded_files, limit=int(max_emails))
                st.session_state.loaded_emails = emails
            except Exception as exc:
                st.error(f"Lecture impossible: {exc}")
    else:
        if st.button("Lire Outlook localement"):
            try:
                emails = fetch_recent_emails(limit=int(max_emails))
                st.session_state.loaded_emails = emails
                if not emails:
                    st.info("Outlook AppleScript n'a retourne aucun courriel.")
            except OutlookAppleScriptError as exc:
                st.error(f"Outlook AppleScript indisponible: {exc}")

    emails = list(st.session_state.loaded_emails)
    if not emails:
        st.info("Importe des fichiers ou essaie Outlook AppleScript pour commencer.")
        return

    st.subheader("Courriels charges")
    st.write(f"{len(emails)} courriel(s) pret(s) pour analyse.")
    for email in emails:
        with st.expander(email.subject or "(sans sujet)"):
            st.write(f"**Expediteur**: {email.sender or 'inconnu'}")
            st.write(f"**Date**: {email.date or 'inconnue'}")
            st.text_area("Contenu", email.body[:4000], height=160, disabled=True)

    if not st.button("Analyser et generer les fichiers locaux", type="primary"):
        return

    processed = process_emails(
        emails,
        output_dir=output_dir,
        timezone=timezone,
        max_personal_block_minutes=int(max_block),
        llm_mode=llm_mode,
        openai_api_key=openai_api_key,
        create_ics=create_ics,
    )

    st.success(f"Analyse terminee. Resultats ecrits dans {output_dir}.")
    st.subheader("Taches detectees")
    st.dataframe(_task_rows(processed), use_container_width=True, hide_index=True)

    tasks_path = output_dir / "tasks.csv"
    if tasks_path.exists():
        st.download_button(
            "Telecharger tasks.csv",
            data=tasks_path.read_bytes(),
            file_name="tasks.csv",
            mime="text/csv",
        )

    st.subheader("Brouillons a valider")
    for item in processed:
        with st.expander(item.email.subject or "(sans sujet)", expanded=False):
            st.text_area("Brouillon", item.draft_text, height=220)
            st.download_button(
                "Telecharger le brouillon",
                data=item.draft_text.encode("utf-8"),
                file_name=item.draft_path.name,
                mime="text/plain",
                key=f"draft-{item.email.email_id}",
            )
            if item.ics_path and item.ics_path.exists():
                st.download_button(
                    "Telecharger le bloc .ics",
                    data=item.ics_path.read_bytes(),
                    file_name=item.ics_path.name,
                    mime="text/calendar",
                    key=f"ics-{item.email.email_id}",
                )


if __name__ == "__main__":
    main()
