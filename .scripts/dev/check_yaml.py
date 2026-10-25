# ///////////////////////////////////////////////////////////////
# CHECK_YAML - Pre-commit hook: YAML syntax validator
# Project: works-on-my-machine
# ///////////////////////////////////////////////////////////////

"""Pre-commit hook: validate YAML syntax."""

# ///////////////////////////////////////////////////////////////
# IMPORTS
# ///////////////////////////////////////////////////////////////
# Standard library
import sys

# Third-party
import yaml

# ///////////////////////////////////////////////////////////////

rc = 0
for path in sys.argv[1:]:
    try:
        with open(path, encoding="utf-8") as f:
            # compose(), not load(): it builds the node graph and so catches
            # every syntax error, without *constructing* Python objects. That
            # matters for mkdocs.yml, whose `!!python/name:` tags would
            # otherwise require mkdocs-material to be installed — it lives in
            # the `docs` group, which pre-commit does not sync.
            yaml.compose(f)
    except yaml.YAMLError as exc:
        print(f"{path}: {exc}")
        rc = 1
    except OSError as exc:
        print(f"{path}: {exc}")
        rc = 1

sys.exit(rc)
