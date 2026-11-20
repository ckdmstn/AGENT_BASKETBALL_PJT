from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints, computed_field, field_validator, model_validator

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
        try:
            return value.astimezone(KST) if value is not None else None
        except OverflowError:
            raise ValueError('한국 표준시로 변환할 수 있는 날짜와 시각을 입력하세요.') from None


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

    @computed_field
    @property
    def game_date(self) -> date:
        return self.start_at.date()


class PlanSaved(BaseModel):
    plan: Plan
    overlapping_plan_ids: list[int]
    overlap_warnings: list[str]


router = APIRouter(prefix='/api/plans', tags=['plans'])
DB = Annotated[Database, Depends(get_database)]
PlanID = Annotated[int, Path(ge=1, le=2**63 - 1)]
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


def overlap_result(conn, plan: Plan) -> PlanSaved:
    times = values(plan)
    # Stored timestamps share a fixed KST format. An open-ended plan contributes only its start instant.
    matches = conn.execute(
        '''SELECT id, reason FROM (
               SELECT id, CASE
                   WHEN match_id = :match_id THEN 'same_game'
                   WHEN start_at = :start_at THEN 'same_start'
                   WHEN start_at < COALESCE(:end_at, :start_at)
                        AND COALESCE(end_at, start_at) > :start_at THEN 'time_range'
               END AS reason
               FROM plans WHERE id != :id
           ) WHERE reason IS NOT NULL ORDER BY id''',
        {'id': plan.id, 'match_id': plan.match_id, 'start_at': times['start_at'], 'end_at': times['end_at']},
    ).fetchall()
    reasons = {row['reason'] for row in matches}
    warnings = {
        'same_game': '이미 저장한 경기입니다.',
        'same_start': '같은 시각에 시작하는 다른 경기 일정이 있습니다.',
        'time_range': '기존 일정의 시간 범위와 겹칠 수 있습니다.',
    }
    return PlanSaved(plan=plan, overlapping_plan_ids=[row['id'] for row in matches],
                     overlap_warnings=[warning for reason, warning in warnings.items() if reason in reasons])


def ensure_match_available(conn, match_id: str):
    if conn.execute('SELECT 1 FROM plans WHERE match_id = ? LIMIT 1', (match_id,)).fetchone():
        raise HTTPException(409, '이미 저장한 경기입니다. 저장한 계획에서 확인하거나 수정해 주세요.')


@router.post('', status_code=201, responses={409: {'description': '이미 저장한 경기'}})
def create_plan(request: PlanCreate, db: DB) -> PlanSaved:
    now = datetime.now(KST).isoformat(timespec='microseconds')
    data = values(request)
    with db.connection(write=True) as conn:
        ensure_match_available(conn, request.match_id)
        columns = ', '.join(PLAN_COLUMNS)
        placeholders = ', '.join('?' for _ in PLAN_COLUMNS)
        cursor = conn.execute(
            f'INSERT INTO plans ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?)',
            (*data.values(), now, now),
        )
        return overlap_result(conn, get_row(conn, cursor.lastrowid))


@router.get('')
def list_plans(db: DB) -> list[Plan]:
    with db.connection() as conn:
        return [Plan.model_validate(dict(row)) for row in conn.execute('SELECT * FROM plans ORDER BY start_at, id')]


@router.get('/{plan_id}')
def read_plan(plan_id: PlanID, db: DB) -> Plan:
    with db.connection() as conn:
        return get_row(conn, plan_id)


@router.patch('/{plan_id}', responses={409: {'description': '이미 저장한 경기'}})
def patch_plan(plan_id: PlanID, request: PlanPatch, db: DB) -> PlanSaved:
    with db.connection(write=True) as conn:
        current = get_row(conn, plan_id).model_dump(include=set(PLAN_COLUMNS))
        changes = request.model_dump(exclude_unset=True)
        merged = {**current, **changes}
        if merged['match_id'] != current['match_id']:
            ensure_match_available(conn, merged['match_id'])
        if merged['end_at'] is not None and merged['end_at'] <= merged['start_at']:
            raise HTTPException(422, '종료 시각은 시작 시각보다 늦어야 합니다.')
        data = values(PlanCreate.model_validate(merged))
        assignments = ', '.join(f'{field} = ?' for field in changes)
        conn.execute(f'UPDATE plans SET {assignments}, updated_at = ? WHERE id = ?',
                     (*(data[field] for field in changes), datetime.now(KST).isoformat(timespec='microseconds'), plan_id))
        return overlap_result(conn, get_row(conn, plan_id))


@router.delete('/{plan_id}', status_code=204)
def delete_plan(plan_id: PlanID, db: DB) -> Response:
    with db.connection(write=True) as conn:
        if not conn.execute('DELETE FROM plans WHERE id = ?', (plan_id,)).rowcount:
            raise HTTPException(404, '계획을 찾을 수 없습니다.')
    return Response(status_code=204)
