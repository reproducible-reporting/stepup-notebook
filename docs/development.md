---
description: >-
  Set up a StepUp Notebook development environment with uv, direnv and pre-commit,
  and find out how to run the tests, build the documentation and make a release.
---

<!--
SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: CC-BY-SA-4.0
-->

# Developer Guide

If you would like to contribute, please read [CONTRIBUTING.md](https://github.com/reproducible-reporting/.github/blob/main/CONTRIBUTING.md).

## Development Environment

If you break your development environment, you can discard it
by running `git clean -dfX` in the project root and repeating the instructions below.

We use [uv](https://docs.astral.sh/uv/) to manage the development environment.
Install it by following the [uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

A local installation for testing and development can be set up
using the following commands:

```bash
git clone git@github.com:reproducible-reporting/stepup-notebook.git
cd stepup-notebook
uv sync --extra dev
pre-commit install
```

Put the following lines in `.envrc`:

```bash
source .venv/bin/activate
export XDG_CACHE_HOME="${VIRTUAL_ENV}/cache"
export STEPUP_DEBUG="1"
export STEPUP_BUILD_DURATION="0"
export STEPUP_SYNC_RPC_TIMEOUT="30"
```

Finally, run the following commands:

```bash
direnv allow
```

Alternatively, you can prefix commands with `uv run` (e.g. `uv run pytest`)
instead of activating the virtual environment.

Note that `uv.lock` is not committed to the repo.
For development and CI, the latest versions of dependencies are used instead of some locked versions.

## Tests

We use pytest, so you can run the tests as follows:

```bash
pytest -vv
```

### Tests on Windows

The test suite also runs on Windows,
e.g. in the Windows test VM of StepUp Core,
which `tools/winvm/winvm.sh` in the
[StepUp Core repository](https://github.com/reproducible-reporting/stepup-core/blob/main/tools/winvm/README.md)
manages.
With a checkout of StepUp Core next to this repository and an existing VM,
run the tests as follows:

```bash
W=../stepup-core/tools/winvm/winvm.sh
$W start
$W sync
$W test
$W stop
```

## Documentation

The documentation is created using [Zensical](https://zensical.org/),
configured in `zensical.toml`.
Only the current version is published:
every commit on the main branch republishes the site with GitHub Pages.

Edit the documentation Markdown files with a live preview by running:

```bash
zensical serve
```

(Keep this running.)
Then open the live preview in your browser at
[http://localhost:8000/stepup-notebook/](http://localhost:8000/stepup-notebook/)
and edit Markdown files in your IDE.

Pages that walk through an example include its sources and outputs
with the block form of the [Snippets](https://facelessuser.github.io/pymdown-extensions/extensions/snippets/)
extension, using paths relative to `docs/`:

<!-- The leading semicolons escape the snippet markers and do not appear on the page. -->

````markdown
```python
;--8<--
usage/example/plan.py
;--8<--
```
````

Do not use the single-line form `--8<-- "path"` in a Python code block,
because Ruff formats the code blocks in Markdown files and rewrites that line
as if it were a Python expression.
The block form is not valid Python, so Ruff leaves it alone.

Please use [Semantic Line Breaks](https://sembr.org/)
because it results in cleaner file diffs when editing documentation.

## How to Make a Release

- Mark the release in `changelog.md`.
- Make a new commit and tag it with `vX.Y.Z`.
- Trigger the PyPI GitHub Action: `git push origin main --tags`.
