import hashlib
import json
import re
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
    def write_catalog_variant(self, folder, manifest, asset):
        root = Path(folder)
        asset_dir = root / "packages"
        asset_dir.mkdir()
        asset_bytes = json.dumps(asset, ensure_ascii=False).encode("utf-8")
        package = manifest["packages"][0]
        package["sizeBytes"] = len(asset_bytes)
        package["sha256"] = hashlib.sha256(asset_bytes).hexdigest()
        (asset_dir / "original-sample-1.0.0.json").write_bytes(asset_bytes)
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return manifest_path, asset_dir

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
        self.assertEqual(package["redistributionStatus"], "verified")
        self.assertTrue(package["notices"])

    def test_existing_v1_asset_without_distribution_remains_valid(self):
        asset = json.loads(
            (ROOT / "packages" / "original-sample-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("distribution", asset)
        self.assertEqual(validate_catalog(allow_placeholder=True)["schemaVersion"], 1)

    def test_prepare_manifest_pins_the_data_commit(self):
        commit = "a" * 40
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "manifest.json"
            manifest = json.loads(
                (ROOT / "manifest.json").read_text(encoding="utf-8")
            )
            package = manifest["packages"][0]
            package["downloadUrl"] = re.sub(
                r"/[0-9a-f]{40}/catalog/",
                "/__DATA_COMMIT_SHA__/catalog/",
                package["downloadUrl"],
                count=1,
            )
            target.write_text(json.dumps(manifest), encoding="utf-8")
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

    def test_rejects_package_without_verified_redistribution_rights(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["redistributionStatus"] = "unverified"
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "manifest.json"
            target.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CatalogValidationError, "must be verified"):
                validate_catalog(target, ROOT / "packages")

    def test_rejects_package_without_notices(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["notices"] = []
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "manifest.json"
            target.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(CatalogValidationError, "at least one"):
                validate_catalog(target, ROOT / "packages")

    def test_rejects_ogl_package_without_embedded_distribution(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["license"] = "OGL-1.0a"
        asset = json.loads(
            (ROOT / "packages" / "original-sample-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        with tempfile.TemporaryDirectory() as folder:
            target, asset_dir = self.write_catalog_variant(folder, manifest, asset)
            with self.assertRaisesRegex(CatalogValidationError, "must embed distribution"):
                validate_catalog(target, asset_dir)

    def test_accepts_ogl_distribution_with_full_texts_and_item_mappings(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["license"] = "OGL-1.0a"
        asset = json.loads(
            (ROOT / "packages" / "original-sample-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        item_ids = [item["id"] for item in asset["items"]]
        asset["distribution"] = {
            "redistributionStatus": "verified",
            "licenses": [
                {
                    "id": "OGL-1.0a",
                    "name": "Open Game License v1.0a",
                    "text": "Complete license text included for structural testing.",
                }
            ],
            "notices": [
                {
                    "id": "test-section15",
                    "type": "section15",
                    "text": "Complete Section 15 notice included for structural testing.",
                    "appliesToItemIds": item_ids,
                }
            ],
            "sources": [
                {
                    "id": "test-source",
                    "name": "Verified source",
                    "url": "https://example.org/source",
                    "revision": "test-revision",
                    "itemIds": item_ids,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            target, asset_dir = self.write_catalog_variant(folder, manifest, asset)
            self.assertEqual(validate_catalog(target, asset_dir)["schemaVersion"], 1)

    def test_rejects_ogl_distribution_without_section15_notice(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["license"] = "OGL-1.0a"
        asset = json.loads(
            (ROOT / "packages" / "original-sample-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        item_ids = [item["id"] for item in asset["items"]]
        asset["distribution"] = {
            "redistributionStatus": "verified",
            "licenses": [
                {"id": "OGL-1.0a", "name": "OGL", "text": "Full license text"}
            ],
            "notices": [
                {
                    "id": "test-copyright",
                    "type": "copyright",
                    "text": "Copyright notice",
                    "appliesToItemIds": item_ids,
                }
            ],
            "sources": [
                {
                    "id": "test-source",
                    "name": "Verified source",
                    "url": "https://example.org/source",
                    "revision": "test-revision",
                    "itemIds": item_ids,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            target, asset_dir = self.write_catalog_variant(folder, manifest, asset)
            with self.assertRaisesRegex(CatalogValidationError, "Section 15 notice"):
                validate_catalog(target, asset_dir)

    def test_rejects_distribution_source_map_missing_package_items(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        manifest["packages"][0]["license"] = "OGL-1.0a"
        asset = json.loads(
            (ROOT / "packages" / "original-sample-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        item_ids = [item["id"] for item in asset["items"]]
        asset["distribution"] = {
            "redistributionStatus": "verified",
            "licenses": [
                {"id": "OGL-1.0a", "name": "OGL", "text": "Full license text"}
            ],
            "notices": [
                {
                    "id": "test-section15",
                    "type": "section15",
                    "text": "Section 15 notice",
                    "appliesToItemIds": item_ids,
                }
            ],
            "sources": [
                {
                    "id": "test-source",
                    "name": "Verified source",
                    "url": "https://example.org/source",
                    "revision": "test-revision",
                    "itemIds": item_ids[:1],
                }
            ],
        }
        with tempfile.TemporaryDirectory() as folder:
            target, asset_dir = self.write_catalog_variant(folder, manifest, asset)
            with self.assertRaisesRegex(CatalogValidationError, "every item must map"):
                validate_catalog(target, asset_dir)

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
