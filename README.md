# University Mapper

University Mapper is a focused data engineering project. It maps Netaji Subhash Engineering College programs into PostgreSQL and adds a lightweight QA layer for duplicate, completeness, and naming checks.

## Problem Statement

Decision System need reliable university intelligence that can support search, matching, enrichment, and an eventual education taxonomy graph. This project models one college, NSEC, as structured data with programs, degree types, intake capacity, duration, source URL, and verification date.

## Schema Design

The database uses two normalized tables:

- `universities`: one row per institution with name, location, and website.
- `programs`: one row per academic program with a foreign key to `universities`.

`programs` includes a unique constraint across `university_id`, `program_name`, `specialization`, and `degree_type` so repeated runs update existing records instead of creating duplicates.

## Source

The scraper targets the NSEC courses and intake page:

- `https://www.nsec.ac.in/page.php?id=354`

If the live site is unavailable or the table markup changes, `scraper.py` falls back to the curated NSEC B.Tech intake list so the pipeline remains demoable.

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Create the PostgreSQL database:

```sql
CREATE DATABASE university_mapper;
```

Create tables and seed the current NSEC program list:

```bash
psql -U postgres -d university_mapper -f database_setup.sql
```

Run the scraper:

```bash
python scraper.py
```

Run QA validation:

```bash
python validator.py
```

The default database config is defined at the top of both Python files and can be overridden with environment variables:

```python
dbname=university_mapper user=postgres password=postgres
```

PowerShell example:

```powershell
$env:DB_PASSWORD="your-postgres-password"
python scraper.py
python validator.py
```

## QA Process

`validator.py` checks:

- Duplicate programs after normalization.
- Missing values for intake, duration, source URL, and verification date.
- Naming inconsistencies such as abbreviation-only values like `CSE` instead of canonical `Computer Science & Engineering`.

Example output should include total rows checked, pass/fail sections, warnings, and a final status.

## Next Steps

- Add more universities and normalize locations.
- Create a program taxonomy table for AI, ML, data science, cybersecurity, core engineering, business, and health-tech categories.
- Add source confidence and verification history.
- Store scraped raw HTML snapshots for auditability.
- Build an AI taxonomy mapper that clusters related specializations into reusable intelligence graph nodes.
