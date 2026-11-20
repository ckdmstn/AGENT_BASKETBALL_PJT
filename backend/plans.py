from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints, field_validator, model_validator

from backend.config import KST
from backend.database import Database, get_database


RequiredText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PlanFields(BaseModel):
    model_config = ConfigDict(extra='forbid')

    session_id: RequiredText | None = None
    venue_address: str | None = None
    note: str | None = None
    end_at: AwareDatetime | None = None

    @field_validator('start_at', 'end_at', mode='before', check_fields=False)
    @classmethod
    def require_datetime(cls, value):
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError('시간대가 포함된 날짜와 시각을 입력하세요.')
        if isinstance(value, str) and not any(separator in value for separator in ('T', 't', ' ')):
            raise ValueError('시간대가 포함된 날짜와 시각을 입력하세요.')
        return value

    @field_validator('start_at', 'end_at', check_fields=False)
    @classmethod
    def normalize_time(cls, value):
        return value.astimezone(KST) if value is not None else None


class PlanCreate(PlanFields):
    match_id: RequiredText
    home_team: RequiredText
    away_team: RequiredText
    venue_name: RequiredText
    start_at: AwareDatetime

    @model_validator(mode='after')
    def validate_interval(self):
        if self.end_at is not None and self.end_at <= self.start_at:
            raise ValueError('종료 시각은 시작 시각보다 늦어야 합니다.')
        return self


class PlanPatch(PlanFields):
    match_id: RequiredText | None = None
    home_team: RequiredText | None = None
    away_team: RequiredText | None = None
    venue_name: RequiredText | None = None
    start_at: AwareDatetime | None = None

    @model_validator(mode='after')
    def validate_patch(self):
        required = PlanCreate.model_fields.keys() - PlanFields.model_fields.keys()
        if not self.model_fields_set or any(getattr(self, field) is None for field in self.model_fields_set & required):
            raise ValueError('수정할 필드를 입력하세요. 필수 필드는 비울 수 없습니다.')
        return self


class Plan(PlanCreate):
    id: int
    created_at: datetime
    updated_at: datetime


router = APIRouter(prefix='/api/plans', tags=['plans'])
DB = Annotated[Database, Depends(get_database)]
PLAN_COLUMNS = tuple(PlanCreate.model_fields)


def values(plan: PlanCreate):
    data = plan.model_dump()
    for field in ('start_at', 'end_at'):
        if data[field] is not None:
            data[field] = data[field].isoformat(timespec='microseconds')
    return data


def get_row(conn, plan_id):
    row = conn.execute('SELECT * FROM plans WHERE id = ?', (plan_id,)).fetchone()
    if row is None:
        raise HTTPException(404, '계획을 찾을 수 없습니다.')
    return Plan.model_validate(dict(row))


@router.post('', status_code=201)
def create_plan(request: PlanCreate, db: DB) -> Plan:
    now = datetime.now(KST).isoformat(timespec='microseconds')
    data = values(request)
    with db.connection(write=True) as conn:
        columns = ', '.join(PLAN_COLUMNS)
        placeholders = ', '.join('?' for _ in PLAN_COLUMNS)
        cursor = conn.execute(
            f'INSERT INTO plans ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?)',
            (*data.values(), now, now),
        )
        return get_row(conn, cursor.lastrowid)


@router.get('')
def list_plans(db: DB) -> list[Plan]:
    with db.connection() as conn:
        return [Plan.model_validate(dict(row)) for row in conn.execute('SELECT * FROM plans ORDER BY start_at, id')]


@router.get('/{plan_id}')
def read_plan(plan_id: int, db: DB) -> Plan:
    with db.connection() as conn:
        return get_row(conn, plan_id)


@router.patch('/{plan_id}')
def patch_plan(plan_id: int, request: PlanPatch, db: DB) -> Plan:
    with db.connection(write=True) as conn:
        current = get_row(conn, plan_id).model_dump(include=set(PLAN_COLUMNS))
        changes = request.model_dump(exclude_unset=True)
        merged = {**current, **changes}
        if merged['end_at'] is not None and merged['end_at'] <= merged['start_at']:
            raise HTTPException(422, '종료 시각은 시작 시각보다 늦어야 합니다.')
        data = values(PlanCreate.model_validate(merged))
        assignments = ', '.join(f'{field} = ?' for field in changes)
        conn.execute(f'UPDATE plans SET {assignments}, updated_at = ? WHERE id = ?',
                     (*(data[field] for field in changes), datetime.now(KST).isoformat(timespec='microseconds'), plan_id))
        return get_row(conn, plan_id)


@router.delete('/{plan_id}', status_code=204)
def delete_plan(plan_id: int, db: DB) -> Response:
    with db.connection(write=True) as conn:
        if not conn.execute('DELETE FROM plans WHERE id = ?', (plan_id,)).rowcount:
            raise HTTPException(404, '계획을 찾을 수 없습니다.')
    return Response(status_code=204)
