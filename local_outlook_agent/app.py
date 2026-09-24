import tempfile
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import streamlit as st

from config import load_config
from email_parser import ParsedEmail, load_email_files, parse_csv, parse_email_file
from outlook_local import OutlookLocalError, fetch_recent_emails
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


def _load_sample_emails(limit: int) -> list[ParsedEmail]:
    sample_dir = Path("sample_emails")
    emails: list[ParsedEmail] = []
    if not sample_dir.exists():
        return emails

    for path in sorted(sample_dir.iterdir()):
        if len(emails) >= limit:
            break
        if path.suffix.lower() == ".csv":
            for parsed in parse_csv(path):
                if len(emails) >= limit:
                    break
                emails.append(parsed)
        elif path.suffix.lower() in {".txt", ".eml", ".msg"}:
            emails.append(parse_email_file(path))
    return emails


def _filtered_items(processed_items, categories, urgencies, actions):
    filtered = []
    for item in processed_items:
        if categories and item.assessment.category not in categories:
            continue
        if urgencies and item.assessment.urgency not in urgencies:
            continue
        if actions and item.assessment.recommended_action not in actions:
            continue
        filtered.append(item)
    return filtered


def _outputs_zip(processed_items, output_dir: Path) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        tasks_path = output_dir / "tasks.csv"
        if tasks_path.exists():
            archive.write(tasks_path, arcname="tasks.csv")
        for item in processed_items:
            if item.draft_path.exists():
                archive.write(item.draft_path, arcname=f"drafts/{item.draft_path.name}")
            if item.ics_path and item.ics_path.exists():
                archive.write(item.ics_path, arcname=f"calendar_blocks/{item.ics_path.name}")
    return buffer.getvalue()


def _reset_analysis_state() -> None:
    st.session_state.processed_items = []
    for key in list(st.session_state.keys()):
        if key.startswith("draft_edit_"):
            del st.session_state[key]


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
            ["Fichiers importes", "Outlook local"],
            help="Outlook local utilise AppleScript sur macOS et COM sur Windows. Les fichiers restent le chemin le plus fiable.",
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
        st.divider()
        show_bodies = st.checkbox("Afficher le contenu des courriels", value=True)
        if st.button("Vider la session"):
            st.session_state.loaded_emails = []
            _reset_analysis_state()
            st.rerun()

    if "loaded_emails" not in st.session_state:
        st.session_state.loaded_emails = []
    if "processed_items" not in st.session_state:
        st.session_state.processed_items = []
    if "loaded_source" not in st.session_state:
        st.session_state.loaded_source = source
    if st.session_state.loaded_source != source:
        st.session_state.loaded_emails = []
        _reset_analysis_state()
        st.session_state.loaded_source = source

    emails: list[ParsedEmail] = []
    if source == "Fichiers importes":
        col_upload, col_input, col_sample = st.columns([2, 1, 1])
        with col_upload:
            uploaded_files = st.file_uploader(
                "Importer des courriels",
                type=["txt", "eml", "msg", "csv"],
                accept_multiple_files=True,
                help="CSV accepte: sender/from/expediteur, subject/sujet, date/received/recu, body/contenu/message.",
            )
        with col_input:
            st.write("")
            st.write("")
            if st.button("Charger input_emails"):
                loaded = load_email_files(config.input_dir, limit=int(max_emails))
                st.session_state.loaded_emails = loaded
                _reset_analysis_state()
                if not loaded:
                    st.warning(f"Aucun fichier .txt, .eml, .msg ou .csv trouve dans {config.input_dir}.")
                else:
                    st.rerun()
        with col_sample:
            st.write("")
            st.write("")
            if st.button("Charger exemples"):
                loaded = _load_sample_emails(limit=int(max_emails))
                st.session_state.loaded_emails = loaded
                _reset_analysis_state()
                if not loaded:
                    st.warning("Aucun exemple trouve dans sample_emails/.")
                else:
                    st.rerun()

        if uploaded_files:
            try:
                emails = _parse_uploaded_files(uploaded_files, limit=int(max_emails))
                st.session_state.loaded_emails = emails
                _reset_analysis_state()
            except Exception as exc:
                st.error(f"Lecture impossible: {exc}")
    else:
        if st.button("Lire Outlook localement"):
            try:
                emails = fetch_recent_emails(limit=int(max_emails))
                st.session_state.loaded_emails = emails
                _reset_analysis_state()
                if not emails:
                    st.info("Outlook local n'a retourne aucun courriel.")
                    st.caption(
                        "Sur macOS, le nouvel Outlook peut repondre a AppleScript tout en exposant 0 message. "
                        "Dans ce cas, utilise l'import de fichiers ou input_emails/."
                    )
            except OutlookLocalError as exc:
                st.error(f"Outlook local indisponible: {exc}")

    emails = list(st.session_state.loaded_emails)
    if not emails:
        st.info(
            "Aucun courriel charge. Importe des fichiers, clique sur 'Charger exemples', "
            "clique sur 'Charger input_emails' ou essaie Outlook local."
        )
        return

    st.subheader("Courriels charges")
    st.write(f"{len(emails)} courriel(s) pret(s) pour analyse.")
    st.dataframe(
        [
            {
                "sujet": email.subject,
                "expediteur": email.sender or "inconnu",
                "date": email.date or "inconnue",
                "source": email.source,
            }
            for email in emails
        ],
        use_container_width=True,
        hide_index=True,
    )
    if show_bodies:
        for index, email in enumerate(emails, start=1):
            with st.expander(email.subject or f"Courriel {index}"):
                st.write(f"**Expediteur**: {email.sender or 'inconnu'}")
                st.write(f"**Date**: {email.date or 'inconnue'}")
                st.text_area("Contenu", email.body[:4000], height=160, disabled=True, key=f"body_{index}")

    if st.button("Analyser et generer les fichiers locaux", type="primary"):
        with st.spinner("Analyse locale en cours..."):
            st.session_state.processed_items = process_emails(
                emails,
                output_dir=output_dir,
                timezone=timezone,
                max_personal_block_minutes=int(max_block),
                llm_mode=llm_mode,
                openai_api_key=openai_api_key,
                create_ics=create_ics,
            )

    processed = list(st.session_state.processed_items)
    if not processed:
        return

    st.success(f"Analyse terminee. Resultats ecrits dans {output_dir}.")
    total_minutes = sum(item.assessment.estimated_minutes for item in processed)
    high_urgency = sum(1 for item in processed if item.assessment.urgency == "haute")
    planned = sum(1 for item in processed if item.assessment.recommended_action == "planifier")
    col_total, col_time, col_urgent, col_plan = st.columns(4)
    col_total.metric("Courriels", len(processed))
    col_time.metric("Temps estime", f"{total_minutes} min")
    col_urgent.metric("Urgents", high_urgency)
    col_plan.metric("A planifier", planned)

    st.subheader("Filtres")
    category_options = sorted({item.assessment.category for item in processed})
    urgency_options = sorted({item.assessment.urgency for item in processed})
    action_options = sorted({item.assessment.recommended_action for item in processed})
    col_cat, col_urg, col_action = st.columns(3)
    selected_categories = col_cat.multiselect("Categories", category_options)
    selected_urgencies = col_urg.multiselect("Urgences", urgency_options)
    selected_actions = col_action.multiselect("Actions", action_options)
    visible_items = _filtered_items(
        processed,
        selected_categories,
        selected_urgencies,
        selected_actions,
    )

    st.subheader("Taches detectees")
    st.dataframe(_task_rows(visible_items), use_container_width=True, hide_index=True)

    tasks_path = output_dir / "tasks.csv"
    col_tasks, col_zip = st.columns([1, 1])
    with col_tasks:
        if tasks_path.exists():
            st.download_button(
                "Telecharger tasks.csv",
                data=tasks_path.read_bytes(),
                file_name="tasks.csv",
                mime="text/csv",
            )
    with col_zip:
        st.download_button(
            "Telecharger toutes les sorties",
            data=_outputs_zip(processed, output_dir),
            file_name="local_outlook_agent_outputs.zip",
            mime="application/zip",
        )

    st.subheader("Brouillons a valider")
    for index, item in enumerate(visible_items, start=1):
        with st.expander(item.email.subject or "(sans sujet)", expanded=False):
            draft_key = f"draft_edit_{index}_{item.email.email_id}"
            draft_text = st.text_area("Brouillon", item.draft_text, height=220, key=draft_key)
            col_save, col_download, col_ics = st.columns([1, 1, 1])
            with col_save:
                if st.button("Sauvegarder le brouillon", key=f"save-{index}-{item.email.email_id}"):
                    item.draft_path.write_text(draft_text, encoding="utf-8")
                    st.success(f"Brouillon sauvegarde: {item.draft_path}")
            with col_download:
                st.download_button(
                    "Telecharger le brouillon",
                    data=draft_text.encode("utf-8"),
                    file_name=item.draft_path.name,
                    mime="text/plain",
                    key=f"draft-{index}-{item.email.email_id}",
                )
            with col_ics:
                if item.ics_path and item.ics_path.exists():
                    st.download_button(
                        "Telecharger le bloc .ics",
                        data=item.ics_path.read_bytes(),
                        file_name=item.ics_path.name,
                        mime="text/calendar",
                        key=f"ics-{index}-{item.email.email_id}",
                    )
                else:
                    st.caption("Aucun .ics genere")


if __name__ == "__main__":
    main()
