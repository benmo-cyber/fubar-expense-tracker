import unittest

from app.services.passwords import (
    FORGOT_MESSAGE,
    MAIL_UNAVAILABLE,
    can_send_reset,
    forgot_message,
    generate_temp_password,
    make_reset_token,
    must_change_after_issue,
    read_reset_token,
    reset_link,
    validate_new_password,
)


class PasswordRuleTests(unittest.TestCase):
    def test_temporary_password_is_ten_characters_from_the_allowed_set(self):
        password = generate_temp_password()
        self.assertEqual(len(password), 10)
        self.assertTrue(password.isalnum())
        self.assertNotIn("0", password)
        self.assertNotIn("O", password)

    def test_a_temporary_password_always_requires_a_change(self):
        self.assertTrue(must_change_after_issue("admin", "sales"))
        self.assertTrue(must_change_after_issue("admin", "admin"))

    def test_new_password_rules(self):
        self.assertEqual(validate_new_password("short", "short"), "Password must be at least 8 characters.")
        self.assertEqual(validate_new_password("longenough", "different"), "Passwords do not match.")
        self.assertEqual(
            validate_new_password("longenough", "longenough", "longenough"),
            "Pick a password different from the current one.",
        )
        self.assertIsNone(validate_new_password("longenough", "longenough", "old-pass"))

    def test_forgot_message_does_not_say_an_email_was_sent_when_mail_is_off(self):
        self.assertEqual(forgot_message(False), MAIL_UNAVAILABLE)
        self.assertEqual(forgot_message(True), FORGOT_MESSAGE)
        self.assertFalse(can_send_reset("", "https://example.test"))
        self.assertTrue(can_send_reset("box@example.test", "https://example.test"))

    def test_reset_token_expires_and_dies_when_the_password_changes(self):
        secret = "test-secret"
        token = make_reset_token(secret, "user-1", "hash-a", issued_at=1_000, ttl=50)
        self.assertEqual(read_reset_token(secret, token, "hash-a", now=1_040), "user-1")
        self.assertIsNone(read_reset_token(secret, token, "hash-a", now=1_051))
        self.assertIsNone(read_reset_token(secret, token, "hash-b", now=1_020))
        self.assertEqual(reset_link("https://example.test/", token), f"https://example.test/reset?token={token}")


if __name__ == "__main__":
    unittest.main()
