import tempfile
from html.parser import HTMLParser
import unittest
from unittest.mock import patch

from backend.app import create_app
from backend.dataset import DatasetValidationError, load_dataset


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.assets.append((attrs["href"], "text/css"))
        if tag == "script" and "src" in attrs:
            self.assets.append((attrs["src"], "text/javascript"))


class AppTests(unittest.TestCase):
    def test_page_assets_and_health(self):
        client = create_app().test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'role="status"', response.data)
        parser = AssetParser()
        parser.feed(response.get_data(as_text=True))
        self.assertEqual(len(parser.assets), 2)
        response.close()
        for asset, content_type in parser.assets + [("/static/src/api.js", "text/javascript")]:
            with client.get(asset) as asset_response:
                self.assertEqual(asset_response.status_code, 200)
                self.assertEqual(asset_response.mimetype, content_type)
        self.assertEqual(client.get("/api/health").json, {"status": "ok", "dataset_loaded": True})
        for private in ("/jobs.json", "/applicants.json", "/static/../applicants.json", "/api/applicants"):
            self.assertEqual(client.get(private).status_code, 404)

    def test_load_once_and_reuse(self):
        with patch("backend.app.load_dataset", wraps=load_dataset) as loader:
            app = create_app()
            dataset = app.extensions["dataset"]
            client = app.test_client()
            client.get("/api/health")
            client.get("/api/health")
            loader.assert_called_once()
            self.assertIs(app.extensions["dataset"], dataset)

    def test_invalid_data_prevents_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(DatasetValidationError, "jobs.json"):
                create_app(directory)
