import subprocess
import sys
from pathlib import Path

import pytest

from check_site import check_site


@pytest.fixture
def site(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/style.css").write_text("body { color: black; }")
    (tmp_path / "index.html").write_text(
        '<link href="/relay/assets/style.css" rel="stylesheet">'
        '<a href="Reflections.html">Reflections</a>'
        '<a href="https://github.com/example/repo">Source</a>'
        '<a href="#project">Project</a>'
    )
    (tmp_path / "Reflections.html").write_text('<a href="/relay/">Home</a>')
    return tmp_path


@pytest.mark.ac("PLT-2.2", "PLT-2.3")
def test_valid_rendered_artifact(site):
    assert check_site(site, "/relay", "https://example.github.io") == []


@pytest.mark.ac("PLT-2.2", "PLT-2.3")
@pytest.mark.parametrize(
    "missing", ["index.html", "Reflections.html", "assets/style.css"]
)
def test_missing_required_page_or_asset_fails(site, missing):
    (site / missing).unlink()
    assert check_site(site, "/relay", "https://example.github.io")


@pytest.mark.ac("PLT-2.2", "PLT-2.3")
@pytest.mark.parametrize(
    "link",
    [
        "/assets/style.css",
        "/relay-other/assets/style.css",
        "missing.html?query=1#section",
        "../outside.html",
        "/relay/%2e%2e/outside.html",
        "https://example.github.io/relay/missing.html",
        "//example.github.io/relay/missing.html",
    ],
)
def test_broken_or_outside_local_link_fails(site, link):
    with (site / "index.html").open("a") as page:
        page.write(f'<a href="{link}">Link</a>')
    assert check_site(site, "/relay", "https://example.github.io")


@pytest.mark.ac("PLT-2.2", "PLT-2.3")
@pytest.mark.parametrize("guide", ["UserGuide", "DeveloperGuide"])
@pytest.mark.parametrize("suffix", [".html", ".md", "/index.html"])
def test_guide_leakage_fails(site, guide, suffix):
    leaked = site / (guide + suffix)
    leaked.parent.mkdir(exist_ok=True)
    leaked.write_text("Guide content")
    assert check_site(site, "/relay", "https://example.github.io")


@pytest.mark.ac("PLT-2.2", "PLT-2.3")
def test_css_asset_reference_is_checked(site):
    (site / "assets/style.css").write_text('body {background: url("missing.png")}')
    assert check_site(site, "/relay", "https://example.github.io")


@pytest.mark.ac("PLT-2.2", "PLT-2.3")
def test_artifact_without_theme_stylesheet_fails(site):
    (site / "index.html").write_text('<a href="Reflections.html">Reflections</a>')
    assert "Missing local theme stylesheet" in check_site(
        site, "/relay", "https://example.github.io"
    )


@pytest.mark.ac("PLT-2.2", "PLT-2.3")
def test_valid_encoded_nested_links_and_external_assets(site):
    (site / "nested").mkdir()
    (site / "nested/index.html").write_text(
        '<a href="../Reflections.html?x=1#section">Back</a>'
        '<img src="https://external.example/unfetched.png">'
        '<img src="../assets/a%20b.png">'
    )
    (site / "assets/a b.png").write_bytes(b"synthetic")
    (site / "assets/style.css").write_text(
        'body {background: url("data:image/png;base64,AA==")}'
    )
    assert check_site(site, "/relay", "https://example.github.io") == []


@pytest.mark.ac("PLT-2.3")
@pytest.mark.parametrize("valid", [True, False])
def test_checker_command_reports_actual_artifact_status(site, tmp_path, valid):
    config = tmp_path / "config.yml"
    config.write_text("url: https://example.github.io\nbaseurl: /relay\n")
    if not valid:
        (site / "Reflections.html").unlink()
    checker = Path(__file__).resolve().parents[1] / "check_site.py"
    result = subprocess.run(
        [sys.executable, str(checker), str(site), "--config", str(config)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == (0 if valid else 1)
    if valid:
        assert result.stderr == ""
    else:
        assert "Reflections.html" in result.stderr


@pytest.mark.ac("PLT-2.3", "PLT-2.4", "PLT-2.5")
def test_ci_site_publication_boundaries():
    workflow = (
        Path(__file__).resolve().parents[2] / ".github/workflows/ci.yml"
    ).read_text()
    site_job = workflow.split("\n  site:\n")[1].split("\n  deploy:\n")[0]
    deploy_job = workflow.split("\n  deploy:\n")[1]
    assert "\n  pull_request:\n" in workflow
    assert "\n  push:\n    branches:\n      - main\n" in workflow
    assert "workflow_dispatch" not in workflow
    assert "configure-pages" not in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "if:" not in site_job
    assert "persist-credentials: false" in site_job
    assert "source: docs" in site_job and "destination: _site" in site_job
    assert "python src/check_site.py _site --config docs/_config.yml" in site_job
    assert site_job.index("python src/check_site.py") < site_job.index(
        "actions/upload-pages-artifact@"
    )
    assert "needs: [verify, site]" in deploy_job
    assert (
        "if: github.event_name == 'push' && github.ref == 'refs/heads/main'"
        in deploy_job
    )
    assert "always()" not in deploy_job and "continue-on-error" not in workflow
    assert "name: github-pages" in deploy_job
    assert "pages: write" in deploy_job and "id-token: write" in deploy_job
    assert "pages: write" not in workflow.split("\n  deploy:\n")[0]
    assert "id-token: write" not in workflow.split("\n  deploy:\n")[0]
    assert "group: pages" in deploy_job and "cancel-in-progress: false" in deploy_job
    for action in (
        "jekyll-build-pages@44a6e6beabd48582f863aeeb6cb2151cc1716697",
        "upload-pages-artifact@7b1f4a764d45c48632c6b24a0339c27f5614fb0b",
        "deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e",
    ):
        assert f"actions/{action}" in workflow
