import argparse
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "catalog_v1_prepare_manifest", ROOT.parent / "v1" / "prepare_manifest.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load shared manifest helper")
PREPARER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREPARER)

prepare_manifest = PREPARER.prepare_manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pin v2 package URLs to a data commit SHA"
    )
    parser.add_argument(
        "--data-commit",
        required=True,
        help="Full 40-character lowercase Git SHA",
    )
    args = parser.parse_args()
    count = prepare_manifest(args.data_commit, ROOT / "manifest.json")
    print(f"Pinned {count} v2 package URL(s) to {args.data_commit}.")
