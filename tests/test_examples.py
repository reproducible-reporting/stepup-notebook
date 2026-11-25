# SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Run examples."""

import os
import shutil

import pytest

from stepup.core.path import Path
from stepup.core.pytest import EXAMPLE_TIMEOUT, run_example

pytestmark = pytest.mark.timeout(2 * EXAMPLE_TIMEOUT)
"""Budget for a whole example, which `run_example` already bounds with `EXAMPLE_TIMEOUT`.

Setup, call and teardown share this budget,
and it must stay above the deadline of the example itself,
so that a stalled example is reported with its own output instead of a bare timeout.
"""

OVERWRITE_EXPECTED = "STEPUP_OVERWRITE_EXPECTED" in os.environ


@pytest.mark.skipif(not shutil.which("jupyter"), reason="No Jupyter")
@pytest.mark.parametrize(
    "name",
    [
        "convert_jupyter",
        "convert_jupyter_parameters",
        "convert_jupyter_subdir",
        "convert_jupyter_figures",
        "convert_jupyter_step_info",
        "convert_jupyter_error",
        "convert_jupyter_timeout",
        pytest.param("convert_jupyter_concurrency", marks=pytest.mark.heavy),
    ],
)
@pytest.mark.asyncio
async def test_jupyter_example(path_tmp: Path, name: str):
    await run_example(Path("tests/examples") / name, path_tmp, OVERWRITE_EXPECTED)


@pytest.mark.skipif(not shutil.which("jupyter"), reason="No Jupyter")
@pytest.mark.skipif(not shutil.which("xelatex"), reason="No XeLaTeX")
@pytest.mark.asyncio
async def test_jupyter_pdf_example(path_tmp: Path):
    await run_example(Path("tests/examples/convert_jupyter_pdf"), path_tmp, OVERWRITE_EXPECTED)
