#!/usr/bin/env -S bash -x
source ../example.rc

# Run the example
export PYDEVD_DISABLE_FILE_VALIDATION=1
sb -w -j 1 & # > current_stdout.txt &
PID=$!

# Get the graph after completion of the pending steps.
stepup wait
stepup graph current_graph
stepup join

# Wait for background processes, if any.
set +e; wait $PID; RETURNCODE=$?; set -e
[[ "${RETURNCODE}" -eq $((RETURN_CODE_FAILED | RETURN_CODE_DRAINED)) ]] || exit 1

# The output of the failed step is written up to the failing cell.
[[ -f fail.html ]] || exit 1
grep -F "first result" fail.html
grep -F "ZeroDivisionError" fail.html
grep -F "last result" fail.html && exit 1
grep -F "ZeroDivisionError" .stepup/fail.log
