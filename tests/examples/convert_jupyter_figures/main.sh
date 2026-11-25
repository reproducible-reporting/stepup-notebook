#!/usr/bin/env -S bash -x
source ../example.rc

# Run the example
echo 2 > count.txt
export PYDEVD_DISABLE_FILE_VALIDATION=1
sb -w -j 1 & # > current_stdout.txt &
PID=$!

# Get the graph after completion of the pending steps.
stepup wait
stepup graph current_graph

# Each format refers to the figures in a directory of its own.
grep -F '](demo_md_files/output_2_0.png)' demo.md
grep -F '](demo_md_files/output_2_1.png)' demo.md
grep -F '{demo_tex_files/output_2_0.png}' demo.tex
grep -F '{demo_tex_files/output_2_1.png}' demo.tex
# Both executions of the notebook give the same figures.
cmp demo_md_files/output_2_0.png demo_tex_files/output_2_0.png
cmp demo_md_files/output_2_1.png demo_tex_files/output_2_1.png

# A figure that is no longer produced is removed.
echo 1 > count.txt
stepup wait -u count.txt
stepup rebuild
stepup join

# Wait for background processes, if any.
set +e; wait $PID; RETURNCODE=$?; set -e
[[ "${RETURNCODE}" -eq 0 ]] || exit 1

# Check files that are expected to be present and/or missing.
[[ -f demo.md ]] || exit 1
[[ -f demo.tex ]] || exit 1
[[ -f demo_md_files/output_2_0.png ]] || exit 1
[[ -f demo_tex_files/output_2_0.png ]] || exit 1
[[ ! -f demo_md_files/output_2_1.png ]] || exit 1
[[ ! -f demo_tex_files/output_2_1.png ]] || exit 1
