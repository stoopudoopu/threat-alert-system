from threatalert.prefilter import extract_cves


def test_finds_a_cve():
    assert extract_cves("Flaw CVE-2026-58882 in Android") == ["CVE-2026-58882"]


def test_lowercase_is_normalized():
    assert extract_cves("flaw cve-2026-1234") == ["CVE-2026-1234"]


def test_repeated_cve_appears_once():
    assert extract_cves("CVE-2026-1234 and again CVE-2026-1234") == ["CVE-2026-1234"]

def test_cve_mentioned_not_a_report():
    assert extract_cves("Something about a cve") == []


def test_two_cves_mentioned():
    assert extract_cves("cve-2025-1234 and cve-2026-1111") == ["CVE-2025-1234", "CVE-2026-1111"]