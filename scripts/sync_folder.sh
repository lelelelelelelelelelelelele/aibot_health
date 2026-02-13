#!/usr/bin/env bash
set -euo pipefail

# Bidirectional folder sync helper.
#
# Preferred engine: unison (true bidirectional, conflict tracking).
# Fallback engine: rsync in both directions (NOT a true 2-way sync; last-writer-wins risks).
#
# Examples:
#   # Sync local data1 <-> remote data1 (recommended)
#   bash scripts/sync_folder.sh sync \
#     --left /project/aibot_health/data1 \
#     --right ssh://user@host//project/aibot_health/data1 \
#     --exclude 'data/logs/**' --exclude 'data/temp/**' --exclude '**/__pycache__/**'
#
#   # One-way push
#   bash scripts/sync_folder.sh push --src data1 --dst ssh://user@host//project/aibot_health/data1
#
#   # One-way pull
#   bash scripts/sync_folder.sh pull --src ssh://user@host//project/aibot_health/data1 --dst data1

usage() {
  cat <<'EOF'
Usage:
  sync_folder.sh sync --left <path> --right <path> [--exclude <pattern> ...] [--prefer <left|right>] [--dry-run]
  sync_folder.sh push --src <path> --dst <path> [--exclude <pattern> ...] [--dry-run]
  sync_folder.sh pull --src <path> --dst <path> [--exclude <pattern> ...] [--dry-run]

Path forms:
  - Local: /abs/path or relative path
  - Remote (for unison): ssh://USER@HOST//abs/path
  - Remote (for rsync):  USER@HOST:/abs/path

Notes:
  - For true bidirectional sync, install `unison` on BOTH sides.
  - The rsync fallback for `sync` runs pull then push; it can overwrite changes.
EOF
}

cmd=${1:-}
shift || true

if [[ -z "${cmd}" ]]; then
  usage
  exit 2
fi

excludes=()
prefer=""
dry_run=false
left=""
right=""
src=""
dst=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --exclude)
      excludes+=("$2")
      shift 2
      ;;
    --prefer)
      prefer="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=true
      shift
      ;;
    --left)
      left="$2"
      shift 2
      ;;
    --right)
      right="$2"
      shift 2
      ;;
    --src)
      src="$2"
      shift 2
      ;;
    --dst)
      dst="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

have() { command -v "$1" >/dev/null 2>&1; }

# Build unison args from excludes.
unison_exclude_args=()
for pat in "${excludes[@]}"; do
  # unison uses path patterns (not globstars). We pass as-is and let unison interpret.
  unison_exclude_args+=("-ignore" "Path" "$pat")
done

# rsync uses --exclude pattern (glob-like)
rsync_exclude_args=()
for pat in "${excludes[@]}"; do
  rsync_exclude_args+=("--exclude" "$pat")
done

run() {
  if $dry_run; then
    echo "+ $*"
  else
    "$@"
  fi
}

# Convert unison ssh://user@host//abs/path to rsync user@host:/abs/path
unison_to_rsync() {
  local p="$1"
  if [[ "$p" =~ ^ssh://([^/]+)//(.*)$ ]]; then
    echo "${BASH_REMATCH[1]}:/${BASH_REMATCH[2]}"
  else
    echo "$p"
  fi
}

normalize_local_dir() {
  local p="$1"
  # Ensure trailing slash semantics are consistent for rsync.
  if [[ -d "$p" ]]; then
    echo "$p"
  else
    echo "$p"
  fi
}

unison_sync() {
  local a="$1"
  local b="$2"

  local prefer_args=()
  if [[ -n "$prefer" ]]; then
    if [[ "$prefer" != "left" && "$prefer" != "right" ]]; then
      echo "--prefer must be left or right" >&2
      exit 2
    fi
    if [[ "$prefer" == "left" ]]; then
      prefer_args+=("-prefer" "$a")
    else
      prefer_args+=("-prefer" "$b")
    fi
  fi

  local common=("unison" "-batch" "-confirmbigdel" "true" "-times" "true" "-perms" "0" "-fastcheck" "true")
  common+=("${unison_exclude_args[@]}")
  common+=("${prefer_args[@]}")

  if $dry_run; then
    echo "+ ${common[*]} $a $b"
  else
    "${common[@]}" "$a" "$b"
  fi
}

rsync_one_way() {
  local from="$1"
  local to="$2"

  local base=("rsync" "-av" "--delete" "--info=progress2")
  base+=("${rsync_exclude_args[@]}")

  # For directory contents sync, enforce trailing slash on source.
  if [[ "$from" != *"/" ]]; then
    from="$from/"
  fi

  if $dry_run; then
    echo "+ ${base[*]} "$from" "$to""
  else
    "${base[@]}" "$from" "$to"
  fi
}

rsync_two_way_best_effort() {
  local a="$1"
  local b="$2"

  # WARNING: not a true bidirectional sync.
  # Strategy: pull then push.
  local ra rb
  ra=$(unison_to_rsync "$a")
  rb=$(unison_to_rsync "$b")

  # If both are local, still works.
  rsync_one_way "$rb" "$ra"
  rsync_one_way "$ra" "$rb"
}

case "$cmd" in
  sync)
    if [[ -z "$left" || -z "$right" ]]; then
      echo "sync requires --left and --right" >&2
      usage
      exit 2
    fi

    if have unison; then
      # Best effort: unison must also exist on remote when using ssh://.
      unison_sync "$left" "$right"
    else
      echo "WARN: unison not found; falling back to rsync (not true two-way sync)." >&2
      rsync_two_way_best_effort "$left" "$right"
    fi
    ;;

  push)
    if [[ -z "$src" || -z "$dst" ]]; then
      echo "push requires --src and --dst" >&2
      usage
      exit 2
    fi
    rsync_one_way "$src" "$(unison_to_rsync "$dst")"
    ;;

  pull)
    if [[ -z "$src" || -z "$dst" ]]; then
      echo "pull requires --src and --dst" >&2
      usage
      exit 2
    fi
    rsync_one_way "$(unison_to_rsync "$src")" "$dst"
    ;;

  *)
    echo "Unknown command: $cmd" >&2
    usage
    exit 2
    ;;
esac
