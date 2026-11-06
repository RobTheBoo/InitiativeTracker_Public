import argparse
import json
import re
from pathlib import Path


MANIFEST = Path(__file__).resolve().parent / "manifest.json"
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def prepare_manifest(commit_sha, manifest_path=MANIFEST):
    if not COMMIT_SHA.fullmatch(commit_sha):
        raise ValueError("data commit must be a full 40-character lowercase Git SHA")
    path = Path(manifest_path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    replaced = 0
    for package in manifest["packages"]:
        url = package["downloadUrl"]
        if "__DATA_COMMIT_SHA__" in url:
            package["downloadUrl"] = url.replace("__DATA_COMMIT_SHA__", commit_sha)
            replaced += 1
    if not replaced:
        raise ValueError("manifest contains no __DATA_COMMIT_SHA__ placeholders")
    path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return replaced


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pin catalog asset URLs to a data commit SHA"
    )
    parser.add_argument(
        "--data-commit",
        required=True,
        help="Full 40-character lowercase Git SHA",
    )
    args = parser.parse_args()
    count = prepare_manifest(args.data_commit)
    print(f"Pinned {count} package URL(s) to {args.data_commit}.")
