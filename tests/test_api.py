# SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for stepup.notebook.api."""

import inspect
import pathlib

import pytest

from stepup.core.exceptions import PathError
from stepup.notebook import api
from stepup.notebook.api import convert_jupyter


@pytest.fixture
def run_commands(monkeypatch) -> list[str]:
    """Replace `run()` in the API module by a function that records the commands."""
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)

    monkeypatch.setattr("stepup.notebook.api.run", fake_run)
    return commands


@pytest.mark.parametrize("name", api.__all__)
def test_signature_conventions(name: str):
    """Only the input paths and `dest` are positional, all other arguments are keyword-only."""
    signature = inspect.signature(getattr(api, name))
    positional = [
        parameter.name
        for parameter in signature.parameters.values()
        if parameter.kind != inspect.Parameter.KEYWORD_ONLY
    ]
    assert all(arg.startswith("path") or arg == "dest" for arg in positional)
    for option in "optional", "resources", "duration", "step_info":
        parameter = signature.parameters.get(option)
        if parameter is not None:
            assert parameter.kind == inspect.Parameter.KEYWORD_ONLY


def test_convert_jupyter_timeout(run_commands: list[str]):
    convert_jupyter("demo.ipynb", timeout=1200)
    assert run_commands == [
        "sn-convert-jupyter demo.ipynb demo.html --to html --execute --timeout=1200"
    ]


def test_convert_jupyter_timeout_zero(run_commands: list[str]):
    convert_jupyter("demo.ipynb", timeout=0)
    assert run_commands == [
        "sn-convert-jupyter demo.ipynb demo.html --to html --execute --timeout=0"
    ]


def test_convert_jupyter_timeout_default(run_commands: list[str]):
    convert_jupyter("demo.ipynb")
    assert run_commands == ["sn-convert-jupyter demo.ipynb demo.html --to html --execute"]


def test_convert_jupyter_timeout_no_execute(run_commands: list[str]):
    convert_jupyter("demo.ipynb", execute=False, timeout=1200)
    assert run_commands == ["sn-convert-jupyter demo.ipynb demo.html --to html"]


@pytest.mark.parametrize("timeout", [-1, 1.5, "60", True])
def test_convert_jupyter_timeout_invalid(run_commands: list[str], timeout):
    with pytest.raises(ValueError, match="timeout must be a non-negative integer"):
        convert_jupyter("demo.ipynb", timeout=timeout)
    assert run_commands == []


@pytest.mark.parametrize(
    ("dest", "args"),
    [
        (None, "demo.html --to html"),
        ("out/", "out/demo.html --to html"),
        ("demo.md", "demo.md --to markdown"),
        ("out/demo.tex", "out/demo.tex --to latex"),
        ("demo.py", "demo.py --to script"),
        ("demo.pdf", "demo.pdf --to pdf"),
        ("demo_out.ipynb", "demo_out.ipynb --to notebook"),
    ],
)
def test_convert_jupyter_formats(run_commands: list[str], dest: str | None, args: str):
    convert_jupyter("demo.ipynb", dest, execute=False)
    assert run_commands == [f"sn-convert-jupyter demo.ipynb {args}"]


@pytest.mark.parametrize("dest", ["demo.rst", "demo.txt"])
def test_convert_jupyter_unsupported_extension(run_commands: list[str], dest: str):
    with pytest.raises(PathError):
        convert_jupyter("demo.ipynb", dest)
    assert run_commands == []


def test_convert_jupyter_wrong_notebook_extension(run_commands: list[str]):
    with pytest.raises(ValueError, match=r"\.ipynb, got demo\.py"):
        convert_jupyter("demo.py")
    assert run_commands == []


def test_convert_jupyter_parameters(run_commands: list[str]):
    convert_jupyter("demo.ipynb", execute=False, parameters={"dpi": 50})
    assert run_commands == [
        """sn-convert-jupyter demo.ipynb demo.html --to html --parameters='{"dpi": 50}'"""
    ]


@pytest.mark.parametrize("key", ["not valid", 1, "class"])
def test_convert_jupyter_parameters_invalid_key(run_commands: list[str], key):
    with pytest.raises(ValueError, match="valid Python identifiers"):
        convert_jupyter("demo.ipynb", parameters={key: 1})
    assert run_commands == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), [float("-inf")]])
def test_convert_jupyter_parameters_non_finite(run_commands: list[str], value):
    with pytest.raises(ValueError, match="cannot be NaN or infinity"):
        convert_jupyter("demo.ipynb", parameters={"x": value})
    assert run_commands == []


def test_convert_jupyter_parameters_not_dict(run_commands: list[str]):
    with pytest.raises(TypeError, match="must be a dict"):
        convert_jupyter("demo.ipynb", parameters=[("dpi", 50)])
    assert run_commands == []


def test_convert_jupyter_pathlib_inp_out(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "stepup.notebook.api.run", lambda command, **kwargs: calls.append((command, kwargs))
    )
    convert_jupyter("demo.ipynb", inp=pathlib.Path("data.csv"), out=pathlib.Path("plot.png"))
    ((_, kwargs),) = calls
    assert kwargs["inp"] == ["demo.ipynb", "data.csv"]
    assert kwargs["out"] == ["demo.html", "plot.png"]


def test_convert_jupyter_step_info(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "stepup.notebook.api.run", lambda command, **kwargs: calls.append((command, kwargs))
    )
    convert_jupyter("demo.ipynb", out="plot.png", step_info="info dir/demo.json")
    ((command, kwargs),) = calls
    assert command == (
        "sn-convert-jupyter demo.ipynb demo.html --to html --execute "
        "--step-info='info dir/demo.json'"
    )
    assert kwargs["out"] == ["demo.html", "plot.png", "info dir/demo.json"]
