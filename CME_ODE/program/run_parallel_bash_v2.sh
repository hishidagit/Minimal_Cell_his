#!/bin/bash
#
# Enhanced Bash script to run parallel MinCell simulations with shared initial conditions
# and controlled CPU usage
#
# Usage: ./run_parallel_bash_v2.sh [options]
# 
# Examples:
#   ./run_parallel_bash_v2.sh                    # Default: 10 sims, 20 min, auto cores
#   ./run_parallel_bash_v2.sh -n 5 -t 60 -j 4   # 5 sims, 60 min, 4 cores
#

# Default configuration
NUM_SIMS=10
INIT_TIME=1      # minutes
SIM_TIME=20      # minutes
RESTART_TIME=1   # minutes
TOTAL_CORES=""   # Auto-detect by default

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -n NUM_SIMS      Number of simulations (default: 10)"
    echo "  -t SIM_TIME      Simulation time in minutes (default: 20)"
    echo "  -i INIT_TIME     Initialization time in minutes (default: 1)"
    echo "  -r RESTART_TIME  Restart interval in minutes (default: 1)"
    echo "  -j CORES         Number of CPU cores to use (default: auto-detect)"
    echo "  -h               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # 10 sims, 20 min, all cores"
    echo "  $0 -n 5 -t 60 -j 4     # 5 sims, 60 min, 4 cores"
    echo "  $0 -n 20 -t 10 -j 8    # 20 sims, 10 min, 8 cores"
}

# Parse command line arguments
while getopts "n:t:i:r:j:h" opt; do
    case $opt in
        n) NUM_SIMS="$OPTARG" ;;
        t) SIM_TIME="$OPTARG" ;;
        i) INIT_TIME="$OPTARG" ;;
        r) RESTART_TIME="$OPTARG" ;;
        j) TOTAL_CORES="$OPTARG" ;;
        h) show_usage; exit 0 ;;
        \?) echo "Invalid option -$OPTARG" >&2; show_usage; exit 1 ;;
    esac
done

# Auto-detect cores if not specified
if [[ -z "$TOTAL_CORES" ]]; then
    TOTAL_CORES=$(nproc)
fi

# Calculate resource allocation
MAX_WORKERS=$(( NUM_SIMS < TOTAL_CORES ? NUM_SIMS : TOTAL_CORES ))
THREADS_PER_PROCESS=$(( TOTAL_CORES / MAX_WORKERS ))
if [[ $THREADS_PER_PROCESS -lt 1 ]]; then
    THREADS_PER_PROCESS=1
fi

echo "Starting $NUM_SIMS parallel minimal cell simulations"
echo "Configuration: Init=${INIT_TIME}min, Simulation=${SIM_TIME}min, Restart=${RESTART_TIME}min"
echo "Resource allocation: ${MAX_WORKERS} processes × ${THREADS_PER_PROCESS} threads = $((MAX_WORKERS * THREADS_PER_PROCESS)) cores"
echo "(Requested: ${TOTAL_CORES} cores, Available: $(nproc) cores)"
echo "============================================================"

# Activate conda environment
export PATH="/mnt2/home/hishida/.pyenv/versions/miniconda3-4.7.12/envs/minimal-cell/bin:$PATH"

# Set threading environment variables for the session
export OMP_NUM_THREADS="$THREADS_PER_PROCESS"
export MKL_NUM_THREADS="$THREADS_PER_PROCESS"
export OPENBLAS_NUM_THREADS="$THREADS_PER_PROCESS"
export NUMEXPR_NUM_THREADS="$THREADS_PER_PROCESS"
export VECLIB_MAXIMUM_THREADS="$THREADS_PER_PROCESS"

# Function to create shared initial condition
create_shared_initial_condition() {
    local log_file="shared_initial_condition.log"
    
    echo "STEP 1: Creating shared initial condition"
    echo "----------------------------------------"
    echo "Creating shared initial condition..." | tee "$log_file"
    
    # Use proc_id = 0 for the master initial condition
    if python3 MinCell_CMEODE.py -procid 0 -t "$INIT_TIME" >> "$log_file" 2>&1; then
        if [[ -f "../simulations/out-0.lm" ]]; then
            echo "✅ Shared initial condition created: ../simulations/out-0.lm" | tee -a "$log_file"
            return 0
        else
            echo "❌ Initial condition file not found: ../simulations/out-0.lm" | tee -a "$log_file"
            return 1
        fi
    else
        echo "❌ Failed to create shared initial condition" | tee -a "$log_file"
        return 1
    fi
}

# Function to run a single simulation using shared initial condition
run_simulation() {
    local proc_id=$1
    local log_file="simulation_${proc_id}.log"
    
    echo "[Process $proc_id] Copying shared initial condition..." | tee -a "$log_file"
    
    # Copy the shared initial condition to this process's file
    local master_file="../simulations/out-0.lm"
    local proc_file="../simulations/out-${proc_id}.lm"
    
    if [[ ! -f "$master_file" ]]; then
        echo "[Process $proc_id] ❌ FAILED - Shared initial condition not found: $master_file" | tee -a "$log_file"
        return 1
    fi
    
    cp "$master_file" "$proc_file"
    if [[ $? -ne 0 ]]; then
        echo "[Process $proc_id] ❌ FAILED - Could not copy initial condition" | tee -a "$log_file"
        return 1
    fi
    
    echo "[Process $proc_id] Initial condition copied. Starting simulation..." | tee -a "$log_file"
    
    # Run main simulation with threading limits
    if python3 MinCell_restart.py -procid "$proc_id" -t "$SIM_TIME" -rs "$RESTART_TIME" >> "$log_file" 2>&1; then
        echo "[Process $proc_id] ✅ SUCCESS" | tee -a "$log_file"
        return 0
    else
        echo "[Process $proc_id] ❌ FAILED in main simulation" | tee -a "$log_file"
        return 1
    fi
}

# Export functions and variables so they're available to subshells
export -f run_simulation
export INIT_TIME SIM_TIME RESTART_TIME
export OMP_NUM_THREADS MKL_NUM_THREADS OPENBLAS_NUM_THREADS NUMEXPR_NUM_THREADS VECLIB_MAXIMUM_THREADS

# Record start time
start_time=$(date +%s)

# Step 1: Create shared initial condition
if ! create_shared_initial_condition; then
    echo "❌ Failed to create shared initial condition. Exiting."
    exit 1
fi

echo ""
echo "STEP 2: Running parallel simulations"
echo "----------------------------------------"

# Step 2: Run simulations in parallel using GNU parallel or xargs
if command -v parallel >/dev/null 2>&1; then
    # Use GNU parallel if available (more efficient)
    echo "Using GNU parallel for job management (max $MAX_WORKERS concurrent jobs)"
    seq 1 $NUM_SIMS | parallel -j $MAX_WORKERS run_simulation {}
    exit_codes=$?
else
    # Fallback: use background processes with bash
    echo "Using bash background processes (GNU parallel not found)"
    echo "Running $MAX_WORKERS concurrent jobs"
    
    pids=()
    running_jobs=0
    
    # Function to wait for a job slot to become available
    wait_for_slot() {
        while [[ $running_jobs -ge $MAX_WORKERS ]]; do
            for i in "${!pids[@]}"; do
                if [[ -n "${pids[i]}" ]]; then
                    if ! kill -0 "${pids[i]}" 2>/dev/null; then
                        # Job finished, remove from tracking
                        unset pids[i]
                        ((running_jobs--))
                    fi
                fi
            done
            sleep 0.1
        done
    }
    
    # Start simulations with controlled parallelism
    for i in $(seq 1 $NUM_SIMS); do
        wait_for_slot
        
        run_simulation $i &
        pid=$!
        pids[i]=$pid
        ((running_jobs++))
        
        echo "Started simulation $i with PID $pid"
    done
    
    # Wait for all remaining processes to complete
    exit_codes=0
    for i in "${!pids[@]}"; do
        if [[ -n "${pids[i]}" ]]; then
            pid=${pids[i]}
            if wait $pid; then
                echo "Process $i (PID $pid) completed successfully"
            else
                echo "Process $i (PID $pid) failed"
                exit_codes=1
            fi
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

# Clean up shared initial condition
if [[ -f "../simulations/out-0.lm" ]]; then
    rm "../simulations/out-0.lm"
    echo ""
    echo "Cleaned up shared initial condition file"
fi

if [[ $successful -eq $NUM_SIMS ]]; then
    echo ""
    echo "🎉 All simulations completed successfully!"
    exit 0
else
    echo ""
    echo "⚠️  Some simulations failed. Check individual log files: simulation_*.log"
    exit 1
fi