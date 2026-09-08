#!/bin/sh
# Audit explicit product inputs, not just whichever tools happen to be installed.
set -eu
audit_python=${1:?Provide the isolated audit environment Python executable}
reports=${2:?Provide the report directory}
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
mkdir -p "$reports"
audit_status=0

"$audit_python" -m pip_audit --strict --local --format json --output "$reports/tools.json" || audit_status=1
"$audit_python" -m pip_audit --strict "$repo_root" --format json --output "$reports/runtime.json" || audit_status=1
"$audit_python" -m pip_audit --strict "$repo_root/tools/guard-lab" --format json --output "$reports/guard-lab.json" || audit_status=1
"$audit_python" -m pip_audit --strict -r "$repo_root/tools/guard-lab/build-constraints.txt" --format json --output "$reports/guard-lab-build.json" || audit_status=1

# Keep collecting reports after a finding or service failure, but fail the job.
exit "$audit_status"
