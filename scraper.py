import re
import os
from datetime import date

import psycopg2
import requests
from bs4 import BeautifulSoup


DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "university_mapper"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "postgres"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
}

UNIVERSITY = {
    "name": "Netaji Subhash Engineering College",
    "location": "Kolkata, West Bengal, India",
    "website": "https://www.nsec.ac.in",
}

SOURCE_URLS = [
    "https://www.nsec.ac.in/page.php?id=354",
    "https://www.nsec.ac.in/page.php?id=149",
    "https://www.nsec.ac.in",
]

EXPECTED_PROGRAMS = [
    ("B.Tech. in Computer Science & Engineering", "Computer Science & Engineering", 300),
    ("B.Tech. in Computer Science and Engineering (Internet of Things)", "Internet of Things", 30),
    ("B.Tech. in Electronics & Communication Engineering", "Electronics & Communication Engineering", 120),
    ("B.Tech. in Computer Science and Business Systems", "Computer Science and Business Systems", 30),
    ("B.Tech. in Information Technology", "Information Technology", 180),
    ("B.Tech. in Applied Electronics & Instrumentation Engineering", "Applied Electronics & Instrumentation Engineering", 30),
    ("B.Tech. in Electrical Engineering", "Electrical Engineering", 60),
    ("B.Tech. in Civil Engineering", "Civil Engineering", 30),
    ("B.Tech. in Electrical and Computer Engineering", "Electrical and Computer Engineering", 60),
    ("B.Tech. in Mechanical Engineering", "Mechanical Engineering", 30),
    ("B.Tech. in Bio-Medical Engineering", "Bio-Medical Engineering", 60),
    ("B.Tech. in Computer Science and Information Technology", "Computer Science and Information Technology", 60),
    (
        "B.Tech. in Computer Science and Engineering (Artificial Intelligence and Machine Learning)",
        "Artificial Intelligence and Machine Learning",
        300,
    ),
    ("B.Tech. in Artificial Intelligence (AI) and Data Science", "Artificial Intelligence and Data Science", 120),
    ("B.Tech. in Computer Science and Engineering (Data Science)", "Data Science", 60),
    ("B.Tech. in Computer Science and Engineering (Cyber Security)", "Cyber Security", 60),
]


def normalize_space(value):
    return re.sub(r"\s+", " ", value).strip()


def duration_to_years(value):
    match = re.search(r"(\d+)\s*Years?", value, re.IGNORECASE)
    return int(match.group(1)) if match else 4


def extract_specialization(program_name):
    name = re.sub(r"^B\.?Tech\.?\s+in\s+", "", program_name, flags=re.IGNORECASE).strip()
    if "(" in name and name.endswith(")"):
        base, detail = name.rsplit("(", 1)
        detail = detail.rstrip(")")
        if "Computer Science" in base:
            return normalize_space(detail.replace("AI)", "AI"))
    name = re.sub(r"\s*\(AI\)\s*", " ", name)
    return normalize_space(name)


def canonical_program_name(raw_name):
    name = normalize_space(raw_name.replace("\xa0", " "))
    name = name.replace("B.Tech in", "B.Tech. in")
    name = name.replace("B.Tech. Computer", "B.Tech. in Computer")
    if name.lower().startswith("b.tech") and " in " not in name.lower():
        name = re.sub(r"^B\.?Tech\.?\s*", "B.Tech. in ", name, flags=re.IGNORECASE)
    return name


def parse_courses_page(html, source_url):
    soup = BeautifulSoup(html, "html.parser")
    candidates = []

    for row in soup.find_all("tr"):
        cells = [normalize_space(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
        if len(cells) < 2:
            continue

        joined = " | ".join(cells)
        if "B.Tech" not in joined:
            continue

        intake = None
        for cell in reversed(cells):
            if re.fullmatch(r"\d{1,4}", cell):
                intake = int(cell)
                break

        if not intake:
            continue

        program_name = next((cell for cell in cells if "B.Tech" in cell), None)
        duration_cell = next((cell for cell in cells if "Years" in cell), "")
        if program_name:
            candidates.append(
                {
                    "program_name": canonical_program_name(program_name),
                    "specialization": extract_specialization(program_name),
                    "degree_type": "B.Tech",
                    "intake": intake,
                    "duration_years": duration_to_years(duration_cell),
                    "source_url": source_url,
                    "last_verified": date.today(),
                }
            )

    if candidates:
        return candidates

    text = soup.get_text("\n", strip=True)
    pattern = re.compile(
        r"(B\.?Tech\.?\s+in\s+[^\n|]+?)\s*(?:\||\n)\s*([0-9]\s*Years?[^\n|]*)\s*(?:\||\n)\s*(\d{1,4})",
        re.IGNORECASE,
    )
    for program_name, duration, intake in pattern.findall(text):
        candidates.append(
            {
                "program_name": canonical_program_name(program_name),
                "specialization": extract_specialization(program_name),
                "degree_type": "B.Tech",
                "intake": int(intake),
                "duration_years": duration_to_years(duration),
                "source_url": source_url,
                "last_verified": date.today(),
            }
        )

    return candidates


def fetch_programs():
    headers = {"User-Agent": "zyra-university-mapper/1.0"}
    errors = []

    for url in SOURCE_URLS:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as exc:
            errors.append(f"{url}: {exc}")
            continue

        programs = parse_courses_page(response.text, url)
        btech_programs = [program for program in programs if program["degree_type"] == "B.Tech"]
        if len(btech_programs) >= 10:
            print(f"Scraped {len(btech_programs)} B.Tech programs from {url}")
            return dedupe_programs(btech_programs)

        errors.append(f"{url}: found only {len(btech_programs)} B.Tech rows")

    print("Warning: live scraping did not return the expected course table.")
    for error in errors:
        print(f"  - {error}")
    print("Using curated NSEC B.Tech intake list as fallback.")
    return [
        {
            "program_name": program_name,
            "specialization": specialization,
            "degree_type": "B.Tech",
            "intake": intake,
            "duration_years": 4,
            "source_url": SOURCE_URLS[0],
            "last_verified": date.today(),
        }
        for program_name, specialization, intake in EXPECTED_PROGRAMS
    ]


def dedupe_programs(programs):
    by_key = {}
    for program in programs:
        key = (
            program["program_name"].lower(),
            program["specialization"].lower(),
            program["degree_type"].lower(),
        )
        by_key[key] = program
    return list(by_key.values())


def ensure_schema(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS universities (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            location VARCHAR(255),
            website TEXT
        );

        CREATE TABLE IF NOT EXISTS programs (
            id SERIAL PRIMARY KEY,
            university_id INTEGER NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
            program_name VARCHAR(255) NOT NULL,
            specialization VARCHAR(255),
            degree_type VARCHAR(50) NOT NULL,
            intake INTEGER,
            duration_years INTEGER,
            source_url TEXT,
            last_verified DATE DEFAULT CURRENT_DATE,
            UNIQUE (university_id, program_name, specialization, degree_type)
        );
        """
    )


def upsert_university(cursor):
    cursor.execute(
        """
        INSERT INTO universities (name, location, website)
        VALUES (%s, %s, %s)
        ON CONFLICT (name) DO UPDATE
        SET location = EXCLUDED.location,
            website = EXCLUDED.website
        RETURNING id;
        """,
        (UNIVERSITY["name"], UNIVERSITY["location"], UNIVERSITY["website"]),
    )
    return cursor.fetchone()[0]


def upsert_programs(cursor, university_id, programs):
    for program in programs:
        cursor.execute(
            """
            INSERT INTO programs (
                university_id,
                program_name,
                specialization,
                degree_type,
                intake,
                duration_years,
                source_url,
                last_verified
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (university_id, program_name, specialization, degree_type) DO UPDATE
            SET intake = EXCLUDED.intake,
                duration_years = EXCLUDED.duration_years,
                source_url = EXCLUDED.source_url,
                last_verified = EXCLUDED.last_verified;
            """,
            (
                university_id,
                program["program_name"],
                program["specialization"],
                program["degree_type"],
                program["intake"],
                program["duration_years"],
                program["source_url"],
                program["last_verified"],
            ),
        )


def main():
    programs = fetch_programs()
    connection = None

    try:
        connection = psycopg2.connect(**DB_CONFIG)
        with connection:
            with connection.cursor() as cursor:
                ensure_schema(cursor)
                university_id = upsert_university(cursor)
                upsert_programs(cursor, university_id, programs)
        print(f"Inserted/updated {len(programs)} programs for {UNIVERSITY['name']}.")
    except psycopg2.Error as exc:
        print(f"Database error: {exc}")
        raise
    finally:
        if connection:
            connection.close()


if __name__ == "__main__":
    main()
