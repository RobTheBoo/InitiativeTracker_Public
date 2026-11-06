# Public data catalog

The app reads the stable manifest at:

`https://raw.githubusercontent.com/RobTheBoo/InitiativeTracker_Public/main/catalog/v1/manifest.json`

Each package points to a JSON asset using a full, immutable Git commit SHA in its `raw.githubusercontent.com` URL. The client should verify byte length and lowercase SHA-256 before parsing. The asset is plain JSON, so no archive extraction is needed.

Each asset is `{schemaVersion: 1, id, name, ruleset: {id, edition}, items: [...]}`; each item has `id`, `category`, `name`, `description`, and object-valued `rulesData`. Limits are 500 items and 2 MiB (2,097,152 bytes). The manifest includes version, exact size and digest, license, source name/URL/revision, ruleset, categories, and language. `manifest.schema.json` describes the manifest contract.

## Validate

```powershell
python catalog\v1\validate_catalog.py --allow-placeholder
python -m unittest discover -s catalog\v1\tests
```

## Publish a package revision

Use two commits. First commit the JSON package and record that data commit's full SHA. Then substitute the manifest placeholder and commit the manifest update:

```powershell
python catalog\v1\prepare_manifest.py --data-commit <full-40-character-sha>
python catalog\v1\validate_catalog.py
```

The helper refuses malformed SHAs and only replaces `__DATA_COMMIT_SHA__`. This ordering ensures the raw URL addresses a commit that already contains the immutable asset. There is currently no repository publication workflow; these commands prepare and validate the metadata but do not publish it.

The included `original-sample` fixture is newly written example content marked `CC0-1.0`; it is not a game rules database. No PSRD-Data content is included.
