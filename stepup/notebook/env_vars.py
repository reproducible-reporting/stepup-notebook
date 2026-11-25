# SPDX-FileCopyrightText: 2026 Toon Verstraelen <Toon.Verstraelen@UGent.be>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""The `STEPUP_NOTEBOOK_*` environment variables of StepUp Notebook.

They are registered with StepUp Core through the `stepup.env_vars` entry point,
so that `stepup config` lists them and checks their values.
"""

from stepup.core.env_vars import EnvVarInfo, EnvVarRegistry
from stepup.core.exceptions import StepUpError

__all__ = ("env_vars", "parse_timeout")


def parse_timeout(value: str) -> int | None:
    """Convert the value of `STEPUP_NOTEBOOK_CELL_TIMEOUT` to a timeout in seconds.

    Parameters
    ----------
    value
        A non-negative integer number of seconds, with optional surrounding whitespace.
        `0` and an empty string mean that cells have no timeout.

    Returns
    -------
    timeout
        The timeout in seconds, or `None` when cells have no timeout.

    Raises
    ------
    StepUpError
        If the value is not a non-negative integer.
    """
    value = value.strip()
    if value == "":
        return None
    try:
        timeout = int(value)
    except ValueError as exc:
        raise StepUpError(f"must be a non-negative integer, got {value!r}") from exc
    if timeout < 0:
        raise StepUpError(f"must be a non-negative integer, got {value!r}")
    return None if timeout == 0 else timeout


def env_vars() -> EnvVarRegistry:
    """Return the environment variables of StepUp Notebook."""
    return EnvVarRegistry(
        "StepUp Notebook",
        {"STEPUP_NOTEBOOK_CELL_TIMEOUT": EnvVarInfo(secret=False, validator=parse_timeout)},
    )
