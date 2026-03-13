import csv
import random
import time
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path


SAMPLE_LIMIT = 8
MAP_POINT_LIMIT = 2200
TOP_TAXA_LIMIT = 12
TOP_OBSERVER_LIMIT = 12

MONTH_NAMES = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}

FAMILY_META = [
    {
        "key": "spatial",
        "title": "Spatial bias",
        "description": "Geographic holdouts and habitat labels reveal where the model sees wilderness, modified landscapes, and city-adjacent nature.",
    },
    {
        "key": "temporal",
        "title": "Temporal bias",
        "description": "Observation density is uneven across years and seasons, shaping which phenological stages dominate the dataset.",
    },
    {
        "key": "taxonomic",
        "title": "Taxonomic bias",
        "description": "Balanced and unbalanced taxon partitions expose how often a small set of plant names dominates the training signal.",
    },
    {
        "key": "sociopolitical",
        "title": "Sociopolitical bias",
        "description": "State-specific socioeconomic splits approximate who gets represented in the west coast geography and who does not.",
    },
    {
        "key": "observer",
        "title": "Observer quality",
        "description": "Engaged versus casual observers and iNaturalist quality grades surface differences in curation and contributor behavior.",
    },
    {
        "key": "reference",
        "title": "Reference partitions",
        "description": "Existing benchmark and construction splits are included so you can move from bias diagnosis to concrete evaluation subsets.",
    },
]

COLUMN_GROUP_SPECS = [
    {
        "family": "spatial",
        "key": "spatial_split",
        "label": "Spatial holdout",
        "description": "Primary train/test split that withholds geography.",
        "column": "spatial_split",
        "order": ["train", "test"],
        "labels": {"train": "Train", "test": "Test"},
    },
    {
        "family": "spatial",
        "key": "spatial_wilderness",
        "label": "Wilderness frontier",
        "description": "Partition focused on wilderness-heavy locations.",
        "column": "spatial_wilderness",
        "order": ["train", "test", "not_eligible"],
        "labels": {"train": "Train", "test": "Test", "not_eligible": "Not eligible"},
    },
    {
        "family": "spatial",
        "key": "spatial_modified",
        "label": "Modified landscapes",
        "description": "Human-modified environments separated into train/test coverage.",
        "column": "spatial_modified",
        "order": ["train", "test", "not_eligible"],
        "labels": {"train": "Train", "test": "Test", "not_eligible": "Not eligible"},
    },
    {
        "family": "spatial",
        "key": "city_nature",
        "label": "City nature",
        "description": "Nature observed close to cities.",
        "column": "city_nature",
        "order": ["train", "test"],
        "labels": {"train": "Train", "test": "Test"},
    },
    {
        "family": "spatial",
        "key": "not_city_nature",
        "label": "Away from cities",
        "description": "Counterpart to city-adjacent nature.",
        "column": "not_city_nature",
        "order": ["train", "test"],
        "labels": {"train": "Train", "test": "Test"},
    },
    {
        "family": "taxonomic",
        "key": "taxonomic_balanced",
        "label": "Balanced taxa",
        "description": "Partition curated to reduce overrepresented taxa.",
        "column": "taxonomic_balanced",
        "order": ["train", "test", "not_eligible"],
        "labels": {"train": "Train", "test": "Test", "not_eligible": "Not eligible"},
    },
    {
        "family": "taxonomic",
        "key": "taxonomic_unbalanced",
        "label": "Unbalanced taxa",
        "description": "Natural class imbalance preserved as-is.",
        "column": "taxonomic_unbalanced",
        "order": ["train", "test", "not_eligible"],
        "labels": {"train": "Train", "test": "Test", "not_eligible": "Not eligible"},
    },
    {
        "family": "taxonomic",
        "key": "rank",
        "label": "Taxonomic rank",
        "description": "Species, subspecies, genus, and other ranks represented in the CSV.",
        "column": "rank",
        "order": ["species", "subspecies", "genus", "variety", "complex"],
        "labels": {},
    },
    {
        "family": "observer",
        "key": "obs_engaged",
        "label": "Engaged observers",
        "description": "Contributors with deeper activity histories.",
        "column": "obs_engaged",
        "order": ["train", "test"],
        "labels": {"train": "Train", "test": "Test"},
    },
    {
        "family": "observer",
        "key": "obs_casual",
        "label": "Casual observers",
        "description": "Contributors with lighter activity histories.",
        "column": "obs_casual",
        "order": ["train", "test"],
        "labels": {"train": "Train", "test": "Test"},
    },
    {
        "family": "observer",
        "key": "quality_grade",
        "label": "iNaturalist quality grade",
        "description": "Research, needs ID, and casual quality labels.",
        "column": "quality_grade",
        "order": ["research", "needs_id", "casual"],
        "labels": {"needs_id": "Needs ID"},
    },
    {
        "family": "reference",
        "key": "random_split",
        "label": "Random split",
        "description": "Non-spatial baseline split.",
        "column": "random_split",
        "order": ["train", "test"],
        "labels": {"train": "Train", "test": "Test"},
    },
    {
        "family": "reference",
        "key": "inat2021",
        "label": "iNat 2021 overlap",
        "description": "Rows aligned with the iNat 2021 benchmark.",
        "column": "inat2021",
        "order": ["train", "validation", "test"],
        "labels": {"train": "Train", "validation": "Validation", "test": "Test"},
    },
    {
        "family": "reference",
        "key": "inat2021mini",
        "label": "iNat 2021 mini",
        "description": "Smaller benchmark overlap used for quick iteration.",
        "column": "inat2021mini",
        "order": ["train", "validation", "test"],
        "labels": {"train": "Train", "validation": "Validation", "test": "Test"},
    },
    {
        "family": "reference",
        "key": "imagenet",
        "label": "ImageNet overlap",
        "description": "Rows aligned with ImageNet-flavored transfer baselines.",
        "column": "imagenet",
        "order": ["train", "validation", "test"],
        "labels": {"train": "Train", "validation": "Validation", "test": "Test"},
    },
    {
        "family": "reference",
        "key": "supervised",
        "label": "Supervised availability",
        "description": "Whether the sample is included in supervised subsets.",
        "column": "supervised",
        "order": ["true", "false"],
        "labels": {"true": "Available", "false": "Held out"},
    },
    {
        "family": "reference",
        "key": "single_image",
        "label": "Single-image rows",
        "description": "Whether an observation contributes exactly one image.",
        "column": "single_image",
        "order": ["true", "false"],
        "labels": {"true": "Single image", "false": "Multiple images"},
    },
    {
        "family": "reference",
        "key": "unsupervised_shared",
        "label": "Unsupervised shared pool",
        "description": "Shared pool membership for unsupervised use.",
        "column": "unsupervised_shared",
        "order": ["true", "false"],
        "labels": {"true": "Shared", "false": "Exclusive"},
    },
    {
        "family": "reference",
        "key": "supervised_shared",
        "label": "Supervised shared pool",
        "description": "Shared pool membership for supervised use.",
        "column": "supervised_shared",
        "order": ["true", "false"],
        "labels": {"true": "Shared", "false": "Exclusive"},
    },
]

SOCIOECO_GROUP_SPECS = [
    ("alaska_socioeco", "Alaska"),
    ("arizona_socioeco", "Arizona"),
    ("baja_california_socioeco", "Baja California"),
    ("baja_california_sur_socioeco", "Baja California Sur"),
    ("british_columbia_socioeco", "British Columbia"),
    ("california_socioeco", "California"),
    ("nevada_socioeco", "Nevada"),
    ("oregon_socioeco", "Oregon"),
    ("sonora_socioeco", "Sonora"),
    ("washington_socioeco", "Washington"),
    ("yukon_socioeco", "Yukon"),
]

TEMPORAL_GROUP_SPECS = [
    {
        "family": "temporal",
        "key": "year_band",
        "label": "Year bands",
        "description": "Coarse year buckets used to surface recent collection spikes.",
        "order": ["pre_2020", "2020_2021", "2022", "2023_plus"],
        "labels": {
            "pre_2020": "Before 2020",
            "2020_2021": "2020-2021",
            "2022": "2022",
            "2023_plus": "2023+",
        },
    },
    {
        "family": "temporal",
        "key": "season",
        "label": "Seasonality",
        "description": "Month-of-year buckets that show flowering and growth season peaks.",
        "order": ["winter", "spring", "summer", "fall"],
        "labels": {
            "winter": "Winter",
            "spring": "Spring",
            "summer": "Summer",
            "fall": "Fall",
        },
    },
]


def _summary_cache_key(path: Path) -> tuple[str, int, int]:
    stat = path.stat()
    return (str(path.resolve()), stat.st_mtime_ns, stat.st_size)


def build_divshift_summary(path: Path) -> dict:
    return _build_divshift_summary_cached(*_summary_cache_key(path))


def clean_string(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_partition_value(value: object) -> str:
    normalized = clean_string(value).lower()
    if normalized in {"true", "false", "train", "test", "validation", "not_eligible", "research", "needs_id", "casual"}:
        return normalized
    return normalized


def titleize(token: str) -> str:
    if not token:
        return "Unknown"
    return token.replace("_", " ").title()


def parse_year_month(row: dict) -> tuple[int | None, int | None, str]:
    year_raw = clean_string(row.get("year"))
    observed_on = clean_string(row.get("observed_on") or row.get("date"))
    year_value = None
    month_value = None

    if year_raw.isdigit() and len(year_raw) == 4:
        year_value = int(year_raw)
    elif len(observed_on) >= 4 and observed_on[:4].isdigit():
        year_value = int(observed_on[:4])

    if len(observed_on) >= 7 and observed_on[5:7].isdigit():
        candidate = int(observed_on[5:7])
        if 1 <= candidate <= 12:
            month_value = candidate

    return year_value, month_value, observed_on


def classify_year_band(year_value: int | None) -> str | None:
    if year_value is None:
        return None
    if year_value < 2020:
        return "pre_2020"
    if year_value <= 2021:
        return "2020_2021"
    if year_value == 2022:
        return "2022"
    return "2023_plus"


def classify_season(month_value: int | None) -> str | None:
    if month_value is None:
        return None
    if month_value in {12, 1, 2}:
        return "winter"
    if month_value in {3, 4, 5}:
        return "spring"
    if month_value in {6, 7, 8}:
        return "summer"
    return "fall"


def reservoir_append(sample_state: dict, item: dict, limit: int, rng: random.Random):
    seen = int(sample_state.get("seen", 0)) + 1
    sample_state["seen"] = seen
    items = sample_state.setdefault("items", [])
    if len(items) < limit:
        items.append(item)
        return
    slot = rng.randrange(seen)
    if slot < limit:
        items[slot] = item


def try_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def make_sample(row: dict, *, partition_label: str) -> dict | None:
    state_name = clean_string(row.get("state_name")).lower()
    photo_id = clean_string(row.get("photo_id"))
    if not state_name or not photo_id.isdigit():
        return None
    year_value, _, observed_on = parse_year_month(row)
    return {
        "state_name": state_name,
        "photo_id": photo_id,
        "observation_uuid": clean_string(row.get("observation_uuid")),
        "observer_id": clean_string(row.get("observer_id")),
        "name": clean_string(row.get("name")) or "Unknown taxon",
        "rank": clean_string(row.get("rank")) or "Unknown rank",
        "quality_grade": clean_string(row.get("quality_grade")) or "unknown",
        "observed_on": observed_on,
        "year": year_value,
        "partition_label": partition_label,
    }


def make_point(row: dict) -> dict | None:
    lon = try_float(row.get("longitude"))
    lat = try_float(row.get("latitude"))
    if lon is None or lat is None:
        return None
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        return None
    return {
        "lon": lon,
        "lat": lat,
        "state_name": clean_string(row.get("state_name")).lower(),
        "split": normalize_partition_value(row.get("spatial_split")) or "unknown",
    }


def sort_counter(counter: Counter, *, limit: int | None = None) -> list[dict]:
    items = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    if limit is not None:
        items = items[:limit]
    return [{"key": key, "label": titleize(str(key)), "count": int(count)} for key, count in items]


def compute_taxon_tail_buckets(taxon_counts: Counter) -> list[dict]:
    buckets = Counter({"1": 0, "2_5": 0, "6_20": 0, "21_plus": 0})
    for count in taxon_counts.values():
        if count <= 1:
            buckets["1"] += 1
        elif count <= 5:
            buckets["2_5"] += 1
        elif count <= 20:
            buckets["6_20"] += 1
        else:
            buckets["21_plus"] += 1
    labels = {
        "1": "Singleton taxa",
        "2_5": "2-5 images",
        "6_20": "6-20 images",
        "21_plus": "21+ images",
    }
    return [{"key": key, "label": labels[key], "count": int(buckets[key])} for key in ("1", "2_5", "6_20", "21_plus")]


def build_group_payload(spec: dict, counts: dict[str, Counter], samples: dict[tuple[str, str], dict]) -> dict | None:
    counter = counts.get(spec["key"], Counter())
    if not counter:
        return None

    ordered_keys = []
    seen = set()
    for key in spec.get("order", []):
        if counter.get(key, 0) > 0:
            ordered_keys.append(key)
            seen.add(key)
    for key, _count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
        if not key or key in seen or counter[key] <= 0:
            continue
        ordered_keys.append(key)

    partitions = []
    total = sum(counter.values())
    for partition_key in ordered_keys:
        partition_count = int(counter[partition_key])
        if partition_count <= 0:
            continue
        label = spec.get("labels", {}).get(partition_key) or titleize(partition_key)
        partitions.append(
            {
                "key": partition_key,
                "label": label,
                "count": partition_count,
                "share": float(partition_count / total) if total else 0.0,
                "samples": list(samples.get((spec["key"], partition_key), {}).get("items", [])),
            }
        )

    if not partitions:
        return None

    return {
        "key": spec["key"],
        "label": spec["label"],
        "description": spec["description"],
        "total_count": int(total),
        "partitions": partitions,
    }


@lru_cache(maxsize=8)
def _build_divshift_summary_cached(path_str: str, _mtime_ns: int, _size: int) -> dict:
    path = Path(path_str)
    rng = random.Random(0)
    build_started = time.perf_counter()

    group_counts: dict[str, Counter] = defaultdict(Counter)
    group_samples: dict[tuple[str, str], dict] = {}

    total_rows = 0
    species = set()
    observers = set()
    state_counts = Counter()
    year_counts = Counter()
    month_counts = Counter()
    quality_grade_counts = Counter()
    taxon_counts = Counter()
    observer_counts = Counter()

    geo_seen = 0
    geo_points: list[dict] = []
    geo_sample_state = {"seen": 0, "items": geo_points}
    min_lon = float("inf")
    max_lon = float("-inf")
    min_lat = float("inf")
    max_lat = float("-inf")
    min_date = None
    max_date = None

    all_specs = list(COLUMN_GROUP_SPECS)
    all_specs.extend(
        {
            "family": "sociopolitical",
            "key": column,
            "label": label,
            "description": f"Sociopolitical split for {label}.",
            "column": column,
            "order": ["train", "test"],
            "labels": {"train": "Train", "test": "Test"},
        }
        for column, label in SOCIOECO_GROUP_SPECS
    )
    all_specs.extend(TEMPORAL_GROUP_SPECS)

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            total_rows += 1

            state_name = clean_string(row.get("state_name")).lower()
            if state_name:
                state_counts[state_name] += 1

            name = clean_string(row.get("name")) or "Unknown taxon"
            species.add(name)
            taxon_counts[name] += 1

            observer_id = clean_string(row.get("observer_id"))
            if observer_id:
                observers.add(observer_id)
                observer_counts[observer_id] += 1

            year_value, month_value, observed_on = parse_year_month(row)
            if year_value is not None:
                year_counts[str(year_value)] += 1
            if month_value is not None:
                month_counts[MONTH_NAMES[month_value]] += 1
            if observed_on:
                min_date = observed_on if min_date is None else min(min_date, observed_on)
                max_date = observed_on if max_date is None else max(max_date, observed_on)

            quality_grade = normalize_partition_value(row.get("quality_grade")) or "unknown"
            quality_grade_counts[quality_grade] += 1

            point = make_point(row)
            if point is not None:
                geo_seen += 1
                geo_sample_state["seen"] = geo_seen - 1
                reservoir_append(geo_sample_state, point, MAP_POINT_LIMIT, rng)
                min_lon = min(min_lon, point["lon"])
                max_lon = max(max_lon, point["lon"])
                min_lat = min(min_lat, point["lat"])
                max_lat = max(max_lat, point["lat"])

            for spec in all_specs:
                if spec["key"] == "year_band":
                    partition_key = classify_year_band(year_value)
                elif spec["key"] == "season":
                    partition_key = classify_season(month_value)
                else:
                    partition_key = normalize_partition_value(row.get(spec["column"]))
                    if not partition_key:
                        continue
                if not partition_key:
                    continue

                group_counts[spec["key"]][partition_key] += 1
                label = spec.get("labels", {}).get(partition_key) or titleize(partition_key)
                sample = make_sample(row, partition_label=label)
                if sample is None:
                    continue
                sample_state = group_samples.setdefault((spec["key"], partition_key), {"seen": 0, "items": []})
                reservoir_append(sample_state, sample, SAMPLE_LIMIT, rng)

    total_observer_rows = sum(observer_counts.values())
    top_observer_share = 0.0
    if total_observer_rows:
        top_observer_share = float(sum(count for _observer, count in observer_counts.most_common(10)) / total_observer_rows)

    families = []
    for family_meta in FAMILY_META:
        groups = []
        for spec in all_specs:
            if spec["family"] != family_meta["key"]:
                continue
            payload = build_group_payload(spec, group_counts, group_samples)
            if payload is not None:
                groups.append(payload)
        if groups:
            families.append(
                {
                    "key": family_meta["key"],
                    "title": family_meta["title"],
                    "description": family_meta["description"],
                    "groups": groups,
                }
            )

    summary = {
        "artifact_name": path.name,
        "overview": {
            "total_rows": int(total_rows),
            "distinct_species": int(len(species)),
            "distinct_observers": int(len(observers)),
            "distinct_states": int(len(state_counts)),
            "date_start": min_date,
            "date_end": max_date,
            "top_10_observer_share": top_observer_share,
            "build_seconds": round(time.perf_counter() - build_started, 2),
        },
        "families": families,
        "state_counts": sort_counter(state_counts, limit=12),
        "year_counts": sorted(
            [{"year": key, "count": int(value)} for key, value in year_counts.items()],
            key=lambda item: item["year"],
        ),
        "month_counts": [
            {"month": MONTH_NAMES[index], "count": int(month_counts.get(MONTH_NAMES[index], 0))}
            for index in range(1, 13)
        ],
        "top_taxa": [
            {"name": key, "count": int(value), "share": float(value / total_rows) if total_rows else 0.0}
            for key, value in taxon_counts.most_common(TOP_TAXA_LIMIT)
        ],
        "taxon_tail": compute_taxon_tail_buckets(taxon_counts),
        "quality_grade_counts": sort_counter(quality_grade_counts),
        "top_observers": [
            {"observer_id": key, "count": int(value), "share": float(value / total_rows) if total_rows else 0.0}
            for key, value in observer_counts.most_common(TOP_OBSERVER_LIMIT)
        ],
        "geo_points": geo_points,
        "bounds": {
            "min_lon": min_lon if min_lon != float("inf") else -180.0,
            "max_lon": max_lon if max_lon != float("-inf") else 180.0,
            "min_lat": min_lat if min_lat != float("inf") else -90.0,
            "max_lat": max_lat if max_lat != float("-inf") else 90.0,
        },
    }
    return summary
