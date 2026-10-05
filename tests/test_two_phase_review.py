"""Tests for two-phase PR review and cross-model audit templates."""
from pathlib import Path
from ai_team.skills import list_skills

TEMPLATES = Path(__file__).resolve().parent.parent / "src" / "ai_team" / "templates"


def test_review_pr_skills_exist_and_bilingual():
    agents_en = TEMPLATES / ".agents" / "skills" / "core" / "review-pr" / "SKILL.md"
    agents_pl = TEMPLATES / ".agents" / "skills" / "core" / "review-pr" / "SKILL.pl.md"
    claude_en = TEMPLATES / ".claude" / "skills" / "core" / "review-pr" / "SKILL.md"
    claude_pl = TEMPLATES / ".claude" / "skills" / "core" / "review-pr" / "SKILL.pl.md"

    for p in [agents_en, agents_pl, claude_en, claude_pl]:
        assert p.is_file(), f"Missing file: {p}"
        content = p.read_text(encoding="utf-8")
        assert "review-pr" in content
        assert "diff" in content.lower() or "pr" in content.lower()


def test_independent_reviewer_agent_templates_exist():
    agents_en = TEMPLATES / ".agents" / "agents" / "independent-reviewer.md"
    agents_pl = TEMPLATES / ".agents" / "agents" / "independent-reviewer.pl.md"
    claude_en = TEMPLATES / ".claude" / "agents" / "independent-reviewer.md"
    claude_pl = TEMPLATES / ".claude" / "agents" / "independent-reviewer.pl.md"

    for p in [agents_en, agents_pl, claude_en, claude_pl]:
        assert p.is_file(), f"Missing file: {p}"
        content = p.read_text(encoding="utf-8")
        assert "independent-reviewer" in content or "reviewer" in content
        assert "review-pr" in content


def test_reviewer_agents_have_review_pr_skill():
    agents_reviewer = TEMPLATES / ".agents" / "agents" / "reviewer.md"
    agents_reviewer_pl = TEMPLATES / ".agents" / "agents" / "reviewer.pl.md"
    assert "review-pr" in agents_reviewer.read_text(encoding="utf-8")
    assert "review-pr" in agents_reviewer_pl.read_text(encoding="utf-8")


def test_list_skills_discovers_review_pr():
    project_root = Path(__file__).resolve().parent.parent
    data = list_skills(project_root)
    ids = {s["id"] for s in data["available"]}
    assert "core/review-pr" in ids
