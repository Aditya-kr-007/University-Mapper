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

INSERT INTO universities (name, location, website)
VALUES (
    'Netaji Subhash Engineering College',
    'Kolkata, West Bengal, India',
    'https://www.nsec.ac.in'
)
ON CONFLICT (name) DO UPDATE
SET location = EXCLUDED.location,
    website = EXCLUDED.website;

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
SELECT
    u.id,
    v.program_name,
    v.specialization,
    'B.Tech',
    v.intake,
    4,
    'https://www.nsec.ac.in/page.php?id=354',
    CURRENT_DATE
FROM universities u
CROSS JOIN (
    VALUES
        ('B.Tech. in Computer Science & Engineering', 'Computer Science & Engineering', 300),
        ('B.Tech. in Computer Science and Engineering (Internet of Things)', 'Internet of Things', 30),
        ('B.Tech. in Electronics & Communication Engineering', 'Electronics & Communication Engineering', 120),
        ('B.Tech. in Computer Science and Business Systems', 'Computer Science and Business Systems', 30),
        ('B.Tech. in Information Technology', 'Information Technology', 180),
        ('B.Tech. in Applied Electronics & Instrumentation Engineering', 'Applied Electronics & Instrumentation Engineering', 30),
        ('B.Tech. in Electrical Engineering', 'Electrical Engineering', 60),
        ('B.Tech. in Civil Engineering', 'Civil Engineering', 30),
        ('B.Tech. in Electrical and Computer Engineering', 'Electrical and Computer Engineering', 60),
        ('B.Tech. in Mechanical Engineering', 'Mechanical Engineering', 30),
        ('B.Tech. in Bio-Medical Engineering', 'Bio-Medical Engineering', 60),
        ('B.Tech. in Computer Science and Information Technology', 'Computer Science and Information Technology', 60),
        ('B.Tech. in Computer Science and Engineering (Artificial Intelligence and Machine Learning)', 'Artificial Intelligence and Machine Learning', 300),
        ('B.Tech. in Artificial Intelligence (AI) and Data Science', 'Artificial Intelligence and Data Science', 120),
        ('B.Tech. in Computer Science and Engineering (Data Science)', 'Data Science', 60),
        ('B.Tech. in Computer Science and Engineering (Cyber Security)', 'Cyber Security', 60)
) AS v(program_name, specialization, intake)
WHERE u.name = 'Netaji Subhash Engineering College'
ON CONFLICT (university_id, program_name, specialization, degree_type) DO UPDATE
SET intake = EXCLUDED.intake,
    duration_years = EXCLUDED.duration_years,
    source_url = EXCLUDED.source_url,
    last_verified = EXCLUDED.last_verified;
