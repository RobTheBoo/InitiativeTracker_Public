import argparse
import html
import hashlib
import html.parser
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REVISION = "76ea4784604145ba3dea40eb56f83bb904759467"
SOURCE_REPOSITORY = "https://github.com/devonjones/PSRD-Data"
OFFICIAL_OGL_SOURCE = "https://legacy.aonprd.com/openGameLicense.html"
OGL_DECLARATION = (
    "Product Identity: The following items are hereby identified as Product "
    "Identity, as defined in the Open Game License 1.0a, Section 1(e), and are "
    "not Open Content: All trademarks, registered trademarks, proper names "
    "(characters, deities, etc.), dialogue, plots, storylines, locations, "
    "characters, artworks, and trade dress. (Elements that have previously "
    "been designated as Open Game Content are not included in this declaration.)\n\n"
    "Open Content: Except for material designated as Product Identity (see above), "
    "the game mechanics of this Paizo Publishing game product are Open Game "
    "Content, as defined in the Open Game License version 1.0a Section 1(d). "
    "No portion of this work other than the material designated as Open Game "
    "Content may be reproduced in any form without written permission."
)
RULESET = {"id": "PTFD", "edition": "1e"}

BOOK_DATABASES = {
    "Core Rulebook": "book-cr.db",
    "Advanced Players Guide": "book-apg.db",
    "Advanced Player's Guide": "book-apg.db",
    "Advanced Class Guide": "book-acg.db",
    "Advanced Race Guide": "book-arg.db",
    "Bestiary": "book-b1.db",
    "Bestiary 2": "book-b2.db",
    "Bestiary 3": "book-b3.db",
    "Bestiary 4": "book-b4.db",
    "Game Mastery Guide": "book-gmg.db",
    "Monster Codex": "book-mc.db",
    "Mythic Adventures": "book-ma.db",
    "NPC Codex": "book-npc.db",
    "Ultimate Combat": "book-uc.db",
    "Ultimate Campaign": "book-ucampaign.db",
    "Ultimate Equipment": "book-ue.db",
    "Ultimate Magic": "book-um.db",
}
SECTION15_TITLES = {
    "Core Rulebook": "Pathfinder Roleplaying Game Core Rulebook",
    "Advanced Players Guide": "Pathfinder Roleplaying Game Advanced Player's Guide",
    "Advanced Player's Guide": "Pathfinder Roleplaying Game Advanced Player's Guide",
    "Advanced Class Guide": "Pathfinder Roleplaying Game Advanced Class Guide",
    "Advanced Race Guide": "Pathfinder Roleplaying Game Advanced Race Guide",
    "Bestiary": "Pathfinder Roleplaying Game Bestiary",
    "Bestiary 2": "Pathfinder Roleplaying Game Bestiary 2",
    "Bestiary 3": "Pathfinder Roleplaying Game Bestiary 3",
    "Bestiary 4": "Pathfinder Roleplaying Game Bestiary 4",
    "Game Mastery Guide": "Pathfinder Roleplaying Game GameMastery Guide",
    "Monster Codex": "Pathfinder Roleplaying Game Monster Codex",
    "Mythic Adventures": "Pathfinder Roleplaying Game Mythic Adventures",
    "NPC Codex": "Pathfinder Roleplaying Game NPC Codex",
    "Ultimate Combat": "Pathfinder Roleplaying Game Ultimate Combat",
    "Ultimate Campaign": "Pathfinder Roleplaying Game Ultimate Campaign",
    "Ultimate Equipment": "Pathfinder Roleplaying Game Ultimate Equipment",
    "Ultimate Magic": "Pathfinder Roleplaying Game Ultimate Magic",
}
EFFECT_PARENTS = {
    "Bestiary": "Universal Monster Rules",
    "Bestiary 2": "Universal Monster Rules",
    "Bestiary 3": "Universal Monster Rules",
    "Bestiary 4": "Universal Monster Rules",
    "Mythic Adventures": "New Universal Monster Rules",
}
EFFECT_SOURCES = tuple(EFFECT_PARENTS)
CREATURE_SOURCES = (
    "Bestiary",
    "Bestiary 2",
    "Bestiary 3",
    "Bestiary 4",
    "Game Mastery Guide",
    "Monster Codex",
    "Mythic Adventures",
    "NPC Codex",
    "Ultimate Magic",
)
CLASS_FEATURE_REVIEW_EXCLUSIONS = {
    "Core Rulebook": {
        "Armor Mastery": "corrupted-source-text",
        "Divine Health": "references-potential-product-identity",
        "Favored Enemy": "creature-category-table-needs-individual-review",
        "Swift Tracker": "corrupted-source-text",
    },
    "Advanced Player's Guide": {
        "Alchemy": "corrupted-source-text",
        "Bomb": "corrupted-source-text",
        "Mutagen": "corrupted-source-text",
    },
    "Advanced Class Guide": {
        "Swift Tracker": "corrupted-source-text",
    },
    "Ultimate Magic": {
        "Spellstrike": "corrupted-source-text",
    },
    "Ultimate Combat": {
        "Grit": "contains-nonmechanical-flavor-prose",
        "Mounted Archer": "corrupted-source-text",
    },
}
CLASS_FEATURE_SOURCES = tuple(CLASS_FEATURE_REVIEW_EXCLUSIONS)
CREATURE_NAME_RISK = re.compile(
    r"\b(?:gorthek|yzobu|xenopterid)\b|worm that walks",
    re.IGNORECASE,
)
ITEM_SOURCES = tuple(
    source for source in SECTION15_TITLES if source in BOOK_DATABASES
)
ITEM_SOURCE_ORDER = ITEM_SOURCES
CREATURE_SOURCE_ORDER = CREATURE_SOURCES
ANIMAL_HANDLING_ITEM_RECORDS = {
    "Core Rulebook": {
        "Barding, Medium Creature and Large Creature",
        "Bit and Bridle",
        "Feed",
        "Saddle, Exotic",
        "Saddle, Military",
        "Saddle, Pack",
        "Saddle, Riding",
        "Saddlebags",
        "Stabling",
    },
    "Advanced Player's Guide": {
        "Animal Harness",
        "Cage",
        "Dog Sled",
    },
    "Ultimate Equipment": {
        "Animal Harness",
        "Barding",
        "Bit and Bridle",
        "Cage",
        "Feed",
        "Saddle",
        "Saddlebags",
        "Stabling",
    },
}
ITEM_NAME_RISK = re.compile(
    r"\btome of epics\b",
    re.IGNORECASE,
)
ITEM_PARENT_RISK = re.compile(r"\bartifacts?\b", re.IGNORECASE)
EFFECT_NAME_RISK = re.compile(
    r"\b(?:desna|iomedae|sarenrae|pharasma|abadar|asmodeus|golarion|"
    r"hellknight|pathfinder chronicler)\b",
    re.IGNORECASE,
)
MAX_ITEMS_PER_PACKAGE = 400
GENERATED_PACKAGE_IDS = {
    "core-reviewed-conditions",
    "bestiary-general-effects",
    "bestiary-general-effects-batch2",
    "bestiary-generic-creatures",
    "core-mundane-items",
    "apg-mundane-items",
    "acg-mundane-items",
    "ultimate-combat-general-equipment",
    "ultimate-equipment-mundane-items",
    "ultimate-equipment-mundane-items-batch2",
}


class TextExtractor(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def plain_text(value):
    if not value:
        return ""
    parser = TextExtractor()
    value = re.sub(r"&([A-Za-z]+)(?![A-Za-z0-9;])", r"&\1;", value)
    parser.feed(value)
    parser.close()
    text = html.unescape(" ".join(parser.parts))
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(
        r"(?i)\b((?:lb|lbs|oz|ounce|ounces|ft|feet|mile|miles)\.)\d+$",
        r"\1",
        text,
    )


def slug(value):
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "entry"


def unique_item_id(category, name, used, source=None):
    base = f"{category}-{slug(name)}"
    candidate = base
    if candidate in used:
        candidate = f"{base}-{slug(source or 'source')}"
    suffix = 2
    while candidate in used:
        candidate = f"{base}-{slug(source or 'source')}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


def connect_readonly(path):
    if not path.is_file():
        raise FileNotFoundError(f"Required PSRD database not found: {path}")
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def source_ref(source_name, database_name, item_ids):
    if source_name not in SECTION15_TITLES:
        raise ValueError(f"No verified Section 15 title for {source_name}")
    return {
        "id": f"psrd-{slug(source_name)}",
        "name": SECTION15_TITLES[source_name],
        "url": (
            f"{SOURCE_REPOSITORY}/blob/{REVISION}/{database_name}"
        ),
        "revision": REVISION,
        "itemIds": sorted(item_ids),
    }


def package_distribution(template_distribution, items, item_sources):
    section15_text = next(
        notice["text"]
        for notice in template_distribution["notices"]
        if notice["type"] == "section15"
    )
    notices = [
        {
            "id": "paizo-product-identity-and-open-content",
            "type": "designation",
            "text": OGL_DECLARATION,
        },
        {
            "id": "official-ogl-source",
            "type": "attribution",
            "text": (
                "Paizo Publishing, LLC, Open Game License source declaration: "
                f"{OFFICIAL_OGL_SOURCE}"
            ),
        },
        {
            "id": "prd-section15",
            "type": "section15",
            "text": section15_text,
        },
    ]
    sources_by_name = defaultdict(list)
    for item in items:
        source_name, database_name = item_sources[item["id"]]
        sources_by_name[(source_name, database_name)].append(item["id"])
    sources = [
        source_ref(source_name, database_name, item_ids)
        for (source_name, database_name), item_ids in sorted(
            sources_by_name.items()
        )
    ]
    return {
        "redistributionStatus": "verified",
        "licenses": template_distribution["licenses"],
        "notices": notices,
        "sources": sources,
    }


def first_sentence(text):
    if not text:
        return "See the structured rules data."
    match = re.search(r"^(.+?[.!?])(?:\s|$)", text)
    return match.group(1) if match else text


def index_inventory(index):
    inventory = {
        "conditions": Counter(),
        "abilities": Counter(),
        "afflictions": Counter(),
        "creatures": Counter(),
        "items": Counter(),
    }
    inventory["conditions"].update(
        {
            source: count
            for source, count in index.execute(
                """
                SELECT source, COUNT(*)
                FROM central_index
                WHERE type = 'section' AND parent_name = 'Conditions'
                GROUP BY source
                """
            )
        }
    )
    for source, count in index.execute(
        "SELECT source, COUNT(*) FROM central_index WHERE type = 'ability' "
        "GROUP BY source"
    ):
        inventory["abilities"][source] = count
    for source, count in index.execute(
        "SELECT source, COUNT(*) FROM central_index WHERE type = 'affliction' "
        "GROUP BY source"
    ):
        inventory["afflictions"][source] = count
    for source, count in index.execute(
        "SELECT source, COUNT(*) FROM central_index WHERE type = 'creature' "
        "GROUP BY source"
    ):
        inventory["creatures"][source] = count
    for source, count in index.execute(
        "SELECT source, COUNT(*) FROM central_index WHERE type = 'item' "
        "GROUP BY source"
    ):
        inventory["items"][source] = count
    return inventory


def make_rule_item(category, name, source, url, text, item_id):
    if not text:
        raise ValueError(f"Empty rules text for {source}: {name}")
    return {
        "id": item_id,
        "category": category,
        "name": name,
        "description": first_sentence(text),
        "rulesData": {
            "text": text,
            "sourceReference": url,
        },
    }


def third_party_attribution_names(source_dir):
    database = connect_readonly(source_dir / "book-ogl.db")
    titles = [
        row[0]
        for row in database.execute(
            "SELECT name FROM sections "
            "WHERE lower(name) LIKE '%tome of horrors%'"
        )
    ]
    database.close()
    names = set()
    for title in titles:
        match = re.match(r"(.+?)\s+from the tome of horrors", title, re.IGNORECASE)
        if match:
            names.add(match.group(1).casefold())
    return names


def collect_conditions(index, source_dir, used_ids, third_party_names):
    rows = index.execute(
        """
        SELECT section_id, name, source, url, parent_name
        FROM central_index
        WHERE type = 'section' AND parent_name = 'Conditions'
        ORDER BY source, name
        """
    ).fetchall()
    items = []
    item_sources = {}
    included = Counter()
    included_by_parent = Counter()
    attribution_excluded = Counter()
    for section_id, name, source, url, parent_name in rows:
        database_name = BOOK_DATABASES.get(source)
        if source != "Core Rulebook" or not database_name:
            continue
        if name.casefold() in third_party_names:
            attribution_excluded[source] += 1
            continue
        book = connect_readonly(source_dir / database_name)
        body = book.execute(
            "SELECT body FROM sections WHERE section_id = ?", (section_id,)
        ).fetchone()
        book.close()
        text = plain_text(body[0] if body else "")
        item_id = unique_item_id("condition", name, used_ids)
        item = make_rule_item("condition", name, source, url, text, item_id)
        items.append(item)
        item_sources[item_id] = (source, database_name)
        included[source] += 1
        included_by_parent[(source, "Conditions")] += 1
    return items, item_sources, included, attribution_excluded, included_by_parent


def collect_effects(index, source_dir, used_ids, condition_names, third_party_names):
    rows = index.execute(
        """
        SELECT section_id, name, source, url, parent_name
        FROM central_index
        WHERE type = 'ability' AND parent_name IN (
            'Universal Monster Rules', 'New Universal Monster Rules'
        )
        ORDER BY source, name
        """
    ).fetchall()
    priority = {name: position for position, name in enumerate(EFFECT_SOURCES)}
    rows = sorted(
        rows,
        key=lambda row: (priority.get(row[2], 999), (row[1] or "").casefold()),
    )
    items = []
    item_sources = {}
    included = Counter()
    included_by_parent = Counter()
    excluded = Counter()
    exclusion_reasons = defaultdict(Counter)
    attribution_excluded = Counter()
    seen_text = defaultdict(set)
    review_outcomes = {}
    for section_id, name, source, url, parent_name in rows:
        if not name:
            excluded[source] += 1
            exclusion_reasons["missing-record-name"][source] += 1
            review_outcomes[(source, url)] = "missing-record-name"
            continue
        if source not in SECTION15_TITLES:
            excluded[source] += 1
            exclusion_reasons["outside-selected-source"][source] += 1
            review_outcomes[(source, url)] = "outside-section15-reviewed-effect-source"
            continue
        if parent_name != EFFECT_PARENTS.get(source):
            excluded[source] += 1
            exclusion_reasons["outside-selected-rules-parent"][source] += 1
            review_outcomes[(source, url)] = "outside-reviewed-universal-rule-parent"
            continue
        if name.casefold() in third_party_names:
            excluded[source] += 1
            attribution_excluded[source] += 1
            exclusion_reasons["third-party-attribution"][source] += 1
            review_outcomes[(source, url)] = "named-third-party-attribution"
            continue
        if name.casefold() in condition_names:
            excluded[source] += 1
            exclusion_reasons["condition-category-overlap"][source] += 1
            review_outcomes[(source, url)] = "condition-category-overlap"
            continue
        database_name = BOOK_DATABASES[source]
        book = connect_readonly(source_dir / database_name)
        body = book.execute(
            "SELECT body FROM sections WHERE section_id = ?", (section_id,)
        ).fetchone()
        book.close()
        text = plain_text(body[0] if body else "")
        if not text:
            excluded[source] += 1
            exclusion_reasons["empty-source-record"][source] += 1
            review_outcomes[(source, url)] = "empty-source-record"
            continue
        if text in seen_text[name.casefold()]:
            excluded[source] += 1
            exclusion_reasons["duplicate-rule-name"][source] += 1
            review_outcomes[(source, url)] = "duplicate-rule-name"
            continue
        seen_text[name.casefold()].add(text)
        item_id = unique_item_id("effect", name, used_ids)
        items.append(
            {
                "id": item_id,
                "category": "effect",
                "name": name,
                "description": first_sentence(text),
                "rulesData": {
                    "text": text,
                    "sourceReference": url,
                },
            }
        )
        item_sources[item_id] = (source, database_name)
        included[source] += 1
        included_by_parent[(source, parent_name)] += 1
    return (
        items,
        item_sources,
        included,
        excluded,
        exclusion_reasons,
        attribution_excluded,
        included_by_parent,
        review_outcomes,
    )


def collect_generic_afflictions(index, source_dir, used_ids, third_party_names):
    rows = index.execute(
        """
        SELECT section_id, name, source, parent_name, url
        FROM central_index
        WHERE type = 'affliction'
        ORDER BY source, parent_name, name
        """
    ).fetchall()
    items = []
    item_sources = {}
    included = Counter()
    included_by_parent = Counter()
    review_outcomes = {}
    for section_id, name, source, parent, url in rows:
        if not name:
            review_outcomes[(source, url)] = "missing-record-name"
            continue
        if source not in SECTION15_TITLES:
            continue
        if name.casefold() in third_party_names:
            review_outcomes[(source, url)] = "named-third-party-attribution"
            continue
        database_name = BOOK_DATABASES[source]
        book = connect_readonly(source_dir / database_name)
        book.row_factory = sqlite3.Row
        detail = book.execute(
            "SELECT contracted, save, onset, frequency, effect, "
            "initial_effect, secondary_effect, cure, cost "
            "FROM affliction_details WHERE section_id = ?",
            (section_id,),
        ).fetchone()
        book.close()
        if detail is None:
            review_outcomes[(source, url)] = "missing-structured-affliction-mechanics"
            continue
        field_names = {
            "contracted": "contracted",
            "save": "save",
            "onset": "onset",
            "frequency": "frequency",
            "effect": "effect",
            "initial_effect": "initialEffect",
            "secondary_effect": "secondaryEffect",
            "cure": "cure",
            "cost": "cost",
        }
        details = {
            target: plain_text(str(detail[field]))
            for field, target in field_names.items()
            if detail[field] not in (None, "")
        }
        details = {
            key: value
            for key, value in details.items()
            if value and value != "\u2014" and "\ufffd" not in value
        }
        if not details:
            review_outcomes[(source, url)] = "empty-or-corrupted-affliction-mechanics"
            continue
        item_id = unique_item_id("effect", name, used_ids, source)
        affliction_label = {
            "Diseases": "disease",
            "Poison": "poison",
        }.get(parent, "affliction")
        items.append(
            {
                "id": item_id,
                "category": "effect",
                "name": name,
                "description": (
                    f"Generic {affliction_label} mechanics from {SECTION15_TITLES[source]}."
                ),
                "rulesData": {
                    "afflictionType": parent,
                    **details,
                    "sourceReference": url,
                },
            }
        )
        item_sources[item_id] = (source, database_name)
        included[source] += 1
        included_by_parent[(source, parent)] += 1
    return items, item_sources, included, included_by_parent, review_outcomes


def collect_other_abilities(
    index,
    source_dir,
    used_ids,
    existing_names,
    existing_effect_items,
    third_party_names,
):
    source_placeholders = ",".join("?" for _ in SECTION15_TITLES)
    rows = index.execute(
        f"""
        SELECT section_id, name, source, url, parent_name
        FROM central_index
        WHERE type = 'ability' AND source IN ({source_placeholders})
        ORDER BY source, parent_name, name
        """,
        tuple(SECTION15_TITLES),
    ).fetchall()
    items = []
    item_sources = {}
    included = Counter()
    included_by_parent = Counter()
    review_outcomes = {}
    blocked_names = set(existing_names)
    seen_text = defaultdict(set)
    for existing in existing_effect_items:
        text = existing.get("rulesData", {}).get("text")
        if text:
            seen_text[existing["name"].casefold()].add(text)
    for section_id, name, source, url, parent in rows:
        if not name:
            review_outcomes[(source, url)] = "missing-record-name"
            continue
        if parent in ("Universal Monster Rules", "New Universal Monster Rules"):
            continue
        if source in CLASS_FEATURE_REVIEW_EXCLUSIONS and parent == "Class Features":
            continue
        if name.casefold() in third_party_names:
            review_outcomes[(source, url)] = "named-third-party-attribution"
            continue
        if EFFECT_NAME_RISK.search(name):
            review_outcomes[(source, url)] = "potential-product-identity-name-marker"
            continue
        name_key = name.casefold()
        book = connect_readonly(source_dir / BOOK_DATABASES[source])
        body = book.execute(
            "SELECT body FROM sections WHERE section_id = ?", (section_id,)
        ).fetchone()
        book.close()
        text = plain_text(body[0] if body else "")
        if not text or "\ufffd" in text:
            review_outcomes[(source, url)] = "empty-or-corrupted-rule-text"
            continue
        if name_key in blocked_names or text in seen_text[name_key]:
            review_outcomes[(source, url)] = "duplicate-rule-name"
            continue
        seen_text[name_key].add(text)
        item_id = unique_item_id("effect", name, used_ids, source)
        items.append(
            {
                "id": item_id,
                "category": "effect",
                "name": name,
                "description": first_sentence(text),
                "rulesData": {"text": text, "sourceReference": url},
            }
        )
        item_sources[item_id] = (source, BOOK_DATABASES[source])
        included[source] += 1
        included_by_parent[(source, parent)] += 1
    return items, item_sources, included, included_by_parent, review_outcomes


def collect_generic_class_features(
    index,
    source_dir,
    used_ids,
    existing_names,
    existing_effect_items,
    third_party_names,
):
    items = []
    item_sources = {}
    included = Counter()
    included_by_parent = Counter()
    blocked_names = set(existing_names)
    seen_text = defaultdict(set)
    for existing in existing_effect_items:
        text = existing.get("rulesData", {}).get("text")
        if text:
            seen_text[existing["name"].casefold()].add(text)
    review_outcomes = {}
    for source in CLASS_FEATURE_SOURCES:
        rows = index.execute(
            f"""
            SELECT section_id, name, source, url
            FROM central_index
            WHERE type = 'ability' AND source = ?
              AND parent_name = 'Class Features'
            ORDER BY name
            """,
            (source,),
        ).fetchall()
        book = connect_readonly(source_dir / BOOK_DATABASES[source])
        for section_id, name, _, url in rows:
            if not name:
                review_outcomes[(source, url)] = "missing-record-name"
                continue
            if name in CLASS_FEATURE_REVIEW_EXCLUSIONS.get(source, {}):
                review_outcomes[(source, url)] = (
                    CLASS_FEATURE_REVIEW_EXCLUSIONS[source][name]
                )
                continue
            if name.casefold() in third_party_names:
                review_outcomes[(source, url)] = "named-third-party-attribution"
                continue
            detail = book.execute(
                "SELECT body FROM sections WHERE section_id = ?", (section_id,)
            ).fetchone()
            text = plain_text(detail[0] if detail else "")
            if not text or "\ufffd" in text:
                review_outcomes[(source, url)] = (
                    "empty-or-corrupted-class-feature-text"
                )
                continue
            name_key = name.casefold()
            if name_key in blocked_names or text in seen_text[name_key]:
                review_outcomes[(source, url)] = "duplicate-class-feature-name"
                continue
            seen_text[name_key].add(text)
            item_id = unique_item_id("effect", name, used_ids, source)
            items.append(
                {
                    "id": item_id,
                    "category": "effect",
                    "name": name,
                    "description": first_sentence(text),
                    "rulesData": {
                        "text": text,
                        "sourceReference": url,
                    },
                }
            )
            item_sources[item_id] = (source, BOOK_DATABASES[source])
            included[source] += 1
            included_by_parent[(source, "Class Features")] += 1
        book.close()
    return items, item_sources, included, included_by_parent, review_outcomes


CREATURE_FIELD_NAMES = {
    "cr": "challengeRating",
    "xp": "experience",
    "alignment": "alignment",
    "size": "size",
    "creature_type": "creatureType",
    "creature_subtype": "creatureSubtype",
    "init": "initiative",
    "senses": "senses",
    "ac": "armorClass",
    "hp": "hitPoints",
    "fortitude": "fortitude",
    "reflex": "reflex",
    "will": "will",
    "defensive_abilities": "defensiveAbilities",
    "dr": "damageReduction",
    "resist": "resistances",
    "immune": "immunities",
    "sr": "spellResistance",
    "speed": "speed",
    "melee": "melee",
    "ranged": "ranged",
    "space": "space",
    "reach": "reach",
    "strength": "strength",
    "dexterity": "dexterity",
    "constitution": "constitution",
    "intelligence": "intelligence",
    "wisdom": "wisdom",
    "charisma": "charisma",
    "base_attack": "baseAttack",
    "cmb": "combatManeuverBonus",
    "cmd": "combatManeuverDefense",
    "feats": "feats",
    "skills": "skills",
    "languages": "languages",
    "hit_dice": "hitDice",
    "natural_armor": "naturalArmor",
}


def collect_creatures(index, source_dir, used_ids, third_party_names):
    rows = index.execute(
        """
        SELECT section_id, name, source, url, creature_type, parent_name
        FROM central_index
        WHERE type = 'creature'
        ORDER BY source, name
        """
    ).fetchall()
    priority = {name: position for position, name in enumerate(CREATURE_SOURCE_ORDER)}
    rows = sorted(rows, key=lambda row: (priority.get(row[2], 999), row[1].casefold()))
    items = []
    item_sources = {}
    included = Counter()
    excluded = Counter()
    name_excluded = Counter()
    attribution_excluded = Counter()
    included_by_parent = Counter()
    seen = defaultdict(set)
    review_outcomes = {}
    for section_id, name, source, url, indexed_type, parent_name in rows:
        if not name:
            excluded[source] += 1
            review_outcomes[(source, url)] = "missing-record-name"
            continue
        if source not in CREATURE_SOURCES:
            excluded[source] += 1
            review_outcomes[(source, url)] = "outside-reviewed-creature-source"
            continue
        if name.casefold() in third_party_names:
            attribution_excluded[source] += 1
            review_outcomes[(source, url)] = "named-third-party-attribution"
            continue
        if CREATURE_NAME_RISK.search(name):
            name_excluded[source] += 1
            review_outcomes[(source, url)] = (
                "potential-product-identity-name-marker"
            )
            continue
        database_name = BOOK_DATABASES[source]
        book = connect_readonly(source_dir / database_name)
        book.row_factory = sqlite3.Row
        detail = book.execute(
            "SELECT * FROM creature_details WHERE section_id = ?", (section_id,)
        ).fetchone()
        book.close()
        if detail is None:
            excluded[source] += 1
            review_outcomes[(source, url)] = "missing-creature-statistics"
            continue
        stats = {
            target: plain_text(str(detail[source_field]))
            for source_field, target in CREATURE_FIELD_NAMES.items()
            if detail[source_field] not in (None, "")
        }
        stats = {
            key: value
            for key, value in stats.items()
            if value not in ("", "\u2014")
        }
        signature = json.dumps(stats, sort_keys=True, ensure_ascii=False)
        name_key = name.casefold()
        if signature in seen[name_key]:
            excluded[source] += 1
            review_outcomes[(source, url)] = "duplicate-creature-stat-block"
            continue
        seen[name_key].add(signature)
        stats["sourceReference"] = url
        size = stats.get("size", "")
        creature_type = stats.get("creatureType", indexed_type)
        cr = stats.get("challengeRating")
        description = f"{size} {creature_type} entry".strip()
        if cr:
            description += f"; CR {cr}"
        description += "."
        item_id = unique_item_id("creature", name, used_ids)
        items.append(
            {
                "id": item_id,
                "category": "creature",
                "name": name,
                "description": description,
                "rulesData": stats,
            }
        )
        item_sources[item_id] = (source, database_name)
        included[source] += 1
        included_by_parent[(source, parent_name)] += 1
    return (
        items,
        item_sources,
        included,
        excluded,
        name_excluded,
        attribution_excluded,
        included_by_parent,
        review_outcomes,
    )


def item_attributes(book, section_id, source, corrupted_fields):
    book.row_factory = sqlite3.Row
    detail = book.execute(
        "SELECT aura, slot, cl, price, weight FROM item_details "
        "WHERE section_id = ?",
        (section_id,),
    ).fetchone()
    details = {}
    if detail:
        field_names = {
            "aura": "aura",
            "slot": "slot",
            "cl": "casterLevel",
            "price": "price",
            "weight": "weight",
        }
        for field in field_names:
            if detail[field] in (None, ""):
                continue
            value = plain_text(str(detail[field]))
            if "\ufffd" in value:
                corrupted_fields[(source, field)] += 1
                continue
            if value == "\u2014":
                corrupted_fields[(source, f"{field}:unspecified")] += 1
                continue
            details[field_names[field]] = value
    table_fields = []
    for row in book.execute(
        "SELECT field, subsection, value FROM item_misc WHERE section_id = ? "
        "ORDER BY item_misc_id",
        (section_id,),
    ):
        value = plain_text(row["value"])
        if "\ufffd" in value:
            corrupted_fields[(source, row["field"])] += 1
            continue
        if value == "\u2014":
            corrupted_fields[(source, f"{row['field']}:unspecified")] += 1
            continue
        if value:
            field = {"field": row["field"], "value": value}
            if row["subsection"]:
                field["subsection"] = row["subsection"]
            table_fields.append(field)
    return details, table_fields


def collect_items(index, source_dir, used_ids, third_party_names):
    placeholders = ",".join("?" for _ in ITEM_SOURCES)
    rows = index.execute(
        f"""
        SELECT section_id, name, source, parent_name, url
        FROM central_index
        WHERE type = 'item' AND source IN ({placeholders})
        ORDER BY source, parent_name, name
        """,
        ITEM_SOURCE_ORDER,
    ).fetchall()
    source_priority = {
        source: position for position, source in enumerate(ITEM_SOURCE_ORDER)
    }
    rows = sorted(
        rows,
        key=lambda row: (
            source_priority[row[2]],
            row[1].casefold(),
            (row[3] or "").casefold(),
        ),
    )
    candidates = []
    corrupted_fields = Counter()
    for section_id, name, source, parent_name, url in rows:
        database_name = BOOK_DATABASES[source]
        book = connect_readonly(source_dir / database_name)
        details, table_fields = item_attributes(
            book, section_id, source, corrupted_fields
        )
        book.close()
        source_reference = url
        rules_data = {
            "group": parent_name,
            "details": details,
            "tableFields": table_fields,
            "sourceReference": source_reference,
        }
        duplicate_model = {
            "name": name,
            "details": details,
            "tableFields": table_fields,
        }
        candidates.append(
            {
                "name": name,
                "source": source,
                "database": database_name,
                "url": url,
                "parent": parent_name,
                "animalHandling": name in ANIMAL_HANDLING_ITEM_RECORDS.get(source, set()),
                "rulesData": rules_data,
                "signature": json.dumps(
                    duplicate_model, sort_keys=True, ensure_ascii=False
                ),
            }
        )

    canonical = {}
    duplicates = Counter()
    conflicting_names = Counter()
    name_excluded = Counter()
    attribution_excluded = Counter()
    selected = []
    review_outcomes = {}
    for candidate in candidates:
        if candidate["name"].casefold() in third_party_names:
            attribution_excluded[candidate["source"]] += 1
            review_outcomes[(candidate["source"], candidate["url"])] = (
                "named-third-party-attribution"
            )
            continue
        if ITEM_PARENT_RISK.search(candidate["parent"] or ""):
            name_excluded[candidate["source"]] += 1
            review_outcomes[(candidate["source"], candidate["url"])] = (
                "artifact-parent-held-for-individual-pi-review"
            )
            continue
        if ITEM_NAME_RISK.search(candidate["name"]):
            name_excluded[candidate["source"]] += 1
            review_outcomes[(candidate["source"], candidate["url"])] = (
                "potential-product-identity-name-marker"
            )
            continue
        if not candidate["rulesData"]["details"] and not candidate["rulesData"]["tableFields"]:
            review_outcomes[(candidate["source"], candidate["url"])] = (
                "missing-structured-item-mechanics"
            )
            continue
        name_key = candidate["name"].casefold()
        existing_signatures = canonical.setdefault(name_key, set())
        if candidate["signature"] in existing_signatures:
            duplicates[candidate["source"]] += 1
            review_outcomes[(candidate["source"], candidate["url"])] = (
                "duplicate-item-record"
            )
            continue
        existing_signatures.add(candidate["signature"])
        selected.append(candidate)

    by_source = defaultdict(list)
    item_sources = {}
    supplemental_included = Counter()
    included_by_parent = Counter()
    for candidate in selected:
        if candidate["animalHandling"]:
            supplemental_included[candidate["source"]] += 1
        included_by_parent[(candidate["source"], candidate["parent"])] += 1
        details = candidate["rulesData"]["details"]
        summary_parts = []
        if details.get("price"):
            summary_parts.append(f"price {details['price'].rstrip(' .')}")
        if details.get("weight"):
            summary_parts.append(f"weight {details['weight'].rstrip(' .')}")
        description = "Mundane equipment entry"
        if summary_parts:
            description += "; " + ", ".join(summary_parts)
        description += "."
        item_id = unique_item_id(
            "item", candidate["name"], used_ids, candidate["source"]
        )
        item = {
            "id": item_id,
            "category": "item",
            "name": candidate["name"],
            "description": description,
            "rulesData": candidate["rulesData"],
        }
        by_source[candidate["source"]].append(item)
        item_sources[item_id] = (candidate["source"], candidate["database"])
    for items in by_source.values():
        items.sort(key=lambda item: item["name"].casefold())
    return (
        by_source,
        item_sources,
        duplicates,
        conflicting_names,
        corrupted_fields,
        name_excluded,
        attribution_excluded,
        supplemental_included,
        included_by_parent,
        review_outcomes,
    )


def source_inventory(index):
    records = []
    queries = (
        ("condition", "type = 'section' AND parent_name = 'Conditions'"),
        ("ability", "type = 'ability'"),
        ("affliction", "type = 'affliction'"),
        ("creature", "type = 'creature'"),
        ("item", "type = 'item'"),
    )
    for category, predicate in queries:
        rows = index.execute(
            "SELECT source, type, COALESCE(parent_name, ''), COUNT(*) "
            f"FROM central_index WHERE {predicate} "
            "GROUP BY source, type, parent_name ORDER BY source, parent_name"
        )
        for source, item_type, parent, count in rows:
            records.append(
                {
                    "inventory": category,
                    "source": source,
                    "recordType": item_type,
                    "parent": parent or None,
                    "count": count,
                }
            )
    return records


def record_review(
    index,
    package_for_record,
    third_party_names,
    effect_review_outcomes,
    creature_review_outcomes,
    item_review_outcomes,
):
    queries = (
        ("condition", "type = 'section' AND parent_name = 'Conditions'"),
        ("effect", "type IN ('ability', 'affliction')"),
        ("creature", "type = 'creature'"),
        ("item", "type = 'item'"),
    )
    records = []
    batch_counts = defaultdict(Counter)
    batch_metadata = {}
    for category, predicate in queries:
        rows = index.execute(
            "SELECT index_id, section_id, type, name, source, parent_name, url, "
            "creature_type FROM central_index "
            f"WHERE {predicate} ORDER BY source, parent_name, name, section_id"
        )
        for (
            index_id,
            section_id,
            record_type,
            name,
            source,
            parent,
            url,
            creature_type,
        ) in rows:
            name = name or ""
            parent = parent or ""
            record_key = f"{category}:{index_id}"
            source_key = (
                f"{slug(source)}-{hashlib.sha256(source.encode()).hexdigest()[:8]}"
            )
            parent_name = parent or "unclassified"
            parent_key = (
                f"{slug(parent_name)}-"
                f"{hashlib.sha256(parent_name.encode()).hexdigest()[:8]}"
            )
            batch_id = f"{category}:{source_key}:{parent_key}"
            batch_metadata[batch_id] = (category, source, parent or None)
            package_id = package_for_record.get((category, source, url))
            if package_id:
                disposition = "included"
                reason = "source-section15-and-reviewed-category-policy"
            elif name.casefold() in third_party_names:
                disposition = "held"
                reason = "named-third-party-attribution"
            elif category == "condition":
                disposition = "held"
                reason = "outside-reviewed-condition-source"
            elif category == "effect":
                disposition = "held"
                if (
                    source in CLASS_FEATURE_REVIEW_EXCLUSIONS
                    and parent == "Class Features"
                    and name in CLASS_FEATURE_REVIEW_EXCLUSIONS[source]
                ):
                    reason = CLASS_FEATURE_REVIEW_EXCLUSIONS[source][name]
                elif (source, url) in effect_review_outcomes:
                    reason = effect_review_outcomes[(source, url)]
                else:
                    reason = "outside-section15-reviewed-effect-source"
            elif category == "creature":
                disposition = "held"
                if (source, url) in creature_review_outcomes:
                    reason = creature_review_outcomes[(source, url)]
                else:
                    reason = "duplicate-or-unusable-creature-record"
            else:
                disposition = "held"
                if (source, url) in item_review_outcomes:
                    reason = item_review_outcomes[(source, url)]
                elif ITEM_NAME_RISK.search(name):
                    reason = "potential-product-identity-name-marker"
                else:
                    reason = "outside-section15-reviewed-item-source"

            records.append(
                {
                    "recordKey": record_key,
                    "reviewBatch": batch_id,
                    "category": category,
                    "recordType": record_type,
                    "source": source,
                    "sourceDatabase": BOOK_DATABASES.get(source),
                    "parent": parent or None,
                    "indexId": index_id,
                    "sectionId": section_id,
                    "name": name,
                    "sourceReference": url,
                    "disposition": disposition,
                    "reason": reason,
                    "packageId": package_id,
                }
            )
            batch_counts[batch_id][(disposition, reason)] += 1

    batches = []
    for batch_id, decisions in sorted(batch_counts.items()):
        category, source, parent = batch_metadata[batch_id]
        reasons = Counter()
        dispositions = Counter()
        for (disposition, reason), count in decisions.items():
            reasons[reason] += count
            dispositions[disposition] += count
        batches.append(
            {
                "id": batch_id,
                "category": category,
                "source": source,
                "parent": parent,
                "recordCount": sum(decisions.values()),
                "includedCount": dispositions["included"],
                "heldCount": dispositions["held"],
                "decisionsByReason": dict(sorted(reasons.items())),
            }
        )
    summary = {
        category: {
            "included": sum(
                row["disposition"] == "included"
                for row in records
                if row["category"] == category
            ),
            "held": sum(
                row["disposition"] == "held"
                for row in records
                if row["category"] == category
            ),
        }
        for category, _ in queries
    }
    return records, batches, summary


def records_by_source_parent(counts):
    return [
        {
            "source": source,
            "parent": parent or None,
            "count": count,
        }
        for (source, parent), count in sorted(
            counts.items(), key=lambda entry: (entry[0][0], entry[0][1] or "")
        )
    ]


def pending_by_source_parent(inventory, included):
    totals = Counter()
    for record in inventory:
        category = record["inventory"]
        if category in ("ability", "affliction"):
            category = "effect"
        totals[(category, record["source"], record["parent"] or "")] += record[
            "count"
        ]

    pending = defaultdict(list)
    for (category, source, parent), total in sorted(
        totals.items(), key=lambda entry: (entry[0][0], entry[0][1], entry[0][2])
    ):
        included_counts = included.get(category, Counter())
        parent_key = parent or ""
        included_count = included_counts.get((source, parent_key), 0)
        if not parent_key:
            included_count += included_counts.get((source, None), 0)
        remaining = total - included_count
        if remaining > 0:
            pending[category].append(
                {"source": source, "parent": parent or None, "count": remaining}
            )
    return dict(pending)


def inspect_license_database(source_dir, selected_items):
    database = connect_readonly(source_dir / "book-ogl.db")
    community_use_count = database.execute(
        "SELECT COUNT(*) FROM sections "
        "WHERE lower(name) LIKE '%community use license%'"
    ).fetchone()[0]
    third_party = [
        row[0]
        for row in database.execute(
            "SELECT name FROM sections "
            "WHERE lower(name) LIKE '%tome of horrors%'"
        )
    ]
    selected_names = {item["name"].casefold() for item in selected_items}
    named_attributions = []
    for title in third_party:
        match = re.match(r"(.+?)\s+from the tome of horrors", title, re.IGNORECASE)
        if match:
            named_attributions.append(match.group(1).casefold())
    matching_third_party = sum(
        name in selected_names for name in named_attributions
    )
    database.close()
    return {
        "communityUseLicenseNamedRowsExcluded": community_use_count,
        "tomeOfHorrorsRelatedLicenseRows": len(third_party),
        "tomeOfHorrorsNamedAttributions": len(named_attributions),
        "selectedRecordsMatchingTomeOfHorrorsAttributions": matching_third_party,
    }


def package_entry(package_id, name, description, categories, asset_bytes, source):
    return {
        "id": package_id,
        "name": name,
        "version": "1.0.0",
        "description": description,
        "downloadUrl": (
            "https://raw.githubusercontent.com/RobTheBoo/InitiativeTracker_Public/"
            f"__DATA_COMMIT_SHA__/catalog/v2/packages/{package_id}-1.0.0.json"
        ),
        "format": "json",
        "assetSchemaVersion": 2,
        "sizeBytes": len(asset_bytes),
        "sha256": hashlib.sha256(asset_bytes).hexdigest(),
        "license": "OGL-1.0a",
        "redistributionStatus": "verified",
        "notices": [
            "Includes Paizo's Product Identity/Open Game Content declaration; "
            "only generic game mechanics are selected.",
            "Includes the complete OGL 1.0a and applicable Section 15 notices.",
        ],
        "source": source,
        "ruleset": RULESET,
        "categories": categories,
        "language": "en",
    }


def build_package(
    package_id,
    name,
    description,
    category,
    items,
    item_sources,
    template_distribution,
):
    asset = {
        "schemaVersion": 2,
        "id": package_id,
        "name": name,
        "ruleset": RULESET,
        "items": items,
        "distribution": package_distribution(
            template_distribution, items, item_sources
        ),
    }
    asset_bytes = (
        json.dumps(asset, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    ).encode("utf-8")
    source_names = sorted(
        {item_sources[item["id"]][0] for item in items}
    )
    for source_name in source_names:
        title = SECTION15_TITLES[source_name]
        if title.casefold() not in package_distribution(
            template_distribution, items, item_sources
        )["notices"][-1]["text"].casefold():
            raise ValueError(f"Section 15 notice is missing {title}")
    return asset, asset_bytes


def source_summary(package_items, item_sources):
    counts = Counter(item_sources[item["id"]][0] for item in package_items)
    return [{"source": source, "itemCount": counts[source]} for source in sorted(counts)]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    path.write_bytes(data)
    return len(data)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Build conservative non-spell v2 packages and coverage evidence "
            "from a read-only PSRD-Data snapshot."
        )
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        type=Path,
        help="Directory containing index.db and the source book-*.db files",
    )
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    for filename in ("index.db", "book-ogl.db", *BOOK_DATABASES.values()):
        if not (source_dir / filename).is_file():
            raise FileNotFoundError(f"Missing source snapshot database: {filename}")

    template_path = ROOT / "packages" / "core-reviewed-spells-1.0.0.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))
    template_distribution = template["distribution"]
    section15_text = next(
        notice["text"]
        for notice in template_distribution["notices"]
        if notice["type"] == "section15"
    )
    for source_name in (
        "Core Rulebook",
        "Advanced Players Guide",
        "Advanced Class Guide",
        "Bestiary",
        "Bestiary 2",
        "Bestiary 3",
        "Bestiary 4",
        "Monster Codex",
        "Mythic Adventures",
        "Ultimate Combat",
        "Ultimate Equipment",
        "Ultimate Magic",
    ):
        title = SECTION15_TITLES[source_name]
        if title.casefold() not in section15_text.casefold():
            raise ValueError(f"Embedded Section 15 does not cover {title}")

    index = connect_readonly(source_dir / "index.db")
    used_ids = set()
    third_party_names = third_party_attribution_names(source_dir)
    (
        condition_items,
        condition_sources,
        condition_counts,
        condition_attribution_excluded,
        condition_parent_counts,
    ) = collect_conditions(
        index, source_dir, used_ids, third_party_names
    )
    condition_names = {item["name"].casefold() for item in condition_items}
    (
        effect_items,
        effect_sources,
        effect_counts,
        effect_excluded,
        effect_exclusion_reasons,
        effect_attribution_excluded,
        effect_parent_counts,
        universal_effect_review_outcomes,
    ) = collect_effects(
        index, source_dir, used_ids, condition_names, third_party_names
    )
    ability_effect_counts = effect_counts.copy()
    (
        generic_affliction_items,
        generic_affliction_sources,
        generic_affliction_counts,
        generic_affliction_parent_counts,
        affliction_review_outcomes,
    ) = collect_generic_afflictions(
        index, source_dir, used_ids, third_party_names
    )
    effect_items.extend(generic_affliction_items)
    effect_sources.update(generic_affliction_sources)
    effect_counts.update(generic_affliction_counts)
    effect_parent_counts.update(generic_affliction_parent_counts)
    (
        generic_class_feature_items,
        generic_class_feature_sources,
        generic_class_feature_counts,
        generic_class_feature_parent_counts,
        class_feature_review_outcomes,
    ) = collect_generic_class_features(
        index,
        source_dir,
        used_ids,
        condition_names,
        effect_items,
        third_party_names,
    )
    effect_items.extend(generic_class_feature_items)
    effect_sources.update(generic_class_feature_sources)
    ability_effect_counts.update(generic_class_feature_counts)
    effect_counts.update(generic_class_feature_counts)
    effect_parent_counts.update(generic_class_feature_parent_counts)
    (
        other_ability_items,
        other_ability_sources,
        other_ability_counts,
        other_ability_parent_counts,
        other_ability_review_outcomes,
    ) = collect_other_abilities(
        index,
        source_dir,
        used_ids,
        condition_names,
        effect_items,
        third_party_names,
    )
    effect_items.extend(other_ability_items)
    effect_sources.update(other_ability_sources)
    ability_effect_counts.update(other_ability_counts)
    effect_counts.update(other_ability_counts)
    effect_parent_counts.update(other_ability_parent_counts)
    effect_review_outcomes = {
        **universal_effect_review_outcomes,
        **class_feature_review_outcomes,
        **affliction_review_outcomes,
        **other_ability_review_outcomes,
    }
    (
        creature_items,
        creature_sources,
        creature_counts,
        creature_excluded,
        creature_name_excluded,
        creature_attribution_excluded,
        creature_parent_counts,
        creature_review_outcomes,
    ) = collect_creatures(index, source_dir, used_ids, third_party_names)
    (
        item_groups,
        item_sources,
        item_duplicates,
        item_conflicts,
        corrupted_item_fields,
        item_name_excluded,
        item_attribution_excluded,
        supplemental_items_included,
        item_parent_counts,
        item_review_outcomes,
    ) = collect_items(index, source_dir, used_ids, third_party_names)

    packages = []
    package_records = []
    package_for_record = {}

    def add_package(
        package_id,
        name,
        description,
        category,
        items,
        item_source_map,
        source_label,
    ):
        if not items:
            raise ValueError(f"Refusing to create an empty package: {package_id}")
        asset, asset_bytes = build_package(
            package_id,
            name,
            description,
            category,
            items,
            item_source_map,
            template_distribution,
        )
        if len(items) > 500:
            raise ValueError(f"{package_id} exceeds the 500 item consumer limit")
        if len(asset_bytes) > 2 * 1024 * 1024:
            raise ValueError(f"{package_id} exceeds the 2 MiB consumer limit")
        asset_path = ROOT / "packages" / f"{package_id}-1.0.0.json"
        asset_path.write_bytes(asset_bytes)
        for item in items:
            source_name = item_source_map[item["id"]][0]
            package_for_record[
                (category, source_name, item["rulesData"]["sourceReference"])
            ] = package_id
        packages.append(
            package_entry(
                package_id,
                name,
                description,
                [category],
                asset_bytes,
                {
                    "name": source_label,
                    "url": SOURCE_REPOSITORY,
                    "revision": REVISION,
                },
            )
        )
        package_records.append(
            {
                "id": package_id,
                "category": category,
                "itemCount": len(items),
                "sizeBytes": len(asset_bytes),
                "sha256": hashlib.sha256(asset_bytes).hexdigest(),
                "sources": source_summary(items, item_source_map),
            }
        )

    add_package(
        "core-reviewed-conditions",
        "Core rules: general conditions",
        "The 34 standard condition entries indexed under Conditions in the Core Rulebook.",
        "condition",
        condition_items,
        condition_sources,
        "PSRD-Data Core Rulebook snapshot",
    )
    effect_chunks = [
        effect_items[position : position + MAX_ITEMS_PER_PACKAGE]
        for position in range(0, len(effect_items), MAX_ITEMS_PER_PACKAGE)
    ]
    for chunk_index, chunk in enumerate(effect_chunks, 1):
        package_id = "bestiary-general-effects"
        package_name = "Generic effects, afflictions, and class features"
        source_label = "PSRD-Data rules and bestiaries snapshot"
        if chunk_index > 1:
            package_id = f"{package_id}-batch{chunk_index}"
            package_name = f"Generic effects, afflictions, and class features ({chunk_index})"
            source_label = f"{source_label}, additional set {chunk_index}"
        chunk_ids = {item["id"] for item in chunk}
        add_package(
            package_id,
            package_name,
            "Open Game Content rules mechanics from Section 15-listed sources; reviewed exceptions and record-level decisions are in the coverage audit.",
            "effect",
            chunk,
            {
                item_id: effect_sources[item_id]
                for item_id in chunk_ids
            },
            source_label,
        )
    creature_chunks = [
        creature_items[position : position + MAX_ITEMS_PER_PACKAGE]
        for position in range(0, len(creature_items), MAX_ITEMS_PER_PACKAGE)
    ]
    for chunk_index, chunk in enumerate(creature_chunks, 1):
        package_id = "bestiary-generic-creatures"
        package_name = "Generic creature stat blocks"
        if chunk_index > 1:
            package_id = f"{package_id}-batch{chunk_index}"
            package_name = f"Generic creature stat blocks ({chunk_index})"
        chunk_ids = {item["id"] for item in chunk}
        add_package(
            package_id,
            package_name,
            "Creature game statistics from Section 15-listed sources; named PI entries and flavor prose are omitted.",
            "creature",
            chunk,
            {
                item_id: creature_sources[item_id]
                for item_id in chunk_ids
            },
            "PSRD-Data Bestiaries and rules supplements snapshot",
        )

    item_package_labels = {
        "Core Rulebook": ("core-mundane-items", "Core rules: ordinary equipment"),
        "Advanced Player's Guide": (
            "apg-mundane-items",
            "Advanced Player's Guide: ordinary equipment",
        ),
        "Advanced Class Guide": (
            "acg-mundane-items",
            "Advanced Class Guide: alchemical and adventuring equipment",
        ),
        "Ultimate Combat": (
            "ultimate-combat-general-equipment",
            "Ultimate Combat: general weapons and equipment",
        ),
        "Ultimate Equipment": (
            "ultimate-equipment-mundane-items",
            "Ultimate Equipment: ordinary equipment",
        ),
        "Bestiary": ("bestiary-items", "Bestiary: game items"),
        "Bestiary 2": ("bestiary-2-items", "Bestiary 2: game items"),
        "Bestiary 3": ("bestiary-3-items", "Bestiary 3: game items"),
        "Bestiary 4": ("bestiary-4-items", "Bestiary 4: game items"),
        "Monster Codex": ("monster-codex-items", "Monster Codex: game items"),
        "Mythic Adventures": ("mythic-adventures-items", "Mythic Adventures: game items"),
        "Ultimate Magic": ("ultimate-magic-items", "Ultimate Magic: game items"),
        "Advanced Players Guide": (
            "advanced-players-guide-items",
            "Advanced Player's Guide: game items",
        ),
        "Advanced Race Guide": ("advanced-race-guide-items", "Advanced Race Guide: game items"),
        "Game Mastery Guide": ("game-mastery-guide-items", "GameMastery Guide: game items"),
        "NPC Codex": ("npc-codex-items", "NPC Codex: game items"),
        "Ultimate Campaign": ("ultimate-campaign-items", "Ultimate Campaign: game items"),
    }
    for source_name in ITEM_SOURCE_ORDER:
        items = item_groups.get(source_name, [])
        if not items:
            continue
        package_id, label = item_package_labels[source_name]
        chunks = [
            items[position : position + MAX_ITEMS_PER_PACKAGE]
            for position in range(0, len(items), MAX_ITEMS_PER_PACKAGE)
        ]
        for chunk_index, chunk in enumerate(chunks, 1):
            current_id = package_id
            current_label = label
            if chunk_index > 1:
                current_id = f"{package_id}-batch{chunk_index}"
                current_label = f"{label}, additional set {chunk_index}"
            chunk_ids = {item["id"] for item in chunk}
            chunk_sources = {
                item_id: item_sources[item_id] for item_id in chunk_ids
            }
            add_package(
                current_id,
                current_label,
                f"{len(chunk)} game item entries from {source_name}; mechanics and table facts only.",
                "item",
                chunk,
                chunk_sources,
                f"PSRD-Data {source_name} snapshot",
            )

    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing_ids = {
        entry["id"]: entry for entry in manifest["packages"]
    }
    generated_prefixes = (
        "bestiary-general-effects",
        "bestiary-generic-creatures",
        "core-mundane-items",
        "apg-mundane-items",
        "acg-mundane-items",
        "ultimate-combat-general-equipment",
        "ultimate-equipment-mundane-items",
        "bestiary-items",
        "bestiary-2-items",
        "bestiary-3-items",
        "bestiary-4-items",
        "monster-codex-items",
        "mythic-adventures-items",
        "ultimate-magic-items",
        "advanced-players-guide-items",
        "advanced-race-guide-items",
        "game-mastery-guide-items",
        "npc-codex-items",
        "ultimate-campaign-items",
    )

    def is_generated_package(package_id):
        return package_id in GENERATED_PACKAGE_IDS or any(
            package_id == prefix or package_id.startswith(prefix + "-batch")
            for prefix in generated_prefixes
        )

    retained = [
        entry
        for entry in manifest["packages"]
        if not is_generated_package(entry["id"])
    ]
    for entry in packages:
        if entry["id"] in existing_ids and not is_generated_package(entry["id"]):
            raise ValueError(f"Generated package id conflicts with existing id: {entry['id']}")
    manifest["catalogVersion"] = "2.19.0"
    manifest["packages"] = retained + packages
    write_json(manifest_path, manifest)
    generated_ids = {package["id"] for package in packages}
    for asset_path in (ROOT / "packages").glob("*.json"):
        package_id = asset_path.name.removesuffix("-1.0.0.json")
        if is_generated_package(package_id) and package_id not in generated_ids:
            asset_path.unlink()

    inventory = source_inventory(index)
    review_records, review_batches, record_review_summary = record_review(
        index,
        package_for_record,
        third_party_names,
        effect_review_outcomes,
        creature_review_outcomes,
        item_review_outcomes,
    )
    included_by_parent = {
        "condition": condition_parent_counts,
        "effect": effect_parent_counts,
        "creature": creature_parent_counts,
        "item": item_parent_counts,
    }
    counts = index_inventory(index)
    condition_all = sum(counts["conditions"].values())
    effect_inventory = counts["abilities"] + counts["afflictions"]
    creature_inventory = counts["creatures"]
    item_inventory = counts["items"]
    included = {
        "condition": sum(condition_counts.values()),
        "effect": sum(effect_counts.values()),
        "creature": sum(creature_counts.values()),
        "item": sum(len(values) for values in item_groups.values()),
    }
    inventory_totals = {
        "condition": condition_all,
        "effect": sum(effect_inventory.values()),
        "creature": sum(creature_inventory.values()),
        "item": sum(item_inventory.values()),
    }
    pending = {
        "condition": max(0, inventory_totals["condition"] - included["condition"]),
        "effect": max(0, inventory_totals["effect"] - included["effect"]),
        "creature": max(0, inventory_totals["creature"] - included["creature"]),
        "item": max(0, inventory_totals["item"] - included["item"]),
    }
    evidence = {
        "auditVersion": 1,
        "snapshot": {
            "repository": SOURCE_REPOSITORY,
            "revision": REVISION,
            "databaseFiles": sorted(
                {"index.db", *(path.name for path in source_dir.glob("book-*.db"))}
            ),
        },
        "licenseEvidence": [
            {
                "name": "Paizo OGL/Product Identity and Open Content declaration",
                "url": OFFICIAL_OGL_SOURCE,
                "scope": (
                    "The published declaration states that game mechanics are Open Game "
                    "Content except material designated Product Identity. Each included "
                    "book title is also checked against the embedded Section 15 text."
                ),
            },
            {
                "name": "Embedded Open Game License and Section 15",
                "url": (
                    "https://github.com/RobTheBoo/InitiativeTracker_Public/blob/main/"
                    "catalog/v2/packages/core-reviewed-spells-1.0.0.json"
                ),
                "scope": (
                    "The full OGL 1.0a and Section 15 notice text are copied into every "
                    "generated asset; the OGL declaration is embedded separately."
                ),
            },
            {
                "name": "Mythic Adventures Section 15 notice",
                "url": (
                    "https://github.com/devonjones/PSRD-Data/blob/"
                    f"{REVISION}/book-ma.db"
                ),
                "scope": (
                    "Mythic Adventures is listed in the embedded Section 15 notice; "
                    "its indexed game mechanics, stat blocks, and item-table facts are "
                    "selected subject to record-level exclusions."
                ),
            },
            {
                "name": "PSRD-Data book-ogl.db license records",
                "url": (
                    "https://github.com/devonjones/PSRD-Data/blob/"
                    f"{REVISION}/book-ogl.db"
                ),
                "scope": (
                    "The database's Community Use License rows are excluded. All "
                    "Tome of Horrors named attributions are checked by exact item name; "
                    "matching records are excluded before package generation."
                ),
            },
        ],
        "selectionPolicy": {
            "included": [
                "Indexed game mechanics, afflictions, creature statistics, and item-table facts from snapshot books whose exact titles appear in the embedded Section 15 notice.",
                "All indexed ability records in verified Section 15 books are reviewed; distinct same-name rules are retained, while exact duplicate text, empty/corrupted records, known PI markers, and exact third-party attributions are held with record-level reasons.",
                "Creature packages contain structured game statistics only, without artwork or narrative flavor prose.",
                "Item descriptions are generated from structured table facts; source item prose is not copied.",
                "Conditions are categorized separately from effects when their names overlap; identical duplicate records are represented once.",
            ],
            "excluded": [
                "Records from sources not named in the embedded Section 15 notice, including Technology Guide.",
                "Records whose names match individual third-party attributions in book-ogl.db.",
                "Known PI-related names and records from artifact sections are held for individual review; a hold is not a conclusion that every artifact or name is PI.",
                "Records with missing names or structured data, corrupted/empty source text, and exact duplicate data are held with record-level reasons.",
            ],
            "excludedCountsAreNotRightsDeterminations": True,
            "noImagesOrArtwork": True,
            "reviewedSection15Sources": sorted(SECTION15_TITLES),
            "reviewedClassFeatureSources": [
                {
                    "source": source,
                    "section": "Class Features",
                    "reviewedRecordCount": sum(
                        row["category"] == "effect"
                        and row["source"] == source
                        and row["parent"] == "Class Features"
                        for row in review_records
                    ),
                    "includedCount": sum(
                        row["category"] == "effect"
                        and row["source"] == source
                        and row["parent"] == "Class Features"
                        and row["disposition"] == "included"
                        for row in review_records
                    ),
                }
                for source in CLASS_FEATURE_SOURCES
            ],
            "classFeatureReviewOutcomes": {
                source: dict(
                    sorted(
                        Counter(
                            row["reason"]
                            for row in review_records
                            if row["category"] == "effect"
                            and row["source"] == source
                            and row["parent"] == "Class Features"
                            and row["disposition"] == "held"
                        ).items()
                    )
                )
                for source in CLASS_FEATURE_SOURCES
            },
            "reviewedClassFeatureExclusions": {
                source: dict(sorted(exclusions.items()))
                for source, exclusions in sorted(
                    CLASS_FEATURE_REVIEW_EXCLUSIONS.items()
                )
            },
        },
        "separateLicenseAndThirdPartyChecks": inspect_license_database(
            source_dir,
            condition_items + effect_items + creature_items
            + [item for items in item_groups.values() for item in items],
        ),
        "coverage": {
            "inventoryRecordsBySourceAndParent": inventory,
            "totals": inventory_totals,
            "included": included,
            "excludedOrPendingReview": pending,
            "includedBySource": {
                "condition": dict(sorted(condition_counts.items())),
                "effect": dict(sorted(effect_counts.items())),
                "creature": dict(sorted(creature_counts.items())),
                "item": {
                    source: len(items)
                    for source, items in sorted(item_groups.items())
                },
            },
            "includedBySourceAndParent": {
                category: records_by_source_parent(parent_counts)
                for category, parent_counts in included_by_parent.items()
            },
            "animalHandlingItemRecordsIncludedBySource": dict(
                sorted(supplemental_items_included.items())
            ),
            "duplicateOrNameConflictCounts": {
                "effect": dict(sorted(effect_excluded.items())),
                "effectExclusionsByReason": {
                    reason: dict(sorted(source_counts.items()))
                    for reason, source_counts in sorted(
                        effect_exclusion_reasons.items()
                    )
                },
                "creature": dict(sorted(creature_excluded.items())),
                "potentialProductIdentityCreatureNames": dict(
                    sorted(creature_name_excluded.items())
                ),
                "itemEquivalentDuplicates": dict(sorted(item_duplicates.items())),
                "itemSameNameDifferentData": dict(sorted(item_conflicts.items())),
                "potentialProductIdentityItemNames": dict(
                    sorted(item_name_excluded.items())
                ),
                "thirdPartyAttributionExclusions": {
                    "condition": dict(sorted(condition_attribution_excluded.items())),
                    "effect": dict(sorted(effect_attribution_excluded.items())),
                    "creature": dict(sorted(creature_attribution_excluded.items())),
                    "item": dict(sorted(item_attribution_excluded.items())),
                },
                "omittedCorruptItemFieldValues": [
                    {
                        "source": source,
                        "field": field,
                        "count": count,
                    }
                    for (source, field), count in sorted(corrupted_item_fields.items())
                ],
            },
            "status": (
                "Selection inventory is fully counted. Excluded/pending records are not "
                "claimed to be non-redistributable and require individual rights/content review."
            ),
            "recordReviewSummary": record_review_summary,
            "recordReviewBatchCount": len(review_batches),
        },
        "packages": package_records,
    }
    audit_path = ROOT / "evidence" / f"nonspell-coverage-{REVISION[:7]}.json"
    write_json(audit_path, evidence)
    record_audit_path = (
        ROOT / "evidence" / f"nonspell-record-review-{REVISION[:7]}.json"
    )
    pending_afflictions = Counter(
        row["source"]
        for row in review_records
        if row["category"] == "effect"
        and row["recordType"] == "affliction"
        and row["disposition"] == "held"
    )
    write_json(
        record_audit_path,
        {
            "reviewVersion": 1,
            "snapshotRevision": REVISION,
            "notice": (
                "Record dispositions reflect the documented catalog-selection rules. "
                "Held records need individual rights/content review; holding a record "
                "does not assert that it is non-redistributable."
            ),
            "summary": record_review_summary,
            "batches": review_batches,
            "records": review_records,
        },
    )
    queue = {
        "queueVersion": 1,
        "snapshotRevision": REVISION,
        "status": "pending-record-level-review",
        "notice": (
            "Held records are enumerated in the linked record-review audit. "
            "A record being held does not mean it is non-redistributable."
        ),
        "recordReviewFile": record_audit_path.name,
        "pendingRecordsByCategory": pending,
        "pendingRecordsBySourceAndParent": pending_by_source_parent(
            inventory, included_by_parent
        ),
        "pendingRecordKeys": [
            record["recordKey"]
            for record in review_records
            if record["disposition"] == "held"
        ],
        "pendingSources": {
            "effect": {
                "abilitiesOutsideIncludedRules": dict(
                    sorted(
                        (
                            source,
                            count
                            - ability_effect_counts.get(source, 0)
                            - effect_excluded.get(source, 0),
                        )
                        for source, count in counts["abilities"].items()
                    )
                ),
                "allAfflictions": dict(sorted(pending_afflictions.items())),
            },
            "creature": {
                "allNonIncludedRecords": {
                    source: count - creature_counts.get(source, 0)
                    for source, count in sorted(counts["creatures"].items())
                    if count - creature_counts.get(source, 0)
                }
            },
            "item": {
                "allNonIncludedRecords": {
                    source: count - len(item_groups.get(source, []))
                    for source, count in sorted(counts["items"].items())
                    if count - len(item_groups.get(source, []))
                },
                "sameNameDifferentData": dict(sorted(item_conflicts.items())),
            },
        },
    }
    queue_path = ROOT / "evidence" / f"nonspell-review-queue-{REVISION[:7]}.json"
    write_json(queue_path, queue)
    index.close()
    print(
        json.dumps(
            {
                "catalogVersion": manifest["catalogVersion"],
                "packageCount": len(packages),
                "newItems": included,
                "inventoryTotals": inventory_totals,
                "pendingReview": pending,
                "audit": str(audit_path),
                "queue": str(queue_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
