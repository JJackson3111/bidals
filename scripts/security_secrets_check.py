from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    "__pycache__",
    "media",
    "node_modules",
    "playwright-report",
    "staticfiles",
}
SKIP_FILES = {".env"}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic-secret-assignment": re.compile(
        r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|refresh[_-]?token|password)\b"
        r"\s*[:=]\s*['\"](?!<|changeme|example|placeholder|test-secret|release-check-test-secret|unsafe-development-secret-key)[^'\"]{16,}['\"]"
    ),
}


def main() -> int:
    findings: list[str] = []
    for path in ROOT.rglob("*"):
        if path.is_dir():
            continue
        if path.name in SKIP_FILES or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in {".py", ".js", ".jsx", ".ts", ".tsx", ".json", ".yml", ".yaml", ".md", ".env", ".example"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(ROOT)}: possible {label}")

    if findings:
        print("Potential secrets found. Review before committing:")
        for finding in findings:
            print(f" - {finding}")
        return 1

    print("No obvious committed secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
