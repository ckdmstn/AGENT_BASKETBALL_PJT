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

    def save(self, session_id, conditions: Conditions, summary: str):
        with self.lock:
            self._items[session_id] = {'conditions': conditions.model_dump(mode='json'), 'summary': summary[:1000]}
            self._items.move_to_end(session_id)
            while len(self._items) > self.capacity:
                self._items.popitem(last=False)
