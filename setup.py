import os
import re

from setuptools import setup
from setuptools_scm import Configuration
from setuptools_scm._get_version_impl import parse_version


def get_version() -> str:
    """Create version string based on branch name.

    release branch -> 1.2.3rc4
    develop branch -> 1.2.3a4
    other branch -> 1.2.3.dev4+<branch_name>

    Returns:
        version
    """
    config = Configuration()
    version = parse_version(config)
    # Handle version.distance None or any other unexpected falsy value that cannot be coerced to int
    if not version.distance:
        return str(version.tag)

    from setuptools_scm.version import guess_next_version

    branch = os.getenv("CI_COMMIT_REF_NAME", version.branch)
    if branch.startswith("release"):
        fmt = "{guessed}rc{distance}"
    elif branch.startswith("develop"):
        fmt = "{guessed}a{distance}"
    else:
        local = re.sub("[^0-9a-zA-Z]+", ".", branch)
        fmt = f"{{guessed}}.dev{{distance}}+{local}"

    return version.format_next_version(guess_next_version, fmt)


setup(
    setuptools_git_versioning={
        "enabled": True,
        "version_callback": get_version,
    },
)
