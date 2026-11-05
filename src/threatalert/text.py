import re

from bs4 import BeautifulSoup

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)


def extract_cves(text: str) -> list[str]:
    found = [cve.upper() for cve in CVE_PATTERN.findall(text)]
    return list(dict.fromkeys(found))


def clean_html(text: str) -> str:
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(" ", strip=True)
