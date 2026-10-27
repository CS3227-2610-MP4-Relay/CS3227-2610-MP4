"""Check the small rendered Pages artifact without fetching or executing content."""

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit


class _References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.links.extend(
            value for name, value in attrs if name in {"href", "src"} and value
        )
        if tag == "link" and "stylesheet" in attributes.get("rel", "").split():
            self.stylesheets.append(attributes.get("href", ""))


def _local_target(reference, source, root, baseurl, site_url):
    # Resolve browser-relative URLs using their published location, not local paths.
    page_url = site_url + baseurl + "/" + source.relative_to(root).as_posix()
    parsed = urlsplit(urljoin(page_url, reference))
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.netloc != urlsplit(site_url).netloc:
        return None
    path = unquote(parsed.path)
    if not path.startswith(baseurl + "/") and path != baseurl:
        raise ValueError("outside configured base path")
    relative = path[len(baseurl) :].lstrip("/")
    target = (root / relative).resolve()
    if "\\" in relative or not target.is_relative_to(root):
        raise ValueError("outside rendered artifact")
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file():
        raise ValueError("missing local target")
    return target


def check_site(site, baseurl, site_url):
    """Return errors for missing entries/assets, invalid local links or guide leaks."""
    root = Path(site).resolve()
    baseurl = baseurl.rstrip("/")
    site_url = site_url.rstrip("/")
    errors = []
    for page in ("index.html", "Reflections.html"):
        if not (root / page).is_file():
            errors.append(f"Missing required page: {page}")
    stylesheets = []
    for source in sorted(root.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(root)
        if not source.resolve().is_relative_to(root):
            errors.append(f"File outside rendered artifact: {relative}")
            continue
        if any(
            Path(part).stem.casefold() in {"userguide", "developerguide"}
            for part in relative.parts
        ):
            errors.append(f"Guide must remain excluded: {relative}")
        if source.suffix not in {".html", ".css"}:
            continue
        text = source.read_text(encoding="utf-8")
        if source.suffix == ".html":
            parser = _References()
            parser.feed(text)
            links = parser.links
            stylesheets.extend((source, href) for href in parser.stylesheets)
        else:
            links = [
                match.strip().strip("\"'")
                for match in re.findall(r"url\(\s*([^)]*?)\s*\)", text)
            ]
        for reference in links:
            try:
                _local_target(reference, source, root, baseurl, site_url)
            except ValueError as exc:
                errors.append(f"{relative}: {reference!r}: {exc}")
    local_stylesheets = []
    for source, href in stylesheets:
        try:
            target = _local_target(href, source, root, baseurl, site_url)
            if target is not None:
                local_stylesheets.append(target)
        except ValueError:
            pass  # The reference loop already reports this broken stylesheet.
    if not local_stylesheets:
        errors.append("Missing local theme stylesheet")
    return errors


def _configuration(path):
    # Only the two simple scalar values used by this repository are needed.
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"(url|baseurl):\s*(\S+)\s*", line)
        if match:
            values[match[1]] = match[2].strip("\"'")
    origin = urlsplit(values.get("url", ""))
    baseurl = values.get("baseurl", "")
    if (
        origin.scheme != "https"
        or not origin.netloc
        or origin.path not in {"", "/"}
        or origin.query
        or origin.fragment
        or not re.fullmatch(r"/[A-Za-z0-9_-]+", baseurl)
    ):
        raise ValueError("Expected HTTPS url and repository baseurl in site config")
    return baseurl, values["url"]


def main():
    """Validate a generated site using this repository's URL configuration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        baseurl, site_url = _configuration(args.config)
        errors = check_site(args.site, baseurl, site_url)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
