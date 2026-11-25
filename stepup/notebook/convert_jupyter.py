# SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Wrapper for Jupyter notebook conversion using nbconvert Python API."""

import argparse
import asyncio
import copy
import json
import keyword
import os
import sys
from collections.abc import Sequence

# StepUp is imported before the optional Jupyter packages,
# so that StepUp's short traceback is in place when one of them is missing.
from stepup.core.api import amend, get_amended_info, get_info
from stepup.core.cattrs import json_converter
from stepup.core.exceptions import InputNotFoundError, StepUpError, UsageError
from stepup.core.extapi import child_env
from stepup.core.path import Path
from stepup.core.stepinfo import StepInfo, dump_step_info
from stepup.notebook.env_vars import parse_timeout

try:
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError, CellTimeoutError
    from nbconvert import exporters
    from nbformat import NotebookNode, read, v4

    from stepup.notebook.jupyter_kernel import kernel_config
except ModuleNotFoundError as exc:
    raise UsageError(
        f"sn-convert-jupyter cannot import {exc.name}. "
        "Install the Jupyter dependencies of StepUp Notebook, "
        "e.g. with: pip install 'stepup-notebook[jupyter]'"
    ) from None

__all__ = ("main",)

NO_TIMEOUT_TAG = "stepup-no-timeout"

KERNEL_QUERY_CODE = "from stepup.notebook.kernel_hook import finish as _stepup_finish"
"""The code of the request that `query_kernel` sends after the last cell."""

KERNEL_QUERY_EXPRESSION = "_stepup_finish()"
"""The user expression that the kernel evaluates after `KERNEL_QUERY_CODE`."""


def main(argv: Sequence[str] | None = None):
    """Main program."""
    args = parse_args(argv)

    if not args.path_nb.endswith(".ipynb"):
        raise ValueError("The notebook file must have extension .ipynb")

    notebook = read(args.path_nb, as_version=4)

    if args.parameters is not None:
        inject_parameters(notebook, load_parameters(args.parameters))

    kernel_info = None
    if args.execute:
        timeout = resolve_timeout(args.timeout)
        # A failed notebook is still written up to the failing cell,
        # so that the error can be inspected in the context of the preceding results.
        try:
            kernel_info = execute_notebook(notebook, Path(args.path_nb).parent.normpath(), timeout)
        except CellExecutionError:
            write_output(notebook, args.path_nb, args.to, args.path_out)
            raise
        except CellTimeoutError as exc:
            write_output(notebook, args.path_nb, args.to, args.path_out)
            raise RuntimeError(
                f"A cell in {args.path_nb} exceeded the timeout of {timeout} s. "
                f"Tag the cell with '{NO_TIMEOUT_TAG}' to disable its timeout, "
                "or change the timeout with the 'timeout' argument of convert_jupyter() "
                "or the STEPUP_NOTEBOOK_CELL_TIMEOUT environment variable."
            ) from exc
    write_output(notebook, args.path_nb, args.to, args.path_out)
    if args.step_info is not None:
        write_step_info(args.step_info, kernel_info)


def execute_notebook(notebook: NotebookNode, dir_nb: Path, timeout: int | None) -> StepInfo:
    """Execute the code cells of a notebook in a new kernel, up to the first error.

    The outputs stored in the notebook are removed first,
    so that the cells after a failing cell have no outputs.
    After the last cell, the kernel amends the local modules imported by the notebook,
    and reports the dependencies amended in the kernel, see `query_kernel`.

    Parameters
    ----------
    notebook
        The notebook, which is modified in place.
    dir_nb
        The directory in which the cells are executed.
    timeout
        The timeout in seconds for the execution of a single cell, or `None` for no timeout.
        Cells tagged `stepup-no-timeout` never time out.

    Returns
    -------
    kernel_info
        The dependencies amended in the kernel, as returned by `query_kernel`.

    Raises
    ------
    CellExecutionError
        When a cell not tagged `raises-exception` raises an exception.
        The outputs of that cell include the traceback.
    CellTimeoutError
        When a cell exceeds the timeout.
        An error output is added to that cell.
    InputNotFoundError, UsageError, RuntimeError
        When the kernel cannot report its dependencies, see `parse_kernel_reply`.
    """
    clear_outputs(notebook)
    running_index = None

    def track_cell(cell: NotebookNode, cell_index: int):
        nonlocal running_index
        running_index = cell_index

    with kernel_config() as config:
        client = NotebookClient(
            notebook,
            config=config,
            timeout=timeout,
            timeout_func=lambda cell: get_cell_timeout(cell, timeout),
            kernel_name="python3",
            extra_arguments=["--IPKernelApp.log_level=40"],
            # Timestamps in the cell metadata would make every executed notebook differ.
            record_timing=False,
            on_cell_execute=track_cell,
        )
        # pyzmq needs the `add_reader` methods of a selector event loop.
        # The default event loop on Windows lacks them,
        # and pyzmq then warns on standard error (as of pyzmq 27.3).
        try:
            with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
                return runner.run(run_kernel(client, dir_nb))
        except CellTimeoutError:
            # The cell may already end with a `KeyboardInterrupt` traceback,
            # showing where it got stuck, because the kernel is interrupted before it shuts down
            # (observed with jupyter_client 8.10 and nbclient 0.11).
            if running_index is not None:
                evalue = f"The cell exceeded the timeout of {timeout} s."
                notebook.cells[running_index].outputs.append(
                    v4.new_output(
                        "error",
                        ename="CellTimeoutError",
                        evalue=evalue,
                        traceback=[f"CellTimeoutError: {evalue}"],
                    )
                )
            raise


async def run_kernel(client: NotebookClient, dir_nb: Path) -> StepInfo:
    """Execute the cells of a notebook and query the kernel before it shuts down.

    Parameters
    ----------
    client
        The client of the notebook, which has not started a kernel yet.
    dir_nb
        The directory in which the kernel runs.

    Returns
    -------
    kernel_info
        The dependencies amended in the kernel, as returned by `query_kernel`.
    """
    # This block starts the kernel and shuts it down.
    # The block inside `async_execute()` finds the running kernel and leaves it alive.
    # When it exits, it also removes the `atexit` and signal handlers of this block
    # (observed with nbclient 0.11), which only leaves the short query without them.
    async with client.async_setup_kernel(cwd=str(dir_nb), env=child_env(dir_nb)):
        await client.async_execute(cleanup_kc=False)
        return await query_kernel(client)


async def query_kernel(client: NotebookClient) -> StepInfo:
    """Make the kernel amend the local modules imported by the notebook and report its amends.

    The request is silent, so it changes neither the execution count nor the history of the kernel,
    and the notebook gets no output from it.

    Parameters
    ----------
    client
        The client of the notebook, whose kernel has executed all cells.

    Returns
    -------
    kernel_info
        The dependencies amended in the kernel, see `parse_kernel_reply`.
    """
    # The request is not a cell, so the cell timeout does not apply.
    # Without a cell, nbclient 0.11 cannot report a timeout and fails on an assertion instead.
    client.timeout = None
    msg_id = client.kc.execute(
        KERNEL_QUERY_CODE,
        silent=True,
        store_history=False,
        user_expressions={"info": KERNEL_QUERY_EXPRESSION},
    )
    reply = await client.async_wait_for_reply(msg_id)
    return parse_kernel_reply(reply["content"])


def parse_kernel_reply(content: dict) -> StepInfo:
    """Extract the dependencies amended in the kernel from the reply to `query_kernel`.

    Parameters
    ----------
    content
        The content of the `execute_reply` message.

    Returns
    -------
    kernel_info
        The dependencies amended in the kernel, without a command.
        Relative paths are relative to its `workdir`, which is the directory of the notebook.

    Raises
    ------
    InputNotFoundError
        When a local module imported by the notebook is not available yet as an input.
    UsageError
        When the IPython configuration of the kernel disables the formatter of JSON results.
    RuntimeError
        When the kernel could not import `stepup.notebook.kernel_hook` or run its `finish()`.
    """
    if content["status"] != "ok":
        raise RuntimeError(
            "The Jupyter kernel failed to import stepup.notebook.kernel_hook: "
            + describe_kernel_error(content)
        )
    result = content["user_expressions"]["info"]
    if result["status"] != "ok":
        if result.get("ename") == "InputNotFoundError":
            raise InputNotFoundError(result.get("evalue"))
        raise RuntimeError(
            "The Jupyter kernel failed to report its amended dependencies: "
            + describe_kernel_error(result)
        )
    data = result["data"].get("application/json")
    if data is None:
        raise UsageError(
            "The Jupyter kernel did not report its amended dependencies as JSON. "
            "Check that the IPython configuration does not disable the formatter "
            "of application/json."
        )
    return json_converter.structure(data, StepInfo)


def describe_kernel_error(content: dict) -> str:
    """Describe the error in the content of a reply from a Jupyter kernel."""
    return f"{content.get('ename', content['status'])}: {content.get('evalue', '')}"


def write_step_info(path_step_info: str, kernel_info: StepInfo | None):
    """Write all inputs and outputs of the current step to a step info file.

    The file lists the dependencies declared when the step was defined,
    those amended by this tool, such as the extracted figures,
    and those amended in the kernel, including the local modules imported by the notebook.
    The step info file itself is not listed.

    Parameters
    ----------
    path_step_info
        The step info file, in the format of `dump_step_info()` of StepUp Core.
    kernel_info
        The dependencies amended in the kernel, or `None` if the notebook was not executed.
    """
    infos = [get_amended_info()]
    if kernel_info is not None:
        infos.append(kernel_info)
    info = get_info().merge(*infos)
    # This tool runs in the working directory of its step,
    # so its arguments are relative to `info.workdir`, like the paths in `info`.
    path_self = Path(path_step_info).normpath()
    info.out = [path for path in info.out if path != path_self]
    dump_step_info(path_step_info, info)


def clear_outputs(notebook: NotebookNode):
    """Remove the outputs and execution counts of all code cells, in place."""
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None


def write_output(notebook: NotebookNode, path_nb: str, to: str, path_out: str):
    """Convert a notebook and write the result to a file.

    Formats that refer to figures instead of embedding them, such as Markdown and LaTeX,
    get the figures and attachments as separate files in a directory next to the output,
    e.g. `demo_md_files/` for `demo.md`.
    These files are declared as outputs of the step with `amend()`.

    Parameters
    ----------
    notebook
        The notebook to convert.
    path_nb
        The notebook file, which sets the document title
        and the directory against which relative paths of images are resolved.
    to
        The output format, i.e. the name of an nbconvert exporter.
    path_out
        The output file, whose parent directory is created if needed.
    """
    exporter = exporters.get_exporter(to)()
    # The modification date of the notebook, which `from_filename` also sets, is left out,
    # because it would make the output depend on the file system.
    nb = Path(path_nb)
    out = Path(path_out)
    # The format is part of the directory name, so that converting one notebook
    # to several formats in the same directory gives no conflicting outputs.
    resources = {
        "metadata": {"name": nb.stem, "path": nb.parent.normpath()},
        "output_files_dir": out.name.replace(".", "_") + "_files",
    }
    # The LaTeX template prints the build date below the title,
    # unless the notebook metadata sets a date, which may be empty.
    if isinstance(exporter, exporters.LatexExporter) and "date" not in notebook.metadata:
        notebook = copy.deepcopy(notebook)
        notebook.metadata.date = ""
    body, resources = exporter.from_notebook_node(notebook, resources=resources)
    dir_out = out.parent.normpath()
    dir_out.makedirs_p()
    # Exporters of binary formats, such as PDF, return bytes instead of a string.
    if isinstance(body, bytes):
        with open(path_out, "wb") as f:
            f.write(body)
    else:
        with open(path_out, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
    # The keys are paths relative to the output directory, which the body refers to.
    paths_extracted = []
    for name, data in sorted(resources.get("outputs", {}).items()):
        path_extracted = dir_out / name
        path_extracted.parent.makedirs_p()
        path_extracted.write_bytes(data)
        paths_extracted.append(path_extracted)
    if len(paths_extracted) > 0:
        amend(out=paths_extracted)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="sn-convert-jupyter",
        description="Convert a Jupyter notebook using the nbconvert Python API.",
    )
    parser.add_argument("path_nb", help="The input Jupyter notebook (.ipynb).")
    parser.add_argument("path_out", help="The output file.")
    parser.add_argument(
        "--to",
        default="html",
        help="The output format (html, pdf, latex, markdown, etc.). Default: html",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute the notebook before conversion.",
    )
    parser.add_argument(
        "--parameters",
        type=str,
        help="Arguments to pass to the notebook as a literal JSON string.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="The timeout in seconds for executing a single cell. "
        "0 disables the timeout. "
        "The default is ${STEPUP_NOTEBOOK_CELL_TIMEOUT} or no timeout if the variable is unset. "
        f"Cells tagged {NO_TIMEOUT_TAG} never time out.",
    )
    parser.add_argument(
        "--step-info",
        help="Write all inputs and outputs of the step to this file, "
        "including those amended by the notebook. "
        "Only possible in a step of StepUp.",
    )
    return parser.parse_args(argv)


def inject_parameters(notebook: NotebookNode, parameters: dict):
    """Insert a code cell that assigns the parameters.

    The new cell is inserted after the first cell tagged `parameters`.
    When no cell has this tag, the new cell is inserted at the top of the notebook
    and a warning is printed on standard error.

    Parameters
    ----------
    notebook
        The notebook, which is modified in place.
    parameters
        The parameters to assign, as loaded with `load_parameters`.

    Raises
    ------
    ValueError
        When a key is not a valid Python identifier or is a keyword.
    """
    param_lines = [
        "# This cell is automatically generated by sn-convert-jupyter to inject parameters."
    ]
    for name, value in parameters.items():
        if not (isinstance(name, str) and name.isidentifier()) or keyword.iskeyword(name):
            raise ValueError(f"A parameter name must be a Python identifier, got {name!r}.")
        # The repr of a value loaded from JSON is a Python literal with the same value.
        param_lines.append(f"{name} = {value!r}")
    cell_id = "sn-convert-jupyter-inject-parameters"
    param_cell = v4.new_code_cell("\n".join(param_lines), id=cell_id)
    for i, cell in enumerate(notebook.cells):
        if "parameters" in cell.get("metadata", {}).get("tags", []):
            notebook.cells.insert(i + 1, param_cell)
            return
    print(
        "WARNING: The notebook has no cell tagged 'parameters'. "
        "The parameters are inserted at the top of the notebook.",
        file=sys.stderr,
    )
    notebook.cells.insert(0, param_cell)


def load_parameters(parameters_str: str) -> dict:
    """Load the parameters of a notebook from a JSON object.

    Parameters
    ----------
    parameters_str
        A JSON object whose keys are the names of the parameters.

    Returns
    -------
    parameters
        The parameters, whose values are JSON values without NaN or infinity.

    Raises
    ------
    ValueError
        When the string is not valid JSON or contains NaN or infinity,
        which have no Python literal.
    TypeError
        When the JSON value is not an object.
    """

    def reject_constant(constant: str):
        raise ValueError(f"A parameter value cannot be {constant}.")

    parameters = json.loads(parameters_str, parse_constant=reject_constant)
    if not isinstance(parameters, dict):
        raise TypeError(f"The parameters must be a JSON object, got {parameters_str}.")
    return parameters


def resolve_timeout(timeout: int | None) -> int | None:
    """Combine the `--timeout` option with the `STEPUP_NOTEBOOK_CELL_TIMEOUT` environment variable.

    Parameters
    ----------
    timeout
        The value of the `--timeout` option, or `None` if it was not given.

    Returns
    -------
    timeout
        The timeout in seconds, or `None` when no timeout applies.

    Raises
    ------
    StepUpError
        When the option is not given and the environment variable is invalid.
    ValueError
        When the option is negative.
    """
    if timeout is None:
        # Not read with getenv from StepUp Core, which would make it a step dependency.
        # A timeout never changes the result of a successful run,
        # so changing it should not cause notebooks to be executed again.
        try:
            return parse_timeout(os.environ.get("STEPUP_NOTEBOOK_CELL_TIMEOUT", ""))
        except ValueError as exc:
            raise StepUpError(f"Invalid value of STEPUP_NOTEBOOK_CELL_TIMEOUT: {exc}") from exc
    if timeout < 0:
        raise ValueError(f"The timeout must be a non-negative integer, got {timeout}")
    return None if timeout == 0 else timeout


def get_cell_timeout(cell: NotebookNode, default_timeout: int | None) -> int | None:
    """Return the timeout of a cell, which is `None` for cells tagged `stepup-no-timeout`."""
    if NO_TIMEOUT_TAG in cell.get("metadata", {}).get("tags", []):
        return None
    return default_timeout


if __name__ == "__main__":
    sys.exit(main())
