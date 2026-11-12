import unittest

from app.utils.avatars import icon_url, icon_version
from app.utils.sql import like_escape


class AvatarUrlTests(unittest.TestCase):
    def test_empty_icon_has_no_version_and_points_to_endpoint(self):
        self.assertEqual(icon_version("", ""), "")
        url = icon_url("alice")
        self.assertTrue(url.endswith("/api/icon/alice.svg"))
        self.assertNotIn("?v=", url)

    def test_version_changes_with_icon_content(self):
        a = icon_url("alice", "F" * 1024)
        b = icon_url("alice", "1" * 1024)
        self.assertIn("?v=", a)
        self.assertNotEqual(a, b)

    def test_blank_icon_does_not_add_version(self):
        url = icon_url("alice", "0" * 1024)
        self.assertTrue(url.endswith("/api/icon/alice.svg"))
        self.assertNotIn("?v=", url)

    def test_username_is_url_quoted(self):
        self.assertIn("/api/icon/a%20b.svg", icon_url("a b"))


class LikeEscapeTests(unittest.TestCase):
    def test_escapes_like_wildcards(self):
        self.assertEqual(like_escape("100%_real\\"), "100\\%\\_real\\\\")

    def test_plain_keyword_is_unchanged(self):
        self.assertEqual(like_escape("floppy"), "floppy")


if __name__ == "__main__":
    unittest.main()
