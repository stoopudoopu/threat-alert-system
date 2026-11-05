from threatalert.text import clean_html, extract_cves


def test_finds_a_cve():
    assert extract_cves("Flaw CVE-2026-58882 in Android") == ["CVE-2026-58882"]


def test_lowercase_is_normalized():
    assert extract_cves("flaw cve-2026-1234") == ["CVE-2026-1234"]


def test_repeated_cve_appears_once():
    assert extract_cves("CVE-2026-1234 and again CVE-2026-1234") == ["CVE-2026-1234"]


def test_word_cve_without_an_id_is_not_a_match():
    assert extract_cves("Something about a cve") == []


def test_two_cves_are_returned_in_order():
    assert extract_cves("cve-2025-1234 and cve-2026-1111") == ["CVE-2025-1234", "CVE-2026-1111"]


def test_clean_html_removes_tags_and_scripts():
    assert clean_html("<p>Full <b>text</b></p><script>bad()</script>") == "Full text"
