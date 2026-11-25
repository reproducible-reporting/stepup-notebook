# SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for stepup.notebook.jupyter_kernel

The `main` functions are deliberately not called in process.
The synchronous Jupyter API creates an asyncio event loop that it never closes
(observed with jupyter-core 5.9.1),
and the socket pair of such a loop makes Python emit a `ResourceWarning`
when the garbage collector eventually reclaims the loop.
That happens at an unpredictable moment,
so in process it would turn an arbitrary later test into a failure.
"""

import json
import os
import sys

import pytest
import zmq
from conftest import needs_jupyter, run_tool
from jupyter_client.kernelspec import NoSuchKernel
from nbformat import v4, write

from stepup.core.path import Path
from stepup.notebook.jupyter_kernel import (
    NativeKernelManager,
    NativeKernelSpecManager,
    kernel_config,
)

TRANSPORT_SOURCE = """\
from ipykernel.kernelapp import IPKernelApp

print("transport:", IPKernelApp.instance().transport)
"""
"""Source of a notebook cell that prints the transport of the kernel it runs in."""

TRANSPORT = "ipc" if zmq.has("ipc") else "tcp"
"""The transport that `kernel_config` should select."""


def test_kernel_config():
    with kernel_config() as config:
        assert config.NotebookClient.kernel_manager_class is NativeKernelManager
        assert config.KernelManager.transport == TRANSPORT
        path_dir = os.path.dirname(config.KernelManager.connection_file)
        assert os.path.isabs(path_dir)
        assert os.path.isdir(path_dir)
        if TRANSPORT == "ipc":
            assert os.path.dirname(config.KernelManager.ip) == path_dir
        else:
            assert "ip" not in config.KernelManager
    assert not os.path.exists(path_dir)


def test_native_kernel_spec_manager():
    ksm = NativeKernelSpecManager()
    assert list(ksm.find_kernel_specs()) == ["python3"]
    assert ksm.get_kernel_spec("python3").argv[0] == sys.executable
    with pytest.raises(NoSuchKernel):
        ksm.get_kernel_spec("ir")


def test_native_kernel_manager():
    km = NativeKernelManager(kernel_name="python3")
    assert isinstance(km.kernel_spec_manager, NativeKernelSpecManager)
    assert km.kernel_spec.argv[0] == sys.executable


def write_transport_notebook(path_nb: Path):
    """Write a notebook whose only cell prints the transport of its kernel."""
    notebook = v4.new_notebook(cells=[v4.new_code_cell(TRANSPORT_SOURCE)])
    notebook.metadata.kernelspec = {
        "name": "python3",
        "language": "python",
        "display_name": "Python 3",
    }
    with open(path_nb, "w", encoding="utf-8", newline="\n") as fh:
        write(notebook, fh)


@needs_jupyter
def test_convert_jupyter_transport(path_tmp: Path):
    path_nb = path_tmp / "transport.ipynb"
    write_transport_notebook(path_nb)
    path_out = path_tmp / "transport.md"
    run_tool("sn-convert-jupyter", path_nb, path_out, "--to", "markdown", "--execute")
    assert f"transport: {TRANSPORT}" in path_out.read_text(encoding="utf-8")


PREFIX_SOURCE = """\
import sys

print("prefix:", sys.prefix)
"""
"""Source of a notebook cell that prints the prefix of the Python interpreter running the kernel."""


@needs_jupyter
def test_convert_jupyter_ignores_installed_kernelspec(path_tmp: Path):
    # A `python3` kernelspec on `JUPYTER_PATH` takes precedence over all other kernelspecs.
    # This one cannot start, so the notebook only runs if StepUp Notebook ignores it.
    path_kernel = path_tmp / "jupyter" / "kernels" / "python3"
    path_kernel.makedirs_p()
    kernel_dict = {
        "argv": [
            str(path_tmp / "missing-python"),
            "-m",
            "ipykernel_launcher",
            "-f",
            "{connection_file}",
        ],
        "display_name": "Broken Python",
        "language": "python",
    }
    with open(path_kernel / "kernel.json", "w", encoding="utf-8") as fh:
        json.dump(kernel_dict, fh)
    path_nb = path_tmp / "prefix.ipynb"
    notebook = v4.new_notebook(cells=[v4.new_code_cell(PREFIX_SOURCE)])
    with open(path_nb, "w", encoding="utf-8", newline="\n") as fh:
        write(notebook, fh)
    path_out = path_tmp / "prefix.md"
    env = os.environ | {"JUPYTER_PATH": str(path_tmp / "jupyter")}
    run_tool("sn-convert-jupyter", path_nb, path_out, "--to", "markdown", "--execute", env=env)
    assert f"prefix: {sys.prefix}" in path_out.read_text(encoding="utf-8")
