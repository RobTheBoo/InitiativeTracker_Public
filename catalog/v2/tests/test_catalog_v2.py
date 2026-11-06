import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "v1"))
from validate_catalog import CatalogValidationError, validate_catalog


class V2CatalogTests(unittest.TestCase):
    def test_prepared_v2_pilot_validates(self):
        manifest = validate_catalog(
            ROOT / "manifest.json",
            ROOT / "packages",
            allow_placeholder=True,
        )
        self.assertEqual(manifest["schemaVersion"], 2)
        self.assertEqual(manifest["packages"][0]["assetSchemaVersion"], 2)
        self.assertEqual(manifest["packages"][0]["id"], "core-reviewed-spells")

    def test_v2_rejects_asset_without_embedded_distribution(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        asset = json.loads(
            (ROOT / "packages" / "core-reviewed-spells-1.0.0.json").read_text(
                encoding="utf-8"
            )
        )
        del asset["distribution"]
        asset_bytes = (
            json.dumps(asset, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        manifest["packages"][0]["sizeBytes"] = len(asset_bytes)
        manifest["packages"][0]["sha256"] = hashlib.sha256(asset_bytes).hexdigest()

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package_dir = root / "packages"
            package_dir.mkdir()
            (package_dir / "core-reviewed-spells-1.0.0.json").write_bytes(
                asset_bytes
            )
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(
                CatalogValidationError, "requires embedded distribution"
            ):
                validate_catalog(
                    manifest_path,
                    package_dir,
                    allow_placeholder=True,
                )


if __name__ == "__main__":
    unittest.main()
