#!/usr/bin/env bash
# Run ASQ-snap25 under Linux (tmux/systemd friendly).
# Usage from repo root:
#   chmod +x asq_snap25/run_linux.sh
#   # testnet:
#   ./asq_snap25/run_linux.sh
#   # mainnet USDT-M:
#   BINANCE_TESTNET=0 ./asq_snap25/run_linux.sh
#   # mainnet USDC-M (0-maker promo), if instrument enabled in live:
#   BINANCE_TESTNET=0 ASQ_INSTRUMENTS=ETHUSDC-PERP.BINANCE ./asq_snap25/run_linux.sh

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

export ASQ_INSTRUMENTS="${ASQ_INSTRUMENTS:-ETHUSDT-PERP.BINANCE}"
export BINANCE_TESTNET="${BINANCE_TESTNET:-1}"
export PYTHONUNBUFFERED=1

# Prefer conda env if present (match local xqm0702); else current python.
if [[ -n "${CONDA_PREFIX:-}" ]]; then
  PY="${CONDA_PREFIX}/bin/python"
elif command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  conda activate "${ASQ_CONDA_ENV:-xqm0702}"
  PY="$(command -v python)"
else
  PY="$(command -v python3 || command -v python)"
fi

stamp="$(date +%Y%m%d-%H%M%S)"
env_tag="testnet"
[[ "$BINANCE_TESTNET" == "0" ]] && env_tag="mainnet"
mkdir -p "$ROOT/logs"
log="$ROOT/logs/asq-snap25-${env_tag}-${stamp}.log"

echo "cwd:   $ROOT"
echo "py:    $PY"
echo "instr: $ASQ_INSTRUMENTS"
echo "testnet=$BINANCE_TESTNET"
echo "log:   $log"
echo "hot:   $ROOT/asq_snap25/live_hot.json"
echo ""

# Merge stderr so Binance -2011 etc. do not kill the pipe under set -e shells.
exec "$PY" -m asq_snap25 >>"$log" 2>&1
