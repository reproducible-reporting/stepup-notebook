# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Tests for stepup.notebook.env_vars."""

import ast
import os
import re
import subprocess
import sys

import pytest

import stepup.notebook
from stepup.core.cli.env_vars_loader import core_env_vars
from stepup.core.exceptions import StepUpError
from stepup.core.path import Path
from stepup.notebook.env_vars import env_vars, parse_timeout


def _string_constants(source: str) -> set[str]:
    """Return every string literal in a module that has the form of a StepUp variable name."""
    return {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and re.fullmatch("STEPUP_[A-Z0-9_]+", node.value)
    }


def test_env_vars_are_registered():
    """Every variable that StepUp Notebook reads is registered, and vice versa.

    A variable that is read but not registered would be listed by `stepup config`
    as being without effect.
    """
    path_package = Path(stepup.notebook.__file__).parent
    found = set()
    for path in path_package.walkfiles("*.py"):
        if path.name != "env_vars.py":
            found.update(_string_constants(path.read_text(encoding="utf-8")))
    registered = set(env_vars().env_vars)
    assert found - registered <= set(core_env_vars().env_vars)
    assert registered - found == set()


def test_registry():
    registry = env_vars()
    assert registry.package == "StepUp Notebook"
    for name, info in registry.env_vars.items():
        assert name.startswith("STEPUP_NOTEBOOK_")
        assert not info.secret
        assert not info.overridden


@pytest.mark.parametrize(
    ("value", "expected"),
    [("", None), ("  ", None), ("0", None), ("300", 300), (" 60\n", 60)],
)
def test_parse_timeout(value: str, expected: int | None):
    assert parse_timeout(value) == expected


@pytest.mark.parametrize("value", ["abc", "-5", "1.5"])
def test_parse_timeout_invalid(value: str):
    with pytest.raises(
        StepUpError, match=re.escape(f"must be a non-negative integer, got {value!r}")
    ):
        parse_timeout(value)


def _stepup_config(path_tmp: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run `stepup config` in an environment with no other StepUp variables than those given.

    The home directory is replaced, so that a config file of the developer cannot interfere.
    """
    full_env = {name: value for name, value in os.environ.items() if not name.startswith("STEPUP_")}
    full_env.update(HOME=path_tmp, STEPUP_ROOT=path_tmp, **env)
    return subprocess.run(
        [sys.executable, "-m", "stepup.core", "config"],
        cwd=path_tmp,
        env=full_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_stepup_config(path_tmp: Path):
    cp = _stepup_config(path_tmp, {"STEPUP_NOTEBOOK_CELL_TIMEOUT": "600"})
    assert cp.returncode == 0, cp.stdout + cp.stderr
    assert (
        '# StepUp Notebook environment variables:\n#   STEPUP_NOTEBOOK_CELL_TIMEOUT = "600"\n'
    ) in cp.stdout
    assert "ERROR" not in cp.stdout


def test_stepup_config_invalid(path_tmp: Path):
    cp = _stepup_config(path_tmp, {"STEPUP_NOTEBOOK_CELL_TIMEOUT": "-5"})
    assert cp.returncode != 0
    assert (
        '#   STEPUP_NOTEBOOK_CELL_TIMEOUT = "-5"  '
        "<-- ERROR: must be a non-negative integer, got '-5'\n"
    ) in cp.stdout
