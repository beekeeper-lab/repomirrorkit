#!/usr/bin/env bash
#
# claude-sync.sh — Generate symlinks from kit/ and local/ into Claude Code
# discovery paths (.claude/{agents,commands,skills,hooks}/).
#
# Usage:
#   scripts/claude-sync.sh            # run normally
#   scripts/claude-sync.sh --dry-run  # preview without making changes
#
# Run after: git clone, git pull, git submodule update
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_DIR="${REPO_ROOT}/.claude"
KIT_SHARED="${CLAUDE_DIR}/kit/.claude/shared"
LOCAL_DIR="${CLAUDE_DIR}/local"

DRY_RUN=false
CONFLICTS=0
LINKS_CREATED=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

log()  { echo "[sync] $*"; }
warn() { echo "[sync] WARNING: $*" >&2; }

# --- Ensure submodule is initialized ---
if [ ! -f "${KIT_SHARED}/settings.json" ]; then
  log "Initializing git submodule..."
  if $DRY_RUN; then
    log "(dry-run) Would run: git submodule update --init --recursive"
  else
    git -C "$REPO_ROOT" submodule update --init --recursive
  fi
fi

# --- Helper: create a relative symlink ---
# Usage: make_link <target> <link_path>
make_link() {
  local target="$1"
  local link_path="$2"
  local link_dir
  link_dir="$(dirname "$link_path")"
  local rel_target
  rel_target="$(realpath --relative-to="$link_dir" "$target")"

  if $DRY_RUN; then
    log "(dry-run) ${link_path} -> ${rel_target}"
  else
    ln -sfn "$rel_target" "$link_path"
  fi
  LINKS_CREATED=$((LINKS_CREATED + 1))
}

# --- Clean and recreate generated directories ---
clean_generated() {
  local dir="$1"
  if [ -d "$dir" ] || [ -L "$dir" ]; then
    if $DRY_RUN; then
      log "(dry-run) Would remove: $dir"
    else
      rm -rf "$dir"
    fi
  fi
  if ! $DRY_RUN; then
    mkdir -p "$dir"
  fi
}

# --- Sync file-based assets (agents, commands, hooks) ---
# Symlinks individual files. Local overrides kit on name collision.
sync_files() {
  local asset_type="$1"       # e.g. "agents", "commands", "hooks"
  local dest_dir="${CLAUDE_DIR}/${asset_type}"

  clean_generated "$dest_dir"

  # Kit files first (base layer)
  local kit_dir="${KIT_SHARED}/${asset_type}"
  if [ -d "$kit_dir" ]; then
    for f in "$kit_dir"/*; do
      [ -f "$f" ] || continue
      local name
      name="$(basename "$f")"
      make_link "$f" "${dest_dir}/${name}"
    done
  fi

  # Local files second (override layer)
  local local_asset_dir="${LOCAL_DIR}/${asset_type}"
  if [ -d "$local_asset_dir" ]; then
    for f in "$local_asset_dir"/*; do
      [ -f "$f" ] || continue
      local name
      name="$(basename "$f")"
      if [ -L "${dest_dir}/${name}" ]; then
        local existing_target
        existing_target="$(readlink -f "${dest_dir}/${name}")"
        if [[ "$existing_target" == *"/kit/"* ]]; then
          warn "Local '${name}' overrides kit version in ${asset_type}/"
          CONFLICTS=$((CONFLICTS + 1))
        fi
      fi
      make_link "$f" "${dest_dir}/${name}"
    done
  fi
}

# --- Sync internal/ subdirectory for commands and skills ---
sync_internal_files() {
  local asset_type="$1"  # "commands"
  local dest_dir="${CLAUDE_DIR}/${asset_type}/internal"

  if ! $DRY_RUN; then
    mkdir -p "$dest_dir"
  fi

  # Kit internal files
  local kit_internal="${KIT_SHARED}/${asset_type}/internal"
  if [ -d "$kit_internal" ]; then
    for f in "$kit_internal"/*; do
      [ -f "$f" ] || continue
      local name
      name="$(basename "$f")"
      make_link "$f" "${dest_dir}/${name}"
    done
  fi

  # Local internal files (if any exist)
  local local_internal="${LOCAL_DIR}/${asset_type}/internal"
  if [ -d "$local_internal" ]; then
    for f in "$local_internal"/*; do
      [ -f "$f" ] || continue
      local name
      name="$(basename "$f")"
      if [ -L "${dest_dir}/${name}" ]; then
        warn "Local internal '${name}' overrides kit version in ${asset_type}/internal/"
        CONFLICTS=$((CONFLICTS + 1))
      fi
      make_link "$f" "${dest_dir}/${name}"
    done
  fi
}

# --- Sync skill directories ---
# Skills are directories containing SKILL.md, so we symlink entire dirs.
sync_skills() {
  local dest_dir="${CLAUDE_DIR}/skills"

  clean_generated "$dest_dir"

  # Kit public skills
  local kit_skills="${KIT_SHARED}/skills"
  if [ -d "$kit_skills" ]; then
    for d in "$kit_skills"/*/; do
      [ -d "$d" ] || continue
      local name
      name="$(basename "$d")"
      [ "$name" = "internal" ] && continue
      make_link "$d" "${dest_dir}/${name}"
    done
  fi

  # Local public skills
  local local_skills="${LOCAL_DIR}/skills"
  if [ -d "$local_skills" ]; then
    for d in "$local_skills"/*/; do
      [ -d "$d" ] || continue
      local name
      name="$(basename "$d")"
      [ "$name" = "internal" ] && continue
      if [ -L "${dest_dir}/${name}" ]; then
        local existing_target
        existing_target="$(readlink -f "${dest_dir}/${name}")"
        if [[ "$existing_target" == *"/kit/"* ]]; then
          warn "Local skill '${name}' overrides kit version"
          CONFLICTS=$((CONFLICTS + 1))
        fi
      fi
      make_link "$d" "${dest_dir}/${name}"
    done
  fi

  # Internal skills subdirectory
  local dest_internal="${dest_dir}/internal"
  if ! $DRY_RUN; then
    mkdir -p "$dest_internal"
  fi

  # Kit internal skills
  local kit_internal="${KIT_SHARED}/skills/internal"
  if [ -d "$kit_internal" ]; then
    for d in "$kit_internal"/*/; do
      [ -d "$d" ] || continue
      local name
      name="$(basename "$d")"
      make_link "$d" "${dest_internal}/${name}"
    done
  fi

  # Local internal skills (if any exist)
  local local_internal="${LOCAL_DIR}/skills/internal"
  if [ -d "$local_internal" ]; then
    for d in "$local_internal"/*/; do
      [ -d "$d" ] || continue
      local name
      name="$(basename "$d")"
      if [ -L "${dest_internal}/${name}" ]; then
        warn "Local internal skill '${name}' overrides kit version"
        CONFLICTS=$((CONFLICTS + 1))
      fi
      make_link "$d" "${dest_internal}/${name}"
    done
  fi
}

# --- Sync top-level config files ---
sync_config() {
  # settings.json from kit
  if [ -f "${KIT_SHARED}/settings.json" ]; then
    make_link "${KIT_SHARED}/settings.json" "${CLAUDE_DIR}/settings.json"
  fi

  # mcp.json from local
  if [ -f "${LOCAL_DIR}/mcp.json" ]; then
    make_link "${LOCAL_DIR}/mcp.json" "${CLAUDE_DIR}/mcp.json"
  fi
}

# --- Main ---
log "Syncing Claude Code assets..."
log "  Kit:   ${KIT_SHARED}"
log "  Local: ${LOCAL_DIR}"
log ""

sync_files "agents"
sync_files "commands"
sync_internal_files "commands"
sync_files "hooks"
sync_skills
sync_config

log ""
log "Done. ${LINKS_CREATED} symlinks created, ${CONFLICTS} override(s)."
if [ "$CONFLICTS" -gt 0 ]; then
  warn "Override conflicts are expected when local extends kit. Review warnings above."
fi
