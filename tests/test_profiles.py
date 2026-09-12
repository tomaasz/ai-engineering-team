import pytest
from pathlib import Path
from ai_team.installer import _profile, _selected, _all_files, profiles_root

ALL_PROFILES = ["core", "python", "web", "postgres", "ocr", "geneteka", "full"]

def test_all_expected_profiles_exist():
    available = sorted([p.stem for p in profiles_root().glob("*.json")])
    assert sorted(ALL_PROFILES) == available

@pytest.mark.parametrize("profile_name", ALL_PROFILES)
def test_profile_loads_and_has_includes(profile_name):
    prof = _profile(profile_name)
    assert isinstance(prof, dict)
    assert "include" in prof
    assert isinstance(prof["include"], list)
    assert len(prof["include"]) > 0

@pytest.mark.parametrize("profile_name", ALL_PROFILES)
def test_profile_selects_valid_files(profile_name):
    prof = _profile(profile_name)
    selected = _selected(prof)
    assert len(selected) > 0
    all_known = _all_files()
    for rel_path, src_path in selected.items():
        assert rel_path in all_known
        assert Path(src_path).is_file()
        assert Path(src_path).exists()

def test_unknown_profile_raises():
    with pytest.raises(RuntimeError, match="Nieznany profil 'nonexistent'"):
        _profile("nonexistent")

def test_full_profile_contains_all_profiles_files():
    full_prof = _profile("full")
    full_selected = set(_selected(full_prof).keys())
    
    for prof_name in ["core", "python", "web", "postgres", "ocr", "geneteka"]:
        sub_prof = _profile(prof_name)
        sub_selected = set(_selected(sub_prof).keys())
        assert sub_selected.issubset(full_selected), f"{prof_name} files missing in full profile"

