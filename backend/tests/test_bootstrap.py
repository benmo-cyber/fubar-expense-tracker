import unittest

from app.core.bootstrap import planned_users


class PlannedUsersTests(unittest.TestCase):
    def test_development_gets_sample_accounts_only_on_an_empty_database(self):
        created = planned_users("development", False, "", "", "")
        self.assertEqual([user["email"] for user in created], ["admin@example.com", "field@example.com"])
        self.assertEqual(planned_users("development", True, "", "", ""), [])

    def test_production_uses_the_server_admin_and_skips_sample_logins(self):
        created = planned_users("production", False, "ben@wildwoodingredients.com", "a-real-password", "Ben")
        self.assertEqual(created, [{
            "email": "ben@wildwoodingredients.com",
            "password": "a-real-password",
            "full_name": "Ben",
            "role": "admin",
        }])
        self.assertEqual(planned_users("production", False, "", "", "Ben"), [])
        self.assertEqual(
            planned_users("production", True, "ben@wildwoodingredients.com", "a-real-password", "Ben"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
