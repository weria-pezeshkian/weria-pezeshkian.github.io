# Parses BibTeX using bibtexparser and renders site-specific Markdown for /publications/.
# Parsing is delegated to the library; only the website formatting is custom.

#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from collections import defaultdict
import bibtexparser


ROOT = Path(__file__).resolve().parent.parent
BIB_FILE = ROOT / "publications" / "ref.bib"
OUT_FILE = ROOT / "publications" / "generated.md"


def clean_latex(text: str) -> str:
    if not text:
        return ""

    replacements = {
        r"\&": "&",
        r"~": " ",
        r"---": "—",
        r"--": "–",
        "{": "",
        "}": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove common LaTeX commands but keep contents if braced
    text = re.sub(r"\\textit\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\emph\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\url\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\\href\{([^}]*)\}\{([^}]*)\}", r"\2", text)

    # Drop remaining simple latex commands
    text = re.sub(r"\\[a-zA-Z]+\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_authors(author_field: str) -> list[str]:
    if not author_field:
        return []
    authors = [clean_latex(a.strip()) for a in author_field.split(" and ")]
    return [a for a in authors if a]


def format_authors(author_field: str) -> str:
    authors = split_authors(author_field)
    if not authors:
        return ""

    if len(authors) <= 6:
        return ", ".join(authors)

    return ", ".join(authors[:6]) + ", et al."


def first_nonempty(entry: dict, keys: list[str]) -> str:
    for key in keys:
        value = entry.get(key, "")
        if value:
            return clean_latex(value)
    return ""


def format_link(label: str, url: str) -> str:
    url = url.strip()
    if not url:
        return ""
    return f"[{label}]({url})"


def entry_year(entry: dict) -> str:
    year = clean_latex(entry.get("year", "")).strip()
    if year:
        return year
    return "Unknown"


def sort_key(entry: dict) -> tuple:
    year = clean_latex(entry.get("year", "")).strip()
    month = clean_latex(entry.get("month", "")).strip().lower()
    title = clean_latex(entry.get("title", "")).strip().lower()

    month_map = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }

    try:
        year_num = int(year)
    except ValueError:
        year_num = -1

    month_num = month_map.get(month, 0)
    return (year_num, month_num, title)


def format_entry(entry: dict) -> str:
    title = first_nonempty(entry, ["title"])
    authors = format_authors(entry.get("author", ""))
    venue = first_nonempty(entry, [
        "journal",
        "booktitle",
        "publisher",
        "school",
        "institution",
    ])
    year = first_nonempty(entry, ["year"])
    volume = first_nonempty(entry, ["volume"])
    number = first_nonempty(entry, ["number"])
    pages = first_nonempty(entry, ["pages"])
    doi = first_nonempty(entry, ["doi"])
    url = first_nonempty(entry, ["url"])
    arxiv = first_nonempty(entry, ["eprint"])

    parts: list[str] = []

    if authors:
        parts.append(authors + ".")
    if title:
        parts.append(f"**{title}.**")
    if venue:
        venue_part = f"*{venue}*"
        extra = []
        if volume:
            extra.append(volume)
        if number:
            extra.append(f"({number})")
        if pages:
            extra.append(f"pp. {pages}")
        if year:
            extra.append(year)
        if extra:
            venue_part += ", " + ", ".join(extra)
        venue_part += "."
        parts.append(venue_part)
    elif year:
        parts.append(year + ".")

    links = []
    if doi:
        doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        links.append(format_link("DOI", doi_url))
    if url:
        links.append(format_link("Link", url))
    if arxiv:
        arxiv_url = arxiv if arxiv.startswith("http") else f"https://arxiv.org/abs/{arxiv}"
        links.append(format_link("arXiv", arxiv_url))

    line = " ".join(parts).strip()
    if links:
        line += " " + " · ".join(links)

    return f"- {line}"


def main() -> None:
    if not BIB_FILE.exists():
        raise FileNotFoundError(f"BibTeX file not found: {BIB_FILE}")

    with BIB_FILE.open("r", encoding="utf-8") as f:
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        db = bibtexparser.load(f, parser=parser)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in db.entries:
        grouped[entry_year(entry)].append(entry)

    years = sorted(
        grouped.keys(),
        key=lambda y: int(y) if y.isdigit() else -1,
        reverse=True,
    )

    output: list[str] = []
    output.append("<!-- This file is generated automatically from publications/ref.bib. -->")
    output.append("<!-- Do not edit this file manually. -->")
    output.append("")

    for year in years:
        output.append(f"## {year}")
        output.append("")
        entries = sorted(grouped[year], key=sort_key, reverse=True)
        for entry in entries:
            output.append(format_entry(entry))
        output.append("")

    OUT_FILE.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
