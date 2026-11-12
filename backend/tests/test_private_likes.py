import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import users


class PrivateLikesTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(users.router)
        self.client = TestClient(app)
        self.owner = patch.object(users, "fetch_one", return_value={"id": 7}).start()
        self.rows = patch.object(users, "fetch_all", return_value=[]).start()
        self.addCleanup(patch.stopall)

    def test_anonymous_cannot_read_history(self):
        response = self.client.get("/api/users/alice/likes")
        self.assertEqual(response.status_code, 401)
        self.rows.assert_not_called()
        self.owner.assert_not_called()

    def test_invalid_token_cannot_read_history(self):
        with patch("app.security.fetch_one", return_value=None):
            response = self.client.get("/api/users/alice/likes", headers={"Authorization": "Bearer invalid"})
        self.assertEqual(response.status_code, 401)
        self.rows.assert_not_called()

    def test_other_user_cannot_read_history(self):
        with patch.object(users, "require_user", return_value={"id": 8}):
            response = self.client.get("/api/users/alice/likes")
        self.assertEqual(response.status_code, 403)
        self.assertIn("no-store", response.headers["cache-control"])
        self.rows.assert_not_called()

    def test_missing_user_does_not_fall_back_to_another_history(self):
        self.owner.return_value = None
        with patch.object(users, "require_user", return_value={"id": 7}):
            response = self.client.get("/api/users/missing/likes")
        self.assertEqual(response.status_code, 403)
        self.rows.assert_not_called()

    def test_owner_history_is_private_paginated_and_sorted_by_like_time(self):
        self.rows.return_value = [{"id": i} for i in range(51)]
        with (
            patch.object(users, "require_user", return_value={"id": 7}),
            patch.object(users, "with_media", side_effect=lambda post: post),
            patch.object(users, "attach_likes", side_effect=lambda posts, me: posts),
            patch.object(users, "attach_reply_counts", side_effect=lambda posts: posts),
            patch.object(users, "attach_disks", side_effect=lambda posts: posts),
        ):
            response = self.client.get("/api/users/alice/likes?offset=50&user_id=999")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "private, no-store")
        self.assertEqual(len(response.json()["posts"]), 50)
        self.assertEqual(response.json()["next_offset"], 100)
        sql, params = self.rows.call_args.args
        self.assertEqual(params, (7, 50))
        self.assertIn("WHERE l.user_id = %s", sql)
        self.assertIn("ORDER BY l.created_at DESC, p.id DESC", sql)

    def test_empty_history_has_no_next_page(self):
        with patch.object(users, "require_user", return_value={"id": 7}):
            response = self.client.get("/api/users/alice/likes")
        self.assertEqual(response.json(), {"posts": [], "next_offset": None})

    def test_negative_offset_is_rejected(self):
        self.assertEqual(self.client.get("/api/users/alice/likes?offset=-1").status_code, 422)
        self.rows.assert_not_called()


if __name__ == "__main__":
    unittest.main()
