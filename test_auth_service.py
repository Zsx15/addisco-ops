"""Tests unitaires — auth_service.py"""
import os
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path


def _make_temp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    return Path(tmp.name)


class AuthServiceTestCase(unittest.TestCase):

    def setUp(self):
        import database as db
        self._orig_path = db.DB_PATH
        self._tmp_path  = _make_temp_db()
        db.DB_PATH      = self._tmp_path
        db.init_db()
        self.db   = db
        import auth_service
        self.auth = auth_service

    def tearDown(self):
        import database as db
        db.DB_PATH = self._orig_path
        try:
            os.unlink(self._tmp_path)
        except OSError:
            pass

    # ── register_user ────────────────────────────────────────────────────────

    def test_register_returns_uuid(self):
        user_id = self.auth.register_user("alice", "secret123")
        self.assertIsInstance(user_id, str)
        self.assertEqual(len(user_id), 36)

    def test_register_duplicate_raises_value_error(self):
        self.auth.register_user("alice", "secret123")
        with self.assertRaises(ValueError):
            self.auth.register_user("alice", "autre_mdp")

    def test_register_custom_role(self):
        self.auth.register_user("trainer", "pass", role="formateur")
        user = self.auth.get_user_by_username("trainer")
        self.assertEqual(user["role"], "formateur")

    def test_register_default_role_apprenant(self):
        self.auth.register_user("bob", "pass")
        user = self.auth.get_user_by_username("bob")
        self.assertEqual(user["role"], "apprenant")

    # ── get_user_by_username ─────────────────────────────────────────────────

    def test_get_user_found(self):
        user_id = self.auth.register_user("bob", "pass456")
        user = self.auth.get_user_by_username("bob")
        self.assertIsNotNone(user)
        self.assertEqual(user["user_id"], user_id)
        self.assertEqual(user["username"], "bob")
        self.assertIsNotNone(user["password_hash"])

    def test_get_user_not_found(self):
        self.assertIsNone(self.auth.get_user_by_username("inconnu"))

    # ── verify_password ──────────────────────────────────────────────────────

    def test_verify_valid_credentials(self):
        self.auth.register_user("carol", "mypassword")
        result = self.auth.verify_password("carol", "mypassword")
        self.assertIsNotNone(result)
        self.assertEqual(result["username"], "carol")
        self.assertEqual(result["role"], "apprenant")

    def test_verify_wrong_password_returns_none(self):
        self.auth.register_user("dave", "correct")
        self.assertIsNone(self.auth.verify_password("dave", "wrong"))

    def test_verify_unknown_user_returns_none(self):
        self.assertIsNone(self.auth.verify_password("nobody", "anything"))

    def test_verify_null_hash_returns_none(self):
        uid = str(uuid.uuid4())
        with sqlite3.connect(str(self.db.DB_PATH)) as conn:
            conn.execute(
                "INSERT INTO users (user_id, username, password_hash, role) VALUES (?, ?, NULL, ?)",
                (uid, "nulluser", "apprenant"),
            )
        self.assertIsNone(self.auth.verify_password("nulluser", "anything"))

    def test_verify_does_not_expose_password_hash(self):
        self.auth.register_user("eve", "supersecret")
        result = self.auth.verify_password("eve", "supersecret")
        self.assertNotIn("password_hash", result)

    def test_verify_returns_user_id(self):
        expected_id = self.auth.register_user("frank", "pw")
        result = self.auth.verify_password("frank", "pw")
        self.assertEqual(result["user_id"], expected_id)

    # ── Rôles explicites (préparation admin creation TASK-050B) ──────────────

    def test_register_admin_role(self):
        """register_user(role='admin') stocke et retourne le rôle admin via verify_password."""
        user_id = self.auth.register_user("admin_user", "adminpass", role="admin")
        user = self.auth.get_user_by_username("admin_user")
        self.assertEqual(user["role"], "admin")
        result = self.auth.verify_password("admin_user", "adminpass")
        self.assertIsNotNone(result)
        self.assertEqual(result["role"], "admin")
        self.assertEqual(result["user_id"], user_id)

    def test_register_formateur_role(self):
        """register_user(role='formateur') stocke et retourne le rôle formateur via verify_password."""
        user_id = self.auth.register_user("form_user", "formpass", role="formateur")
        user = self.auth.get_user_by_username("form_user")
        self.assertEqual(user["role"], "formateur")
        result = self.auth.verify_password("form_user", "formpass")
        self.assertIsNotNone(result)
        self.assertEqual(result["role"], "formateur")
        self.assertEqual(result["user_id"], user_id)


if __name__ == "__main__":
    unittest.main()
