import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers import users
from app.utils.pixels import DEFAULT_AVATAR_ROWS, default_avatar_svg


class IconSvgTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(users.router)
        self.client = TestClient(app)
        self.user = patch.object(
            users,
            "fetch_one",
            return_value={"id": 7, "icon_pixel": "", "avatar_path": ""},
        ).start()
        self.pixel = patch.object(users, "user_avatar_pixel", return_value=None).start()
        self.addCleanup(patch.stopall)

    def test_unknown_user_is_404(self):
        self.user.return_value = None
        response = self.client.get("/api/icon/missing.svg")
        self.assertEqual(response.status_code, 404)

    def test_profile_icon_is_rendered_as_svg(self):
        self.user.return_value = {
            "id": 7,
            "icon_pixel": "3" * 1024,
            "avatar_path": "",
        }
        response = self.client.get("/api/icon/alice.svg")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("image/svg+xml"))
        self.assertIn("immutable", response.headers["cache-control"])
        self.assertIn("<svg", response.text)

    def test_empty_icon_falls_back_to_default_instead_of_404(self):
        response = self.client.get("/api/icon/alice.svg")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("image/svg+xml"))
        self.assertEqual(response.headers["cache-control"], "public, max-age=300")
        # サイトのロゴ色（深緑）とクリームで描いた初期アイコン
        self.assertIn('<svg xmlns="http://www.w3.org/2000/svg"', response.text)
        self.assertIn('fill="#174d35"', response.text)
        self.assertIn('fill="#e8e4d2"', response.text)
        self.assertIn('width="128" height="128"', response.text)
        self.pixel.assert_called_once_with(7)

    def test_default_icon_matches_frontend_grid_size(self):
        expected = sum(
            1
            for row in DEFAULT_AVATAR_ROWS
            for char in row
            if char != "."
        )
        self.assertEqual(expected, 196)
        svg = default_avatar_svg(cell=8)
        self.assertEqual(svg.count("<rect"), expected)
        self.assertTrue(svg.endswith("</svg>"))


if __name__ == "__main__":
    unittest.main()

