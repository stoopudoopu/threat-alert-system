import re

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)

def extract_cves(text: str) -> list[str]:
    found = [cve.upper() for cve in CVE_PATTERN.findall(text)]
    return list(dict.fromkeys(found))

    