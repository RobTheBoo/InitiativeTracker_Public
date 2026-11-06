import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prepare_manifest import prepare_manifest
from validate_catalog import (
    MAX_PACKAGE_BYTES,
    MAX_PACKAGE_ITEMS,
    CatalogValidationError,
    ROOT,
    validate_catalog,
)


class CatalogValidationTests(unittest.TestCase):
    def test_included_fixture_matches_manifest_and_integrity_metadata(self):
        manifest = validate_catalog(allow_placeholder=True)
        package = manifest["packages"][0]
        asset = json.loads(
            (ROOT / "packages" / "original-sample-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(package["sizeBytes"], (ROOT / "packages" / "original-sample-1.0.0.json").stat().st_size)
        self.assertLessEqual(package["sizeBytes"], MAX_PACKAGE_BYTES)
        self.assertLessEqual(len(asset["items"]), MAX_PACKAGE_ITEMS)
        self.assertEqual(package["license"], "CC0-1.0")

    def test_prepare_manifest_pins_the_data_commit(self):
        commit = "a" * 40
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "manifest.json"
            target.write_bytes((ROOT / "manifest.json").read_bytes())
            self.assertEqual(prepare_manifest(commit, target), 1)
            manifest = json.loads(target.read_text(encoding="utf-8"))
            self.assertIn(
                "/" + commit + "/catalog/v1/packages/",
                manifest["packages"][0]["downloadUrl"],
            )
            validate_catalog(target, ROOT / "packages")

    def test_prepare_manifest_rejects_short_commit_sha(self):
        with self.assertRaisesRegex(ValueError, "full 40-character"):
            prepare_manifest("abc", ROOT / "manifest.json")

    def test_rejects_mismatched_asset_checksum(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "manifest.json"
            target.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CatalogValidationError, "sha256 does not match"):
                validate_catalog(target, ROOT / "packages", allow_placeholder=True)

    def test_rejects_non_commit_download_url(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["downloadUrl"] = "https://example.com/package.json"
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "manifest.json"
            target.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CatalogValidationError, "immutable commit SHA"):
                validate_catalog(target, ROOT / "packages", allow_placeholder=True)

    def test_rejects_more_than_500_items(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        asset = json.loads(
            (ROOT / "packages" / "original-sample-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        asset["items"] = [
            {
                "id": f"item-{index}",
                "category": "condition",
                "name": f"Item {index}",
                "description": "Original test item",
                "rulesData": {},
            }
            for index in range(MAX_PACKAGE_ITEMS + 1)
        ]
        asset_bytes = json.dumps(asset).encode("utf-8")
        manifest["packages"][0]["sizeBytes"] = len(asset_bytes)
        manifest["packages"][0]["sha256"] = hashlib.sha256(asset_bytes).hexdigest()

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            asset_dir = root / "packages"
            asset_dir.mkdir()
            (asset_dir / "original-sample-1.0.0.json").write_bytes(asset_bytes)
            target = root / "manifest.json"
            target.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CatalogValidationError, "500 item limit"):
                validate_catalog(target, asset_dir, allow_placeholder=True)

    def test_rejects_asset_over_2_mib(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        asset = json.loads(
            (ROOT / "packages" / "original-sample-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        asset["oversized-test-field"] = "x" * (MAX_PACKAGE_BYTES + 1)
        asset_bytes = json.dumps(asset).encode("utf-8")
        manifest["packages"][0]["sizeBytes"] = len(asset_bytes)
        manifest["packages"][0]["sha256"] = hashlib.sha256(asset_bytes).hexdigest()

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            asset_dir = root / "packages"
            asset_dir.mkdir()
            (asset_dir / "original-sample-1.0.0.json").write_bytes(asset_bytes)
            target = root / "manifest.json"
            target.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CatalogValidationError, "no larger than 2 MiB"):
                validate_catalog(target, asset_dir, allow_placeholder=True)


if __name__ == "__main__":
    unittest.main()
