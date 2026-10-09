#!/usr/bin/env bash
# Runs the automated evals (evals/prompts.md sections 1-4: triggering, negative,
# AGENTS.md activation, rule adherence)
# with `claude plugin eval`.
#
# Why a build step: the repo root is a marketplace whose plugins share "./" as source
# and have no plugin.json - `claude plugin eval` does not load such a root as a plugin.
# This script assembles a temporary plugin (all skills = both plugins enabled, as
# recommended for DLC projects) plus the generated cases and evaluates that.
#
# Usage:  evals/run.sh [extra claude plugin eval options]
#   evals/run.sh --runs 1                      # quick iteration
#   evals/run.sh --case 't1*' --runs 1         # subset
#   evals/run.sh --tag negative
#   evals/run.sh --threshold 0.8 --max-cost-usd 20 --json results.json   # CI
# Results: evals/results/<timestamp>/ (report.html, aggregate-result.json)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/evals/.build/dlc-skills"

python3 "$ROOT/evals/generate.py"

rm -rf "$BUILD"
mkdir -p "$BUILD/.claude-plugin" "$BUILD/evals"
cat > "$BUILD/.claude-plugin/plugin.json" <<'EOF'
{
  "name": "dlc-skills",
  "description": "Eval build: all DLC-Skills (ddd-tactical-java + domainlifecycles plugins)"
}
EOF
cp -R "$ROOT/skills" "$BUILD/skills"
cp -R "$ROOT/evals/cases" "$BUILD/evals/cases"

claude plugin eval "$BUILD" \
  --ablation none \
  --scaffold \
  --trust-plugin \
  --no-publish \
  --output-dir "$ROOT/evals/results/$(date -u +%Y-%m-%dT%H-%M-%SZ)" \
  "$@"
