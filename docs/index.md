---
title: Jupyter Notebooks as Build Steps
description: >-
  StepUp Notebook is a StepUp extension that executes Jupyter notebooks as build steps,
  optionally with parameters or with a conversion to HTML.
---

<!--
SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: CC-BY-SA-4.0
-->

<!-- The front matter sets the HTML title of the page, not a second heading. -->
<!-- pyml disable-num-lines 3 single-title -->

# StepUp Notebook: Jupyter Notebooks as Build Steps

<!-- snipwise.md BEGIN abstract -->
StepUp Notebook runs Jupyter notebooks as build steps in
[StepUp Core](https://reproducible-reporting.github.io/stepup-core/),
a universal dynamic build tool.
Notebooks can be executed with parameters and converted to HTML.
A notebook can also declare its own inputs and outputs,
so that StepUp reruns it only when its dependencies have changed.
StepUp Notebook is part of [Reproducible Reporting](https://github.com/reproducible-reporting).
<!-- snipwise.md END abstract -->

!!! warning "StepUp Notebook is in early development, and its API may still change."

    For production use,
    stay with [StepUp RepRep 4.2](https://reproducible-reporting.github.io/stepup-reprep/)
    until StepUp Notebook 4.3 is released.

A minimal `plan.py` executes a notebook and converts it to HTML:

```python
#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("analysis.ipynb")
convert_jupyter("analysis.ipynb")
```

See [Installation](installation.md) to get started,
and [Usage](usage.md) for parameters, inputs and outputs, and timeouts.
