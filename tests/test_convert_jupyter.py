# SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for stepup.notebook.convert_jupyter."""

import base64
import importlib
import json
import subprocess
import sys

import nbformat
import pytest
from conftest import needs_jupyter
from nbformat import v4

from stepup.core.exceptions import InputNotFoundError, UsageError
from stepup.core.path import Path
from stepup.core.stepinfo import StepInfo, load_step_info
from stepup.notebook.convert_jupyter import (
    NO_TIMEOUT_TAG,
    clear_outputs,
    execute_notebook,
    get_cell_timeout,
    inject_parameters,
    load_parameters,
    main,
    parse_args,
    parse_kernel_reply,
    resolve_timeout,
    write_step_info,
)


def test_resolve_timeout_unset(monkeypatch):
    monkeypatch.delenv("STEPUP_NOTEBOOK_CELL_TIMEOUT", raising=False)
    assert resolve_timeout(None) is None


def test_resolve_timeout_empty_variable(monkeypatch):
    monkeypatch.setenv("STEPUP_NOTEBOOK_CELL_TIMEOUT", "")
    assert resolve_timeout(None) is None


def test_resolve_timeout_variable(monkeypatch):
    monkeypatch.setenv("STEPUP_NOTEBOOK_CELL_TIMEOUT", "300")
    assert resolve_timeout(None) == 300


def test_resolve_timeout_variable_zero(monkeypatch):
    monkeypatch.setenv("STEPUP_NOTEBOOK_CELL_TIMEOUT", "0")
    assert resolve_timeout(None) is None


def test_resolve_timeout_argument(monkeypatch):
    monkeypatch.delenv("STEPUP_NOTEBOOK_CELL_TIMEOUT", raising=False)
    assert resolve_timeout(120) == 120


def test_resolve_timeout_argument_overrides_variable(monkeypatch):
    monkeypatch.setenv("STEPUP_NOTEBOOK_CELL_TIMEOUT", "300")
    assert resolve_timeout(120) == 120
    assert resolve_timeout(0) is None


@pytest.mark.parametrize("value", ["abc", "-5", "1.5"])
def test_resolve_timeout_invalid_variable(monkeypatch, value: str):
    monkeypatch.setenv("STEPUP_NOTEBOOK_CELL_TIMEOUT", value)
    with pytest.raises(ValueError, match="STEPUP_NOTEBOOK_CELL_TIMEOUT"):
        resolve_timeout(None)


def test_resolve_timeout_invalid_argument(monkeypatch):
    monkeypatch.delenv("STEPUP_NOTEBOOK_CELL_TIMEOUT", raising=False)
    with pytest.raises(ValueError, match="The timeout must be a non-negative integer"):
        resolve_timeout(-5)


def test_get_cell_timeout_untagged():
    cell = v4.new_code_cell("pass")
    assert get_cell_timeout(cell, 60) == 60


def test_get_cell_timeout_tagged():
    cell = v4.new_code_cell("pass", metadata={"tags": [NO_TIMEOUT_TAG]})
    assert get_cell_timeout(cell, 60) is None


def test_get_cell_timeout_other_tags():
    cell = v4.new_code_cell("pass", metadata={"tags": ["parameters"]})
    assert get_cell_timeout(cell, 60) == 60


def test_inject_parameters_after_tagged_cell(capsys):
    notebook = v4.new_notebook(
        cells=[
            v4.new_markdown_cell("# Title"),
            v4.new_code_cell("dpi = 100", metadata={"tags": ["parameters"]}),
            v4.new_code_cell("print(dpi)"),
        ]
    )
    inject_parameters(notebook, {"dpi": 50})
    sources = [cell.source for cell in notebook.cells]
    assert sources[:2] == ["# Title", "dpi = 100"]
    assert sources[2].splitlines()[1:] == ["dpi = 50"]
    assert sources[3] == "print(dpi)"
    assert capsys.readouterr().err == ""


def test_inject_parameters_without_tagged_cell(capsys):
    notebook = v4.new_notebook(
        cells=[v4.new_markdown_cell("# Title"), v4.new_code_cell("print(dpi)")]
    )
    inject_parameters(notebook, {"dpi": 50})
    sources = [cell.source for cell in notebook.cells]
    assert sources[0].splitlines()[1:] == ["dpi = 50"]
    assert sources[1:] == ["# Title", "print(dpi)"]
    assert "no cell tagged 'parameters'" in capsys.readouterr().err


def test_inject_parameters_json_values():
    parameters = {
        "flag": True,
        "off": False,
        "missing": None,
        "x": 1.5,
        "name": 'Zoë\'s "data"\n',
        "nested": {"a": [1, None, True], "b": {}},
    }
    notebook = v4.new_notebook(cells=[v4.new_code_cell("", metadata={"tags": ["parameters"]})])
    inject_parameters(notebook, load_parameters(json.dumps(parameters)))
    namespace = {}
    exec(notebook.cells[1].source, namespace)
    del namespace["__builtins__"]
    assert namespace == parameters


@pytest.mark.parametrize("name", ["class", "not valid", "1x"])
def test_inject_parameters_invalid_name(name: str):
    notebook = v4.new_notebook(cells=[])
    with pytest.raises(ValueError, match="must be a Python identifier"):
        inject_parameters(notebook, {name: 1})
    assert notebook.cells == []


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_load_parameters_non_finite(value: str):
    with pytest.raises(ValueError, match=f"cannot be {value}"):
        load_parameters(f'{{"x": {value}}}')


def test_load_parameters_not_object():
    with pytest.raises(TypeError, match="must be a JSON object"):
        load_parameters("[1, 2]")


def test_parse_args_timeout():
    assert parse_args(["demo.ipynb", "demo.html"]).timeout is None
    assert parse_args(["demo.ipynb", "demo.html", "--timeout=30"]).timeout == 30


def test_parse_args_step_info():
    assert parse_args(["demo.ipynb", "demo.html"]).step_info is None
    args = parse_args(["demo.ipynb", "demo.html", "--step-info", "info.json"])
    assert args.step_info == "info.json"


def make_kernel_reply(result: dict) -> dict:
    """Return the content of a successful reply to the kernel query with the given result."""
    return {"status": "ok", "user_expressions": {"info": result}}


def test_parse_kernel_reply(path_tmp: Path):
    data = {
        "inp": ["helper.py"],
        "env": [],
        "out": ["result.txt"],
        "vol": [],
        "abs_workdir": str(path_tmp / "sub"),
        "is_abs": False,
    }
    content = make_kernel_reply({"status": "ok", "data": {"application/json": data}})
    assert parse_kernel_reply(content) == StepInfo(
        None, inp=["helper.py"], out=["result.txt"], abs_workdir=path_tmp / "sub"
    )


def test_parse_kernel_reply_import_error():
    content = {"status": "error", "ename": "ModuleNotFoundError", "evalue": "No module named 'x'"}
    with pytest.raises(RuntimeError, match="ModuleNotFoundError: No module named 'x'"):
        parse_kernel_reply(content)


def test_parse_kernel_reply_input_not_found():
    content = make_kernel_reply(
        {"status": "error", "ename": "InputNotFoundError", "evalue": "Not available yet."}
    )
    with pytest.raises(InputNotFoundError, match="Not available yet"):
        parse_kernel_reply(content)


def test_parse_kernel_reply_expression_error():
    content = make_kernel_reply({"status": "error", "ename": "OSError", "evalue": "Broken"})
    with pytest.raises(RuntimeError, match="OSError: Broken"):
        parse_kernel_reply(content)


def test_parse_kernel_reply_no_json():
    content = make_kernel_reply({"status": "ok", "data": {"text/plain": "<JSON object>"}})
    with pytest.raises(UsageError, match="application/json"):
        parse_kernel_reply(content)


@pytest.fixture
def step_info_context(path_tmp: Path, monkeypatch) -> StepInfo:
    """Mimic a step in `path_tmp` that declared a notebook in `sub/` and a step info file.

    Returns
    -------
    declared
        The step info that `get_info()` returns in `sn-convert-jupyter`.
    """
    monkeypatch.setenv("STEPUP_ROOT", str(path_tmp))
    monkeypatch.chdir(path_tmp)
    declared = StepInfo(
        "sn-convert-jupyter sub/demo.ipynb sub/demo.md --to markdown --step-info info.json",
        inp=["sub/demo.ipynb"],
        out=["sub/demo.md", "info.json"],
    )
    amended = StepInfo(out=["sub/demo_md_files/output_0_0.png"])
    monkeypatch.setattr("stepup.notebook.convert_jupyter.get_info", lambda: declared)
    monkeypatch.setattr("stepup.notebook.convert_jupyter.get_amended_info", lambda: amended)
    return declared


def test_write_step_info(path_tmp: Path, step_info_context: StepInfo):
    kernel_info = StepInfo(
        inp=["data.txt", "./helper.py", "../sub/data.txt"],
        env=["STEPUP_PATH_FILTER"],
        out=["result.txt"],
        abs_workdir=path_tmp / "sub",
    )
    write_step_info("./info.json", kernel_info)
    assert load_step_info(path_tmp / "info.json") == StepInfo(
        step_info_context.command,
        inp=["sub/data.txt", "sub/demo.ipynb", "sub/helper.py"],
        env=["STEPUP_PATH_FILTER"],
        out=["sub/demo.md", "sub/demo_md_files/output_0_0.png", "sub/result.txt"],
    )


def test_write_step_info_without_kernel(path_tmp: Path, step_info_context: StepInfo):
    write_step_info("info.json", None)
    assert load_step_info(path_tmp / "info.json") == StepInfo(
        step_info_context.command,
        inp=["sub/demo.ipynb"],
        out=["sub/demo.md", "sub/demo_md_files/output_0_0.png"],
    )


@needs_jupyter
def test_execute_notebook_kernel_info(path_tmp: Path, monkeypatch):
    monkeypatch.setenv("STEPUP_ROOT", str(path_tmp))
    # Outside a step, `amend()` would print its calls in the outputs of the cells.
    monkeypatch.delenv("STEPUP_DEBUG", raising=False)
    monkeypatch.chdir(path_tmp)
    dir_nb = path_tmp / "sub"
    dir_nb.makedirs_p()
    (dir_nb / "helper.py").write_text("VALUE = 42\n", encoding="utf-8")
    (dir_nb / "data.txt").write_text("1\n", encoding="utf-8")
    notebook = v4.new_notebook(
        cells=[
            v4.new_code_cell("import helper\n\nfrom stepup.core.api import amend"),
            v4.new_code_cell('amend(inp="data.txt", out="result.txt")\nhelper.VALUE'),
        ]
    )
    kernel_info = execute_notebook(notebook, Path("sub"), None)
    assert kernel_info == StepInfo(
        inp=["data.txt", "helper.py"],
        env=["STEPUP_PATH_FILTER"],
        out=["result.txt"],
        abs_workdir=path_tmp / "sub",
    )
    # The query of the kernel after the last cell leaves no trace in the notebook.
    assert [cell.execution_count for cell in notebook.cells] == [1, 2]
    assert notebook.cells[0].outputs == []
    assert len(notebook.cells[1].outputs) == 1
    assert notebook.cells[1].outputs[0].data == {"text/plain": "42"}


class FakeBinaryExporter:
    """An exporter that returns bytes, like the PDF exporter of nbconvert."""

    def from_notebook_node(self, notebook, resources=None):
        return b"%PDF-fake\r\n\x00\xff", {}


def test_main_binary_output(path_tmp: Path, monkeypatch):
    path_nb = path_tmp / "demo.ipynb"
    nbformat.write(v4.new_notebook(cells=[v4.new_code_cell("pass")]), path_nb)
    monkeypatch.setattr("nbconvert.exporters.get_exporter", lambda to: FakeBinaryExporter)
    main([path_nb, path_tmp / "demo.pdf", "--to", "pdf"])
    assert (path_tmp / "demo.pdf").read_bytes() == b"%PDF-fake\r\n\x00\xff"


def test_main_html_title(path_tmp: Path):
    path_nb = path_tmp / "demo.ipynb"
    nbformat.write(v4.new_notebook(cells=[v4.new_markdown_cell("# Hello")]), path_nb)
    main([path_nb, path_tmp / "out" / "demo.html"])
    assert "<title>demo</title>" in (path_tmp / "out" / "demo.html").read_text()


def test_main_latex_no_date(path_tmp: Path):
    path_nb = path_tmp / "demo.ipynb"
    nbformat.write(v4.new_notebook(cells=[v4.new_markdown_cell("# Hello")]), path_nb)
    main([path_nb, path_tmp / "demo.tex", "--to", "latex"])
    assert "\\date{}" in (path_tmp / "demo.tex").read_text()


def test_main_latex_date_from_metadata(path_tmp: Path):
    path_nb = path_tmp / "demo.ipynb"
    notebook = v4.new_notebook(cells=[v4.new_markdown_cell("# Hello")])
    notebook.metadata.date = "1 April 2024"
    nbformat.write(notebook, path_nb)
    main([path_nb, path_tmp / "demo.tex", "--to", "latex"])
    assert "\\date{1 April 2024}" in (path_tmp / "demo.tex").read_text()


PNG_DATA = b"\x89PNG\r\n\x1a\nfake"


def make_notebook_with_figure(path_nb: Path):
    """Write a notebook with a figure in a cell output and an image attached to a Markdown cell."""
    png_b64 = base64.b64encode(PNG_DATA).decode("ascii")
    markdown_cell = v4.new_markdown_cell("![logo](attachment:logo.png)")
    markdown_cell.attachments = {"logo.png": {"image/png": png_b64}}
    code_cell = v4.new_code_cell(
        "plot()",
        outputs=[v4.new_output("display_data", data={"image/png": png_b64})],
    )
    nbformat.write(v4.new_notebook(cells=[markdown_cell, code_cell]), path_nb)


@pytest.mark.parametrize(
    ("to", "ext", "reference"),
    [
        ("markdown", "md", "![png](demo_md_files/output_1_0.png)"),
        ("latex", "tex", "{demo_tex_files/output_1_0.png}"),
    ],
)
def test_main_extracted_figures(path_tmp: Path, monkeypatch, to: str, ext: str, reference: str):
    path_nb = path_tmp / "demo.ipynb"
    make_notebook_with_figure(path_nb)
    amended = []
    monkeypatch.setattr(
        "stepup.notebook.convert_jupyter.amend", lambda out: amended.extend(map(str, out))
    )
    main([path_nb, path_tmp / "out" / f"demo.{ext}", "--to", to])
    assert reference in (path_tmp / "out" / f"demo.{ext}").read_text()
    path_figure = path_tmp / "out" / f"demo_{ext}_files" / "output_1_0.png"
    assert path_figure.read_bytes() == PNG_DATA
    assert str(path_figure) in amended


def test_main_extracted_attachment(path_tmp: Path, monkeypatch):
    path_nb = path_tmp / "demo.ipynb"
    make_notebook_with_figure(path_nb)
    monkeypatch.setattr("stepup.notebook.convert_jupyter.amend", lambda out: None)
    main([path_nb, path_tmp / "demo.md", "--to", "markdown"])
    assert "![logo](demo_md_files/logo.png)" in (path_tmp / "demo.md").read_text()
    assert (path_tmp / "demo_md_files" / "logo.png").read_bytes() == PNG_DATA


def test_main_embedded_figures(path_tmp: Path, monkeypatch):
    path_nb = path_tmp / "demo.ipynb"
    make_notebook_with_figure(path_nb)
    amended = []
    monkeypatch.setattr("stepup.notebook.convert_jupyter.amend", amended.append)
    main([path_nb, path_tmp / "demo.html"])
    assert not (path_tmp / "demo_html_files").exists()
    assert amended == []


def test_clear_outputs():
    notebook = v4.new_notebook(
        cells=[
            v4.new_markdown_cell("# Title"),
            v4.new_code_cell(
                "print('hello')",
                execution_count=1,
                outputs=[v4.new_output("stream", name="stdout", text="hello\n")],
            ),
        ]
    )
    clear_outputs(notebook)
    assert notebook.cells[0].source == "# Title"
    assert notebook.cells[1].outputs == []
    assert notebook.cells[1].execution_count is None


def run_failing_tool(*args: str) -> str:
    """Run `sn-convert-jupyter` in a subprocess that must fail, and return its standard error."""
    cp = subprocess.run(
        ["sn-convert-jupyter", *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    assert cp.returncode != 0
    return cp.stderr


def write_failing_notebook(path_nb: Path, source: str):
    """Write a notebook whose second code cell runs `source`.

    The last cell has outputs that must be removed when the notebook is executed.
    """
    notebook = v4.new_notebook(
        cells=[
            v4.new_code_cell("print('first', 'result')"),
            v4.new_code_cell(source),
            v4.new_code_cell(
                "print('last result')",
                execution_count=3,
                outputs=[v4.new_output("stream", name="stdout", text="stale output\n")],
            ),
        ]
    )
    with open(path_nb, "w", encoding="utf-8", newline="\n") as fh:
        nbformat.write(notebook, fh)


@needs_jupyter
def test_main_cell_error(path_tmp: Path):
    path_nb = path_tmp / "fail.ipynb"
    write_failing_notebook(path_nb, "1 / 0")
    path_out = path_tmp / "out" / "fail.ipynb"
    stderr = run_failing_tool(path_nb, path_out, "--to", "notebook", "--execute")
    assert "ZeroDivisionError" in stderr
    cells = nbformat.read(path_out, as_version=4).cells
    assert cells[0].outputs[0].text == "first result\n"
    assert cells[1].outputs[-1].output_type == "error"
    assert cells[1].outputs[-1].ename == "ZeroDivisionError"
    assert cells[2].outputs == []
    assert cells[2].execution_count is None


@needs_jupyter
def test_main_cell_timeout(path_tmp: Path):
    path_nb = path_tmp / "slow.ipynb"
    write_failing_notebook(path_nb, "import time\n\ntime.sleep(10)")
    path_out = path_tmp / "slow.html"
    stderr = run_failing_tool(path_nb, path_out, "--execute", "--timeout=1")
    assert "exceeded the timeout of 1 s" in stderr
    html = path_out.read_text(encoding="utf-8")
    assert "first result" in html
    assert "The cell exceeded the timeout of 1 s." in html
    assert "stale output" not in html


def test_import_without_jupyter(monkeypatch):
    monkeypatch.setitem(sys.modules, "nbclient", None)
    monkeypatch.delitem(sys.modules, "stepup.notebook.convert_jupyter")
    with pytest.raises(UsageError, match=r"stepup-notebook\[jupyter\]"):
        importlib.import_module("stepup.notebook.convert_jupyter")
