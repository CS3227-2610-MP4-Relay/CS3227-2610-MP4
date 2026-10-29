"""Opt-in production delivery helpers; never log credentials or remote bodies."""

import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
from http.cookies import SimpleCookie
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    """Refuse redirects, including redirects carrying an API bearer token."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        """Leave every redirect as a failing HTTP response."""
        return


OPENER = build_opener(ProxyHandler({}), NoRedirect())


def request(url, *, token=None, timeout=30, limit=1048576, expected_404=False):
    """Read one bounded HTTPS response, with no redirects or application retries."""
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    outgoing = Request(url, headers=headers, method="GET")
    try:
        response = OPENER.open(outgoing, timeout=timeout)
    except HTTPError as error:
        if not expected_404 or error.code != 404:
            raise
        response = error
    with response:
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError("Response exceeded limit")
        return response.status, response.headers, body


def _required(name, pattern=None):
    value = os.environ.get(name, "")
    if not value or (pattern and re.fullmatch(pattern, value) is None):
        raise ValueError("Invalid configuration")
    return value


def _git(*arguments):
    return subprocess.run(
        ["git", "--literal-pathspecs", *arguments],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        check=True,
        timeout=60,
    ).stdout


def _source_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name:
        raise ValueError("Unsafe archive path")
    return path


def prepare(sha, destination):
    """Extract only committed build inputs into a fresh deployment directory."""
    required = {
        "requirements.txt",
        ".python-version",
        "vercel.json",
        "src/manage.py",
        "src/relay/wsgi.py",
    }
    roots = sorted(required - {"src/relay/wsgi.py"}) + [
        "src/relay",
        "src/accounts",
        "src/rounds",
    ]
    excluded = {
        "tests",
        "e2e",
        ".git",
        ".gitignore",
        ".gitattributes",
        ".gitmodules",
        ".vercel",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
    }
    paths = []
    for entry in _git("ls-tree", "-rz", "--full-tree", sha, "--", *roots).split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        path = _source_path(name.decode())
        if any(
            part.lower() in excluded
            or part.lower() == ".env"
            or part.lower().startswith(".env.")
            for part in path.parts
        ) or path.suffix.lower() in {".pyc", ".pyo"}:
            continue
        if metadata.split()[0] not in {b"100644", b"100755"}:
            raise ValueError("Non-regular build input")
        paths.append(path.as_posix())
    if not required <= set(paths):
        raise ValueError("Missing build inputs")
    archive = _git("archive", "--format=tar", sha, "--", *paths)
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        members = bundle.getmembers()
        for member in members:
            _source_path(member.name)
            if not member.isfile() and not member.isdir():
                raise ValueError("Non-regular archive entry")
        if {member.name for member in members if member.isfile()} != set(paths):
            raise ValueError("Archive input mismatch")
        destination.mkdir()
        bundle.extractall(destination, filter="data")


def _api(path, token, query, timeout=30):
    status, _, body = request(
        f"https://api.vercel.com{path}?{urlencode(query)}",
        token=token,
        timeout=timeout,
    )
    if not 200 <= status < 300:
        raise ValueError("API failure")
    result = json.loads(body)
    if not isinstance(result, dict):
        raise TypeError("Invalid API response")
    return result


def _ready(deployment, project, token, query):
    deadline = time.monotonic() + 600
    while (remaining := deadline - time.monotonic()) > 0:
        result = _api(
            f"/v13/deployments/{deployment}",
            token,
            query,
            timeout=min(30, remaining),
        )
        if result.get("readyState") == "READY":
            if (
                result.get("projectId") != project
                or result.get("target") != "production"
                or time.monotonic() >= deadline
            ):
                raise ValueError("Deployment provenance mismatch")
            return
        if result.get("readyState") not in {"QUEUED", "INITIALIZING", "BUILDING"}:
            raise ValueError("Deployment failed")
        time.sleep(min(5, max(0, deadline - time.monotonic())))
    raise TimeoutError("Readiness deadline")


def _smoke(host):
    for path, status, heading in (
        ("/", 200, b"<h1>Relay</h1>"),
        ("/sign-in/", 200, b"<h1>Sign in</h1>"),
        ("/relay-release-check-not-found/", 404, b"<h1>Page not found.</h1>"),
    ):
        actual, headers, body = request(
            f"https://{host}{path}",
            timeout=10,
            limit=65536,
            expected_404=status == 404,
        )
        if actual != status or heading not in body:
            raise ValueError("Smoke response mismatch")
        for name, expected in (
            ("X-Frame-Options", "DENY"),
            ("Strict-Transport-Security", "max-age=31536000"),
            ("X-Content-Type-Options", "nosniff"),
        ):
            if headers.get(name) != expected:
                raise ValueError("Smoke header mismatch")
        if path == "/sign-in/":
            cookies = SimpleCookie()
            for value in headers.get_all("Set-Cookie", []):
                cookies.load(value)
            if "csrftoken" not in cookies or not cookies["csrftoken"]["secure"]:
                raise ValueError("Smoke cookie mismatch")


def main(arguments=None):
    """Prepare source, migrate or deploy; emit fixed stages and validated IDs."""
    stage, sha, deployment = "configuration", "unavailable", "unknown"
    try:
        sha = _required("GITHUB_SHA", r"[0-9a-f]{40}")
        arguments = sys.argv[1:] if arguments is None else arguments
        if arguments == ["migrate"]:
            database = urlsplit(_required("DATABASE_URL"))
            if (
                not database.hostname
                or "-pooler" in database.hostname
                or os.environ.get("DJANGO_TRUST_PROXY_SSL_HEADER") != "true"
            ):
                raise ValueError("Migration configuration refused")
            for stage, command in (
                ("checks", ["check", "--deploy", "--fail-level", "WARNING"]),
                ("migrations", ["migrate", "--noinput"]),
            ):
                subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).with_name("manage.py")),
                        *command,
                        "--settings=relay.settings.production",
                    ],
                    capture_output=True,
                    check=True,
                    timeout=300,
                )
        elif len(arguments) == 2 and arguments[0] == "prepare":
            stage = "preparation"
            prepare(sha, Path(arguments[1]))
        elif arguments == ["deploy"]:
            token = _required("VERCEL_TOKEN")
            project = _required("VERCEL_PROJECT_ID", r"prj_[A-Za-z0-9]+")
            query = {"teamId": _required("VERCEL_TEAM_ID", r"team_[A-Za-z0-9]+")}
            host = _required(
                "DJANGO_PRODUCTION_HOST",
                r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}",
            )
            with tempfile.TemporaryDirectory() as temporary:
                source = Path(temporary) / "source"
                stage = "preparation"
                prepare(sha, source)
                stage = "creation"
                result = subprocess.run(
                    [
                        "vercel",
                        "deploy",
                        "--prod",
                        "--yes",
                        "--no-wait",
                        "--force",
                        "--cwd",
                        str(source),
                        "--global-config",
                        str(Path(temporary) / "config"),
                        "--token",
                        token,
                    ],
                    cwd=str(source),
                    env={**os.environ, "VERCEL_ORG_ID": query["teamId"]},
                    capture_output=True,
                    check=True,
                    text=True,
                    timeout=300,
                )
                url = re.fullmatch(
                    r"https://([a-z0-9][a-z0-9-]*\.vercel\.app)", result.stdout.strip()
                )
                if not url:
                    raise ValueError("Invalid deployment URL")
                created = _api(f"/v13/deployments/{url[1]}", token, query)
            candidate_id = created.get("id", "")
            if not isinstance(candidate_id, str) or not re.fullmatch(
                r"dpl_[A-Za-z0-9]+", candidate_id
            ):
                raise ValueError("Invalid deployment identifier")
            deployment = candidate_id
            stage = "readiness"
            _ready(deployment, project, token, query)
            stage = "alias"
            alias = _api(f"/v4/aliases/{host}", token, {**query, "projectId": project})
            if (
                alias.get("alias") != host
                or alias.get("deploymentId") != deployment
                or alias.get("projectId") != project
            ):
                raise ValueError("Production alias mismatch")
            stage = "smoke"
            _smoke(host)
            print(f"origin=https://{host}")
        else:
            raise ValueError("Unknown command")
        print(f"stage={stage} commit={sha} deployment={deployment} result=success")
        return 0
    # The process boundary must suppress even unexpected credential-bearing errors.
    except Exception:  # noqa: BLE001
        print(
            f"stage={stage} commit={sha} deployment={deployment} result=failure",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
