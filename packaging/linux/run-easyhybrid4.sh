#!/usr/bin/env bash
set -euo pipefail

bundle_root="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
app_root="$bundle_root/app"
runtime="$bundle_root/runtime"
python="$runtime/bin/python"

if [[ ! -x "$python" || ! -f "$app_root/easyhybrid.py" ]]; then
  echo "EasyHybrid4 bundle is incomplete: expected app/easyhybrid.py and runtime/bin/python beside this launcher." >&2
  exit 2
fi

if [[ -z "${PDYNAMO3_HOME:-}" || ! -d "$PDYNAMO3_HOME/pCore" ]]; then
  echo "Set PDYNAMO3_HOME to a compiled pDynamo3 checkout containing pCore/." >&2
  exit 2
fi

export PDYNAMO3_PARAMETERS="${PDYNAMO3_PARAMETERS:-$PDYNAMO3_HOME/parameters}"
export PDYNAMO3_SCRATCH="${PDYNAMO3_SCRATCH:-${XDG_CACHE_HOME:-$HOME/.cache}/easyhybrid4/scratch}"
export PDYNAMO3_STYLE="${PDYNAMO3_STYLE:-$PDYNAMO3_PARAMETERS/ccsStyleSheets/defaultStyle.css}"
mkdir -p "$PDYNAMO3_SCRATCH"

# Conda-pack relocations are applied once after extraction to the final prefix.
if [[ -x "$runtime/bin/conda-unpack" && ! -e "$runtime/.easyhybrid4-unpacked" ]]; then
  "$runtime/bin/conda-unpack"
  touch "$runtime/.easyhybrid4-unpacked"
fi

export PYTHONNOUSERSITE=1
export PYTHONPATH="$app_root:$app_root/src/graphics_engine/src:$PDYNAMO3_HOME${PYTHONPATH:+:$PYTHONPATH}"
exec "$python" "$app_root/easyhybrid.py" "$@"
