import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
MAX_PACKAGE_ITEMS = 500
PINNED_URL = re.compile(
    r"^https://raw\.githubusercontent\.com/RobTheBoo/"
    r"InitiativeTracker_Public/([0-9a-f]{40})/catalog/v1/packages/([^/]+\.json)$"
)
SHA256 = re.compile(r"^[a-f0-9]{64}$")
VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
LANGUAGE = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")
PLACEHOLDER = "__DATA_COMMIT_SHA__"
OGL_LICENSE = re.compile(r"\bOGL(?:-|\b)", re.IGNORECASE)


class CatalogValidationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise CatalogValidationError(message)


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CatalogValidationError(f"Cannot read JSON file {path}: {error}") from error


def validate_catalog(
    manifest_path=ROOT / "manifest.json",
    package_dir=ROOT / "packages",
    allow_placeholder=False,
):
    manifest = read_json(manifest_path)
    require(isinstance(manifest, dict), "Manifest must be a JSON object")
    require(manifest.get("schemaVersion") == 1, "Manifest schemaVersion must be 1")
    require(
        isinstance(manifest.get("catalogVersion"), str)
        and VERSION.fullmatch(manifest["catalogVersion"]),
        "catalogVersion must use numeric major.minor.patch format",
    )
    packages = manifest.get("packages")
    require(isinstance(packages, list), "Manifest packages must be an array")
    package_ids = set()

    for entry in packages:
        require(isinstance(entry, dict), "Every package entry must be an object")
        required = (
            "id", "name", "version", "description", "downloadUrl", "format",
            "sizeBytes", "sha256", "license", "redistributionStatus",
            "notices", "source", "ruleset",
            "categories", "language",
        )
        for field in required:
            require(field in entry, f"Package entry is missing {field}")
        package_id = entry["id"]
        require(
            isinstance(package_id, str)
            and re.fullmatch(r"[a-z0-9][a-z0-9-]*", package_id),
            "Package id must be lowercase kebab-case",
        )
        require(package_id not in package_ids, f"Duplicate package id: {package_id}")
        package_ids.add(package_id)
        require(
            isinstance(entry["version"], str) and VERSION.fullmatch(entry["version"]),
            f"{package_id}: version must use numeric major.minor.patch format",
        )
        require(
            isinstance(entry["name"], str)
            and bool(entry["name"])
            and isinstance(entry["description"], str)
            and bool(entry["description"]),
            f"{package_id}: name and description must be non-empty strings",
        )
        require(entry["format"] == "json", f"{package_id}: format must be json")

        url = entry["downloadUrl"]
        if allow_placeholder and isinstance(url, str) and PLACEHOLDER in url:
            require(
                url.endswith(
                    "/catalog/v1/packages/"
                    + package_id
                    + "-"
                    + entry["version"]
                    + ".json"
                ),
                f"{package_id}: placeholder URL path does not match package",
            )
        else:
            match = PINNED_URL.fullmatch(url) if isinstance(url, str) else None
            require(
                match is not None,
                f"{package_id}: downloadUrl must pin a package to an immutable commit SHA",
            )
            require(
                match.group(2) == package_id + "-" + entry["version"] + ".json",
                f"{package_id}: asset filename does not match id and version",
            )

        source = entry["source"]
        require(
            isinstance(source, dict)
            and all(
                isinstance(source.get(key), str) and source[key]
                for key in ("name", "url", "revision")
            ),
            f"{package_id}: source must include name, URL, and revision",
        )
        require(
            urlparse(source["url"]).scheme in ("http", "https"),
            f"{package_id}: source URL must be HTTP(S)",
        )
        require(
            isinstance(entry["license"], str) and bool(entry["license"]),
            f"{package_id}: license must be specified",
        )
        require(
            entry["redistributionStatus"] == "verified",
            f"{package_id}: redistribution rights must be verified before publication",
        )
        notices = entry["notices"]
        require(
            isinstance(notices, list)
            and bool(notices)
            and all(isinstance(notice, str) and notice.strip() for notice in notices),
            f"{package_id}: at least one non-empty package notice is required",
        )
        ruleset = entry["ruleset"]
        require(
            isinstance(ruleset, dict)
            and isinstance(ruleset.get("id"), str)
            and bool(ruleset["id"])
            and isinstance(ruleset.get("edition"), str)
            and bool(ruleset["edition"]),
            f"{package_id}: ruleset must include id and edition",
        )
        categories = entry["categories"]
        require(
            isinstance(categories, list)
            and categories
            and all(isinstance(item, str) and item for item in categories)
            and len(categories) == len(set(categories)),
            f"{package_id}: categories must be unique non-empty strings",
        )
        require(
            isinstance(entry["language"], str)
            and LANGUAGE.fullmatch(entry["language"]),
            f"{package_id}: language must be a valid language tag",
        )
        require(
            isinstance(entry["sha256"], str) and SHA256.fullmatch(entry["sha256"]),
            f"{package_id}: sha256 must be 64 lowercase hexadecimal characters",
        )

        asset_path = Path(package_dir) / (
            package_id + "-" + entry["version"] + ".json"
        )
        try:
            asset_bytes = asset_path.read_bytes()
        except OSError as error:
            raise CatalogValidationError(
                f"{package_id}: local asset not found at {asset_path}"
            ) from error
        require(
            0 < len(asset_bytes) <= MAX_PACKAGE_BYTES,
            f"{package_id}: asset must be no larger than 2 MiB",
        )
        require(
            type(entry["sizeBytes"]) is int and entry["sizeBytes"] == len(asset_bytes),
            f"{package_id}: sizeBytes does not match the local asset",
        )
        require(
            hashlib.sha256(asset_bytes).hexdigest() == entry["sha256"],
            f"{package_id}: sha256 does not match the local asset",
        )
        try:
            asset = json.loads(asset_bytes.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise CatalogValidationError(
                f"{package_id}: asset is not valid UTF-8 JSON"
            ) from error
        require(isinstance(asset, dict), f"{package_id}: asset must be a JSON object")
        require(
            asset.get("schemaVersion") == 1,
            f"{package_id}: asset schemaVersion must be 1",
        )
        require(asset.get("id") == package_id, f"{package_id}: asset id does not match")
        require(
            asset.get("name") == entry["name"],
            f"{package_id}: asset name does not match manifest",
        )
        require(
            asset.get("ruleset") == ruleset,
            f"{package_id}: ruleset does not match manifest",
        )
        items = asset.get("items")
        require(isinstance(items, list), f"{package_id}: asset items must be an array")
        require(
            len(items) <= MAX_PACKAGE_ITEMS,
            f"{package_id}: asset exceeds the 500 item limit",
        )
        item_ids = set()
        for item in items:
            require(isinstance(item, dict), f"{package_id}: every item must be an object")
            for field in ("id", "category", "name", "description", "rulesData"):
                require(field in item, f"{package_id}: item is missing {field}")
            require(
                isinstance(item["id"], str)
                and item["id"]
                and item["id"] not in item_ids,
                f"{package_id}: item ids must be non-empty and unique",
            )
            item_ids.add(item["id"])
            require(
                isinstance(item["category"], str)
                and item["category"] in categories,
                f"{package_id}: item category is missing from manifest categories",
            )
            require(
                isinstance(item["name"], str)
                and bool(item["name"])
                and isinstance(item["description"], str)
                and bool(item["description"])
                and isinstance(item["rulesData"], dict),
                f"{package_id}: invalid item field type",
            )
        distribution = asset.get("distribution")
        requires_embedded_legal = bool(OGL_LICENSE.search(entry["license"]))
        require(
            not requires_embedded_legal or isinstance(distribution, dict),
            f"{package_id}: OGL packages must embed distribution text in the asset",
        )
        if distribution is not None:
            validate_distribution(distribution, items, package_id, entry["license"])
    return manifest


def validate_distribution(distribution, items, package_id, manifest_license):
    require(
        isinstance(distribution, dict),
        f"{package_id}: distribution must be an object",
    )
    require(
        distribution.get("redistributionStatus") == "verified",
        f"{package_id}: embedded redistribution status must be verified",
    )
    item_ids = {item["id"] for item in items}

    licenses = distribution.get("licenses")
    require(
        isinstance(licenses, list) and bool(licenses),
        f"{package_id}: distribution must include full license texts",
    )
    license_ids = set()
    for license_entry in licenses:
        require(
            isinstance(license_entry, dict)
            and all(
                isinstance(license_entry.get(field), str)
                and license_entry[field].strip()
                for field in ("id", "name", "text")
            ),
            f"{package_id}: every embedded license needs id, name, and full text",
        )
        require(
            license_entry["id"] not in license_ids,
            f"{package_id}: duplicate embedded license id",
        )
        license_ids.add(license_entry["id"])
    if OGL_LICENSE.search(manifest_license):
        require(
            any(OGL_LICENSE.search(identifier) for identifier in license_ids),
            f"{package_id}: manifest OGL license must be included in the asset",
        )

    notices = distribution.get("notices")
    require(
        isinstance(notices, list) and bool(notices),
        f"{package_id}: distribution must include applicable notices",
    )
    notice_ids = set()
    has_section15_notice = False
    for notice in notices:
        require(
            isinstance(notice, dict)
            and all(
                isinstance(notice.get(field), str) and notice[field].strip()
                for field in ("id", "type", "text")
            )
            and isinstance(notice.get("appliesToItemIds"), list)
            and bool(notice["appliesToItemIds"]),
            f"{package_id}: every notice needs id, type, full text, and item mapping",
        )
        require(notice["id"] not in notice_ids, f"{package_id}: duplicate notice id")
        notice_ids.add(notice["id"])
        require(
            notice["type"] in ("section15", "copyright", "attribution", "other"),
            f"{package_id}: unsupported notice type",
        )
        require(
            all(item_id in item_ids for item_id in notice["appliesToItemIds"]),
            f"{package_id}: notice maps to an unknown item id",
        )
        require(
            all(
                isinstance(item_id, str) and item_id
                for item_id in notice["appliesToItemIds"]
            ),
            f"{package_id}: notice item ids must be non-empty strings",
        )
        require(
            len(notice["appliesToItemIds"])
            == len(set(notice["appliesToItemIds"])),
            f"{package_id}: notice item ids must be unique",
        )
        if notice["type"] == "section15":
            has_section15_notice = True
    if OGL_LICENSE.search(manifest_license):
        require(
            has_section15_notice,
            f"{package_id}: OGL package must embed its Section 15 notice",
        )
        section15_item_ids = {
            item_id
            for notice in notices
            if notice["type"] == "section15"
            for item_id in notice["appliesToItemIds"]
        }
        require(
            section15_item_ids == item_ids,
            f"{package_id}: Section 15 notices must cover every package item",
        )

    sources = distribution.get("sources")
    require(
        isinstance(sources, list) and bool(sources),
        f"{package_id}: distribution must include item-level sources",
    )
    source_ids = set()
    covered_item_ids = set()
    for source in sources:
        require(
            isinstance(source, dict)
            and all(
                isinstance(source.get(field), str) and source[field].strip()
                for field in ("id", "name", "url", "revision")
            )
            and isinstance(source.get("itemIds"), list)
            and bool(source["itemIds"]),
            f"{package_id}: every source needs id, name, URL, revision, and item ids",
        )
        require(source["id"] not in source_ids, f"{package_id}: duplicate source id")
        source_ids.add(source["id"])
        require(
            urlparse(source["url"]).scheme in ("http", "https"),
            f"{package_id}: source URL must be HTTP(S)",
        )
        require(
            all(isinstance(item_id, str) and item_id for item_id in source["itemIds"]),
            f"{package_id}: source item ids must be non-empty strings",
        )
        require(
            len(source["itemIds"]) == len(set(source["itemIds"])),
            f"{package_id}: source item ids must be unique",
        )
        require(
            all(item_id in item_ids for item_id in source["itemIds"]),
            f"{package_id}: source maps to an unknown item id",
        )
        covered_item_ids.update(source["itemIds"])
    require(
        covered_item_ids == item_ids,
        f"{package_id}: every item must map to at least one source",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate the catalog manifest and local JSON package assets"
    )
    parser.add_argument(
        "--allow-placeholder",
        action="store_true",
        help="Allow the draft data commit placeholder in package URLs",
    )
    args = parser.parse_args()
    try:
        result = validate_catalog(allow_placeholder=args.allow_placeholder)
    except CatalogValidationError as error:
        print(f"Catalog validation failed: {error}", file=sys.stderr)
        sys.exit(1)
    print(
        f"Catalog {result['catalogVersion']} is valid "
        f"({len(result['packages'])} package(s))."
    )
