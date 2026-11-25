#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("demo.ipynb", "count.txt")
convert_jupyter("demo.ipynb", "demo.md", inp="count.txt")
convert_jupyter("demo.ipynb", "demo.tex", inp="count.txt")
