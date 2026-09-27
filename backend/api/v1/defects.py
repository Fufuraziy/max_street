from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.deps import InitIdentityDep, SessionDep, require_admin, resolve_identity
from models.enums import DefectStatus
from schemas.defect import DefectCreate, DefectRead, DefectStatusUpdate, DefectWithCourt
from services import defects as defect_service

router = APIRouter(tags=["Поломки"])


@router.post(
    "/courts/{court_id}/defects",
    response_model=DefectRead,
    status_code=201,
    summary="Сообщить о неисправности",
)
@router.post(
    "/spots/{court_id}/defects",
    response_model=DefectRead,
    status_code=201,
    summary="Сообщить о неисправности спота (алиас /spots)",
)
async def report_defect(
    court_id: int,
    payload: DefectCreate,
    session: SessionDep,
    verified: InitIdentityDep,
) -> DefectRead:
    """Создаёт тикет со статусом `reported` («Передано в районные службы»)."""
    reporter = resolve_identity(verified, payload.user_max_id, payload.user_name or "Игрок")
    defect = await defect_service.create_defect(
        session,
        court_id=court_id,
        reporter=reporter,
        defect_type=payload.defect_type.value,
        description=payload.description,
        save_user=verified is not None or payload.user_name is not None,
    )
    return DefectRead.model_validate(defect)


@router.get("/defects", response_model=list[DefectWithCourt], summary="Заявки для городских служб")
async def list_defects(
    session: SessionDep,
    status: DefectStatus | None = None,
    court_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[DefectWithCourt]:
    defects = await defect_service.list_defects(
        session, status=status.value if status else None, court_id=court_id, limit=limit
    )
    return [DefectWithCourt.model_validate(defect) for defect in defects]


@router.patch(
    "/defects/{defect_id}",
    response_model=DefectRead,
    summary="Сменить статус заявки (X-Admin-Token)",
    dependencies=[Depends(require_admin)],
)
async def update_defect_status(defect_id: int, payload: DefectStatusUpdate, session: SessionDep) -> DefectRead:
    defect = await defect_service.update_defect_status(session, defect_id, payload.status.value)
    return DefectRead.model_validate(defect)
