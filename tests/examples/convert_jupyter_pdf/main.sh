#!/usr/bin/env -S bash -x
source ../example.rc

# Run the example
export PYDEVD_DISABLE_FILE_VALIDATION=1
sb -w -j 1 & # > current_stdout.txt &
PID=$!

# Get the graph after completion of the pending steps.
stepup wait
stepup graph current_graph

# Reproducibility test
mv demo.pdf demo1.pdf
stepup wait -d demo.pdf
stepup rebuild
stepup join
cmp demo.pdf demo1.pdf

# Wait for background processes, if any.
set +e; wait $PID; RETURNCODE=$?; set -e
[[ "${RETURNCODE}" -eq 0 ]] || exit 1

# Check files that are expected to be present and/or missing.
[[ -f demo.pdf ]] || exit 1
[[ "$(head -c 5 demo.pdf)" == "%PDF-" ]] || exit 1
[[ -f demo1.pdf ]] || exit 1
