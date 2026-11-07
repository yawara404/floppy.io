import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import users


class ConnectionsTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(users.router)
        self.client = TestClient(app)
        self.owner = patch.object(users, "fetch_one", return_value={"id": 7}).start()
        self.rows = patch.object(users, "fetch_all", return_value=[]).start()
        self.viewer = patch.object(users, "current_user", return_value=None).start()
        self.addCleanup(patch.stopall)

    def test_following_and_followers_use_correct_direction(self):
        for kind, owner, member in [
            ("following", "follower_id", "followee_id"),
            ("followers", "followee_id", "follower_id"),
        ]:
            response = self.client.get(f"/api/users/alice/connections/{kind}")
            self.assertEqual(response.status_code, 200)
            sql, parameters = self.rows.call_args.args
            self.assertIn(f"u.id = f.{member}", sql)
            self.assertIn(f"WHERE f.{owner} = %s", sql)
            self.assertEqual(parameters, (0, 7, 0))
            self.assertEqual(response.json(), {"users": [], "next_offset": None})

    def test_pagination_and_public_fields(self):
        self.viewer.return_value = {"id": 4}
        self.rows.return_value = [
            {"id": i, "username": f"user{i}", "display_name": "", "bio": "紹介",
             "icon_pixel": "", "avatar_path": "", "following": i == 5,
             "password_hash": "must-not-leak"}
            for i in range(1, 52)
        ]
        response = self.client.get("/api/users/alice/connections/followers?offset=50")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["users"]), 50)
        self.assertEqual(data["next_offset"], 100)
        self.assertEqual(self.rows.call_args.args[1], (4, 7, 50))
        self.assertTrue(data["users"][3]["is_self"])
        self.assertTrue(data["users"][4]["following"])
        self.assertEqual(data["users"][0]["display_name"], "user1")
        self.assertNotIn("password_hash", data["users"][0])
        self.assertNotIn("avatar_path", data["users"][0])

    def test_invalid_kind_and_negative_offset(self):
        self.assertEqual(self.client.get("/api/users/alice/connections/invalid").status_code, 400)
        self.assertEqual(self.client.get("/api/users/alice/connections/followers?offset=-1").status_code, 422)
        self.rows.assert_not_called()

    def test_unknown_user(self):
        self.owner.return_value = None
        self.assertEqual(self.client.get("/api/users/missing/connections/following").status_code, 404)
        self.rows.assert_not_called()


if __name__ == "__main__":
    unittest.main()
