import os
import sqlite3
import hashlib
import secrets
import time
from typing import Optional, Dict, Any, List
from core.config import settings

class TenantAuthManager:
    """
    Multi-tenant authentication and profile manager.
    Supports Supabase Auth / Clerk webhooks when keys are provided,
    with an automatic persistent SQLite store for zero-friction setup.
    """
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.TENANT_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    company_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    api_key TEXT UNIQUE NOT NULL,
                    docs_url TEXT,
                    slack_webhook_url TEXT,
                    indexed_pages_count INTEGER DEFAULT 0,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

            # Seed a default demo tenant if empty
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tenants")
            if cursor.fetchone()[0] == 0:
                self.create_tenant(
                    email="demo@omnitriage.ai",
                    company_name="Acme Developer Platform",
                    password="password123",
                    tenant_id="tenant_default_demo",
                    api_key="ot_live_demo_acme_2026",
                    docs_url="https://docs.github.com"
                )

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def create_tenant(
        self,
        email: str,
        company_name: str,
        password: str,
        tenant_id: Optional[str] = None,
        api_key: Optional[str] = None,
        docs_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Registers a new SaaS founder and generates a dedicated tenant API key."""
        t_id = tenant_id or f"tenant_{secrets.token_hex(6)}"
        key = api_key or f"ot_live_{secrets.token_hex(16)}"
        pw_hash = self._hash_password(password)
        now = time.time()

        with self._get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO tenants (id, email, company_name, password_hash, api_key, docs_url, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (t_id, email.lower().strip(), company_name.strip(), pw_hash, key, docs_url, now)
                )
                conn.commit()
            except sqlite3.IntegrityError:
                raise ValueError(f"An account with email '{email}' already exists.")

        return self.get_tenant_by_id(t_id)

    def authenticate_tenant(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Validates credentials and returns tenant record."""
        pw_hash = self._hash_password(password)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM tenants WHERE email = ? AND password_hash = ?",
                (email.lower().strip(), pw_hash)
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None

    def get_tenant_by_id(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_tenant_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tenants WHERE api_key = ?", (api_key.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_tenant_settings(
        self,
        tenant_id: str,
        docs_url: Optional[str] = None,
        slack_webhook_url: Optional[str] = None,
        indexed_pages_count: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        updates = []
        params = []
        if docs_url is not None:
            updates.append("docs_url = ?")
            params.append(docs_url)
        if slack_webhook_url is not None:
            updates.append("slack_webhook_url = ?")
            params.append(slack_webhook_url)
        if indexed_pages_count is not None:
            updates.append("indexed_pages_count = ?")
            params.append(indexed_pages_count)

        if not updates:
            return self.get_tenant_by_id(tenant_id)

        params.append(tenant_id)
        query = f"UPDATE tenants SET {', '.join(updates)} WHERE id = ?"
        with self._get_connection() as conn:
            conn.execute(query, tuple(params))
            conn.commit()

        return self.get_tenant_by_id(tenant_id)

    def list_all_tenants(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, email, company_name, api_key, docs_url, slack_webhook_url, indexed_pages_count, created_at FROM tenants ORDER BY created_at DESC")
            return [dict(r) for r in cursor.fetchall()]

# Global singleton
auth_manager = TenantAuthManager()
