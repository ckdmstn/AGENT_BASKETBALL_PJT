from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
import json
from threading import RLock

from backend.agent.state import Conditions
from backend.config import KST
from backend.database import Database


def restrict(item, checked):
    previous = item.get('permissions', {})
    restricted = {'team': bool(previous.get('team') and checked.get('team')),
                  'date_ranges': [d for d in previous.get('date_ranges', []) if d in checked.get('date_ranges', [])]}
    item['permissions'] = deepcopy(restricted)
    item['conditions']['fallback_teams_allowed'] = restricted['team']
    item['conditions']['alternative_date_ranges'] = deepcopy(restricted['date_ranges'])


class MemorySessions:
    """Process-local bounded summaries, no raw API responses or chat transcripts."""
    def __init__(self, capacity=200):
        self._items = OrderedDict()
        self.capacity = capacity
        # Serializes a complete request to prevent lost updates for a session.
        self.lock = RLock()

    def load(self, session_id):
        with self.lock:
            return deepcopy(self._items.get(session_id))

    def restrict_permissions(self, session_id, checked: dict):
        """Persist only revocations before fallible LLM work; never grant new rights."""
        with self.lock:
            item = self._items.get(session_id)
            if item is None:
                return
            restrict(item, checked)

    def save(self, session_id, conditions: Conditions, summary: str, permissions: dict | None = None):
        with self.lock:
            self._items[session_id] = {'conditions': conditions.model_dump(mode='json'), 'summary': summary[:1000],
                                       'permissions': deepcopy(permissions or {})}
            self._items.move_to_end(session_id)
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)


class SQLiteSessions:
    """Persist session summaries while the runner serializes turns within one process."""

    def __init__(self, db: Database):
        self.db = db
        self.lock = RLock()

    def load(self, session_id):
        with self.lock, self.db.connection() as conn:
            row = conn.execute('SELECT conditions, summary, permissions FROM sessions WHERE session_id = ?',
                               (session_id,)).fetchone()
        if row is None:
            return None
        return {'conditions': json.loads(row['conditions']), 'summary': row['summary'],
                'permissions': json.loads(row['permissions'])}

    def restrict_permissions(self, session_id, checked):
        # Commit revocations before any fallible analysis or planning call.
        with self.lock, self.db.connection(write=True) as conn:
            row = conn.execute('SELECT conditions, permissions FROM sessions WHERE session_id = ?',
                               (session_id,)).fetchone()
            if row is not None:
                item = {field: json.loads(row[field]) for field in ('conditions', 'permissions')}
                restrict(item, checked)
                conn.execute('UPDATE sessions SET conditions = ?, permissions = ?, updated_at = ? WHERE session_id = ?',
                             (json.dumps(item['conditions']), json.dumps(item['permissions']),
                              datetime.now(KST).isoformat(), session_id))

    def save(self, session_id, conditions: Conditions, summary: str, permissions: dict | None = None):
        with self.lock, self.db.connection(write=True) as conn:
            conn.execute(
                '''INSERT INTO sessions (session_id, conditions, summary, permissions, updated_at)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET conditions = excluded.conditions,
                   summary = excluded.summary, permissions = excluded.permissions, updated_at = excluded.updated_at''',
                (session_id, conditions.model_dump_json(), summary[:1000], json.dumps(permissions or {}),
                 datetime.now(KST).isoformat()),
            )
