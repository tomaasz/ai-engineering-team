from pathlib import Path
from ai_team.utils import safe_slug, package_root, template_root, profiles_root

def test_package_paths_exist():
    assert package_root().is_dir()
    assert template_root().is_dir()
    assert profiles_root().is_dir()
    assert (template_root() / "AI_TEAM.md").is_file()
    assert (template_root() / "ai-team.config.json").is_file()

def test_safe_slug_polish_diacritics():
    # Tests conversion of ąćęłńóśźż -> acelnoszz
    raw = "Zażółć gęślą jaźń w module danych"
    slug = safe_slug(raw)
    assert slug == "zazolc-gesla-jazn-w-module-danych"

def test_safe_slug_special_characters():
    raw = "feat: add user auth (OAuth2 & JWT) #123!"
    slug = safe_slug(raw)
    assert slug == "feat-add-user-auth-oauth2-jwt-123"

def test_safe_slug_empty_fallback():
    assert safe_slug("") == "task"
    assert safe_slug("   !!!   ") == "task"

def test_safe_slug_max_len():
    raw = "a" * 100
    slug = safe_slug(raw, max_len=44)
    assert len(slug) <= 44
    assert slug == "a" * 44

def test_safe_slug_trailing_hyphens_stripped():
    raw = "test feature ---"
    slug = safe_slug(raw)
    assert slug == "test-feature"

