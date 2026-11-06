# Public data catalog

The app reads the stable manifest at:

`https://raw.githubusercontent.com/RobTheBoo/InitiativeTracker_Public/main/catalog/v1/manifest.json`

Each package points to a JSON asset using a full, immutable Git commit SHA in its `raw.githubusercontent.com` URL. The client should verify byte length and lowercase SHA-256 before parsing. The asset is plain JSON, so no archive extraction is needed.

Each asset is `{schemaVersion: 1, id, name, ruleset: {id, edition}, items: [...]}`; each item has `id`, `category`, `name`, `description`, and object-valued `rulesData`. Limits are 500 items and 2 MiB (2,097,152 bytes). Every manifest package must include its license, source name/URL/revision, notices, and `redistributionStatus: "verified"` alongside version, exact size and digest, ruleset, categories, and language. The schema and validator reject packages without these fields or without verified redistribution rights.

The verified status is a required publisher attestation, not an automated legal or content review. Before setting it, confirm the rights for the exact included material and satisfy any license and attribution obligations. Keep unverified content out of the manifest and package directory; do not infer permissions or notices from a parser's license or another dataset.

## Embedded distribution metadata

The asset schema is in `package.schema.json`. For backward compatibility, the root-level `distribution` object is optional for existing schema-version-1 packages. Any new OGL package must include it in the downloaded JSON itself; manifest metadata alone is not a copy of the license delivered with the data.

```json
{
  "distribution": {
    "redistributionStatus": "verified",
    "licenses": [
      {
        "id": "OGL-1.0a",
        "name": "Open Game License v1.0a",
        "text": "<complete, exact license text>"
      }
    ],
    "notices": [
      {
        "id": "prd-section15",
        "type": "section15",
        "text": "<complete, exact applicable Section 15 notice>"
      }
    ],
    "sources": [
      {
        "id": "prd-source",
        "name": "Source title",
        "url": "https://example.org/source",
        "revision": "<immutable source revision>",
        "itemIds": ["item-id"]
      }
    ]
  }
}
```

`licenses[].text` and `notices[].text` must contain the full text, not a URL or identifier in place of it. To match the consumer contract, notices have exactly `id`, `type`, and `text`, and each notice applies to the whole package. Include all applicable license texts and copyright/attribution/Section 15 notices for every item in that asset; split packages when a notice would apply to only a subset. Source `itemIds` must collectively map every item to one or more exact sources. For OGL packages the validator requires the embedded OGL license, a non-empty package-wide Section 15 notice, and source coverage of every item. The validator checks structure and mapping, not the legal accuracy or completeness of the supplied text; publishers must compare the exact text to the verified source before setting `verified`.

Older v1 packages without `distribution` remain valid. Consumers must preserve `distribution` when importing a new package into a campaign and expose its license and notices; silently discarding unknown root fields would lose required distribution terms. The embedded legal text counts toward the 2 MiB package limit, so packages may need fewer than 500 items.

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
