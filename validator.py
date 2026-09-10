import re
import os
from collections import defaultdict

import psycopg2


DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "university_mapper"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
}

NAME_ALIASES = {
    "cse": "computer science",
    "cs": "computer science",
    "ece": "electronics",
    "ee": "electrical",
    "it": "information technology",
    "aeie": "applied electronics",
    "bme": "bio-medical",
}


def normalize_name(value):
    value = value.lower()
    value = value.replace("&", "and")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_rows(cursor):
    cursor.execute(
        """
        SELECT
            u.name AS university_name,
            p.program_name,
            p.specialization,
            p.degree_type,
            p.intake,
            p.duration_years,
            p.source_url,
            p.last_verified
        FROM programs p
        JOIN universities u ON u.id = p.university_id
        ORDER BY u.name, p.degree_type, p.program_name;
        """
    )
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def find_duplicates(rows):
    grouped = defaultdict(list)
    same_program_grouped = defaultdict(list)
    for row in rows:
        key = (
            normalize_name(row["university_name"]),
            normalize_name(row["program_name"]),
            normalize_name(row["specialization"] or ""),
            normalize_name(row["degree_type"]),
        )
        grouped[key].append(row)

        same_program_key = (
            normalize_name(row["university_name"]),
            normalize_name(row["program_name"]),
            normalize_name(row["degree_type"]),
        )
        same_program_grouped[same_program_key].append(row)

    duplicates = [items for items in grouped.values() if len(items) > 1]
    duplicates.extend([items for items in same_program_grouped.values() if len(items) > 1])
    return duplicates


def find_missing_values(rows):
    issues = []
    required_fields = ["program_name", "degree_type", "intake", "duration_years", "source_url", "last_verified"]
    for row in rows:
        missing = [field for field in required_fields if row.get(field) in (None, "")]
        if missing:
            issues.append((row, missing))
    return issues


def find_naming_issues(rows):
    issues = []
    normalized_pairs = defaultdict(set)

    for row in rows:
        program_name = row["program_name"]
        normalized = normalize_name(program_name)

        for alias, canonical in NAME_ALIASES.items():
            if re.search(rf"\b{alias}\b", normalized) and canonical not in normalized:
                issues.append((row, f"Uses abbreviation '{alias.upper()}' without canonical wording '{canonical}'."))

        compact = normalized.replace(" and ", " ")
        normalized_pairs[compact].add(program_name)

    for names in normalized_pairs.values():
        if len(names) > 1:
            sample = sorted(names)
            issues.append((None, f"Potential inconsistent naming variants: {', '.join(sample)}"))

    return issues


def print_section(title, items, formatter):
    print(f"\n{title}")
    print("-" * len(title))
    if not items:
        print("PASS")
        return
    for item in items:
        print(formatter(item))


def main():
    connection = None
    try:
        connection = psycopg2.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            rows = fetch_rows(cursor)
    except psycopg2.Error as exc:
        print("University Mapper QA Report")
        print("===========================")
        print(f"Database connection failed: {exc}")
        raise
    finally:
        if connection:
            connection.close()

    duplicates = find_duplicates(rows)
    missing_values = find_missing_values(rows)
    naming_issues = find_naming_issues(rows)

    print("University Mapper QA Report")
    print("===========================")
    print(f"Rows checked: {len(rows)}")

    print_section(
        "Duplicate Programs",
        duplicates,
        lambda group: f"FAIL: {group[0]['program_name']} appears {len(group)} times.",
    )
    print_section(
        "Missing Required Values",
        missing_values,
        lambda item: f"FAIL: {item[0]['program_name']} missing {', '.join(item[1])}.",
    )
    print_section(
        "Naming Consistency",
        naming_issues,
        lambda item: f"WARN: {item[1]}",
    )

    failures = len(duplicates) + len(missing_values)
    warnings = len(naming_issues)
    print("\nSummary")
    print("-------")
    print(f"Failures: {failures}")
    print(f"Warnings: {warnings}")
    print("Status: PASS" if failures == 0 else "Status: FAIL")


if __name__ == "__main__":
    main()
