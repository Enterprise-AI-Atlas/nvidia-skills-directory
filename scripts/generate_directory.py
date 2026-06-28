# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pydantic>=2",
# ]
# ///
# ─── How to run ───
# uv run scripts/generate_directory.py
# ──────────────────
"""Generate the agentic-reader-optimized NVIDIA Skills DIRECTORY.md."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, field_validator

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
CATALOG_PATH: Final[Path] = REPO_ROOT / "nvidia_skills_catalog.json"
DIRECTORY_PATH: Final[Path] = REPO_ROOT / "DIRECTORY.md"
SOURCE_COMMIT: Final[str] = "e537b31f9406831a60b28eff393731e84df60168"


class Skill(BaseModel):
    """Typed representation of a single skill record from the catalog JSON."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    slug: str
    name: str
    description: str
    product: str
    marketplace_product: str
    primary_category: str
    all_categories: list[str]
    license: str
    version: str
    author: str
    tags: list[str]
    entry_url: str

    @field_validator("tags", mode="before")
    @classmethod
    def _normalize_tags(cls, value: str | list[str]) -> list[str]:
        """Normalize tags when the catalog stores them as a space-separated string."""
        if isinstance(value, str):
            return value.split()
        return [str(tag) for tag in value]


class Catalog(BaseModel):
    """Typed representation of the top-level catalog JSON."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    repo: str
    commit: str
    total: int
    skills: list[Skill]


class IndexEntry(BaseModel):
    """A single row in an index table."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    label: str
    count: int


def load_catalog(path: Path) -> Catalog:
    """Parse the catalog JSON into typed Pydantic models."""
    return Catalog.model_validate_json(path.read_text(encoding="utf-8"))


def _now_iso8601() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _md_table_row(cells: list[str]) -> str:
    """Build a Markdown table row, escaping pipe characters in cell text."""
    return "| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |"


def _render_frontmatter(repo: str, total_skills: int, generated_at: str) -> str:
    """Render the YAML frontmatter block."""
    return f"""---
repo: {repo}
source_commit: {SOURCE_COMMIT}
total_skills: {total_skills}
total_local_mcp_servers: 0
total_repo_mcp_servers: 0
generated_at: "{generated_at}"
---
"""


def _render_agent_navigation() -> str:
    """Render the Agent Navigation guidance section."""
    lines = [
        "## Agent Navigation",
        "",
        "Use this directory when you need to locate an NVIDIA-published skill",
        "for a specific product, category, or task.",
        "",
        "- **Looking for a skill by name or slug?** Use the "
        + "[Alphabetical Index](#alphabetical-index).",
        "- **Browsing by domain?** Use the [Category Index](#category-index) "
        + "or [Skills by Category](#skills-by-category).",
        "- **Matching a product?** Use the [Product Index](#product-index).",
        "- **Checking license terms?** Use the [License Index](#license-index).",
        "- **Need the upstream source?** Every skill entry links directly to the "
        + "`SKILL.md` file in the `NVIDIA/skills` repository at the pinned commit.",
        "",
        "Each skill is addressable by the stable heading anchor `## skill-<slug>`.",
        "",
    ]
    return "\n".join(lines)


def _render_index_table(title: str, entries: list[IndexEntry]) -> str:
    """Render a simple two-column index table sorted by label."""
    lines = [f"## {title}", "", "| Name | Count |", "|---|---|"]
    lines.extend(
        _md_table_row([entry.label, str(entry.count)])
        for entry in sorted(entries, key=lambda e: e.label)
    )
    lines.append("")
    return "\n".join(lines)


def _render_alphabetical_index(skills: list[Skill]) -> str:
    """Render the compact alphabetical index of all skills."""
    lines = [
        "## Alphabetical Index",
        "",
        "| Slug | Name | Product | Primary Category | License | Entry Link |",
        "|---|---|---|---|---|---|",
    ]
    lines.extend(
        _md_table_row(
            [
                f"[{skill.slug}](#skill-{skill.slug})",
                skill.name,
                skill.product,
                skill.primary_category,
                skill.license,
                f"[SKILL.md]({skill.entry_url})",
            ],
        )
        for skill in sorted(skills, key=lambda s: s.slug)
    )
    lines.append("")
    return "\n".join(lines)


def _render_skill_detail(skill: Skill) -> str:
    """Render the detailed block for a single skill with a stable anchor."""
    lines = [
        f"## skill-{skill.slug}",
        "",
        "| Field | Value |",
        "|---|---|",
        _md_table_row(["Slug", skill.slug]),
        _md_table_row(["Name", skill.name]),
        _md_table_row(["Product", skill.product]),
        _md_table_row(["Marketplace Product", skill.marketplace_product]),
        _md_table_row(["Primary Category", skill.primary_category]),
        _md_table_row(["All Categories", ", ".join(skill.all_categories)]),
        _md_table_row(["License", skill.license]),
    ]
    if skill.version:
        lines.append(_md_table_row(["Version", skill.version]))
    if skill.author:
        lines.append(_md_table_row(["Author", skill.author]))
    lines.extend(
        [
            _md_table_row(["Description", " ".join(skill.description.split())]),
            _md_table_row(["Tags", ", ".join(skill.tags)]),
            _md_table_row(["Entry", f"[SKILL.md]({skill.entry_url})"]),
            "",
        ],
    )
    return "\n".join(lines)


def _render_skill_details(skills: list[Skill]) -> str:
    """Render a stable anchored detail block for every skill."""
    lines = ["## Skill Details", ""]
    lines.extend(
        _render_skill_detail(skill) for skill in sorted(skills, key=lambda s: s.slug)
    )
    return "\n".join(lines)


def _render_skills_by_category(skills: list[Skill]) -> str:
    """Render skills grouped into subsections by primary category."""
    grouped: dict[str, list[Skill]] = {}
    for skill in skills:
        grouped.setdefault(skill.primary_category, []).append(skill)

    lines = ["## Skills by Category", ""]
    for category in sorted(grouped):
        lines.append(f"### {category}")
        lines.append("")
        lines.append(
            "| Slug | Name | Product | License | Entry Link |",
        )
        lines.append("|---|---|---|---|---|")
        lines.extend(
            _md_table_row(
                [
                    f"[{skill.slug}](#skill-{skill.slug})",
                    skill.name,
                    skill.product,
                    skill.license,
                    f"[SKILL.md]({skill.entry_url})",
                ],
            )
            for skill in sorted(grouped[category], key=lambda s: s.slug)
        )
        lines.append("")
    return "\n".join(lines)


def _render_mcp_servers() -> str:
    """Render the explicit zero-state MCP Servers section."""
    lines = [
        "## MCP Servers",
        "",
        "There are no local MCP servers and no upstream repo MCP servers.",
        "",
    ]
    return "\n".join(lines)


IndexTriple = tuple[list[IndexEntry], list[IndexEntry], list[IndexEntry]]


def _build_indexes(skills: list[Skill]) -> IndexTriple:
    """Compute category, product, and license index entries."""
    categories = Counter(skill.primary_category for skill in skills)
    products = Counter(skill.product for skill in skills)
    licenses = Counter(skill.license for skill in skills)
    return (
        [IndexEntry(label=name, count=count) for name, count in categories.items()],
        [IndexEntry(label=name, count=count) for name, count in products.items()],
        [IndexEntry(label=name, count=count) for name, count in licenses.items()],
    )


def generate_directory(catalog_path: Path, output_path: Path) -> None:
    """Read the catalog and write the rendered DIRECTORY.md."""
    catalog = load_catalog(catalog_path)
    if len(catalog.skills) != catalog.total:
        msg = (
            f"catalog total ({catalog.total}) does not match "
            f"skill count ({len(catalog.skills)})"
        )
        raise ValueError(msg)

    categories, products, licenses = _build_indexes(catalog.skills)
    generated_at = _now_iso8601()

    parts = [
        _render_frontmatter(catalog.repo, catalog.total, generated_at),
        "# NVIDIA Skills & MCP Server Directory\n",
        _render_agent_navigation(),
        _render_index_table("Category Index", categories),
        _render_index_table("Product Index", products),
        _render_index_table("License Index", licenses),
        _render_alphabetical_index(catalog.skills),
        _render_skills_by_category(catalog.skills),
        _render_skill_details(catalog.skills),
        _render_mcp_servers(),
    ]
    _ = output_path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    """CLI entry point for the generator."""
    generate_directory(CATALOG_PATH, DIRECTORY_PATH)
    print(f"Generated {DIRECTORY_PATH}")


if __name__ == "__main__":
    main()
