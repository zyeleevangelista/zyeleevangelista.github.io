"""Offline extractor regression tests. No private Facebook source files required."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


MODULE = Path(__file__).resolve().parents[1] / "facebook-photo-extractor" / "offline_extract.py"
spec = importlib.util.spec_from_file_location("photo_exporter", MODULE)
photo_exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(photo_exporter)

SAMPLE = """<!doctype html><html><body>
<a href="https://www.facebook.com/photo.php?fbid=1562694532553229&amp;set=pb.100064380924007.-2207520000&amp;type=3">
<img alt="Page photo" src="./Example_files/clinic_image.jpg"></a>
<a href="https://www.facebook.com/photo.php?fbid=1562694495886566&amp;set=pb.100064380924007.-2207520000&amp;type=3">
<img alt="Page photo 2" src="./Example_files/clinic_image_2.jpg"></a>
<a href="https://www.facebook.com/photo.php?fbid=999888777&amp;set=pb.200099999999.-2207520000&amp;type=3">
<img src="./Other_files/friend.jpg"></a>
<a href="https://www.facebook.com/profile.php?id=1234">
<img src="./Other_files/avatar.jpg"></a>
</body></html>"""


class SavedPageTests(unittest.TestCase):
    def test_extracts_only_primary_page_photo_set(self):
        assets = photo_exporter.saved_page_photo_assets(SAMPLE)
        self.assertEqual(len(assets), 2)
        self.assertTrue(all(a["mode"] == "local" for a in assets))
        self.assertEqual(assets[0]["photo_id"], "1562694532553229")

    def test_local_images_are_copied_without_network(self):
        with tempfile.TemporaryDirectory() as location:
            directory = Path(location)
            (directory / "Example_files").mkdir()
            jpeg = b"\xff\xd8\xff\xe0" + b"x" * 140
            (directory / "Example_files" / "clinic_image.jpg").write_bytes(jpeg)
            (directory / "output").mkdir()
            result = photo_exporter.copy_saved_image(
                1, "./Example_files/clinic_image.jpg", directory / "output", directory
            )
            self.assertEqual(result["status"], "ok")
            self.assertEqual((directory / "output" / "photo_0001.jpg").read_bytes(), jpeg)

    def test_missing_saved_photo_reports_failure(self):
        with tempfile.TemporaryDirectory() as location:
            base = Path(location)
            result = photo_exporter.copy_saved_image(1, "./Example_files/missing.jpg", base, base)
            self.assertEqual(result["status"], "failed")
            self.assertIn("missing", result["reason"].lower())

    def test_no_path_traversal(self):
        with tempfile.TemporaryDirectory() as location:
            base = Path(location)
            result = photo_exporter.copy_saved_image(1, "../../secret.jpg", base, base)
            self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
