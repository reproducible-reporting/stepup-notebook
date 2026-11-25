#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("fail.ipynb")
convert_jupyter("fail.ipynb")
