from __future__ import annotations

import base64
import hashlib
import hmac
import json

from ..config import settings


class MetaSignedRequestError(Exception):
    pass


class MetaSignedRequestService:
    def __init__(
        self,
        *,
        app_secret: str | None = None,
        public_app_url: str | None = None,
        api_v1_prefix: str | None = None,
    ) -> None:
        self.app_secret = app_secret or settings.meta.app_secret
        self.public_app_url = public_app_url or settings.public_app_url
        self.api_v1_prefix = api_v1_prefix or settings.api_v1_prefix

    @staticmethod
    def _decode_base64url(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        try:
            return base64.urlsafe_b64decode(value + padding)
        except Exception as exc:  # noqa: BLE001
            raise MetaSignedRequestError("Meta signed_request is not valid base64url data") from exc

    def parse_data_deletion_request(self, *, signed_request: str) -> dict[str, object]:
        try:
            encoded_signature, encoded_payload = signed_request.split(".", 1)
        except ValueError as exc:
            raise MetaSignedRequestError("Meta signed_request must contain signature and payload") from exc

        expected_signature = hmac.new(
            self.app_secret.encode("utf-8"),
            msg=encoded_payload.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature = self._decode_base64url(encoded_signature)
        if not hmac.compare_digest(signature, expected_signature):
            raise MetaSignedRequestError("Meta signed_request signature is invalid")

        payload_bytes = self._decode_base64url(encoded_payload)
        try:
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise MetaSignedRequestError("Meta signed_request payload is not valid JSON") from exc

        if not isinstance(payload, dict):
            raise MetaSignedRequestError("Meta signed_request payload must be a JSON object")

        algorithm = str(payload.get("algorithm") or "").upper()
        if algorithm != "HMAC-SHA256":
            raise MetaSignedRequestError("Meta signed_request algorithm must be HMAC-SHA256")

        user_id = str(payload.get("user_id") or "").strip()
        if not user_id:
            raise MetaSignedRequestError("Meta signed_request payload does not contain user_id")

        return payload

    def build_deletion_status_url(self, *, confirmation_code: str) -> str:
        return (
            f"{self.public_app_url.rstrip('/')}"
            f"{self.api_v1_prefix}"
            f"/meta/data-deletion/status/{confirmation_code}"
        )
