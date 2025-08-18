# plot simulation results
#%%
import numpy as np
import sys
import os
import glob
import lm as lm
from pyLM import *

from pySTDLM import PostProcessing as pp

import pandas as pd

import matplotlib.pyplot as plt
#%%
time = 360
restartTime = 2
times=np.arange(0,time+1,1)
numSims=1
procid = 2
# Sets sims folder to your current working directory ... you can modify this if needed
simsFolder = '../simulations/'
fn=f'out-{procid}.lm'# siingle simulation file
# %%
# Sets sims folder to your current working directory ... you can modify this if needed
simsFolder = '../simulations/'
fn=f'out-{procid}.lm'# siingle simulation file
# %%
# Get traces of all cells
def getTraces(sL,numSims,times):
    fileList=[]
    traceArr = np.zeros((numSims,len(sL),len(times)))
    # os.chdir(simsFolder)
    # for i, my_file in enumerate(glob.glob(simsFolder+"*.csv")):
    i=0
    my_file = simsFolder+f'rep-{procid}.csv'
    print(my_file)
    fileList.append(my_file)
    df = pd.read_csv(str(my_file),header=0)
    for j,time in enumerate(times):
        if (j == 0):
            startVal = 0
            endVal=len(sL)
        else:
            startVal=((len(sL)+1)*j)
            endVal=(len(sL)+1)*(j+1)-1
        if endVal > len(df):
            continue
        print(j)
        traceArr[i,:,j] = df[startVal:endVal]['0.0'][:]
    return traceArr,fileList
# %%
# Get a list of all chemical species (genes, RNA, proteins etc.) tracked in the simulation
fh = pp.openLMFile(simsFolder+fn)
spec_list=pp.getSpecies(fh)
ta,fL = getTraces(spec_list,numSims,times)
# %%
# Set beginning and ending times for plottting
startTime=0
endTime=times[-1]
# %%
zeros = np.zeros((numSims,len(spec_list),len(times)))
# Plot multiple chemical species concentrations on one plot
species_list = ['M_atp_c', 'M_adp_c', 'M_amp_c','M_pep_c','M_pyr_c','CellSA','CELLSA_Lip','CellSA_Prot','M_pyr_e']  # Add more species as needed
times = np.arange(startTime,endTime+1,1)

# Define colors for different species
colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray', 'olive', 'cyan']

plt.figure(figsize=(10, 6))
vInd = spec_list.index('CellV')

for i, species in enumerate(species_list):
    try:
        specInd = spec_list.index(species)
        print(f"{species}: index {specInd}")
        
        # 1e-19 conversion factor since 'Volume' is stored as in 10^-19 L to give values of 335 for IC etc.
        conc = ta[:,specInd,startTime:endTime+1]*1000.0/(ta[:,vInd,startTime:endTime+1]*1e-19*6.022e23)
        
        color = colors[i % len(colors)]  # Cycle through colors if more species than colors
        
        # Plot median line for each species
        plt.plot(times[:], np.median(conc,axis=0), label=f'{species} (median)', color=color, linewidth=2)
        
        # Optionally add confidence intervals (commented out to avoid cluttering)
        # plt.fill_between(times[:], np.percentile(conc,25,axis=0), np.percentile(conc,75,axis=0), 
        #                  alpha=0.2, color=color)
        
    except ValueError:
        print(f"Warning: Species '{species}' not found in simulation results")

plt.ylabel('Concentration (mM)',fontsize=14)
plt.xlabel('Time (min)',fontsize=14)
plt.legend(fontsize=12, loc='best')
plt.title(f'Time Course of Multiple Metabolites ({len(species_list)} species)', fontsize=16)
plt.grid(True, alpha=0.3)
# %%
# Get particle counts
def getParts(ta,specInd,startTime,endTime):
    parts=ta[:,specInd,startTime:endTime+1]
    return parts
# Get average minus standard deviation
def sdMinus(conc):
    arr=np.maximum(np.average(conc,axis=0)-np.std(conc,axis=0),zeros[0,0,:])
    return arr
# %%
# Plot multiple chemical species in number of particles
species_particles_list = ['M_DnaA_c', 'M_PTN_JCVISYN3A_0001_c', 'M_PTN_JCVISYN3A_0002_c','CellV']  # Add more species as needed
times = np.arange(startTime,endTime+1,1)

plt.figure(figsize=(10, 6))

for i, species in enumerate(species_particles_list):
    try:
        specInd = spec_list.index(species)
        parts = getParts(ta,specInd,startTime,endTime)
        
        color = colors[i % len(colors)]  # Reuse color list from above
        
        # Plot average line for each species
        plt.plot(times[:], np.average(parts,axis=0), label=f'{species} (avg)', color=color, linewidth=2)
        
        # Optionally add confidence intervals (commented out to avoid cluttering)
        # plt.fill_between(times[:], np.percentile(parts,25,axis=0), np.percentile(parts,75,axis=0), 
        #                  alpha=0.2, color=color)
        
    except ValueError:
        print(f"Warning: Species '{species}' not found in simulation results")

plt.ylabel('Particles',fontsize=14)
plt.xlabel('Time (min)',fontsize=14)
plt.legend(fontsize=12, loc='best')
plt.title(f'Time Course of Multiple Species ({len(species_particles_list)} species)', fontsize=16)
plt.grid(True, alpha=0.3)
# %%
# Sets the fluxes folder to simulations directory (cwd) + the fluxes directory
fluxesFolder = simsFolder+'/fluxes/'

#simTime = 121 # min
#times=np.arange(0,simTime,1)# Quick check of flux file contents (.csv with: rxnID, flux (mM/s))
myfile='rep-1-fluxDF_final.csv'
df=pd.read_csv(fluxesFolder+str(myfile),header=None)
df.head()
# %%
# Get the reaction IDs from the flux file ... 175 non-redundant metabolic reactions
def getRxnList(path):
    fn = path+'rep-1-fluxDF_final.csv'
    df=pd.read_csv(fn,header=None)
    rxn_list = df[0:175][1][:].tolist()
    return rxn_list

# List of reaction IDs
rL = getRxnList(fluxesFolder)
# %%
# Get particle counts, here we will use this to get an array of fluxes (imagining them as particle count values)
def getParts(ta,specInd,startTime,endTime):
    parts=ta[:,specInd,startTime:endTime+1]
    return parts

# Get reaction flux traces for all simulated cells
def getTraces():
    traceArr = np.zeros((numSims,len(rL),len(times)))
    # for i, my_file in enumerate(glob.glob(fluxesFolder+"*.csv")):
    i = 0
    my_file = fluxesFolder+f'rep-{procid}-fluxDF_final.csv'
    print(my_file)
    df = pd.read_csv(str(my_file),header=None)
    for j,time in enumerate(times):
        if (j == 0):
            #print(j)
            startVal = 0
            endVal=len(rL)
            traceArr[i,:,j] = df[startVal:endVal][2][:].values
        else:
            startVal=(len(rL)*j)
            endVal=len(rL)*(j+1)
            # skip if endVal > len(df)
            if endVal> len(df):
                continue
            print(j)
        #print('start:',startVal,'end:',endVal)
            traceArr[i,:,j] = df[startVal:endVal][2][:].values.astype(float)
    return traceArr
# %%
fluxArr = getTraces()
# %%
rxn_list = ['FBA']
times = np.arange(startTime,endTime+1,1)

rxnInd = rL.index(rxn_list[0])
flux = getParts(fluxArr,rxnInd,startTime,endTime)

plt.fill_between(times[:],np.percentile(flux,1,axis=0),np.percentile(flux,99,axis=0),alpha=0.3,label='1-99%',color='black')
plt.fill_between(times[:],np.average(flux,axis=0)+np.std(flux,axis=0),np.average(flux,axis=0)-np.std(flux,axis=0),alpha=0.5,label='Stdev',color='magenta')
plt.plot(times[:],np.median(flux,axis=0),label='Median',color='red')

plt.ylabel('Flux (mM/s)',fontsize=14)
plt.xlabel('Time (min)',fontsize=14)
plt.legend(fontsize=16,loc='lower left')
plt.title(rxn_list,fontsize=16)
# %%
