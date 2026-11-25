---
description: >-
  Release notes for every version of StepUp Notebook,
  following Keep a Changelog and effort-based versioning.
---

<!--
SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Effort-based Versioning](https://jacobtomlinson.dev/effver/).
(Changes to features documented as "experimental" will not increment macro and meso version numbers.)

## [Unreleased][]

This is the first release of StepUp Notebook.
It contains the Jupyter features of StepUp RepRep 4.2, under new names.
StepUp RepRep 4.2 remains the version for production use until StepUp Notebook 4.3 is released.

### Added

- `convert_jupyter()` in `stepup.notebook.api`,
  which was `convert_jupyter()` in `stepup.reprep.api`.
- The command `sn-convert-jupyter`, which was `srr-convert-jupyter`.
- The environment variable `STEPUP_NOTEBOOK_CELL_TIMEOUT`, which was `REPREP_JUPYTER_TIMEOUT`.
  StepUp Notebook ignores the old name.
- `STEPUP_NOTEBOOK_CELL_TIMEOUT` is registered with StepUp Core,
  so that `stepup config` lists it in a group of StepUp Notebook,
  instead of as an unrecognized variable without effect,
  and reports a value that is not a non-negative integer on the line of the variable.
  This requires StepUp Core 4.3.
- `convert_jupyter()` has a `step_info` argument,
  which writes all inputs and outputs of the step to a JSON file,
  including those amended by the notebook and the local modules it imports.

### Changed

- The Jupyter dependencies are optional and installed with the `jupyter` extra,
  e.g. `pip install 'stepup-notebook[jupyter]'`.
  Without them, `sn-convert-jupyter` fails with a message naming the extra.
- An executed notebook saved by `convert_jupyter()` no longer records
  the execution times of its cells in their metadata,
  so that executing the same notebook twice gives the same file.
- `convert_jupyter()` with `parameters` no longer fails
  on a notebook without a cell tagged `parameters`.
  The parameters are then inserted at the top of the notebook,
  and a warning is printed.
- `convert_jupyter()` rejects `parameters` whose keys are Python keywords, such as `class`,
  or whose values contain NaN or infinity, when `plan.py` is executed.
- `convert_jupyter()` also writes its output when a cell raises an exception or times out,
  with the outputs up to that cell and the error, and without the outputs of later cells.
  The step still fails, and StepUp marks the output as outdated.
- The local Python modules imported by an executed notebook are inputs of its step,
  so that the notebook is executed again when one of them changes.
  Such a module must now be a static file or the output of another step,
  as for a Python script in StepUp Core.

### Fixed

- `convert_jupyter()` with output format `pdf` no longer fails
  after LaTeX has made the PDF.
- `convert_jupyter()` with output format `markdown` or `latex`
  writes the figures and cell attachments to which the output refers,
  e.g. to `demo_md_files/` next to `demo.md`, and declares them as outputs of the step.
  Before, the output referred to figure files that were never written.
- `convert_jupyter()` executes notebooks with the Python interpreter that runs the step,
  even when an installed Jupyter kernelspec named `python3` points to another interpreter.
- `convert_jupyter()` with `parameters` accepts the values `True`, `False` and `None`,
  also nested in lists and dictionaries.
  Before, the notebook failed with a `NameError` on `true`, `false` or `null`.
  The injected cell now assigns each parameter on its own line, e.g. `dpi = 50`.
- `convert_jupyter()` with output format `pdf` or `latex` no longer prints the build date
  below the title, so that converting the same notebook twice gives the same file.
  A date in the notebook metadata is still shown.

### Removed

- `execute_papermill()` and `srr-execute-papermill` of StepUp RepRep are not carried over.
  Use `convert_jupyter()` with a destination ending in `.ipynb` and the `parameters` argument.
  Unlike `execute_papermill()`, it executes a notebook in the directory of the notebook,
  as in interactive use, so relative paths in a notebook in a subdirectory may need updating.
  StepUp Notebook no longer depends on papermill.
- `convert_jupyter()` no longer supports the output formats `rst` and `asciidoc`,
  i.e. destinations ending in `.rst` or `.txt`.
- `convert_jupyter()` has no `to` argument.
  The extension of `dest` selects the output format,
  e.g. `convert_jupyter("demo.ipynb", "demo.md")` instead of `to="markdown"`.

[Unreleased]: https://github.com/reproducible-reporting/stepup-notebook
