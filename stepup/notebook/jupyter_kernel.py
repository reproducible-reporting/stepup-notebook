# SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Configuration of the Jupyter kernels launched by StepUp Notebook."""

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import zmq
from ipykernel.kernelspec import RESOURCES, get_kernel_dict
from jupyter_client import AsyncKernelManager
from jupyter_client.kernelspec import (
    NATIVE_KERNEL_NAME,
    KernelSpec,
    KernelSpecManager,
    NoSuchKernel,
)
from traitlets import default
from traitlets.config import Config

__all__ = ("kernel_config",)


class NativeKernelSpecManager(KernelSpecManager):
    """Provide only the IPython kernel of the Python interpreter running this process.

    The `python3` kernel always runs with `sys.executable`.
    Kernelspecs installed in Jupyter data directories are ignored,
    including one named `python3` that would otherwise take precedence.
    """

    def find_kernel_specs(self) -> dict[str, str]:
        return {NATIVE_KERNEL_NAME: RESOURCES}

    def get_kernel_spec(self, kernel_name: str) -> KernelSpec:
        if kernel_name != NATIVE_KERNEL_NAME:
            raise NoSuchKernel(kernel_name)
        return self.kernel_spec_class(resource_dir=RESOURCES, **get_kernel_dict())


class NativeKernelManager(AsyncKernelManager):
    """Asynchronous kernel manager that launches only kernels of `NativeKernelSpecManager`."""

    @default("kernel_spec_manager")
    def _kernel_spec_manager_default(self) -> KernelSpecManager:
        return NativeKernelSpecManager(data_dir=self.data_dir)


@contextmanager
def kernel_config() -> Iterator[Config]:
    """Configure a Jupyter kernel to communicate through a private temporary directory.

    The kernel runs with the Python interpreter of the current process,
    see `NativeKernelSpecManager`.

    The kernel uses ZeroMQ IPC sockets where ZeroMQ supports them.
    With the default TCP transport, `jupyter_client` selects free ports
    by binding sockets to port zero and releasing them again,
    so two kernels starting at the same time may select the same port
    and one of them fails with "Address already in use".
    IPC sockets are files in a directory used by a single process only,
    which cannot collide.

    Where ZeroMQ has no IPC transport, the kernel keeps the default TCP transport.
    This was observed with the Windows wheels of pyzmq 27.3.0.

    Yields
    ------
    config
        A traitlets configuration to pass as the `config` argument
        of an `nbclient.NotebookClient` subclass.
        The temporary directory is removed when the context manager exits.
    """
    with tempfile.TemporaryDirectory(prefix="sn-jupyter-") as tmpdir:
        config = Config()
        config.NotebookClient.kernel_manager_class = NativeKernelManager
        config.KernelManager.connection_file = str(Path(tmpdir) / "connection.json")
        if zmq.has("ipc"):
            config.KernelManager.transport = "ipc"
            # With the IPC transport, ip is a path prefix:
            # the five channels become {ip}-1 up to {ip}-5.
            # It must be absolute, because the kernel runs in the directory of the notebook,
            # while the kernel manager searches for unused socket names in its own directory.
            config.KernelManager.ip = str(Path(tmpdir) / "socket")
        else:
            config.KernelManager.transport = "tcp"
        yield config
