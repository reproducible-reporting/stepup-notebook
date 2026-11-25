#!/usr/bin/env python3
from stepup.core.api import static
from stepup.notebook.api import convert_jupyter

static("demo.ipynb", "data.json", "points.txt")
convert_jupyter(
    "demo.ipynb", "demo_out.ipynb", inp="points.txt", out="plot.png", parameters={"dpi": 50}
)
