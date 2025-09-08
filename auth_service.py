import json
import hashlib
import time
import os
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash


class AuthManager:
    def __init__(self, config_file: str = "auth_config.json"):
        self.config_file = config_file
        self.sessions = {}
        self.login_attempts = {}
        self.lockouts = {}

        self.ph = PasswordHasher()
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    self.config = json.load(f)
            except:
                self.create_default_config()
        else:
            self.create_default_config()

    def create_default_config(self):
        self.config = {
            "username": "admin",
            "password_hash": self.hash_password("admin123"),
            "session_timeout": 3600,
            "max_login_attempts": 3,
            "lockout_duration": 300,
        }
        self.save_config()

    def save_config(self):
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=4)

        try:
            if os.name == "posix":
                os.chmod(self.config_file, 0o600)
        except Exception:
            pass

    def hash_password(self, password: str) -> str:
        return self.ph.hash(password)

    def verify_password(self, password: str) -> bool:
        stored = self.config.get("password_hash", "")
        if not stored.startswith("$argon2"):
            return False
        try:
            if self.ph.verify(stored, password):

                if self.ph.check_needs_rehash(stored):
                    self.config["password_hash"] = self.hash_password(password)
                    self.save_config()
                return True
        except (VerifyMismatchError, InvalidHash):
            return False
        return False

    def is_ip_locked(self, ip: str) -> bool:
        if ip not in self.lockouts:
            return False

        lockout_time = self.lockouts[ip]
        if time.time() - lockout_time > self.config["lockout_duration"]:
            del self.lockouts[ip]
            return False

        return True

    def record_failed_attempt(self, ip: str):
        if ip not in self.login_attempts:
            self.login_attempts[ip] = 0

        self.login_attempts[ip] += 1

        if self.login_attempts[ip] >= self.config["max_login_attempts"]:
            self.lockouts[ip] = time.time()
            self.login_attempts[ip] = 0

    def record_successful_login(self, ip: str):
        if ip in self.login_attempts:
            del self.login_attempts[ip]
        if ip in self.lockouts:
            del self.lockouts[ip]

    def create_session(self, username: str, ip: str) -> str:

        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "username": username,
            "ip": ip,
            "created_at": time.time(),
            "last_activity": time.time(),
        }
        return session_id

    def validate_session(self, session_id: str) -> bool:
        if session_id not in self.sessions:
            return False

        session = self.sessions[session_id]
        current_time = time.time()

        if current_time - session["created_at"] > self.config["session_timeout"]:
            del self.sessions[session_id]
            return False

        session["last_activity"] = current_time
        return True

    def get_session_user(self, session_id: str) -> Optional[str]:
        if self.validate_session(session_id):
            return self.sessions[session_id]["username"]
        return None

    def logout(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]

    def change_password(self, old_password: str, new_password: str) -> bool:
        if self.verify_password(old_password):

            self.config["password_hash"] = self.hash_password(new_password)
            self.save_config()
            return True
        return False

    def change_username(self, password: str, new_username: str) -> bool:
        if self.verify_password(password):

            normalized = self.normalize_username(new_username)
            if not self.is_valid_username(normalized):
                return False
            self.config["username"] = normalized
            self.save_config()
            return True
        return False

    def get_config(self) -> Dict[str, Any]:
        return {
            "username": self.config["username"],
            "session_timeout": self.config["session_timeout"],
            "max_login_attempts": self.config["max_login_attempts"],
            "lockout_duration": self.config["lockout_duration"],
        }

    def normalize_username(self, username: str) -> str:

        return (username or "").strip()

    def is_valid_username(self, username: str) -> bool:

        try:
            import re

            if not (3 <= len(username) <= 32):
                return False
            return bool(re.fullmatch(r"[A-Za-z0-9._-]+", username))
        except Exception:
            return False

    def cleanup_expired_sessions(self):
        current_time = time.time()
        expired_sessions = []

        for session_id, session in self.sessions.items():
            if current_time - session["created_at"] > self.config["session_timeout"]:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            del self.sessions[session_id]


auth_manager = AuthManager()
