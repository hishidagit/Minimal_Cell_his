#!/usr/bin/env python
"""
Parallel Simulation Runner for MinCell
Runs multiple JCVI-syn3A minimal cell simulations in parallel with shared initial conditions

Usage: 
  python run_parallel_simulations.py [options]

Examples:
  # Run 10 simulations for 20 minutes using all available cores
  python run_parallel_simulations.py
  
  # Run 5 simulations for 60 minutes using 4 cores
  python run_parallel_simulations.py -n 5 -t 60 -j 4
  
  # Run 20 simulations for 10 minutes with 2-minute checkpoints
  python run_parallel_simulations.py -n 20 -t 10 -r 2

Key Features:
- All simulations use the same initial condition for proper statistical comparison
- Configurable number of CPU cores for parallel execution
- Automatic checkpoint/restart capability
- Detailed progress monitoring and summary reporting
"""

import subprocess
import multiprocessing
import time
import os
import sys
import argparse
import shutil
from concurrent.futures import ProcessPoolExecutor, as_completed

def create_shared_initial_condition(init_time=1, max_threads=1):
    """
    Create a single shared initial condition that all simulations will use
    
    Args:
        init_time (int): Initialization time in minutes
        max_threads (int): Maximum threads per process
    
    Returns:
        tuple: (success, error_msg)
    """
    try:
        print("Creating shared initial condition...")
        
        # Set environment variables to limit threading
        env = os.environ.copy()
        env.update({
            'OMP_NUM_THREADS': str(max_threads),
            'MKL_NUM_THREADS': str(max_threads),
            'OPENBLAS_NUM_THREADS': str(max_threads),
            'NUMEXPR_NUM_THREADS': str(max_threads),
            'VECLIB_MAXIMUM_THREADS': str(max_threads),
        })
        
        # Use proc_id = 0 for the master initial condition
        init_cmd = [
            'python3', 'MinCell_CMEODE.py', 
            '-procid', '0', 
            '-t', str(init_time)
        ]
        
        result = subprocess.run(
            init_cmd, 
            capture_output=True, 
            text=True, 
            timeout=300,  # 5 minute timeout
            env=env
        )
        
        if result.returncode != 0:
            return (False, f"Failed to create initial condition: {result.stderr}")
        
        # Check if the initial condition file was created
        master_file = "../simulations/out-0.lm"
        if not os.path.exists(master_file):
            return (False, f"Initial condition file not found: {master_file}")
        
        print(f"✅ Shared initial condition created: {master_file}")
        return (True, "Success")
        
    except subprocess.TimeoutExpired:
        return (False, "Initial condition creation timed out")
    except Exception as e:
        return (False, f"Unexpected error: {str(e)}")

def run_single_simulation(proc_id, sim_time=20, restart_time=1, max_threads=1):
    """
    Run a single simulation using shared initial condition
    
    Args:
        proc_id (int): Process ID for this simulation
        sim_time (int): Main simulation time in minutes (default: 20)
        restart_time (int): Restart interval in minutes (default: 1)
        max_threads (int): Maximum threads per process
    
    Returns:
        tuple: (proc_id, success, runtime, error_msg)
    """
    start_time = time.time()
    
    try:
        print(f"[Process {proc_id}] Copying shared initial condition...")
        
        # Copy the shared initial condition to this process's file
        master_file = "../simulations/out-0.lm"
        proc_file = f"../simulations/out-{proc_id}.lm"
        
        if not os.path.exists(master_file):
            return (proc_id, False, 0, f"Shared initial condition not found: {master_file}")
        
        shutil.copy2(master_file, proc_file)
        print(f"[Process {proc_id}] Initial condition copied. Starting simulation...")
        
        # Set environment variables to limit threading
        env = os.environ.copy()
        env.update({
            'OMP_NUM_THREADS': str(max_threads),
            'MKL_NUM_THREADS': str(max_threads),
            'OPENBLAS_NUM_THREADS': str(max_threads),
            'NUMEXPR_NUM_THREADS': str(max_threads),
            'VECLIB_MAXIMUM_THREADS': str(max_threads),
        })
        
        # Run main simulation (MinCell_restart.py)
        sim_cmd = [
            'python3', 'MinCell_restart.py',
            '-procid', str(proc_id),
            '-t', str(sim_time),
            '-rs', str(restart_time)
        ]
        
        result_sim = subprocess.run(
            sim_cmd,
            capture_output=True,
            text=True,
            timeout=sim_time * 60 + 300,  # simulation time + 5 minute buffer
            env=env
        )
        
        if result_sim.returncode != 0:
            return (proc_id, False, 0, f"Simulation failed: {result_sim.stderr}")
        
        total_time = time.time() - start_time
        print(f"[Process {proc_id}] Simulation completed successfully in {total_time/60:.2f} minutes")
        
        return (proc_id, True, total_time, "Success")
        
    except subprocess.TimeoutExpired:
        return (proc_id, False, 0, "Simulation timed out")
    except Exception as e:
        return (proc_id, False, 0, f"Unexpected error: {str(e)}")

def main():
    """Main function to coordinate parallel simulations"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Run multiple parallel MinCell simulations with shared initial conditions"
    )
    parser.add_argument('-n', '--num-sims', type=int, default=10,
                       help='Number of simulations to run (default: 10)')
    parser.add_argument('-t', '--sim-time', type=int, default=20,
                       help='Simulation time in minutes (default: 20)')
    parser.add_argument('-i', '--init-time', type=int, default=1,
                       help='Initialization time in minutes (default: 1)')
    parser.add_argument('-r', '--restart-time', type=int, default=1,
                       help='Restart/checkpoint interval in minutes (default: 1)')
    parser.add_argument('-j', '--cores', type=int, default=None,
                       help='Number of CPU cores to use (default: auto-detect)')
    
    args = parser.parse_args()
    
    # Configuration from arguments
    NUM_SIMULATIONS = args.num_sims
    INIT_TIME = args.init_time
    SIM_TIME = args.sim_time
    RESTART_TIME = args.restart_time
    
    # Determine number of workers and threads per process
    if args.cores is not None:
        TOTAL_CORES = args.cores
        MAX_WORKERS = min(NUM_SIMULATIONS, TOTAL_CORES)
    else:
        TOTAL_CORES = multiprocessing.cpu_count()
        MAX_WORKERS = min(NUM_SIMULATIONS, TOTAL_CORES)
    
    # Calculate threads per process to utilize cores efficiently
    THREADS_PER_PROCESS = max(1, TOTAL_CORES // MAX_WORKERS)
    
    print(f"Starting {NUM_SIMULATIONS} parallel minimal cell simulations")
    print(f"Configuration: Init={INIT_TIME}min, Simulation={SIM_TIME}min, Restart={RESTART_TIME}min")
    print(f"Resource allocation: {MAX_WORKERS} processes × {THREADS_PER_PROCESS} threads = {MAX_WORKERS * THREADS_PER_PROCESS} cores")
    print(f"(Requested: {TOTAL_CORES} cores, Available: {multiprocessing.cpu_count()} cores)")
    print("="*60)
    
    # Change to the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Check if required scripts exist
    required_scripts = ['MinCell_CMEODE.py', 'MinCell_restart.py']
    for script in required_scripts:
        if not os.path.exists(script):
            print(f"ERROR: Required script '{script}' not found in {script_dir}")
            sys.exit(1)
    
    start_time = time.time()
    
    # Step 1: Create shared initial condition
    print("STEP 1: Creating shared initial condition")
    print("-" * 40)
    
    success, error_msg = create_shared_initial_condition(INIT_TIME, THREADS_PER_PROCESS)
    if not success:
        print(f"❌ Failed to create shared initial condition: {error_msg}")
        sys.exit(1)
    
    print(f"✅ Shared initial condition created successfully")
    print()
    
    # Step 2: Run parallel simulations using shared initial condition
    print("STEP 2: Running parallel simulations")
    print("-" * 40)
    
    results = []
    successful_sims = 0
    failed_sims = 0
    
    # Run simulations in parallel
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all simulation jobs (no initialization needed - using shared condition)
        future_to_procid = {
            executor.submit(run_single_simulation, proc_id, SIM_TIME, RESTART_TIME, THREADS_PER_PROCESS): proc_id 
            for proc_id in range(1, NUM_SIMULATIONS + 1)
        }
        
        # Collect results as they complete
        for future in as_completed(future_to_procid):
            proc_id, success, runtime, error_msg = future.result()
            results.append((proc_id, success, runtime, error_msg))
            
            if success:
                successful_sims += 1
                print(f"✅ Process {proc_id}: SUCCESS ({runtime/60:.2f} min)")
            else:
                failed_sims += 1
                print(f"❌ Process {proc_id}: FAILED - {error_msg}")
    
    total_time = time.time() - start_time
    
    # Print summary
    print("="*60)
    print("SIMULATION SUMMARY")
    print("="*60)
    print(f"Total simulations: {NUM_SIMULATIONS}")
    print(f"Successful: {successful_sims}")
    print(f"Failed: {failed_sims}")
    print(f"Total wall time: {total_time/60:.2f} minutes")
    print(f"Average time per simulation: {total_time/NUM_SIMULATIONS/60:.2f} minutes")
    
    # List output files
    print("\nOutput files generated:")
    output_files = []
    for proc_id in range(1, NUM_SIMULATIONS + 1):
        lm_file = f"../simulations/out-{proc_id}.lm"
        csv_file = f"../simulations/rep-{proc_id}.csv"
        if os.path.exists(lm_file):
            output_files.append(lm_file)
        if os.path.exists(csv_file):
            output_files.append(csv_file)
    
    for file in sorted(output_files):
        file_size = os.path.getsize(file) / (1024*1024)  # MB
        print(f"  {file} ({file_size:.2f} MB)")
    
    print(f"\nTotal output files: {len(output_files)}")
    
    if failed_sims == 0:
        print("\n🎉 All simulations completed successfully!")
    else:
        print(f"\n⚠️  {failed_sims} simulations failed. Check error messages above.")
    
    return 0 if failed_sims == 0 else 1

if __name__ == "__main__":
    sys.exit(main())