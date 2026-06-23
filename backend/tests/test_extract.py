"""Tests for deterministic CV field and project extraction."""

from app.services import project_extract, text_extract

CV = """Jane Alexandra Smith
jane.smith@example.com   +1 415 555 0132
linkedin.com/in/janesmith   github.com/janesmith

SUMMARY
Senior backend engineer with 6 years building APIs.

TECHNICAL SKILLS
Languages: Python, Go, JavaScript
Frameworks: FastAPI, React
Tools: Docker, PostgreSQL

PROJECTS
Career Engine | FastAPI, PostgreSQL
- Built an AI job-matching platform
github.com/janesmith/career-engine
Expense Tracker
- Personal finance app
Tech: React, Node.js
https://expense.example.com

EXPERIENCE
Acme Corp - Senior Engineer
"""


def test_fields_are_clean():
    fields = text_extract.extract_fields(CV)
    assert (fields.first_name, fields.last_name) == ("Jane", "Smith")
    assert fields.email == "jane.smith@example.com"
    assert fields.github_url == "https://github.com/janesmith"
    assert fields.summary.startswith("Senior backend engineer")


def test_skills_split_categories_without_labels():
    skills = text_extract.extract_fields(CV).tech_stack
    assert "Python" in skills and "FastAPI" in skills and "PostgreSQL" in skills
    assert not any(":" in s or s.lower() in {"languages", "tools"} for s in skills)


def test_projects_are_separated_with_tech_and_links():
    projects = project_extract.extract_projects(CV)
    assert [p.name for p in projects] == ["Career Engine", "Expense Tracker"]

    career = projects[0]
    assert career.github_url == "https://github.com/janesmith/career-engine"
    assert "FastAPI" in career.tech_stack
    assert "job-matching" in career.summary

    expense = projects[1]
    assert expense.deployed_url == "https://expense.example.com"
    assert "React" in expense.tech_stack


# Blank-line-separated, bullet-free projects — the layout that previously
# collapsed into a single project.
BLANK_SEPARATED_CV = """PROJECTS
Alpha Engine
Built a recommendation system in Python.

Beta Dashboard
Real-time analytics UI in React.

Gamma Pipeline
ETL jobs on AWS.

EDUCATION
"""


def test_blank_separated_projects_are_not_merged():
    projects = project_extract.extract_projects(BLANK_SEPARATED_CV)
    assert [p.name for p in projects] == ["Alpha Engine", "Beta Dashboard", "Gamma Pipeline"]
    assert projects[0].summary.startswith("Built a recommendation")


def test_projects_pdf_without_heading_reads_whole_document():
    pdf_text = "Alpha Engine\n- Did X\n\nBeta Dashboard\n- Did Y\n"
    projects = project_extract.extract_projects(pdf_text, section_only=False)
    assert [p.name for p in projects] == ["Alpha Engine", "Beta Dashboard"]
