import argparse
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "catalog_v1_validator", ROOT.parent / "v1" / "validate_catalog.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load shared catalog validator")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

CatalogValidationError = VALIDATOR.CatalogValidationError
validate_catalog = VALIDATOR.validate_catalog


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate the v2 manifest and embedded-license package assets"
    )
    parser.add_argument(
        "--allow-placeholder",
        action="store_true",
        help="Allow the draft data commit placeholder in package URLs",
    )
    args = parser.parse_args()
    try:
        manifest = validate_catalog(
            manifest_path=ROOT / "manifest.json",
            package_dir=ROOT / "packages",
            allow_placeholder=args.allow_placeholder,
        )
    except CatalogValidationError as error:
        print(f"V2 catalog validation failed: {error}", file=sys.stderr)
        sys.exit(1)
    print(
        f"Catalog v{manifest['schemaVersion']} "
        f"{manifest['catalogVersion']} is valid "
        f"({len(manifest['packages'])} package(s))."
    )
