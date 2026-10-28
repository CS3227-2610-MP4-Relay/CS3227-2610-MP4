import io
import json
import subprocess
import tarfile
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

import release

SHA = "a" * 40
HEADERS = {
    "X-Frame-Options": "DENY",
    "Strict-Transport-Security": "max-age=31536000",
    "X-Content-Type-Options": "nosniff",
    "Set-Cookie": "csrftoken=synthetic; Path=/; Secure; SameSite=Lax",
}


class Response(io.BytesIO):
    def __init__(self, body, status=200, headers=None):
        super().__init__(body)
        self.status = status
        self.headers = Message()
        for key, value in (headers or HEADERS).items():
            self.headers[key] = value


@pytest.fixture
def cli_calls():
    return []


@pytest.fixture
def setup(monkeypatch, cli_calls):
    values = {
        "GITHUB_SHA": SHA,
        "VERCEL_TOKEN": "synthetic-token-never-print",
        "VERCEL_PROJECT_ID": "prj_synthetic",
        "VERCEL_TEAM_ID": "team_synthetic",
        "DJANGO_PRODUCTION_HOST": "relay.example.com",
        "DATABASE_URL": "postgresql://user:synthetic-db-password@ep-test.neon.tech/relay",
        "DJANGO_TRUST_PROXY_SSL_HEADER": "true",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(release.time, "sleep", lambda _: None)

    def cli(command, **options):
        cli_calls.append((command, options))
        return subprocess.CompletedProcess(
            command, 0, "https://relay-test.vercel.app\n"
        )

    monkeypatch.setattr(release.subprocess, "run", cli)
    monkeypatch.setattr(
        release, "prepare", lambda sha, path: path.mkdir(), raising=False
    )
    calls = []
    replies = []

    def open_request(request, timeout):
        calls.append((request, timeout))
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(release.OPENER, "open", open_request)
    return calls, replies


def ready(**changes):
    return {
        "id": "dpl_synthetic",
        "readyState": "READY",
        "projectId": "prj_synthetic",
        "target": "production",
        **changes,
    }


def api(value):
    return Response(json.dumps(value).encode())


def success(replies):
    replies.extend(
        [
            api({"id": "dpl_synthetic"}),
            api(ready(readyState="BUILDING")),
            api(ready()),
            api(
                {
                    "alias": "relay.example.com",
                    "projectId": "prj_synthetic",
                    "deploymentId": "dpl_synthetic",
                }
            ),
            Response(b"<h1>Relay</h1>"),
            Response(b"<h1>Sign in</h1>"),
            Response(b"<h1>Page not found.</h1>", 404),
        ]
    )


@pytest.mark.ac("PLT-1.10", "PLT-1.12", "PLT-1.13")
def test_cli_upload_and_bounded_anonymous_smoke(setup, capsys, cli_calls):
    calls, replies = setup
    success(replies)
    assert release.main(["deploy"]) == 0
    assert len(cli_calls) == 1
    command, options = cli_calls[0]
    assert {
        "deploy",
        "--prod",
        "--yes",
        "--no-wait",
        "--force",
        "--global-config",
    } <= set(command)
    assert options["cwd"] == command[command.index("--cwd") + 1]
    assert options["env"]["VERCEL_ORG_ID"] == "team_synthetic"
    assert options["env"]["VERCEL_PROJECT_ID"] == "prj_synthetic"
    assert options["capture_output"] is True and options["timeout"] <= 300
    assert "relay-test.vercel.app" in calls[0][0].full_url
    assert all(request.method == "GET" for request, _ in calls)
    assert all("withGitRepoInfo" not in request.full_url for request, _ in calls)
    assert [request.full_url for request, _ in calls[4:]] == [
        "https://relay.example.com/",
        "https://relay.example.com/sign-in/",
        "https://relay.example.com/relay-release-check-not-found/",
    ]
    assert all(timeout <= 30 for _, timeout in calls)
    assert all(timeout <= 10 for _, timeout in calls[4:])
    assert all(request.get_header("Authorization") is None for request, _ in calls[4:])
    output = capsys.readouterr()
    assert SHA in output.out and "dpl_synthetic" in output.out
    assert "synthetic-token" not in output.out
    assert output.err == ""


@pytest.mark.ac("PLT-1.11", "PLT-1.12")
@pytest.mark.parametrize("failure", [None, "checks", "migrations"])
def test_checks_precede_direct_migrations_and_errors_are_private(
    setup, monkeypatch, capsys, failure
):
    calls, _ = setup
    commands = []

    def run(command, **options):
        commands.append(command)
        assert options["capture_output"] is True
        assert options["timeout"] <= 300
        if ("check" if failure == "checks" else "migrate") in command and failure:
            raise subprocess.CalledProcessError(
                1, command, stderr=b"synthetic-db-password"
            )

    monkeypatch.setattr(release.subprocess, "run", run)
    assert release.main(["migrate"]) == (1 if failure else 0)
    assert "check" in commands[0] and "--deploy" in commands[0]
    assert "--fail-level" in commands[0] and "WARNING" in commands[0]
    if failure != "checks":
        assert "migrate" in commands[1] and "--noinput" in commands[1]
    assert all(
        "--settings=relay.settings.production" in command for command in commands
    )
    assert calls == []
    assert "synthetic-db-password" not in str(capsys.readouterr())


@pytest.mark.ac("PLT-1.11")
@pytest.mark.parametrize("invalid", ["pooler", "proxy"])
def test_migration_refuses_pooled_endpoint_or_unverified_proxy(
    setup, monkeypatch, invalid
):
    commands = []
    monkeypatch.setattr(release.subprocess, "run", lambda *a, **k: commands.append(a))
    if invalid == "pooler":
        monkeypatch.setenv(
            "DATABASE_URL", "postgresql://u:p@ep-test-pooler.neon.tech/db"
        )
    else:
        monkeypatch.setenv("DJANGO_TRUST_PROXY_SSL_HEADER", "false")
    assert release.main(["migrate"]) == 1
    assert commands == []


@pytest.mark.ac("PLT-1.10", "PLT-1.12")
@pytest.mark.parametrize(
    "result",
    [
        ready(projectId="prj_other"),
        ready(target="preview"),
        ready(readyState="ERROR"),
        ready(readyState="CANCELED"),
        ready(readyState="UNEXPECTED"),
    ],
)
def test_identity_or_terminal_failure_never_reaches_smoke(setup, result):
    calls, replies = setup
    replies.extend([api({"id": "dpl_synthetic"}), api(result)])
    assert release.main(["deploy"]) == 1
    assert len(calls) == 2


@pytest.mark.ac("PLT-1.12")
@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("synthetic-token-never-print"),
        URLError("synthetic-token-never-print"),
        Response(b"not-json"),
        api({"id": "\n::error::synthetic-token-never-print"}),
    ],
)
def test_ambiguous_creation_is_not_repeated_and_diagnostics_are_safe(
    setup, capsys, failure, cli_calls
):
    calls, replies = setup
    replies.append(failure)
    assert release.main(["deploy"]) == 1
    assert len(calls) == 1
    assert len(cli_calls) == 1
    output = capsys.readouterr()
    assert "stage=creation" in output.err
    assert "synthetic-token-never-print" not in str(output)


@pytest.mark.ac("PLT-1.12")
def test_polling_deadline_fails_without_smoke_or_another_creation(
    setup, monkeypatch, cli_calls
):
    calls, replies = setup
    replies.extend([api({"id": "dpl_synthetic"}), api(ready(readyState="BUILDING"))])
    ticks = iter([0, 0, 601])
    monkeypatch.setattr(release.time, "monotonic", lambda: next(ticks, 601))
    assert release.main(["deploy"]) == 1
    assert len(calls) <= 2
    assert len(cli_calls) == 1


@pytest.mark.ac("PLT-1.13")
@pytest.mark.parametrize(
    "change",
    [
        "redirect",
        "status",
        "text",
        "frame",
        "hsts",
        "nosniff",
        "cookie",
        "oversize",
        "timeout",
    ],
)
def test_smoke_failure_fails_release_without_writes(setup, change):
    calls, replies = setup
    replies.extend(
        [
            api({"id": "dpl_synthetic"}),
            api(ready()),
            api(
                {
                    "alias": "relay.example.com",
                    "projectId": "prj_synthetic",
                    "deploymentId": "dpl_synthetic",
                }
            ),
        ]
    )
    headers = {**HEADERS}
    body, status = b"<h1>Relay</h1>", 200
    if change in {"frame", "hsts", "nosniff", "cookie"}:
        headers.pop(
            {
                "frame": "X-Frame-Options",
                "hsts": "Strict-Transport-Security",
                "nosniff": "X-Content-Type-Options",
                "cookie": "Set-Cookie",
            }[change]
        )
    if change == "status":
        status = 503
    if change == "text":
        body = b"unexpected private page"
    if change == "oversize":
        body = b"x" * 65537
    if change == "redirect":
        replies.append(
            HTTPError("https://relay.example.com/", 302, "private", {}, None)
        )
    elif change == "timeout":
        replies.append(TimeoutError("private"))
    else:
        replies.append(Response(body, status, headers))
        if change == "cookie":
            replies.append(Response(b"<h1>Sign in</h1>", headers=headers))
    assert release.main(["deploy"]) == 1
    assert all(request.method == "GET" for request, _ in calls[1:])


@pytest.mark.ac("PLT-1.12", "PLT-1.13")
def test_http_transport_refuses_redirects_and_accepts_only_expected_404(monkeypatch):
    handler = next(
        item for item in release.OPENER.handlers if isinstance(item, release.NoRedirect)
    )
    assert (
        handler.redirect_request(None, None, 302, "", {}, "https://foreign.invalid")
        is None
    )
    monkeypatch.setattr(
        release.OPENER,
        "open",
        lambda *a, **k: (_ for _ in ()).throw(
            HTTPError(
                "https://relay.example.com/missing",
                404,
                "",
                Message(),
                io.BytesIO(b"missing"),
            )
        ),
    )
    assert (
        release.request("https://relay.example.com/missing", expected_404=True)[0]
        == 404
    )
    with pytest.raises(HTTPError):
        release.request("https://api.vercel.com/v13/deployments")


@pytest.mark.ac("PLT-1.10", "PLT-1.12")
@pytest.mark.parametrize(
    "changes",
    [
        {"alias": "other.example.com"},
        {"deploymentId": "dpl_old"},
        {"projectId": "prj_other"},
    ],
)
def test_public_alias_must_point_at_the_new_deployment(setup, changes):
    calls, replies = setup
    replies.extend(
        [
            api({"id": "dpl_synthetic"}),
            api(ready()),
            api(
                {
                    "alias": "relay.example.com",
                    "projectId": "prj_synthetic",
                    "deploymentId": "dpl_synthetic",
                    **changes,
                }
            ),
        ]
    )
    assert release.main(["deploy"]) == 1
    assert len(calls) == 3


@pytest.mark.ac("PLT-1.10", "PLT-1.12")
@pytest.mark.parametrize(
    "name,value",
    [
        ("GITHUB_SHA", "untrusted\n::error::payload"),
        ("VERCEL_PROJECT_ID", "untrusted\n::error::payload"),
        ("VERCEL_TEAM_ID", "untrusted\n::error::payload"),
        ("DJANGO_PRODUCTION_HOST", "https://foreign.invalid/path"),
        ("VERCEL_TOKEN", ""),
    ],
)
def test_invalid_release_configuration_cannot_request_or_inject_output(
    setup, monkeypatch, capsys, name, value
):
    calls, _ = setup
    monkeypatch.setenv(name, value)
    assert release.main(["deploy"]) == 1
    assert calls == []
    output = capsys.readouterr()
    assert "stage=configuration" in output.err
    assert "::error::" not in str(output) and "foreign.invalid" not in str(output)


@pytest.mark.ac("PLT-1.12")
def test_failure_after_creation_retains_only_safe_identity(setup, capsys):
    calls, replies = setup
    replies.extend(
        [api({"id": "dpl_synthetic"}), URLError("synthetic-token-never-print")]
    )
    assert release.main(["deploy"]) == 1
    output = capsys.readouterr()
    assert "stage=readiness" in output.err and "deployment=dpl_synthetic" in output.err
    assert "synthetic-token-never-print" not in str(output)
    assert len(calls) == 2


@pytest.mark.ac("PLT-1.13")
@pytest.mark.parametrize("size,valid", [(65535, True), (65536, True), (65537, False)])
def test_response_read_limit_boundaries(setup, size, valid):
    calls, replies = setup
    replies.append(Response(b"x" * size))
    if valid:
        assert (
            len(release.request("https://relay.example.com/", limit=65536)[2]) == size
        )
    else:
        with pytest.raises(ValueError):
            release.request("https://relay.example.com/", limit=65536)
    assert len(calls) == 1


@pytest.mark.ac("PLT-1.12")
@pytest.mark.parametrize("elapsed,valid", [(599, True), (600, False), (601, False)])
def test_ready_response_at_deadline_is_too_late(setup, monkeypatch, elapsed, valid):
    _, replies = setup
    success(replies)
    del replies[1]  # Go directly to READY to isolate its completion time.
    ticks = iter([0, 0, elapsed])
    monkeypatch.setattr(release.time, "monotonic", lambda: next(ticks, elapsed))
    assert release.main(["deploy"]) == (0 if valid else 1)


@pytest.fixture
def committed(monkeypatch):
    files = dict.fromkeys(
        [
            "requirements.txt",
            ".python-version",
            "pyproject.toml",
            "vercel.json",
            "src/manage.py",
            "src/relay/wsgi.py",
            "src/accounts/models.py",
        ],
        ("100644", b"committed bytes"),
    )
    calls, extras = [], []

    def git(*arguments):
        calls.append(arguments)
        assert SHA in arguments
        if arguments[0] == "ls-tree":
            roots = arguments[arguments.index("--") + 1 :]
            return (
                b"\0".join(
                    f"{mode} blob {'b' * 40}\t{path}".encode()
                    for path, (mode, _) in files.items()
                    if any(
                        path == root or path.startswith(root + "/") for root in roots
                    )
                )
                + b"\0"
            )
        assert arguments[0] == "archive"
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode="w") as archive:
            for path in arguments[arguments.index("--") + 1 :]:
                assert not any(part.startswith(".env") for part in path.split("/"))
                body = files[path][1]
                member = tarfile.TarInfo(path)
                member.size = len(body)
                archive.addfile(member, io.BytesIO(body))
            for member in extras:
                archive.addfile(member)
        return output.getvalue()

    monkeypatch.setattr(release, "_git", git, raising=False)
    return files, calls, extras


@pytest.mark.ac("PLT-1.10")
def test_archive_keeps_runtime_requirements_without_tooling_manifest(
    committed, tmp_path
):
    files, calls, _ = committed
    requirements = b"Django==6.1.2\npsycopg[binary]==3.3.6\n"
    files["requirements.txt"] = ("100644", requirements)
    files["pyproject.toml"] = ("100644", b"[tool.ruff]\nline-length = 88\n")
    destination = tmp_path / "source"

    release.prepare(SHA, destination)

    assert not (destination / "pyproject.toml").exists()
    assert (destination / "requirements.txt").read_bytes() == requirements
    assert (destination / "src/relay/wsgi.py").read_bytes() == b"committed bytes"
    assert all("pyproject.toml" not in command for command in calls)


@pytest.mark.ac("PLT-1.10")
@pytest.mark.parametrize(
    "excluded",
    [
        "src/relay/.env",
        "src/relay/.env.production",
        "src/relay/.ENV.local",
        "src/relay/tests/test_private.py",
        "src/relay/.git/config",
        "src/relay/.vercel/project.json",
        "src/relay/.venv/pyvenv.cfg",
        "src/relay/__pycache__/local.pyc",
        "src/relay/local.pyc",
    ],
)
def test_archive_reads_only_filtered_committed_inputs(
    committed, monkeypatch, tmp_path, excluded
):
    files, calls, _ = committed
    files[excluded] = ("100644", b"excluded")
    working = tmp_path / "work/src"
    working.mkdir(parents=True)
    (working / "manage.py").write_text("dirty uncommitted bytes")
    (working / "local-artifact.txt").write_text("untracked")
    monkeypatch.setattr(release, "__file__", str(working / "release.py"))
    destination = tmp_path / "source"
    release.prepare(SHA, destination)
    assert (destination / "src/manage.py").read_bytes() == b"committed bytes"
    assert not (destination / excluded).exists()
    assert not (destination / "src/local-artifact.txt").exists()
    assert excluded not in calls[1]


@pytest.mark.ac("PLT-1.10")
@pytest.mark.parametrize(
    "invalid", ["symlink", "submodule", "parent", "missing", "tarlink", "tardir"]
)
def test_unsafe_or_incomplete_source_archive_is_refused(committed, tmp_path, invalid):
    files, _, extras = committed
    if invalid in {"symlink", "submodule"}:
        files["src/relay/linked.py"] = (
            "120000" if invalid == "symlink" else "160000",
            b"target",
        )
    elif invalid == "parent":
        files["src/relay/../../outside"] = ("100644", b"outside")
    elif invalid == "missing":
        files.pop("requirements.txt")
    else:
        member = tarfile.TarInfo(
            "../outside" if invalid == "tardir" else "src/relay/link"
        )
        member.type = tarfile.DIRTYPE if invalid == "tardir" else tarfile.SYMTYPE
        member.linkname = "../../outside"
        extras.append(member)
    with pytest.raises(ValueError):
        release.prepare(SHA, tmp_path / "source")
    assert not (tmp_path / "outside").exists()


@pytest.mark.ac("PLT-1.10")
def test_prepare_command_needs_no_provider_secret_and_does_not_overwrite(
    committed, monkeypatch, tmp_path
):
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.delenv("VERCEL_TOKEN", raising=False)
    destination = tmp_path / "source"
    assert release.main(["prepare", str(destination)]) == 0
    with pytest.raises(FileExistsError):
        release.prepare(SHA, destination)
    assert (destination / "src/manage.py").read_bytes() == b"committed bytes"


@pytest.mark.ac("PLT-1.12")
@pytest.mark.parametrize(
    "outcome", ["failure", "timeout", "foreign", "userinfo", "multiple"]
)
def test_cli_failure_or_unsafe_url_is_private_and_never_retried(
    setup, monkeypatch, capsys, outcome
):
    calls, _ = setup
    attempts = []

    def cli(command, **options):
        attempts.append(command)
        if outcome == "failure":
            raise subprocess.CalledProcessError(
                1, command, stderr="synthetic-token-never-print"
            )
        if outcome == "timeout":
            raise subprocess.TimeoutExpired(
                command, 300, stderr="synthetic-token-never-print"
            )
        output = {
            "foreign": "https://foreign.invalid",
            "userinfo": "https://token@a.vercel.app",
            "multiple": "https://a.vercel.app\nhttps://b.vercel.app",
        }[outcome]
        return subprocess.CompletedProcess(command, 0, output)

    monkeypatch.setattr(release.subprocess, "run", cli)
    assert release.main(["deploy"]) == 1
    assert len(attempts) == 1 and calls == []
    output = capsys.readouterr()
    assert "stage=creation" in output.err and "synthetic-token-never-print" not in str(
        output
    )


@pytest.mark.ac("PLT-1.10")
def test_git_archive_selects_literal_filenames(monkeypatch):
    commands = []

    def run(command, **options):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, b"archive")

    monkeypatch.setattr(release.subprocess, "run", run)
    assert release._git("archive", SHA, "--", "src/relay/*") == b"archive"
    assert commands == [
        ["git", "--literal-pathspecs", "archive", SHA, "--", "src/relay/*"]
    ]
