#!/bin/bash
# Sequential simulation runner with results collection

set -e

RESULTS_FILE="/root/rvv-poc/sim-results.json"
LOG_DIR="/root/rvv-poc/sim-logs"
TIMEOUT=1800  # 30 minutes per simulation

mkdir -p "$LOG_DIR"

# Initialize results file
echo '{"experiments": []}' > "$RESULTS_FILE"

run_sim() {
    local idx=$1
    local target=$2
    local elf=$3
    local name=$(basename "$elf" .elf)
    local log_file="$LOG_DIR/${name}.log"

    echo "[$idx/16] Running: $target $name"
    echo "  Log: $log_file"

    start_time=$(date +%s.%N)

    # Run simulation
    python3 /root/rvv-poc/run-sim.sh "$target" "$elf" --timeout=$TIMEOUT 2>&1 > "$log_file" || true

    end_time=$(date +%s.%N)
    wall_time=$(echo "$end_time - $start_time" | bc)

    # Extract cycles from log
    cycles=$(grep -oP 'Cycles:\s*\K[\d,]+' "$log_file" | tr -d ',')
    status=$(grep -oP 'Status:\s*\K\w+' "$log_file")

    echo "  Status: $status, Cycles: $cycles, Time: ${wall_time}s"
    echo ""

    # Save result
    echo "$target,$name,$status,$cycles,$wall_time" >> /root/rvv-poc/sim-results.csv
}

# CSV header
echo "target,name,status,cycles,wall_time" > /root/rvv-poc/sim-results.csv

# Run all 16 simulations sequentially
run_sim 1 saturn /root/rvv-poc/run/out/example_saturn_lmul1.elf
run_sim 2 saturn /root/rvv-poc/run/out/example_saturn_lmul2.elf
run_sim 3 saturn /root/rvv-poc/run/out/example_saturn_lmul4.elf
run_sim 4 saturn /root/rvv-poc/run/out/example_saturn_lmul8.elf
run_sim 5 ara /root/rvv-poc/run/out/example_ara_lmul1.elf
run_sim 6 ara /root/rvv-poc/run/out/example_ara_lmul2.elf
run_sim 7 ara /root/rvv-poc/run/out/example_ara_lmul4.elf
run_sim 8 ara /root/rvv-poc/run/out/example_ara_lmul8.elf
run_sim 9 xiangshan /root/rvv-poc/run/out/example_xiangshan_lmul1.elf
run_sim 10 xiangshan /root/rvv-poc/run/out/example_xiangshan_lmul2.elf
run_sim 11 xiangshan /root/rvv-poc/run/out/example_xiangshan_lmul4.elf
run_sim 12 xiangshan /root/rvv-poc/run/out/example_xiangshan_lmul8.elf
run_sim 13 t1 /root/rvv-poc/run/out/example_t1_lmul1.elf
run_sim 14 t1 /root/rvv-poc/run/out/example_t1_lmul2.elf
run_sim 15 t1 /root/rvv-poc/run/out/example_t1_lmul4.elf
run_sim 16 t1 /root/rvv-poc/run/out/example_t1_lmul8.elf

echo "=========================================="
echo "All simulations complete!"
echo "Results saved to: /root/rvv-poc/sim-results.csv"
cat /root/rvv-poc/sim-results.csv
