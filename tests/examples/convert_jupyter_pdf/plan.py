#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("demo.ipynb")
convert_jupyter("demo.ipynb", "demo.pdf")
