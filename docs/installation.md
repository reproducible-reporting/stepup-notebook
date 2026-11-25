---
description: >-
  Install StepUp Notebook from PyPI or conda-forge, with pip, uv, pixi or conda,
  on Linux, macOS or Windows,
  which also installs StepUp Core.
  The Jupyter dependencies are an optional extra.
---

<!--
SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Installation

## Requirements

- Linux, macOS or Windows.
  [Supported Platforms][core-platforms] in the documentation of StepUp Core
  explains what differs between them.
- [Python](https://www.python.org/) ≥ 3.11.
  On Windows, StepUp Core recommends a minimal patch release for security reasons,
  see its [installation instructions][core-installation].
- A package manager, such as [pip](https://pip.pypa.io/), [uv](https://docs.astral.sh/uv/),
  [pixi](https://pixi.prefix.dev/) or [conda](https://docs.conda.io/).

StepUp Notebook is published on both [PyPI](https://pypi.org/)
and [conda-forge](https://conda-forge.org/), under the same package name `stepup-notebook`.
Both also install StepUp Core as a dependency.

We recommend installing into an isolated environment,
such as a [Python virtual environment](https://docs.python.org/3/library/venv.html)
or a pixi workspace,
and activating it with [direnv](https://direnv.net/).

## Installing from PyPI

The dependencies of each notebook ecosystem are optional,
so that you only install the ecosystems you use.
Select them with an extra, e.g. `jupyter` for Jupyter notebooks,
using one of the following commands:

```bash
pip install 'stepup-notebook[jupyter]'     # in an activated virtual environment
uv pip install 'stepup-notebook[jupyter]'  # same, with uv
uv add 'stepup-notebook[jupyter]'          # in a uv project
```

Without an extra, `plan.py` can still declare notebook steps,
but they fail with a message naming the missing extra.

## Installing from conda-forge

Use one of the following commands:

```bash
pixi add stepup-notebook                      # in a pixi workspace
conda install -c conda-forge stepup-notebook  # in an activated conda environment
```

## Jupyter Kernel

The `jupyter` extra installs the packages needed to execute notebooks,
including [ipykernel](https://ipykernel.readthedocs.io/),
so neither JupyterLab nor a separate kernel installation is required.

Notebooks are always executed with the Python kernel (`python3`)
of the environment in which StepUp Notebook is installed,
regardless of the kernel named in the metadata of a notebook.
Kernelspecs installed for Jupyter, including one named `python3`, are ignored.
Install the packages that your notebooks import, such as NumPy or Matplotlib,
in the same environment.
Kernels for other languages, e.g. R or Julia, are not supported.

## Security

StepUp Notebook requires recent versions of the Jupyter packages,
e.g. `nbconvert` 7.17.1 or later,
because older versions have known security issues.
Keep them up to date when you update your environment.

Executing a notebook runs all of its code with your permissions,
so only execute notebooks that you trust, as with any other script.

## Windows

StepUp Notebook communicates with the Jupyter kernel through ZeroMQ.
On Linux and macOS, it uses IPC sockets in a private temporary directory.
On Windows, it uses TCP ports on `127.0.0.1`,
because the Windows wheels of pyzmq have no IPC transport, as observed with pyzmq 27.3.
When many notebooks start at the same time,
a kernel may then fail to start with "Address already in use",
because Jupyter selects free ports before the kernel binds them.

[core-platforms]: https://reproducible-reporting.github.io/stepup-core/platforms/
[core-installation]: https://reproducible-reporting.github.io/stepup-core/installation/
