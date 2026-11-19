from collections import OrderedDict
from copy import deepcopy
from threading import RLock

from backend.agent.state import Conditions


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
            previous = item.get('permissions', {})
            restricted = {'team': bool(previous.get('team') and checked.get('team')),
                          'date_ranges': [d for d in previous.get('date_ranges', []) if d in checked.get('date_ranges', [])]}
            item['permissions'] = deepcopy(restricted)
            item['conditions']['fallback_teams_allowed'] = restricted['team']
            item['conditions']['alternative_date_ranges'] = deepcopy(restricted['date_ranges'])

    def save(self, session_id, conditions: Conditions, summary: str, permissions: dict | None = None):
        with self.lock:
            self._items[session_id] = {'conditions': conditions.model_dump(mode='json'), 'summary': summary[:1000],
                                       'permissions': deepcopy(permissions or {})}
            self._items.move_to_end(session_id)
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)
