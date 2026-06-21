from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.meta_data_deletion_request import MetaDataDeletionRequest
from ..repositories.meta_connection import MetaConnectionRepository
from ..repositories.meta_data_deletion_request import MetaDataDeletionRequestRepository
from ..services.meta_signed_request_service import MetaSignedRequestError
from ..utils.time import utcnow


class MetaDataDeletionUseCaseError(Exception):
    pass


class HandleMetaDataDeletionCallbackUseCase:
    def __init__(self, *, session: AsyncSession, signed_request_service) -> None:
        self.session = session
        self.signed_request_service = signed_request_service
        self.connection_repo = MetaConnectionRepository(session)
        self.request_repo = MetaDataDeletionRequestRepository(session)

    async def execute(self, *, signed_request: str) -> dict[str, str]:
        try:
            payload = self.signed_request_service.parse_data_deletion_request(signed_request=signed_request)
        except MetaSignedRequestError as exc:
            raise MetaDataDeletionUseCaseError(str(exc)) from exc

        meta_user_id = str(payload["user_id"])
        confirmation_code = str(uuid4())
        deletion_request = MetaDataDeletionRequest(
            id=confirmation_code,
            meta_user_id=meta_user_id,
            status="pending",
            detail="Deletion request received",
        )
        await self.request_repo.create(deletion_request)

        connections = await self.connection_repo.list_by_meta_user_id(meta_user_id=meta_user_id)
        users_by_id = {
            connection.user.id: connection.user for connection in connections if getattr(connection, "user", None) is not None
        }

        for user in users_by_id.values():
            await self.session.delete(user)

        deletion_request.deleted_users_count = len(users_by_id)
        deletion_request.status = "completed"
        deletion_request.detail = (
            "Deleted all matching application data for the Meta user"
            if users_by_id
            else "No matching application data was stored for the Meta user"
        )
        deletion_request.completed_at = utcnow()

        await self.session.commit()
        return {
            "url": self.signed_request_service.build_deletion_status_url(confirmation_code=confirmation_code),
            "confirmation_code": confirmation_code,
        }


class GetMetaDataDeletionStatusUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self.request_repo = MetaDataDeletionRequestRepository(session)

    async def execute(self, *, confirmation_code: str) -> MetaDataDeletionRequest | None:
        return await self.request_repo.get_by_id(confirmation_code)
