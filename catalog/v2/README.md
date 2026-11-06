# Public data catalog v2

The v2 manifest is served separately from the legacy catalog:

`https://raw.githubusercontent.com/RobTheBoo/InitiativeTracker_Public/main/catalog/v2/manifest.json`

Manifest v2 contains only packages built with asset schemaVersion 2. Each package URL is pinned to the immutable commit containing its JSON bytes. V2 assets require `distribution` with verified redistribution status, full license text, package-wide notices, and source revision mappings for every item. The 500-item and 2 MiB limits include the embedded license and notices.

The locally prepared catalog is version 2.19.0 and contains 61 packages for ruleset identifier `PTFD`, edition `1e`: 287 reviewed spells, 34 standard conditions, 6,112 effects, 1,795 creature/NPC stat blocks, and 3,429 items. The non-spell selection covers indexed mechanics, afflictions, structured creature statistics, and item-table facts from available snapshot databases whose exact book titles appear in the embedded Section 15 notice. This includes Advanced Race Guide, Game Mastery Guide, NPC Codex, and Ultimate Campaign. Source text is included only for rules effects; creature prose/artwork and item descriptions are not copied. The current review holds 194 effects, 97 creature records, and 286 item records. These are individually listed by source and parent; reasons include third-party attribution, PI/name review, exact duplicate data, missing/corrupted fields, named artifact parents, and sources outside the embedded Section 15 (including Technology Guide). A hold is not a determination that a record is non-redistributable. `evidence/nonspell-coverage-76ea478.json` records the inventory, license checks, and included counts by source and parent. `evidence/nonspell-record-review-76ea478.json` records each inventory record and its disposition/reason; `evidence/nonspell-review-queue-76ea478.json` indexes every held record and its batch. The audit checks `book-ogl.db` for two Community Use License rows and 105 named Tome of Horrors attributions; exact matching names are held and none remain in packages. The catalog is a reviewed selection, not a claim to contain every record in the PSRD databases.

Non-spell selection was checked against Paizo's published [Product Identity and Open Game Content declaration](https://paizo.com/pathfinderRPG/prd/openGameLicense.html), the embedded complete OGL 1.0a and Section 15 text, and the exact book/database entries in PSRD-Data revision `76ea4784604145ba3dea40eb56f83bb904759467`. Packages contain only records from books listed in the embedded Section 15 notice. The selection omits named/setting-specific material, records with a separate or uncertain rights basis, images, creature flavor prose, and item descriptions; item summaries are generated from structured table facts. The audit is a publisher assessment, not legal advice or an independent legal review.

`redistributionStatus: "verified"` records the publisher's documented assessment. It is not a legal opinion, independent legal review, or guarantee. The included distribution metadata must remain with every distributed copy of a package.

## Legacy demo without duplication

The original sample remains listed only in `catalog/v1/manifest.json`; it is not copied into v2. A new application combines results from the v1 and v2 manifests keyed by package `id`, so the demo appears once and legacy clients continue to read only v1.

## Publish a v2 package

1. Verify rights, complete notices, source provenance, and per-item source mappings for every item.
2. Add the final asset under `catalog/v2/packages/`, calculate the exact UTF-8 byte length and lowercase SHA-256, and set `assetSchemaVersion` to 2.
3. Commit the asset first and pin `downloadUrl` to that full commit SHA.
4. Run `python catalog\v2\validate_catalog.py` and the catalog test suite before publishing.

The structural validator cannot verify that legal text is complete or that content classification is correct; those must be reviewed against the cited source. `redistributionStatus: "verified"` is a publisher attestation.

## Rebuild the reviewed non-spell selection

The PSRD-Data SQLite snapshot is a read-only input and is not copied into this repository. To regenerate the checked-in assets and audit from the same snapshot:

```powershell
python catalog\v2\build_nonspell_catalog.py --source-dir <path-to-psrd-data-76ea478>
python catalog\v2\validate_catalog.py --allow-placeholder
python -m unittest discover -s catalog\v2\tests
```

The builder checks that each selected book title appears in the embedded Section 15 notice, maps every asset item to an immutable book-database URL and revision, enforces both consumer limits, and records each held source record with its batch, source, parent, and reason in the review queue and linked audit. It deliberately does not infer a record's rights from database presence alone.
