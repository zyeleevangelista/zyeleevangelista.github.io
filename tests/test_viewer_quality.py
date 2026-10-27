"""Photo-viewer workflow tests; no Facebook network access or credentials needed."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "facebook-photo-extractor" / "viewer_quality.py"
spec = importlib.util.spec_from_file_location("viewer_quality", SOURCE)
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

SAMPLE = """<!doctype html><html>
<a href="https://www.facebook.com/photo.php?fbid=1234567890123&amp;set=pb.999999999999.0&amp;type=3">
<img src="./Clinic_files/850534819_1234567890123_1234567890123_n.jpg"></a>
<a href="https://www.facebook.com/photo.php?fbid=1234567890124&amp;set=pb.999999999999.0&amp;type=3">
<img src="./Clinic_files/850534820_1234567890124_1234567890124_n.jpg"></a>
<a href="https://www.facebook.com/photo.php?fbid=9876543210123&amp;set=pb.888888888888.0&amp;type=3">
<img src="./Friends_files/other.jpg"></a>
<a href="https://www.facebook.com/profile.php?id=123123123">
<img src="./Friends_files/avatar.jpg"></a></html>"""


class ViewerQualityTests(unittest.TestCase):
    def test_only_majority_page_photo_set(self):
        photos = tool.parse_saved_gallery(SAMPLE)
        self.assertEqual(len(photos), 2)
        self.assertEqual(photos[0]["id"], "1234567890123")

    def test_reject_unrelated_photo_links(self):
        self.assertIsNone(tool.verified_post("https://www.facebook.com/profile.php?id=123456789"))
        self.assertIsNone(tool.verified_post("https://www.facebook.com/photo.php?fbid=1234567890&set=pb.9999.0".replace("facebook.com", "example.com")))
        self.assertIsNone(tool.verified_post("https://www.facebook.com/photo.php?fbid=1234567890&set=some-other-album"))

    def test_file_prefix_for_matching_full_size(self):
        self.assertEqual(tool.photo_filename_prefix(
            "./Clinic_files/850534819_1234567890123_1234567890123_n.jpg"),
            "850534819_1234567890123")

    def test_only_approved_cdn(self):
        self.assertTrue(tool.is_facebook_cdn_photo("https://scontent.xx.fbcdn.net/v/t39/test.jpg"))
        self.assertFalse(tool.is_facebook_cdn_photo("https://evil.example/photos.jpg"))
        self.assertFalse(tool.is_facebook_cdn_photo("http://scontent.xx.fbcdn.net/test.jpg"))

    def test_offline_post_index(self):
        photos = tool.parse_saved_gallery(SAMPLE)
        with TemporaryDirectory() as directory:
            path = Path(directory) / "PHOTO_POST_LINKS.html"
            tool.create_post_index(photos, path)
            self.assertEqual(path.read_text().count("<li>"), 2)
            self.assertIn("Facebook Page photo posts", path.read_text())


if __name__ == "__main__":
    unittest.main()
