Conversion of a notebook to Markdown,
with a step info file that lists all inputs and outputs of the step.

In current_step_info.json, sub/data.txt and sub/result.txt are amended by the notebook,
sub/helper.py is a local module imported by the notebook,
and sub/demo_md_files/output_2_0.png is a figure extracted by sn-convert-jupyter.
The other paths are declared in plan.py.
The paths amended in the kernel are relative to sub/, the directory of the notebook,
and are rebased onto the working directory of the step.
