# SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Application programming interface for StepUp Notebook."""

import json
import keyword
import shlex
from collections.abc import Collection

from stepup.core.api import run, shq, subs_env_vars
from stepup.core.path import StrPath, coerce_paths, make_path_out
from stepup.core.stepinfo import StepInfo

__all__ = ("convert_jupyter",)


def convert_jupyter(
    path_nb: StrPath,
    dest: StrPath | None = None,
    *,
    inp: StrPath | Collection[StrPath] = (),
    out: StrPath | Collection[StrPath] = (),
    step_info: StrPath | None = None,
    execute: bool = True,
    parameters: dict | None = None,
    timeout: int | None = None,
    optional: bool = False,
    resources: dict[str, int] | str | None = None,
    duration: float | None = None,
) -> StepInfo:
    """Convert a Jupyter notebook, by default to HTML with execution of cells.

    The cells are executed with the directory of the notebook as the current directory.
    When a cell raises an exception or exceeds the timeout, the step fails,
    but the output is still written, with the outputs up to that cell and the error.
    Output formats that cannot embed figures, such as Markdown and LaTeX,
    get them as separate files, which are declared as outputs automatically.
    See the [usage page](usage.md) for examples and the location of these files.

    Parameters
    ----------
    path_nb
        The input Jupyter notebook.
    dest
        Output destination: `None`, a directory (with a trailing slash) or a file.
        The output is an HTML file, unless `dest` is a file with extension
        `.ipynb`, `.py`, `.md`, `.tex` or `.pdf`, which selects the output format.
        See [Output Formats](usage.md#output-formats) for a description of each format.
    inp
        One or more input files used by the notebook.
        You can also declare inputs with `amend(inp=...)` in the notebook,
        but specifying them here will make the scheduling more efficient.
    out
        One or more output files produced by the notebook.
        You can also declare outputs with `amend(out=...)` in the notebook,
        but you can specify them here if you want to make the notebook execution optional,
        i.e. dependent on whether the outputs are used in other steps.
    step_info
        A JSON file to which all inputs and outputs of the step are written
        when the step succeeds, in the format of `dump_step_info()` of StepUp Core.
        It includes the dependencies amended by the notebook,
        the local modules imported by the notebook,
        and the figures written to separate files for the Markdown and LaTeX formats.
        The file is an output of the step, but it does not list itself.
        Pass it to `make_inventory()` of StepUp Data to archive these files,
        e.g. to share a notebook together with the data and modules it uses.
    execute
        If `True`, the notebook is executed before conversion.
    parameters
        Arguments to pass to the notebook as a JSON-serializable dictionary,
        whose keys are valid Python identifiers and not keywords.
        NaN and infinity are not supported as values.
        The items are assigned in a new cell after the one tagged `parameters`.
        The `parameters` cell should contain the defaults,
        which may then be overridden by the values in `parameters`.
        When the notebook has no cell tagged `parameters`,
        the new cell is inserted at the top of the notebook and a warning is printed.
    timeout
        The timeout in seconds for the execution of a single cell.
        `0` disables the timeout.
        Defaults to `${STEPUP_NOTEBOOK_CELL_TIMEOUT}` or no timeout if the variable is unset.
        Changing `STEPUP_NOTEBOOK_CELL_TIMEOUT` does not cause notebooks to be executed again.
        Cells tagged `stepup-no-timeout` never time out.
        Ignored when `execute` is `False`.
    optional
        If `True`, the step is only executed when needed by other steps.
    resources
        Named resources required to run this step, e.g. `{"gpu": 1}`.
        See `stepup.core.api.step()` for details.
    duration
        An initial estimate of the step's wall time in seconds.
        See `stepup.core.api.step()` for details.
        This estimate is only used for scheduling and is unrelated to `timeout`.

    Returns
    -------
    step_info
        Holds relevant information of the step, useful for defining follow-up steps.
    """
    if timeout is not None and (
        not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 0
    ):
        raise ValueError(f"timeout must be a non-negative integer or None, got {timeout!r}")
    with subs_env_vars() as subs:
        path_nb = subs(path_nb)
        dest = subs(dest)
        step_info = subs(step_info)
    if not path_nb.endswith(".ipynb"):
        raise ValueError(f"The notebook file must have extension .ipynb, got {path_nb}.")
    formats = {
        ".html": "html",
        ".pdf": "pdf",
        ".ipynb": "notebook",
        ".tex": "latex",
        ".md": "markdown",
        ".py": "script",
    }
    path_out = make_path_out(path_nb, dest, ".html", formats)
    to = formats[path_out.suffix]
    paths_out = [path_out, *coerce_paths(out)]
    parts = ["sn-convert-jupyter", shq(path_nb), shq(path_out), "--to", to]
    if execute:
        parts.append("--execute")
        if timeout is not None:
            parts.append(f"--timeout={timeout}")
    if parameters is not None:
        if not isinstance(parameters, dict):
            raise TypeError(f"parameters must be a dict, got {type(parameters)}")
        invalid = [
            key
            for key in parameters
            if not (isinstance(key, str) and key.isidentifier()) or keyword.iskeyword(key)
        ]
        if len(invalid) > 0:
            raise ValueError(
                "All keys in parameters must be valid Python identifiers "
                f"and not keywords, got {invalid!r}."
            )
        try:
            parameters_str = json.dumps(parameters, allow_nan=False)
        except ValueError as exc:
            raise ValueError(
                f"The values in parameters cannot be NaN or infinity, got {parameters!r}."
            ) from exc
        parts.append(f"--parameters={shlex.quote(parameters_str)}")
    if step_info is not None:
        parts.append(f"--step-info={shq(step_info)}")
        paths_out.append(step_info)
    return run(
        " ".join(parts),
        inp=[path_nb, *coerce_paths(inp)],
        out=paths_out,
        optional=optional,
        resources=resources,
        duration=duration,
    )
