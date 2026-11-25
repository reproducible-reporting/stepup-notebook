#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("sub/demo.ipynb", "sub/helper.py", "sub/data.txt")
convert_jupyter("sub/demo.ipynb", "sub/demo.md", step_info="current_step_info.json")
