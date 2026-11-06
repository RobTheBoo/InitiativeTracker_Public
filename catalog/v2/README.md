# Public data catalog v2

The v2 manifest is served separately from the legacy catalog:

`https://raw.githubusercontent.com/RobTheBoo/InitiativeTracker_Public/main/catalog/v2/manifest.json`

Manifest v2 contains only packages built with asset schemaVersion 2. Each package URL is pinned to the immutable commit containing its JSON bytes. V2 assets require `distribution` with verified redistribution status, full license text, package-wide notices, and source revision mappings for every item. The 500-item and 2 MiB limits include the embedded license and notices.

The catalog contains seven non-overlapping packages for ruleset identifier `PTFD`, edition `1e`, totaling 107 individually reviewed spells. This is a small reviewed selection, not a complete database; every other source record remains excluded and unreviewed. The identifier is a technical label only and does not imply affiliation, sponsorship, or endorsement.

`redistributionStatus: "verified"` records the publisher's documented assessment. It is not a legal opinion, independent legal review, or guarantee. The included distribution metadata must remain with every distributed copy of a package.

## Legacy demo without duplication

The original sample remains listed only in `catalog/v1/manifest.json`; it is not copied into v2. A new application combines results from the v1 and v2 manifests keyed by package `id`, so the demo appears once and legacy clients continue to read only v1.

## Publish a v2 package

1. Verify rights, complete notices, source provenance, and per-item source mappings for every item.
2. Add the final asset under `catalog/v2/packages/`, calculate the exact UTF-8 byte length and lowercase SHA-256, and set `assetSchemaVersion` to 2.
3. Commit the asset first and pin `downloadUrl` to that full commit SHA.
4. Run `python catalog\v2\validate_catalog.py` and the catalog test suite before publishing.

The structural validator cannot verify that legal text is complete or that content classification is correct; those must be reviewed against the cited source. `redistributionStatus: "verified"` is a publisher attestation.
