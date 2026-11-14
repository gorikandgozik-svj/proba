"""Server-side reference quota policy. No hosted service or free GPU is attached.

Only a trusted server may supply authenticated user identities and developer role.
Never allow a desktop client to set its own role.
"""
from datetime import date
from pathlib import Path
import sqlite3
import threading


class QuotaExceeded(Exception):
    pass


class QuotaLedger:
    """Transactional daily quota ledger for an eventual authenticated server."""

    def __init__(self, database: Path | str, limit: int = 5):
        if limit < 1:
            raise ValueError('limit must be positive')
        self.limit = limit
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(database), timeout=20, isolation_level=None, check_same_thread=False)
        self._conn.execute('PRAGMA journal_mode=WAL')
        self._conn.execute('''CREATE TABLE IF NOT EXISTS reservations (
            user_id TEXT NOT NULL, day TEXT NOT NULL, request_key TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN ('reserved','done','failed')),
            PRIMARY KEY(user_id,request_key))''')

    def reserve(self, *, user_id: str, role_from_server: str, request_key: str,
                today: date | None = None) -> str:
        """Idempotent reservation. role_from_server MUST be server-verified."""
        if not user_id or not request_key or len(user_id) > 200 or len(request_key) > 200:
            raise ValueError('invalid identifier')
        if role_from_server not in ('user', 'developer'):
            raise ValueError('unverified role')
        day = (today or date.today()).isoformat()
        with self._lock:
            self._conn.execute('BEGIN IMMEDIATE')
            try:
                old = self._conn.execute('SELECT state FROM reservations WHERE user_id=? AND request_key=?',
                                         (user_id, request_key)).fetchone()
                if old:
                    self._conn.execute('COMMIT')
                    return old[0]
                if role_from_server != 'developer':
                    used = self._conn.execute('''SELECT count(*) FROM reservations
                        WHERE user_id=? AND day=? AND state IN ('reserved','done')''',
                        (user_id, day)).fetchone()[0]
                    if used >= self.limit:
                        raise QuotaExceeded(f'Free daily quota exceeded: {self.limit}')
                self._conn.execute('INSERT INTO reservations VALUES(?,?,?,?)',
                                   (user_id, day, request_key, 'reserved'))
                self._conn.execute('COMMIT')
                return 'reserved'
            except BaseException:
                self._conn.execute('ROLLBACK')
                raise

    def finish(self, user_id: str, request_key: str, succeeded: bool):
        with self._lock:
            result = self._conn.execute('''UPDATE reservations SET state=? WHERE user_id=? AND request_key=?
                AND state='reserved' ''', ('done' if succeeded else 'failed', user_id, request_key))
            if result.rowcount != 1:
                raise KeyError('reservation not active')

    def used(self, user_id: str, today: date | None = None) -> int:
        day = (today or date.today()).isoformat()
        return self._conn.execute('''SELECT count(*) FROM reservations WHERE user_id=?
            AND day=? AND state IN ('reserved','done')''', (user_id, day)).fetchone()[0]

    def close(self):
        self._conn.close()
