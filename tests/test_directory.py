"""Acceptance tests for the generated NVIDIA Skills DIRECTORY.md."""

from __future__ import annotations

import re
from pathlib import Path
from typing import ClassVar, Final

import pytest
import yaml
from pydantic import BaseModel, ConfigDict
from scripts.generate_directory import Catalog, load_catalog

REPO_ROOT: Final[Path] = Path(__file__).resolve().parent.parent
DIRECTORY_PATH: Final[Path] = REPO_ROOT / "DIRECTORY.md"
SOURCE_COMMIT: Final[str] = "e537b31f9406831a60b28eff393731e84df60168"
EXPECTED_TOTAL_SKILLS: Final[int] = 225

REQUIRED_SECTIONS: Final[frozenset[str]] = frozenset(
    {
        "Agent Navigation",
        "Category Index",
        "Product Index",
        "License Index",
        "Alphabetical Index",
        "Skills by Category",
        "MCP Servers",
    }
)


class Frontmatter(BaseModel):
    """Typed shape of the DIRECTORY.md YAML frontmatter."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    repo: str
    source_commit: str
    total_skills: int
    total_local_mcp_servers: int
    total_repo_mcp_servers: int
    generated_at: str


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    """Load the catalog once for the test session."""
    return load_catalog(REPO_ROOT / "nvidia_skills_catalog.json")


@pytest.fixture(scope="session")
def directory_text() -> str:
    """Read DIRECTORY.md once for the test session."""
    if not DIRECTORY_PATH.exists():
        pytest.fail(f"{DIRECTORY_PATH.name} does not exist")
    return DIRECTORY_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def frontmatter(directory_text: str) -> Frontmatter:
    """Parse the YAML frontmatter from DIRECTORY.md."""
    match = re.match(r"^---\n(.*?)\n---\n", directory_text, re.DOTALL)
    if not match:
        pytest.fail("YAML frontmatter not found")
    return Frontmatter.model_validate(yaml.safe_load(match.group(1)))


class TestFrontmatter:
    """Acceptance tests for YAML frontmatter."""

    def test_repo_matches_catalog(
        self, frontmatter: Frontmatter, catalog: Catalog
    ) -> None:
        """Frontmatter repo matches the catalog source."""
        assert frontmatter.repo == catalog.repo

    def test_source_commit_matches_expected(self, frontmatter: Frontmatter) -> None:
        """Frontmatter source_commit is the pinned commit hash."""
        assert frontmatter.source_commit == SOURCE_COMMIT

    def test_total_skills_matches_expected(self, frontmatter: Frontmatter) -> None:
        """Frontmatter total_skills equals 201."""
        assert frontmatter.total_skills == EXPECTED_TOTAL_SKILLS

    def test_local_and_repo_mcp_counts_are_zero(self, frontmatter: Frontmatter) -> None:
        """Frontmatter MCP server counts are both zero."""
        assert frontmatter.total_local_mcp_servers == 0
        assert frontmatter.total_repo_mcp_servers == 0

    def test_generated_at_is_iso8601(self, frontmatter: Frontmatter) -> None:
        """Frontmatter generated_at is an ISO 8601 timestamp."""
        assert (
            re.match(
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
                frontmatter.generated_at,
            )
            is not None
        )


class TestRequiredSections:
    """Acceptance tests for required section headings."""

    @pytest.mark.parametrize("section", sorted(REQUIRED_SECTIONS))
    def test_section_exists(self, directory_text: str, section: str) -> None:
        """Each required section heading is present."""
        pattern = re.compile(rf"^## \s*{re.escape(section)}\s*$", re.MULTILINE)
        assert pattern.search(directory_text) is not None


class TestSkillAnchors:
    """Acceptance tests for per-skill anchors and links."""

    def test_every_slug_has_exactly_one_anchor(
        self, directory_text: str, catalog: Catalog
    ) -> None:
        """Every catalog slug appears exactly once as a skill anchor."""
        found: list[str] = re.findall(r"^## skill-(.+)$", directory_text, re.MULTILINE)
        assert sorted(found) == sorted(skill.slug for skill in catalog.skills)

    def test_no_duplicate_slugs(self, directory_text: str) -> None:
        """No skill slug anchor is duplicated."""
        found: list[str] = re.findall(r"^## skill-(.+)$", directory_text, re.MULTILINE)
        assert len(found) == len(set(found))

    def test_every_entry_url_contains_commit_hash(
        self, directory_text: str, catalog: Catalog
    ) -> None:
        """Every skill entry URL includes the pinned commit hash."""
        for skill in catalog.skills:
            assert SOURCE_COMMIT in skill.entry_url
            assert skill.entry_url in directory_text


class TestMcpZeroState:
    """Acceptance tests for the MCP server zero-state note."""

    def test_zero_state_note_present(self, directory_text: str) -> None:
        """The MCP Servers section contains the zero-state note."""
        lowered = directory_text.lower()
        assert "no local mcp servers" in lowered
        assert "no upstream repo mcp servers" in lowered


class TestNoPlaceholderText:
    """Acceptance tests ensuring no placeholder text remains."""

    def test_no_tbd_or_todo_or_placeholder(self, directory_text: str) -> None:
        """No TBD/TODO/placeholder text remains in the directory."""
        lower = directory_text.lower()
        assert "tbd" not in lower
        assert "todo" not in lower
        assert "placeholder" not in lower
