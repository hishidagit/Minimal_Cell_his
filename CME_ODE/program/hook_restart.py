"""
The hook simulation driver for a Hybrid CME-ODE JCVI Syn3A simulation.

Author: David Bianchi
"""

import Simp as Simp
import Rxns as Rxns
import integrate as integrate
import copy as copy
import in_out as in_out
import sys
import pandas as pd
import numpy as np
import time as timer
import lm as lm

### Define our own hybrid CME-ODE solver class derived from the LM Gillespie Direct Solver:
class MyOwnSolver(lm.GillespieDSolver):


    def __init__(self, delt, ode_step, speciesCount,cythonBool,resTime,procID,iteration=None):

        """
        Initialize the ODE hook solver

        Parameters:
        self, the object pointer
        delt (float), communication timestep between hook simulation and main LM simulation
        ode_step (float), the maximum stepsize given an Adaptive Timestepping ODE solver
        speciesCount (species Count), instance of SpeciesCount Class used to pass species count data
        cythonBool (bool), Should ODE Reaction Solver be compiled with Cython (True, False)
        resTime (float), the total simulation time of each CME Hook Simulation = Restart Time (in minutes)
        procID (str), The Process ID for each simulated "cell".
        iteration (int), The current minute/iteration number for global tracking

        Returns:
        None
        """

        # Call the constructor for the derived class
        # Not necessary to use MESolverFactory.setSolver('lm::cme::GillespieDSolver)?
        lm.GillespieDSolver.__init__(self)

        # Save the initial conditions, for restarting the solver upon a new replicate
        self.ic = (delt,ode_step,speciesCount,cythonBool,resTime)

        # The time a which hook solver has been stepped into, initial value = 0
        self.oldtime = 0.0

        # The process ID for creating flux log files etc.
        self.procID = str(procID)
        
        # Track the global minute number across restart iterations
        self.global_minute = iteration if iteration is not None else 1

        print("initializing solver")

        # Set the initial conditions
        self.restart()
        
    def restart(self):

        """
        Get the same initial conditions for a new simulation replicate (Restart the Hook)

        Parameters:
        self, the object pointer

        Returns:
        None
        """
        
        # Set the previous time to be 0, we are starting the simulation
        self.oldtime = 0.0

        # Deep Copy of all of the initial conditions
        self.delt = copy.deepcopy(self.ic[0])
        self.odestep = copy.deepcopy(self.ic[1])
        self.species = copy.deepcopy(self.ic[2])
        self.cythonBool = copy.deepcopy(self.ic[3])
        self.resTime = copy.deepcopy(self.ic[4])

        # Update need enzyme Counts in the particle map
        self.species.update(self)

        print("Done with restart")

        
        
    def hookSimulation(self, time):

        """
        The hookSimulation method defined here will be called at every frame write
        time.  The return value is either 0 or 1, which will indicate if we
        changed the state or not and need the lattice to be copied back to the GPU
        (In the case of the RDME) before continuing.  If you do not return 1, 
        your changes will not be reflected.

        Parameters:
        self, the object pointer
        time, the current simulation time

        Returns:

        1 (int), if changes should be passed to the main LM Simulation
        0 (int), if changes should not be passed to the main lm Simulation
        """

        # We have reached the simulation start time, if doing multiple replicates
        # No need to update
        if (time==0.0):
            print("New Replicate", flush=True)
            self.restart()
            minute = 0
            return 0

        # We are at a CME-ODE communication timestep
        else:

            # At the first timestep update the needed protein counts
            if ((time > self.delt) and (time < (self.delt*2.0))):
                self.species.update(self)
                #Simp.upIC(self.species)
                #Simp.upIC(self.species)

            # Update to current solver species counts
            # start = timer.time()
            # print("Updating species: ", start)
            # self.species.update(self)
            # end = timer.time()
            # print("Finished update: ",end)
            print("Time is: ",time)

            # Initialize and define the reaction model
            model = Simp.initModel(self.species)


            ### Want to get the current values, not necessarily the initial values
            initVals=integrate.getInitVals(model)

            ### Boolean control of cython compilation, versus scipy ODE solvers
            cythonBool = self.cythonBool

            if (cythonBool == True):
                solver=integrate.setSolver(model)
            
            else:
                solver=integrate.noCythonSetSolver(model)

            ### Run the integrator: But instead of passing self.delt pass self.oldtime
            res = integrate.runODE(initVals,time,self.oldtime,self.odestep,solver,model)

            resFinal = res[-1,:]
            
            resStart = res[0,:]
            
            # Progress reporting every 10 seconds within each minute
            if (int(time) % 10) == 0 and time > 0:
                print(f'Progress: minute {self.global_minute}, time {int(time)}/60 seconds')
            
            # Save flux data at the end of each 1-minute interval
            # For restart simulations, this happens when time approaches 60 seconds
            if time >= (self.resTime - self.delt):
                print(f"Saving flux data for minute {self.global_minute} at time {time}")
                
                # Calculate fluxes at the start and end of this interval
                currentFluxes_start = solver.calcFlux(0, resStart)
                currentFluxes_end = solver.calcFlux(0, resFinal)

                # Save start-of-interval fluxes
                fluxList_start = []
                for indx, rxn in enumerate(model.getRxnList()):
                    fluxList_start.append((rxn.getID(), currentFluxes_start[indx]))

                fluxDF_start = pd.DataFrame(fluxList_start)
                fluxFileName_start = '../simulations/fluxes/' + 'rep-' + self.procID + '-fluxDF-start.csv'
                fluxDF_start.to_csv(fluxFileName_start, header=False, mode='a')

                # Save end-of-interval fluxes (main flux file)
                fluxList_end = []
                for indx, rxn in enumerate(model.getRxnList()):
                    fluxList_end.append((rxn.getID(), currentFluxes_end[indx]))

                fluxDF_end = pd.DataFrame(fluxList_end)
                
                # Save to the main final flux file with global minute tracking
                fluxFileName_final = '../simulations/fluxes/' + 'rep-' + self.procID + '-fluxDF_final.csv'
                fluxDF_end.to_csv(fluxFileName_final, header=False, mode='a')
                
                # Also save to a per-minute flux file for compatibility
                fluxFileName_minute = '../simulations/fluxes/' + 'rep-' + self.procID + '-fluxDF.csv'
                fluxDF_end.to_csv(fluxFileName_minute, header=False, mode='a')

                print(f'Saved fluxes for minute {self.global_minute}.')


            # Get the previous time in minutes
            minute = int(int(time)/60)
            # Set the previous time to the current time
            self.oldtime = time


            # Write the results
            in_out.writeResults(self.species,model,resFinal,time,self.procID)


            # Update the system with changes
            return 1

        return 0

            
