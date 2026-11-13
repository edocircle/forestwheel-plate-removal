"""SQLite account database, session token management, security audit log, and Google OAuth 2.0 verifier."""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PBKDF2_ITERATIONS = 200_000
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
SESSION_TTL_DAYS = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(dt: datetime | None = None) -> str:
    return (dt or _utc_now()).isoformat()


def hash_password_pbkdf2(password: str, salt_hex: str) -> str:
    """Compute 200,000-iteration PBKDF2-HMAC-SHA256 hex digest."""
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    ).hex()


def hash_session_token(raw_token: str) -> str:
    """Hash a raw session token with SHA-256 so raw tokens are never stored in the database."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class AccountDatabase:
    """Comprehensive SQLite database for user accounts, Google OAuth links, sessions, and audit logs."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL DEFAULT '',
                    password_salt TEXT NOT NULL DEFAULT '',
                    google_sub TEXT UNIQUE,
                    google_email TEXT NOT NULL DEFAULT '',
                    google_name TEXT NOT NULL DEFAULT '',
                    google_picture TEXT NOT NULL DEFAULT '',
                    auth_provider TEXT NOT NULL DEFAULT 'email',
                    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
                    locked_until TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_login_at TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS user_sessions (
                    token_hash TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    ip_address TEXT NOT NULL DEFAULT '',
                    user_agent TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    last_active_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS security_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    email TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL,
                    ip_address TEXT NOT NULL DEFAULT '',
                    detail TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS oauth_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    google_client_id TEXT NOT NULL DEFAULT '',
                    google_client_secret TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT ''
                );
                """
            )

    def log_event(
        self,
        event_type: str,
        email: str = "",
        user_id: int | None = None,
        ip_address: str = "",
        detail: str = "",
    ) -> None:
        """Record an immutable security event in security_audit_log."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO security_audit_log (user_id, email, event_type, ip_address, detail, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, email.lower().strip(), event_type, ip_address, detail, _utc_iso()),
            )

    def get_oauth_config(self, env_client_id: str = "", env_client_secret: str = "") -> dict[str, Any]:
        """Return configured Google OAuth 2.0 Client ID and Secret status (DB overrides or env fallback)."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM oauth_settings WHERE id = 1").fetchone()
        db_cid = str(row["google_client_id"]).strip() if row else ""
        db_sec = str(row["google_client_secret"]).strip() if row else ""
        client_id = db_cid or env_client_id.strip()
        client_secret = db_sec or env_client_secret.strip()
        return {
            "google_client_id": client_id,
            "has_client_secret": bool(client_secret),
            "google_client_secret": client_secret,
            "is_configured": bool(client_id),
        }

    def save_oauth_config(self, google_client_id: str, google_client_secret: str = "") -> dict[str, Any]:
        """Persist Google OAuth 2.0 Client ID and optional Client Secret in SQLite."""
        cid = google_client_id.strip()
        sec = google_client_secret.strip()
        now = _utc_iso()
        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM oauth_settings WHERE id = 1").fetchone()
            if existing and not sec:
                sec = str(existing["google_client_secret"] or "")
            conn.execute(
                """
                INSERT INTO oauth_settings (id, google_client_id, google_client_secret, updated_at)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    google_client_id = excluded.google_client_id,
                    google_client_secret = excluded.google_client_secret,
                    updated_at = excluded.updated_at
                """,
                (cid, sec, now),
            )
        return self.get_oauth_config()

    def count_users(self) -> int:
        """Return total number of registered accounts in SQLite."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM users").fetchone()
            return int(row["cnt"]) if row else 0

    def get_user_by_id(self, user_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        norm = email.strip().lower()
        if not norm:
            return None
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE email = ? OR google_email = ?",
                (norm, norm),
            ).fetchone()
            return dict(row) if row else None

    def register_email_user(
        self,
        email: str,
        password: str,
        ip_address: str = "",
    ) -> dict[str, Any]:
        """Register a new user account with email and PBKDF2-HMAC-SHA256 hashed password."""
        norm_email = email.strip().lower()
        if not norm_email or "@" not in norm_email or "." not in norm_email.split("@")[-1]:
            raise ValueError("Please enter a valid email address.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        existing = self.get_user_by_email(norm_email)
        if existing and existing.get("password_hash"):
            raise ValueError("An account with this email already exists. Please sign in.")

        salt_hex = secrets.token_hex(16)
        pw_hash = hash_password_pbkdf2(password, salt_hex)
        now = _utc_iso()

        with self._connect() as conn:
            if existing:
                # Account was previously created via Google OAuth; attach password and set provider='both'
                conn.execute(
                    """
                    UPDATE users
                    SET password_hash = ?, password_salt = ?, auth_provider = 'both',
                        updated_at = ?, last_login_at = ?
                    WHERE id = ?
                    """,
                    (pw_hash, salt_hex, now, now, existing["id"]),
                )
                user_id = int(existing["id"])
            else:
                cur = conn.execute(
                    """
                    INSERT INTO users (
                        email, password_hash, password_salt, auth_provider,
                        created_at, updated_at, last_login_at
                    ) VALUES (?, ?, ?, 'email', ?, ?, ?)
                    """,
                    (norm_email, pw_hash, salt_hex, now, now, now),
                )
                user_id = int(cur.lastrowid)

        self.log_event("register", email=norm_email, user_id=user_id, ip_address=ip_address, detail="Email account registered")
        user = self.get_user_by_id(user_id)
        assert user is not None
        return user

    def authenticate_email_user(
        self,
        email: str,
        password: str,
        ip_address: str = "",
    ) -> dict[str, Any]:
        """Authenticate an email + password login with brute-force lockout protection."""
        norm_email = email.strip().lower()
        user = self.get_user_by_email(norm_email)
        if not user:
            self.log_event("login_failed", email=norm_email, ip_address=ip_address, detail="Account not found")
            raise ValueError("No account found for this email. Please create an account first.")

        user_id = int(user["id"])
        locked_until = str(user.get("locked_until") or "")
        if locked_until:
            try:
                lock_dt = datetime.fromisoformat(locked_until)
                if lock_dt > _utc_now():
                    mins = max(1, int((lock_dt - _utc_now()).total_seconds() // 60) + 1)
                    raise ValueError(f"Account temporarily locked due to failed attempts. Try again in {mins} min.")
            except ValueError as exc:
                if "temporarily locked" in str(exc):
                    raise

        pw_hash = str(user.get("password_hash") or "")
        pw_salt = str(user.get("password_salt") or "")
        if not pw_hash or not pw_salt:
            self.log_event("login_failed", email=norm_email, user_id=user_id, ip_address=ip_address, detail="Google-only account")
            raise ValueError("This account uses Google Sign-In. Please click Continue with Google.")

        cand_hash = hash_password_pbkdf2(password, pw_salt)
        if not secrets.compare_digest(cand_hash.encode("utf-8"), pw_hash.encode("utf-8")):
            attempts = int(user.get("failed_login_attempts") or 0) + 1
            new_lock = ""
            if attempts >= MAX_FAILED_ATTEMPTS:
                new_lock = _utc_iso(_utc_now() + timedelta(minutes=LOCKOUT_MINUTES))
            with self._connect() as conn:
                conn.execute(
                    "UPDATE users SET failed_login_attempts = ?, locked_until = ?, updated_at = ? WHERE id = ?",
                    (attempts, new_lock, _utc_iso(), user_id),
                )
            self.log_event(
                "login_failed",
                email=norm_email,
                user_id=user_id,
                ip_address=ip_address,
                detail=f"Invalid password (attempt {attempts})",
            )
            raise ValueError("Invalid email or password.")

        now = _utc_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET failed_login_attempts = 0, locked_until = '', last_login_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, user_id),
            )
        self.log_event("login_success", email=norm_email, user_id=user_id, ip_address=ip_address, detail="Password login")
        updated = self.get_user_by_id(user_id)
        assert updated is not None
        return updated

    def authenticate_or_link_google_user(
        self,
        google_sub: str,
        google_email: str,
        google_name: str = "",
        google_picture: str = "",
        link_to_user_id: int | None = None,
        ip_address: str = "",
    ) -> dict[str, Any]:
        """Sign in, register, or link an existing user account with a verified Google identity."""
        norm_email = google_email.strip().lower()
        sub = google_sub.strip()
        if not norm_email or "@" not in norm_email or not sub:
            raise ValueError("Verified Google email and subject ID are required.")

        now = _utc_iso()
        with self._connect() as conn:
            # 1. If linking to an currently signed-in account:
            if link_to_user_id is not None:
                target = conn.execute("SELECT * FROM users WHERE id = ?", (link_to_user_id,)).fetchone()
                if not target:
                    raise ValueError("Signed-in user account not found.")
                conflict = conn.execute(
                    "SELECT id FROM users WHERE google_sub = ? AND id != ?",
                    (sub, link_to_user_id),
                ).fetchone()
                if conflict:
                    raise ValueError("This Google account is already linked to another user.")
                has_pw = bool(target["password_hash"] and target["password_salt"])
                provider = "both" if has_pw else "google"
                conn.execute(
                    """
                    UPDATE users
                    SET google_sub = ?, google_email = ?, google_name = ?, google_picture = ?,
                        auth_provider = ?, updated_at = ?, last_login_at = ?
                    WHERE id = ?
                    """,
                    (sub, norm_email, google_name, google_picture, provider, now, now, link_to_user_id),
                )
                user_id = int(link_to_user_id)
                event_type = "google_account_linked"
            else:
                # 2. Check by google_sub first, then by email
                row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (sub,)).fetchone()
                if not row:
                    row = conn.execute(
                        "SELECT * FROM users WHERE email = ? OR google_email = ?",
                        (norm_email, norm_email),
                    ).fetchone()
                if row:
                    user_id = int(row["id"])
                    has_pw = bool(row["password_hash"] and row["password_salt"])
                    provider = "both" if has_pw else "google"
                    conn.execute(
                        """
                        UPDATE users
                        SET google_sub = ?, google_email = ?, google_name = ?, google_picture = ?,
                            auth_provider = ?, failed_login_attempts = 0, locked_until = '',
                            updated_at = ?, last_login_at = ?
                        WHERE id = ?
                        """,
                        (sub, norm_email, google_name, google_picture, provider, now, now, user_id),
                    )
                    event_type = "google_oauth_login"
                else:
                    cur = conn.execute(
                        """
                        INSERT INTO users (
                            email, google_sub, google_email, google_name, google_picture,
                            auth_provider, created_at, updated_at, last_login_at
                        ) VALUES (?, ?, ?, ?, ?, 'google', ?, ?, ?)
                        """,
                        (norm_email, sub, norm_email, google_name, google_picture, now, now, now),
                    )
                    user_id = int(cur.lastrowid)
                    event_type = "google_oauth_register"

        self.log_event(
            event_type,
            email=norm_email,
            user_id=user_id,
            ip_address=ip_address,
            detail=f"Google account ({norm_email}) verified",
        )
        user = self.get_user_by_id(user_id)
        assert user is not None
        return user

    def unlink_google_account(self, user_id: int, ip_address: str = "") -> dict[str, Any]:
        """Unlink Google account from a user (requires user to have a password set so they aren't locked out)."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("Account not found.")
        if not (user.get("password_hash") and user.get("password_salt")):
            raise ValueError("Please set an account password first before unlinking Google Sign-In.")
        now = _utc_iso()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET google_sub = NULL, google_email = '', google_name = '', google_picture = '',
                    auth_provider = 'email', updated_at = ?
                WHERE id = ?
                """,
                (now, user_id),
            )
        self.log_event("google_account_unlinked", email=user["email"], user_id=user_id, ip_address=ip_address)
        updated = self.get_user_by_id(user_id)
        assert updated is not None
        return updated

    def change_user_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
        confirm_password: str,
        ip_address: str = "",
    ) -> dict[str, Any]:
        """Verify current password (unless setting initial password on a Google-only account) and update PBKDF2 hash."""
        user = self.get_user_by_id(user_id)
        if not user:
            raise ValueError("User account not found.")

        has_existing_pw = bool(user.get("password_hash") and user.get("password_salt"))
        if has_existing_pw:
            if not current_password:
                raise ValueError("Current password is incorrect.")
            cand_hash = hash_password_pbkdf2(current_password, str(user["password_salt"]))
            if not secrets.compare_digest(cand_hash.encode("utf-8"), str(user["password_hash"]).encode("utf-8")):
                self.log_event(
                    "password_change_failed",
                    email=user["email"],
                    user_id=user_id,
                    ip_address=ip_address,
                    detail="Incorrect current password",
                )
                raise ValueError("Current password is incorrect.")

        if len(new_password) < 4:
            raise ValueError("New password must be at least 4 characters.")
        if new_password != confirm_password:
            raise ValueError("New password and confirmation do not match.")

        salt_hex = secrets.token_hex(16)
        pw_hash = hash_password_pbkdf2(new_password, salt_hex)
        provider = "both" if user.get("google_sub") else "email"
        now = _utc_iso()

        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET password_hash = ?, password_salt = ?, auth_provider = ?, updated_at = ?
                WHERE id = ?
                """,
                (pw_hash, salt_hex, provider, now, user_id),
            )
        self.log_event("password_changed", email=user["email"], user_id=user_id, ip_address=ip_address)
        updated = self.get_user_by_id(user_id)
        assert updated is not None
        return updated

    def create_session(
        self,
        user_id: int,
        ip_address: str = "",
        user_agent: str = "",
    ) -> str:
        """Create a cryptographically random 256-bit session token and store its SHA-256 hash in SQLite."""
        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_session_token(raw_token)
        now = _utc_now()
        expires = now + timedelta(days=SESSION_TTL_DAYS)
        with self._connect() as conn:
            # Clean up expired sessions
            conn.execute("DELETE FROM user_sessions WHERE expires_at < ?", (_utc_iso(now),))
            conn.execute(
                """
                INSERT INTO user_sessions (token_hash, user_id, ip_address, user_agent, created_at, expires_at, last_active_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    token_hash,
                    user_id,
                    ip_address[:120],
                    user_agent[:250],
                    _utc_iso(now),
                    _utc_iso(expires),
                    _utc_iso(now),
                ),
            )
        return raw_token

    def get_user_by_session_token(self, raw_token: str | None) -> dict[str, Any] | None:
        """Validate a raw session token from cookie/header against user_sessions and return the user dict."""
        if not raw_token:
            return None
        token_hash = hash_session_token(raw_token)
        now_iso = _utc_iso()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT s.token_hash, s.expires_at, u.*
                FROM user_sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.token_hash = ?
                """,
                (token_hash,),
            ).fetchone()
            if not row:
                return None
            if str(row["expires_at"]) < now_iso:
                conn.execute("DELETE FROM user_sessions WHERE token_hash = ?", (token_hash,))
                return None
            conn.execute(
                "UPDATE user_sessions SET last_active_at = ? WHERE token_hash = ?",
                (now_iso, token_hash),
            )
            return dict(row)

    def revoke_session(self, raw_token: str | None, ip_address: str = "") -> None:
        """Delete a single session token on sign-out."""
        if not raw_token:
            return
        token_hash = hash_session_token(raw_token)
        user = self.get_user_by_session_token(raw_token)
        with self._connect() as conn:
            conn.execute("DELETE FROM user_sessions WHERE token_hash = ?", (token_hash,))
        if user:
            self.log_event("logout", email=user["email"], user_id=int(user["id"]), ip_address=ip_address)

    def revoke_other_sessions(self, user_id: int, keep_raw_token: str | None, ip_address: str = "") -> int:
        """Revoke all active sessions for user_id except keep_raw_token."""
        keep_hash = hash_session_token(keep_raw_token) if keep_raw_token else ""
        with self._connect() as conn:
            cur = conn.execute(
                "DELETE FROM user_sessions WHERE user_id = ? AND token_hash != ?",
                (user_id, keep_hash),
            )
            deleted = int(cur.rowcount or 0)
        user = self.get_user_by_id(user_id)
        if user:
            self.log_event(
                "sessions_revoked",
                email=user["email"],
                user_id=user_id,
                ip_address=ip_address,
                detail=f"Revoked {deleted} other session(s)",
            )
        return deleted

    def list_user_sessions(self, user_id: int, current_raw_token: str | None = None) -> list[dict[str, Any]]:
        """List active sessions for user_id."""
        cur_hash = hash_session_token(current_raw_token) if current_raw_token else ""
        now_iso = _utc_iso()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT token_hash, ip_address, user_agent, created_at, last_active_at, expires_at
                FROM user_sessions
                WHERE user_id = ? AND expires_at >= ?
                ORDER BY last_active_at DESC
                """,
                (user_id, now_iso),
            ).fetchall()
        return [
            {
                "id_prefix": str(r["token_hash"])[:10],
                "ip_address": str(r["ip_address"] or "127.0.0.1"),
                "user_agent": str(r["user_agent"] or "Browser Session"),
                "created_at": str(r["created_at"]),
                "last_active_at": str(r["last_active_at"]),
                "is_current": str(r["token_hash"]) == cur_hash,
            }
            for r in rows
        ]

    def list_audit_logs(self, user_id: int, limit: int = 15) -> list[dict[str, Any]]:
        """Return recent security audit log events for user_id."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_type, email, ip_address, detail, created_at
                FROM security_audit_log
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]


def verify_google_id_token(id_token: str, expected_client_id: str = "") -> dict[str, str]:
    """Cryptographically verify a Google ID token via Google's tokeninfo endpoint."""
    url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ValueError("Google ID token verification failed or token expired.") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Could not reach Google OAuth verification server: {exc}") from exc

    if expected_client_id and data.get("aud") != expected_client_id:
        raise ValueError("Google ID token audience does not match configured Google Client ID.")
    if str(data.get("email_verified")).lower() != "true":
        raise ValueError("Google email address is not verified.")

    sub = str(data.get("sub") or "").strip()
    email = str(data.get("email") or "").strip().lower()
    if not sub or not email:
        raise ValueError("Google token did not contain a valid email and subject ID.")

    return {
        "sub": sub,
        "email": email,
        "name": str(data.get("name") or email.split("@")[0]),
        "picture": str(data.get("picture") or ""),
    }


def exchange_google_oauth_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, str]:
    """Exchange an OAuth 2.0 authorization code at Google's token endpoint and fetch verified userinfo."""
    token_data = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    token_req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(token_req, timeout=10) as resp:  # noqa: S310
            tok_json = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        raise ValueError(f"Google OAuth token exchange failed: {err_body}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Could not connect to Google token endpoint: {exc}") from exc

    access_token = str(tok_json.get("access_token") or "")
    id_token = str(tok_json.get("id_token") or "")

    if access_token:
        info_req = urllib.request.Request(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        try:
            with urllib.request.urlopen(info_req, timeout=10) as resp:  # noqa: S310
                uinfo = json.loads(resp.read().decode("utf-8"))
            sub = str(uinfo.get("sub") or "").strip()
            email = str(uinfo.get("email") or "").strip().lower()
            if sub and email:
                return {
                    "sub": sub,
                    "email": email,
                    "name": str(uinfo.get("name") or email.split("@")[0]),
                    "picture": str(uinfo.get("picture") or ""),
                }
        except Exception:  # noqa: BLE001
            pass

    if id_token:
        return verify_google_id_token(id_token, expected_client_id=client_id)

    raise ValueError("Google OAuth response did not include valid user identity.")
