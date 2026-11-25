---
description: >-
  How to execute a Jupyter notebook in a StepUp workflow with convert_jupyter(),
  convert it to HTML or save it with outputs, pass parameters,
  declare its inputs and outputs, write them to a step info file,
  and limit the run time of its cells.
---

<!--
SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Usage

All features of StepUp Notebook are available through one function,
[`convert_jupyter()`][stepup.notebook.api.convert_jupyter],
which you call in `plan.py` to add a step that executes a notebook and converts it.
This page covers the common cases.
The [reference page](stepup.notebook.api.md) documents all arguments.

## Executing a Notebook and Converting It to HTML

The following `plan.py` executes `analysis.ipynb` and converts the result to `analysis.html`:

```python
#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("analysis.ipynb")
convert_jupyter("analysis.ipynb")
```

The notebook is a static file in this example,
but it may also be the output of another step.
StepUp executes the notebook again when the notebook itself or one of its inputs has changed,
and skips the step otherwise.

The cells are executed in a new Python kernel, see [Jupyter Kernel](installation.md#jupyter-kernel),
with the directory of the notebook as the current directory.
Relative paths in the notebook are therefore relative to the directory of the notebook,
as in JupyterLab.
The variables `HERE` and `ROOT` are updated for that directory,
as explained in [`HERE` and `ROOT` Variables][core-here-root] in the documentation of StepUp Core.
The step fails when a cell raises an exception,
unless the cell is tagged `raises-exception`.
The output file is then still written, with the outputs up to the failing cell and its traceback,
so you can inspect the error in the context of the preceding results.
The cells after the failing cell have no outputs.
StepUp marks such an output file as outdated, so no other step uses it.

The second argument, `dest`, sets where the result is written:

- `None` (the default) writes `analysis.html` next to the notebook.
- A directory, i.e. a path that ends with a slash, writes `analysis.html` in that directory.
- A file writes the result to that file.
  The extension of the file selects the output format, see [Output Formats](#output-formats).

## Executing a Notebook with Parameters

A notebook can be executed with different parameters,
which is useful for running the same analysis on several datasets,
or for a quick run with fewer samples while you are developing the workflow.
The notebook defines the default values of its parameters in a cell with the tag `parameters`:

```python
n_samples = 1000
dataset = "full.csv"
```

The parameters are passed to the notebook as a dictionary with the `parameters` argument.
To save the executed notebook with the outputs of its cells,
give a destination with the extension `.ipynb`:

```python
#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("analysis.ipynb", "small.csv")
convert_jupyter(
    "analysis.ipynb",
    "analysis-small.ipynb",
    inp="small.csv",
    parameters={"n_samples": 100, "dataset": "small.csv"},
)
```

The parameters are inserted in a new cell right after the cell tagged `parameters`,
so they override its default values.
The keys of the dictionary must be valid Python identifiers and not keywords,
and the values must be JSON-serializable, e.g. numbers, booleans, `None`, strings,
lists and dictionaries.
NaN and infinity are not supported.
A different output file is needed for each set of parameters,
because every step must have its own outputs.
The original notebook is never modified.

When the notebook has no cell tagged `parameters`,
the parameters are inserted at the top of the notebook and the step prints a warning.
If you clean your notebooks with [nb-clean](https://github.com/srstevenson/nb-clean),
preserve the tags in the cell metadata, so that the `parameters` cell keeps its tag:

```bash
nb-clean clean analysis.ipynb --preserve-cell-metadata tags
```

## Inputs and Outputs

StepUp needs to know which files a notebook reads and writes,
in addition to the notebook itself and the converted result.
There are two ways to declare them, which can be combined.

The first is to list them in `plan.py` with the `inp` and `out` arguments:

```python
convert_jupyter("analysis.ipynb", inp="data.csv", out=["plot.png", "table.txt"])
```

The second is to declare them inside the notebook with
[`amend()`][core-amend] of StepUp Core,
before the cell that uses them:

```python
from stepup.core.api import amend

amend(inp="data.csv", out="plot.png")
```

The paths passed to `amend()` are relative to the directory of the notebook,
whereas those passed to `convert_jupyter()` are relative to the directory of `plan.py`.

Declaring inputs in the notebook keeps the information next to the code that uses it,
but it is only known to StepUp once the notebook runs.
When such an input is the output of a step that has not finished yet,
the notebook stops at the `amend()` call,
and StepUp executes it again from the start once the input is available,
as explained in [Dynamic Dependencies][core-dynamic] in the documentation of StepUp Core.
Inputs given in `plan.py` avoid this, because StepUp then schedules the notebook after them.

Outputs given in `plan.py` are needed when other steps should be able to wait for them
before the notebook has been executed,
and in particular when the notebook is an [optional step][core-optional]:

```python
convert_jupyter("analysis.ipynb", out="plot.png", optional=True)
```

An optional step is only executed when another step needs one of its outputs,
which StepUp can only know about if they are declared in `plan.py`.

The local Python modules imported by the notebook, e.g. `helper.py` next to it,
are inputs of the step too, so StepUp executes the notebook again when one of them changes.
They are amended after the last cell, as StepUp Core does after a Python script.
Hence, such a module must be a static file or the output of another step,
like the other inputs of the notebook.
Modules in a virtual environment are not local,
and the environment variable `STEPUP_PATH_FILTER` controls which modules are,
see [StepUp Core Module Environment Variables][core-path-filter]
in the documentation of StepUp Core.

## Step Info File

With the `step_info` argument, the step writes all its inputs and outputs to a JSON file,
which other steps or tools can read, e.g. to archive the inputs of a notebook:

```python
convert_jupyter("sub/analysis.ipynb", step_info="analysis-info.json")
```

The file has the format of [`StepInfo` objects][core-step-info] of StepUp Core,
with paths relative to the directory of `plan.py`.
It contains the inputs and outputs given in `plan.py`, those amended in the notebook,
the local modules imported by the notebook,
and the figures written to separate files for the [Markdown and LaTeX formats](#output-formats).
The step info file is an output of the step, but it does not list itself.
It is only written when the step succeeds.

Dependencies amended by a process that the notebook starts,
e.g. with `!command` or `subprocess.run()`, are not included,
unless the notebook amends them as well.

## Timeouts

By default, the cells of a notebook have no time limit.
You can set a limit in seconds for each cell with the `timeout` argument:

```python
convert_jupyter("analysis.ipynb", timeout=600)
```

When the argument is not given,
the environment variable `STEPUP_NOTEBOOK_CELL_TIMEOUT` sets the limit for all notebooks,
e.g. to make sure that no notebook hangs forever in an automated build:

```bash
export STEPUP_NOTEBOOK_CELL_TIMEOUT=600
```

The value `0`, in the argument or in the variable, disables the limit.
A cell that exceeds the limit makes the step fail.
As with an exception, the output file is still written,
and the outputs of the cell that timed out end with an error.

Some cells are expected to take long, e.g. a cell that trains a model.
Tag such a cell with `stepup-no-timeout` to exempt it from any limit.

A timeout does not change the result of a notebook that succeeds,
so changing `STEPUP_NOTEBOOK_CELL_TIMEOUT` does not cause notebooks to be executed again.
The `timeout` argument is part of the command of the step,
so changing the argument does cause the notebook to be executed again.

`stepup config` lists `STEPUP_NOTEBOOK_CELL_TIMEOUT` when it is set,
together with an error when its value is not a non-negative integer.
See [Unrecognized Environment Variables][core-env-vars] in the documentation of StepUp Core
for how `stepup config` reveals a misspelled variable name.

## Output Formats

The output format is derived from the extension of `dest`.
When `dest` is `None` or a directory, the output is an HTML file.

| Extension | Result |
|---|---|
| `.html` | A web page with the cells and their outputs. |
| `.ipynb` | The notebook with the outputs of its cells. |
| `.py` | The source code of the code cells. |
| `.md` | Markdown |
| `.tex` | LaTeX |
| `.pdf` | PDF, made with XeLaTeX. |

The HTML, notebook and PDF formats are self-contained:
figures in the outputs of the cells are embedded in the file.
The Markdown and LaTeX formats refer to figures in separate files.
These are written to a directory next to the output file,
whose name is the output file name with dots replaced by underscores and `_files` appended,
e.g. `demo_md_files/output_3_0.png` for `demo.md`.
The figures, and the images attached to Markdown cells, are declared as outputs of the step,
so StepUp removes the ones that are no longer produced.
Because these file names are only known after the notebook has run,
a step that uses the converted file cannot declare the figures as inputs in `plan.py`.
It still runs after the figures are written,
but it is not executed again when a figure changes and the converted file does not.

For a figure that must be a file with a name of your choice, e.g. to include it in a paper,
save it explicitly in the notebook and declare it as an output.

The PDF format requires XeLaTeX and the LaTeX packages used by the template of nbconvert,
e.g. `tcolorbox`, `titling` and `mathrsfs` with its `rsfs` fonts.
A TeX distribution such as [TeX Live](https://tug.org/texlive/) contains all of them,
but a minimal installation may lack some.
The PDF and LaTeX formats show no date below the title,
because the date of the build would make every run give a different file.
To show a date, set it in the notebook metadata, e.g. `"date": "1 April 2024"`.

With `execute=False`, the notebook is converted without executing it,
which is useful when the notebook already contains the outputs you want to show.

[core-amend]: https://reproducible-reporting.github.io/stepup-core/reference/stepup.core.api/#stepup.core.api.amend
[core-dynamic]: https://reproducible-reporting.github.io/stepup-core/advanced_topics/dynamic_dependencies/
[core-env-vars]: https://reproducible-reporting.github.io/stepup-core/reference/configuration/#unrecognized-environment-variables
[core-here-root]: https://reproducible-reporting.github.io/stepup-core/advanced_topics/here_and_root/
[core-optional]: https://reproducible-reporting.github.io/stepup-core/advanced_topics/optional_steps/
[core-path-filter]: https://reproducible-reporting.github.io/stepup-core/reference/configuration/#stepup-core-module-environment-variables
[core-step-info]: https://reproducible-reporting.github.io/stepup-core/advanced_topics/step_info/
