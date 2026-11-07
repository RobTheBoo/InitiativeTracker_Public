import hashlib
import json
import sys
import tempfile
import unittest
from collections import Counter
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

    def test_official_dnd_condition_excerpts_are_separate_and_attributed(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        expected = {
            "dnd-5e-2014-srd-5-1-conditions": {
                "ruleset": {"id": "DND5E", "edition": "2014-SRD-5.1"},
                "count": 14,
                "source_revision": (
                    "SRD 5.1 official PDF; SHA-256 "
                    "2504d2a0abb0a4d491a939be4f17910a2dde0312570ab8d208080225ccf0a1f0"
                ),
                "conditions": {
                    "Blinded", "Charmed", "Deafened", "Exhaustion", "Frightened",
                    "Grappled", "Incapacitated", "Invisible", "Paralyzed",
                    "Poisoned", "Prone", "Restrained", "Stunned", "Unconscious",
                },
                "omitted": "Petrified",
            },
            "dnd-5e-2024-srd-5-2-1-conditions": {
                "ruleset": {"id": "DND5E", "edition": "2024-SRD-5.2.1"},
                "count": 15,
                "source_revision": (
                    "SRD 5.2.1 official PDF; SHA-256 "
                    "8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87"
                ),
                "conditions": {
                    "Blinded", "Charmed", "Deafened", "Exhaustion", "Frightened",
                    "Grappled", "Incapacitated", "Invisible", "Paralyzed",
                    "Petrified", "Poisoned", "Prone", "Restrained", "Stunned",
                    "Unconscious",
                },
                "omitted": None,
            },
        }
        entries = {entry["id"]: entry for entry in manifest["packages"]}
        for package_id, expected_package in expected.items():
            entry = entries[package_id]
            asset = json.loads(
                (ROOT / "packages" / f"{package_id}-1.0.0.json").read_text(
                    encoding="utf-8"
                )
            )
            items = asset["items"]
            names = {item["name"] for item in items}

            self.assertEqual(entry["ruleset"], expected_package["ruleset"])
            self.assertEqual(len(items), expected_package["count"])
            self.assertTrue(all(item["category"] == "condition" for item in items))
            self.assertEqual(names, expected_package["conditions"])
            self.assertTrue(all(item["rulesData"].get("summary") for item in items))
            self.assertTrue(all(item["rulesData"].get("sourceReference") for item in items))
            self.assertIn("partial", entry["description"].casefold())
            self.assertEqual(asset["distribution"]["licenses"][0]["id"], "CC-BY-4.0")
            self.assertIn(
                "Creative Commons Attribution 4.0 International Public License",
                asset["distribution"]["licenses"][0]["text"],
            )
            self.assertIn(
                "Section 3 -- License Conditions",
                asset["distribution"]["licenses"][0]["text"],
            )
            self.assertTrue(
                any(
                    notice["type"] == "attribution"
                    and "System Reference Document" in notice["text"]
                    for notice in asset["distribution"]["notices"]
                )
            )
            self.assertTrue(
                any(
                    notice["id"] == "modifications"
                    and "JSON" in notice["text"]
                    for notice in asset["distribution"]["notices"]
                )
            )
            source = asset["distribution"]["sources"][0]
            self.assertEqual(source["revision"], expected_package["source_revision"])
            self.assertEqual(set(source["itemIds"]), {item["id"] for item in items})
            self.assertEqual(
                "Petrified" in names,
                expected_package["omitted"] is None,
            )

        review = json.loads(
            (ROOT / "evidence" / "dnd-srd-conditions-review.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            review["includedCounts"],
            {
                "dnd-5e-2014-srd-5-1-conditions": 14,
                "dnd-5e-2024-srd-5-2-1-conditions": 15,
            },
        )
        self.assertTrue(
            any(
                "Petrified" in omission
                for omission in review["omissions"]["2014-SRD-5.1"]
            )
        )

    def test_official_dnd_selected_content_has_exact_partial_coverage(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        expected = {
            "dnd-5e-2014-srd-5-1-selected-content": {
                "ruleset": {"id": "DND5E", "edition": "2014-SRD-5.1"},
                "counts": {
                    "class": 1,
                    "creature": 3,
                    "equipment": 5,
                    "magic-item": 3,
                    "rule": 1,
                    "spell": 4,
                    "tool": 1,
                },
                "source_revision": (
                    "SRD 5.1 official PDF; SHA-256 "
                    "2504d2a0abb0a4d491a939be4f17910a2dde0312570ab8d208080225ccf0a1f0"
                ),
            },
            "dnd-5e-2024-srd-5-2-1-selected-content": {
                "ruleset": {"id": "DND5E", "edition": "2024-SRD-5.2.1"},
                "counts": {
                    "class": 1,
                    "creature": 4,
                    "effect": 1,
                    "equipment": 7,
                    "magic-item": 3,
                    "rule": 1,
                    "spell": 5,
                },
                "source_revision": (
                    "SRD 5.2.1 official PDF; SHA-256 "
                    "8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87"
                ),
            },
        }
        entries = {entry["id"]: entry for entry in manifest["packages"]}
        all_ids = set()
        for package_id, expected_package in expected.items():
            entry = entries[package_id]
            asset = json.loads(
                (ROOT / "packages" / f"{package_id}-1.0.0.json").read_text(
                    encoding="utf-8"
                )
            )
            items = asset["items"]
            counts = Counter(item["category"] for item in items)
            item_ids = {item["id"] for item in items}

            self.assertEqual(entry["ruleset"], expected_package["ruleset"])
            self.assertEqual(dict(counts), expected_package["counts"])
            self.assertEqual(set(entry["categories"]), set(counts))
            self.assertTrue(all(item["rulesData"].get("summary") for item in items))
            self.assertTrue(
                all(item["rulesData"].get("sourceReference") for item in items)
            )
            self.assertIn("partial", entry["description"].casefold())
            self.assertEqual(asset["distribution"]["licenses"][0]["id"], "CC-BY-4.0")
            self.assertIn(
                "Creative Commons Attribution 4.0 International Public License",
                asset["distribution"]["licenses"][0]["text"],
            )
            self.assertTrue(
                any(
                    notice["type"] == "attribution"
                    and "System Reference Document" in notice["text"]
                    for notice in asset["distribution"]["notices"]
                )
            )
            self.assertTrue(
                any(
                    notice["id"] == "modifications"
                    and "partial" in notice["text"].casefold()
                    for notice in asset["distribution"]["notices"]
                )
            )
            source = asset["distribution"]["sources"][0]
            self.assertEqual(source["revision"], expected_package["source_revision"])
            self.assertEqual(set(source["itemIds"]), item_ids)
            self.assertFalse(all_ids & item_ids)
            all_ids.update(item_ids)

        review = json.loads(
            (ROOT / "evidence" / "dnd-srd-selected-content-review.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            review["includedCountsByPackageAndCategory"],
            {
                package_id: expected_package["counts"]
                for package_id, expected_package in expected.items()
            },
        )
        self.assertTrue(
            all(
                source["omissions"]
                for source in review["sources"]
            )
        )

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

    def test_nonspell_packages_match_the_coverage_audit(self):
        manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
        entries = [
            entry for entry in manifest["packages"]
            if set(entry["categories"]) & {"condition", "effect", "creature", "item"}
            and entry["ruleset"]["id"] == "PTFD"
        ]
        self.assertTrue(entries)
        self.assertTrue(any(entry["id"] == "core-reviewed-conditions" for entry in entries))

        counts = Counter()
        item_names = set()
        for entry in entries:
            asset = json.loads(
                (ROOT / "packages" / f"{entry['id']}-{entry['version']}.json")
                .read_text(encoding="utf-8")
            )
            counts.update(item["category"] for item in asset["items"])
            item_names.update(item["name"].casefold() for item in asset["items"])

        expected_counts = {
            "condition": 34,
            "effect": 6112,
            "creature": 1795,
            "item": 3429,
        }
        self.assertEqual(dict(counts), expected_counts)
        audit = json.loads(
            (ROOT / "evidence" / "nonspell-coverage-76ea478.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(audit["coverage"]["included"], expected_counts)
        self.assertEqual(
            audit["coverage"]["includedBySource"]["creature"]["NPC Codex"],
            310,
        )
        self.assertEqual(
            audit["coverage"]["includedBySource"]["item"]["Advanced Race Guide"],
            163,
        )
        class_feature_review = audit["selectionPolicy"]["reviewedClassFeatureSources"]
        self.assertEqual(
            {row["source"] for row in class_feature_review},
            {
                "Core Rulebook",
                "Advanced Player's Guide",
                "Advanced Class Guide",
                "Ultimate Magic",
                "Ultimate Combat",
            },
        )
        self.assertEqual(
            sum(row["includedCount"] for row in class_feature_review),
            415,
        )
        class_feature_outcomes = audit["selectionPolicy"][
            "classFeatureReviewOutcomes"
        ]
        self.assertEqual(
            class_feature_outcomes["Core Rulebook"][
                "creature-category-table-needs-individual-review"
            ],
            1,
        )
        self.assertEqual(
            class_feature_outcomes["Ultimate Combat"][
                "contains-nonmechanical-flavor-prose"
            ],
            1,
        )
        self.assertTrue(
            {
                item["name"]
                for entry in entries
                if "effect" in entry["categories"]
                for item in json.loads(
                    (ROOT / "packages" / f"{entry['id']}-{entry['version']}.json")
                    .read_text(encoding="utf-8")
                )["items"]
                if "afflictionType" in item.get("rulesData", {})
            } >= {
                "Blinding Sickness",
                "Bubonic Plague",
                "Cackle Fever",
                "Filth Fever",
                "Leprosy",
                "Mindfire",
                "Red Ache",
                "Shakes",
                "Slimy Doom",
                "Arsenic",
                "Belladonna",
                "Black Adder Venom",
                "Bloodroot",
                "Giant Wasp Poison",
                "Hemlock",
                "Large Scorpion Venom",
                "Medium Spider Venom",
                "Small Centipede Poison",
                "Wolfsbane",
                "Wyvern Poison",
            },
        )
        for category, by_parent in audit["coverage"][
            "includedBySourceAndParent"
        ].items():
            self.assertEqual(
                sum(row["count"] for row in by_parent),
                expected_counts[category],
            )
        queue = json.loads(
            (ROOT / "evidence" / "nonspell-review-queue-76ea478.json")
            .read_text(encoding="utf-8")
        )
        record_review = json.loads(
            (ROOT / "evidence" / "nonspell-record-review-76ea478.json")
            .read_text(encoding="utf-8")
        )
        self.assertEqual(
            record_review["summary"],
            {
                category: {
                    "included": expected_counts[category],
                    "held": audit["coverage"]["excludedOrPendingReview"][category],
                }
                for category in expected_counts
            },
        )
        record_keys = [row["recordKey"] for row in record_review["records"]]
        self.assertEqual(len(record_keys), len(set(record_keys)))
        reviewed_records = {
            (row["source"], row["name"]): row
            for row in record_review["records"]
            if row["category"] == "effect"
            and row["parent"] == "Class Features"
        }
        for source, name, reason in (
            ("Core Rulebook", "Armor Mastery", "corrupted-source-text"),
            (
                "Core Rulebook",
                "Divine Health",
                "references-potential-product-identity",
            ),
            (
                "Core Rulebook",
                "Favored Enemy",
                "creature-category-table-needs-individual-review",
            ),
            ("Core Rulebook", "Swift Tracker", "corrupted-source-text"),
            ("Advanced Player's Guide", "Alchemy", "corrupted-source-text"),
            ("Advanced Player's Guide", "Bomb", "corrupted-source-text"),
            ("Advanced Player's Guide", "Mutagen", "corrupted-source-text"),
            ("Advanced Class Guide", "Swift Tracker", "corrupted-source-text"),
            ("Ultimate Magic", "Spellstrike", "corrupted-source-text"),
            (
                "Ultimate Combat",
                "Grit",
                "contains-nonmechanical-flavor-prose",
            ),
            ("Ultimate Combat", "Mounted Archer", "corrupted-source-text"),
        ):
            self.assertEqual(reviewed_records[(source, name)]["reason"], reason)
        held_keys = {
            row["recordKey"]
            for row in record_review["records"]
            if row["disposition"] == "held"
        }
        self.assertEqual(set(queue["pendingRecordKeys"]), held_keys)
        self.assertTrue(all(row["reviewBatch"] for row in record_review["records"]))
        self.assertTrue(
            all(
                row["packageId"] is None
                for row in record_review["records"]
                if row["disposition"] == "held"
            )
        )
        for category in expected_counts:
            pending = queue["pendingRecordsBySourceAndParent"].get(category, [])
            self.assertEqual(
                sum(row["count"] for row in pending),
                audit["coverage"]["excludedOrPendingReview"][category],
            )
        self.assertEqual(
            audit["coverage"]["animalHandlingItemRecordsIncludedBySource"],
            {
                "Advanced Player's Guide": 3,
                "Core Rulebook": 9,
                "Ultimate Equipment": 8,
            },
        )
        creature_name_exclusions = audit["coverage"]["duplicateOrNameConflictCounts"][
            "potentialProductIdentityCreatureNames"
        ]
        self.assertLessEqual(sum(creature_name_exclusions.values()), 10)
        for held_name in (
            "gorthek",
            "gorthek mounts",
            "yzobu",
            "xenopterid",
            "worm that walks",
        ):
            self.assertNotIn(held_name, item_names)
        third_party = audit["separateLicenseAndThirdPartyChecks"]
        self.assertEqual(
            third_party["selectedRecordsMatchingTomeOfHorrorsAttributions"], 0
        )
        self.assertEqual(third_party["tomeOfHorrorsNamedAttributions"], 105)
        self.assertEqual(third_party["communityUseLicenseNamedRowsExcluded"], 2)
        attribution_exclusions = audit["coverage"]["duplicateOrNameConflictCounts"][
            "thirdPartyAttributionExclusions"
        ]
        self.assertEqual(
            sum(sum(by_source.values()) for by_source in attribution_exclusions.values()),
            94,
        )


if __name__ == "__main__":
    unittest.main()
