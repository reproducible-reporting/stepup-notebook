<!--
SPDX-FileCopyrightText: 2024 Toon Verstraelen <Toon.Verstraelen@UGent.be>
SPDX-License-Identifier: LGPL-3.0-or-later
-->

# Snipwise Configuration

Consult the full documentation at <https://reproducible-reporting.github.io/snipwise/>.

```toml
# The Markdown files show the abstract as it is written below, links and all.
[[targets]]
patterns = ["README.md", "docs/index.md"]

# The summary of the Python package metadata, which is a single-line TOML string.
[[targets]]
patterns = ["pyproject.toml"]
scanner = "regex"
regex = '(?m)^description = "(?P<content>[^"]*)"$'
snippets = ["tagline"]
render = "{{ content | unwrap }}"

# The meta description that every documentation page carries.
[[targets]]
patterns = ["zensical.toml"]
scanner = "regex"
regex = '(?m)^site_description = "(?P<content>[^"]*)"$'
snippets = ["tagline"]
render = "{{ content | unwrap }}"

# The docstring of the package, which is a single-line string.
[[targets]]
patterns = ["stepup/notebook/__init__.py"]
scanner = "regex"
regex = '(?m)^"""(?P<content>[^"]*)"""$'
snippets = ["tagline"]
render = "{{ content | unwrap | suffix('.') }}"

# The tagline in the social card, whose tspan carries the id that locates it.
[[targets]]
patterns = ["docs/social-card.svg"]
scanner = "regex"
regex = '<tspan\b[^>]*\bid="tagline"[^>]*>(?P<content>[^<]*)</tspan>'
snippets = ["tagline"]
render = "{{ content | unwrap }}"

# The keywords array of the Python package metadata.
[[targets]]
patterns = ["pyproject.toml"]
snippets = ["keywords"]
render = '''{{ content | prefix('"') | suffix('",') }}'''

# The abstract of the citation metadata, which is a folded YAML block scalar.
# The template terminates the last line, because the region includes its newline.
[[targets]]
patterns = ["CITATION.cff"]
scanner = "regex"
regex = '(?m)^abstract: >-\n(?P<content>(?:^  .*\n)+)'
snippets = ["abstract"]
render = "{{ content | plain | prefix('  ') }}\n"

# The keywords sequence of the citation metadata.
[[targets]]
patterns = ["CITATION.cff"]
snippets = ["keywords"]
render = "{{ content | prefix('- ') }}"
```

## `tagline`

```text
StepUp extension for Jupyter notebooks
```

## `abstract`

```markdown
StepUp Notebook runs Jupyter notebooks as build steps in
[StepUp Core](https://reproducible-reporting.github.io/stepup-core/),
a universal dynamic build tool.
Notebooks can be executed with parameters and converted to HTML.
A notebook can also declare its own inputs and outputs,
so that StepUp reruns it only when its dependencies have changed.
StepUp Notebook is part of [Reproducible Reporting](https://github.com/reproducible-reporting).
```

## `keywords`

```text
build automation
build tool
cross-platform
extension
Jupyter notebook
open science
Python
reproducibility
reproducible reporting
reproducible research
research software
StepUp
StepUp Core
workflow automation
```
