# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Code that `sn-convert-jupyter` runs in the Jupyter kernel after the last cell of a notebook.

This module is only imported in the kernel, which runs in a separate process.
"""

from IPython.display import JSON

from stepup.core.api import amend, get_amended_info
from stepup.core.cattrs import json_converter
from stepup.core.extapi import get_local_import_paths

__all__ = ("finish",)


def finish() -> JSON:
    """Amend the local modules imported by the notebook and report all amended dependencies.

    Returns
    -------
    result
        An object that IPython formats as `application/json`,
        holding the unstructured result of `get_amended_info()` in the kernel.
        Relative paths in it are relative to its `workdir`,
        which is the current directory of the kernel.

    Raises
    ------
    InputNotFoundError
        When a local module is not available yet as an input of the step,
        see `amend()` of StepUp Core.
    """
    amend(inp=get_local_import_paths())
    return JSON(json_converter.unstructure(get_amended_info()))
