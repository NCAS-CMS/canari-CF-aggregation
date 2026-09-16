#!/bin/bash
# ===============================================================================
# CMIP7 REPACK SLURM WORKER SCRIPT
# ===============================================================================
# USAGE (Paste into terminal from PWD):
#
# DRY_RUN=true; SCENARIO="HIST2"; MEMBER="1"; REALM="ATM"; YEAR="1950"; TARGET_DIR="/gws/ssde/j25b/canari/shared/large-ensemble/priority/${SCENARIO}/${MEMBER}/${REALM}/yearly/${YEAR}"; FILES=("$TARGET_DIR"/*.nc); if [ "$DRY_RUN" = true ]; then echo "[DRY RUN] Would process ${#FILES[@]} files in $TARGET_DIR using Conda env: $CONDA_DEFAULT_ENV"; printf "  - %s\n" "${FILES[@]}"; else [ ${#FILES[@]} -gt 0 ] && [ -e "${FILES[0]}" ] && sbatch --export=ALL --array=0-$(( ${#FILES[@]} - 1 ))%20 submitrepack.sh "$SCENARIO" "$MEMBER" "$REALM" "$YEAR" && echo "Submitted ${#FILES[@]} jobs to Slurm under Conda env: $CONDA_DEFAULT_ENV"; fi
#
# Set DRY_RUN=false to execute live jobs.
# ===============================================================================

#SBATCH --job-name=cmip7repack
#SBATCH --output=%x_%j_%a.out
#SBATCH --error=%x_%j_%a.err
#SBATCH --export=ALL
#SBATCH --account=canari
#SBATCH --partition=debug
#SBATCH --qos=debug

SCENARIO="$1"
MEMBER="$2"
REALM="$3"
YEAR="$4"

BASE_DIR="/gws/ssde/j25b/canari/shared/large-ensemble/priority"
TARGET_DIR="${BASE_DIR}/${SCENARIO}/${MEMBER}/${REALM}/yearly/${YEAR}"

FILES=( "$TARGET_DIR"/*.nc )

TARGET_FILE="${FILES[$SLURM_ARRAY_TASK_ID]}"

if [ -z "$TARGET_FILE" ] || [ ! -f "$TARGET_FILE" ]; then
    echo "Error: No valid file for array index $SLURM_ARRAY_TASK_ID"
    exit 1
fi

echo "Processing Task ID : $SLURM_ARRAY_TASK_ID"
echo "Target File        : $TARGET_FILE"
echo "Active Conda Env   : $CONDA_DEFAULT_ENV"

cmip7repack -o "$TARGET_FILE"
