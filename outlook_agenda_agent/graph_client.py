from typing import Any, Optional

import msal
import requests


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class GraphClientError(RuntimeError):
    pass


class GraphClient:
    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        scopes: list[str],
        timezone: str,
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.scopes = scopes
        self.timezone = timezone
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.app = msal.PublicClientApplication(client_id, authority=self.authority)
        self._access_token: Optional[str] = None

    def _get_access_token(self) -> str:
        if self._access_token:
            return self._access_token

        accounts = self.app.get_accounts()
        result = None
        if accounts:
            result = self.app.acquire_token_silent(self.scopes, account=accounts[0])

        if not result:
            flow = self.app.initiate_device_flow(scopes=self.scopes)
            if "user_code" not in flow:
                raise GraphClientError("Impossible de démarrer le device code flow Microsoft.")

            print(flow["message"])
            result = self.app.acquire_token_by_device_flow(flow)

        if not result or "access_token" not in result:
            error = result.get("error_description") if isinstance(result, dict) else None
            raise GraphClientError(
                "Impossible d'obtenir un jeton Microsoft Graph."
                + (f" Détail: {error}" if error else "")
            )

        self._access_token = result["access_token"]
        return self._access_token

    def _headers(self) -> dict[str, str]:
        token = self._get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Prefer": f'outlook.timezone="{self.timezone}"',
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        response = requests.request(
            method,
            f"{GRAPH_BASE_URL}{path}",
            headers=self._headers(),
            params=params,
            json=json,
            timeout=30,
        )

        if response.status_code in {401, 403}:
            raise GraphClientError(
                "Permissions Microsoft Graph insuffisantes ou jeton invalide. "
                "Vérifiez les permissions déléguées et le consentement administrateur si requis."
            )
        if not response.ok:
            raise GraphClientError(
                f"Erreur Microsoft Graph {response.status_code}: {response.text[:500]}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise GraphClientError("Réponse Microsoft Graph invalide: JSON attendu.") from exc

        if not isinstance(data, dict):
            raise GraphClientError("Réponse Microsoft Graph invalide: objet JSON attendu.")
        return data

    def get_recent_emails(self, top: int = 10) -> list[dict[str, Any]]:
        safe_top = max(1, min(top, 10))
        data = self._request(
            "GET",
            "/me/mailFolders/inbox/messages",
            params={
                "$top": safe_top,
                "$orderby": "receivedDateTime desc",
                "$select": "id,subject,from,receivedDateTime,bodyPreview,body",
            },
        )

        messages = data.get("value")
        if not isinstance(messages, list):
            raise GraphClientError("Réponse Graph invalide: champ 'value' absent ou invalide.")
        return messages

    def get_schedule(
        self,
        start_datetime: str,
        end_datetime: str,
        interval_minutes: int = 30,
    ) -> dict[str, Any]:
        payload = {
            "schedules": ["me"],
            "startTime": {"dateTime": start_datetime, "timeZone": self.timezone},
            "endTime": {"dateTime": end_datetime, "timeZone": self.timezone},
            "availabilityViewInterval": interval_minutes,
        }
        return self._request("POST", "/me/calendar/getSchedule", json=payload)

    def create_draft_reply(
        self,
        to_email: str,
        subject: str,
        body_text: str,
    ) -> dict[str, Any]:
        """Optional v2 path: creates a draft only. It never sends a message."""
        payload = {
            "subject": subject,
            "body": {"contentType": "Text", "content": body_text},
            "toRecipients": [
                {"emailAddress": {"address": to_email}},
            ],
        }
        return self._request("POST", "/me/messages", json=payload)
