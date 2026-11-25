#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("sub/demo.ipynb", "sub/data.json")
convert_jupyter("sub/demo.ipynb")
