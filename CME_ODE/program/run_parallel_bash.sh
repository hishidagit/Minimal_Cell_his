#!/bin/bash
#
# Bash script to run 10 parallel MinCell simulations with 20-minute runtime
# Usage: ./run_parallel_bash.sh
#

# Configuration
NUM_SIMS=10
INIT_TIME=1      # minutes
SIM_TIME=20      # minutes
RESTART_TIME=1   # minutes

echo "Starting $NUM_SIMS parallel minimal cell simulations"
echo "Configuration: Init=${INIT_TIME}min, Simulation=${SIM_TIME}min, Restart=${RESTART_TIME}min"
echo "============================================================"

# Activate conda environment
export PATH="/mnt2/home/hishida/.pyenv/versions/miniconda3-4.7.12/envs/minimal-cell/bin:$PATH"

# Function to run a single simulation
run_simulation() {
    local proc_id=$1
    local log_file="simulation_${proc_id}.log"
    
    echo "[Process $proc_id] Starting initialization..." | tee -a "$log_file"
    
    # Phase 1: Initialization
    if python3 MinCell_CMEODE.py -procid "$proc_id" -t "$INIT_TIME" >> "$log_file" 2>&1; then
        echo "[Process $proc_id] Initialization complete. Starting main simulation..." | tee -a "$log_file"
        
        # Phase 2: Main simulation
        if python3 MinCell_restart.py -procid "$proc_id" -t "$SIM_TIME" -rs "$RESTART_TIME" >> "$log_file" 2>&1; then
            echo "[Process $proc_id] ✅ SUCCESS" | tee -a "$log_file"
            return 0
        else
            echo "[Process $proc_id] ❌ FAILED in main simulation" | tee -a "$log_file"
            return 1
        fi
    else
        echo "[Process $proc_id] ❌ FAILED in initialization" | tee -a "$log_file"
        return 1
    fi
}

# Export function so it's available to subshells
export -f run_simulation
export INIT_TIME SIM_TIME RESTART_TIME

# Record start time
start_time=$(date +%s)

# Run simulations in parallel using GNU parallel or xargs
if command -v parallel >/dev/null 2>&1; then
    # Use GNU parallel if available (more efficient)
    echo "Using GNU parallel for job management"
    seq 1 $NUM_SIMS | parallel -j $(nproc) run_simulation {}
    exit_codes=$?
else
    # Fallback: use background processes with bash
    echo "Using bash background processes (GNU parallel not found)"
    pids=()
    
    # Start all simulations in background
    for i in $(seq 1 $NUM_SIMS); do
        run_simulation $i &
        pids+=($!)
        echo "Started simulation $i with PID ${pids[-1]}"
    done
    
    # Wait for all processes to complete
    exit_codes=0
    for i in "${!pids[@]}"; do
        pid=${pids[$i]}
        proc_id=$((i + 1))
        
        if wait $pid; then
            echo "Process $proc_id (PID $pid) completed successfully"
        else
            echo "Process $proc_id (PID $pid) failed"
            exit_codes=1
        fi
    done
fi

# Calculate total time
end_time=$(date +%s)
total_time=$((end_time - start_time))
total_minutes=$((total_time / 60))

echo "============================================================"
echo "SUMMARY"
echo "============================================================"
echo "Total runtime: ${total_minutes} minutes (${total_time} seconds)"

# Count successful outputs
successful=0
for i in $(seq 1 $NUM_SIMS); do
    if [[ -f "../simulations/out-${i}.lm" ]] && [[ -f "../simulations/rep-${i}.csv" ]]; then
        ((successful++))
    fi
done

echo "Successful simulations: $successful / $NUM_SIMS"

# List output files
echo ""
echo "Generated output files:"
for i in $(seq 1 $NUM_SIMS); do
    lm_file="../simulations/out-${i}.lm"
    csv_file="../simulations/rep-${i}.csv"
    
    if [[ -f "$lm_file" ]]; then
        size=$(du -h "$lm_file" | cut -f1)
        echo "  $lm_file ($size)"
    fi
    
    if [[ -f "$csv_file" ]]; then
        size=$(du -h "$csv_file" | cut -f1)
        echo "  $csv_file ($size)"
    fi
done

if [[ $successful -eq $NUM_SIMS ]]; then
    echo ""
    echo "🎉 All simulations completed successfully!"
    exit 0
else
    echo ""
    echo "⚠️  Some simulations failed. Check individual log files: simulation_*.log"
    exit 1
fi