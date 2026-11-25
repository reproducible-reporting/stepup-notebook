# SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Pytest configuration."""

import shutil
import subprocess

import pytest

from stepup.core.path import Path

# As a plugin, `stepup.core.pytest` also gets its assertions rewritten.
pytest_plugins = ("stepup.core.pytest",)

needs_jupyter = pytest.mark.skipif(not shutil.which("jupyter"), reason="No Jupyter")


@pytest.fixture
def path_tmp(tmpdir: str) -> Path:
    return Path(tmpdir)


def run_tool(*args: str, env: dict[str, str] | None = None):
    """Run one of the StepUp Notebook command-line tools in a subprocess, as StepUp does.

    Parameters
    ----------
    args
        The command and its arguments.
    env
        The environment variables of the subprocess.
        When `None`, the subprocess inherits the environment of the current process.
    """
    subprocess.run(args, stdin=subprocess.DEVNULL, check=True, env=env)
