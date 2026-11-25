<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: LGPL-3.0-or-later
-->

# StepUp Notebook

[![release](https://github.com/reproducible-reporting/stepup-notebook/actions/workflows/release.yaml/badge.svg?branch=main)](https://github.com/reproducible-reporting/stepup-notebook/actions/workflows/release.yaml)
[![pytest](https://github.com/reproducible-reporting/stepup-notebook/actions/workflows/pytest.yaml/badge.svg?branch=main)](https://github.com/reproducible-reporting/stepup-notebook/actions/workflows/pytest.yaml)
[![docs](https://github.com/reproducible-reporting/stepup-notebook/actions/workflows/docs.yaml/badge.svg?branch=main)](https://github.com/reproducible-reporting/stepup-notebook/actions/workflows/docs.yaml)
[![PyPI Version](https://img.shields.io/pypi/v/stepup-notebook)](https://pypi.org/project/stepup-notebook/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/stepup-notebook)
![LGPL-3 License](https://img.shields.io/badge/License-LGPL_v3-blue.svg)
[![CodeFactor](https://www.codefactor.io/repository/github/reproducible-reporting/stepup-notebook/badge)](https://www.codefactor.io/repository/github/reproducible-reporting/stepup-notebook)

<!-- snipwise.md BEGIN abstract -->
StepUp Notebook runs Jupyter notebooks as build steps in
[StepUp Core](https://reproducible-reporting.github.io/stepup-core/),
a universal dynamic build tool.
Notebooks can be executed with parameters and converted to HTML.
A notebook can also declare its own inputs and outputs,
so that StepUp reruns it only when its dependencies have changed.
StepUp Notebook is part of [Reproducible Reporting](https://github.com/reproducible-reporting).
<!-- snipwise.md END abstract -->

> **Note:** StepUp Notebook is in early development, and its API may still change.
> For production use,
> stay with [StepUp RepRep 4.2](https://reproducible-reporting.github.io/stepup-reprep/)
> until StepUp Notebook 4.3 is released.

StepUp Notebook contains the Jupyter features of StepUp RepRep 4.2, under new names:

- `convert_jupyter()` in `stepup.notebook.api` executes a notebook
  and converts it to HTML or another format, optionally with parameters.
  Inputs and outputs can be declared in `plan.py` with `inp=` and `out=`,
  or inside the notebook with `amend()` of StepUp Core.
- `sn-convert-jupyter` is the command that `convert_jupyter()` runs.
- `STEPUP_NOTEBOOK_CELL_TIMEOUT` sets the default timeout of a cell, in seconds.
  Cells tagged `stepup-no-timeout` never time out.

A minimal `plan.py` looks like this:

```python
#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("analysis.ipynb")
convert_jupyter("analysis.ipynb")
```

The source code is hosted on [GitHub](https://github.com/reproducible-reporting/stepup-notebook).

For more information, consult the [documentation](https://reproducible-reporting.github.io/stepup-notebook/).
