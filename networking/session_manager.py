import json
import logging
import os
import time
from typing import Dict

logger = logging.getLogger("SessionManager")

class SessionManager:
    def __init__(self, storage_path: str = "sessions.json", session_ttl_days: int = 7):
        self.storage_path = storage_path
        self.session_ttl = session_ttl_days * 86400 # Convert days to seconds
        # Structure: { client_id: {"secret": str, "last_seen": float} }
        self.sessions: Dict[str, dict] = self._load_sessions()

    def _load_sessions(self) -> dict:
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load sessions: {e}")
        return {}

    def save_sessions(self):
        try:
            with open(self.storage_path+".tmp", "w") as f:
                json.dump(self.sessions, f, indent=4)
                os.replace(self.storage_path+".tmp", self.storage_path) #Writing becomes atomic
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def validate_session(self, client_id: str, secret: str) -> bool:
        session = self.sessions.get(client_id)
        if session and session["secret"] == secret:
            # Update last_seen on successful validation
            session["last_seen"] = time.time()
            return True
        return False

    def create_session(self, client_id: str, secret: str):
        self.sessions[client_id] = {
            "secret": secret,
            "last_seen": time.time()
        }
        self.save_sessions()

    def cleanup_zombies(self):
        """Removes sessions that haven't been seen in X days."""
        now = time.time()
        initial_count = len(self.sessions)
        self.sessions = {
            cid: data for cid, data in self.sessions.items()
            if (now - data["last_seen"]) < self.session_ttl
        }
        if len(self.sessions) < initial_count:
            logger.info(f"Cleaned up {initial_count - len(self.sessions)} zombie sessions.")
            self.save_sessions()