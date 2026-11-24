"""Template workflows pin the same action versions as the repository's own."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_WORKFLOWS = ROOT / ".github" / "workflows"
TEMPLATES = ROOT / "src" / "womm" / "assets" / "copier" / "official"

# `uses: owner/action@<40-hex sha>`, the form every workflow here pins to.
USES = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@([0-9a-f]{40})")


def pins(paths: list[Path]) -> dict[str, set[str]]:
    """Map each action to the SHAs it is pinned to across the files."""
    found: dict[str, set[str]] = {}
    for path in paths:
        for action, sha in USES.findall(path.read_text(encoding="utf-8")):
            found.setdefault(action, set()).add(sha)
    return found


TEMPLATE_WORKFLOWS = sorted(TEMPLATES.glob("*/template/**/workflows/*.jinja"))


@pytest.mark.skipif(
    not REPOSITORY_WORKFLOWS.is_dir(), reason="repository workflows not available"
)
@pytest.mark.parametrize("workflow", TEMPLATE_WORKFLOWS, ids=lambda p: p.parts[-5])
def test_template_actions_follow_the_repository_pins(workflow: Path):
    # Dependabot cannot read the templates' `.jinja` workflows: it bumps the
    # repository's, and this test asks for the same bump in the templates.
    repository = pins(sorted(REPOSITORY_WORKFLOWS.glob("*.yml")))
    template = pins([workflow])

    assert template, f"no pinned action found in {workflow}"
    stale = {
        action: (shas, repository[action])
        for action, shas in template.items()
        if action in repository and shas != repository[action]
    }
    assert not stale, f"template pins differ from .github/workflows: {stale}"
