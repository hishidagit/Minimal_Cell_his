"""
Modified in_out module for time-course CSV output.
Based on in_out.py but writes time-course data properly.

Author: David Bianchi (modified for time-course output)
"""

import csv
import numpy as np
import pandas as pd
import os

### CONSTANTS
NA = 6.022e23 # Avogadro's
r_cell = 200e-9 # 200 nm radius, 400 nm diameter
V = ((4/3)*3.14159*(r_cell)**3)*(1000) # for a spherical cell

def outMetCsvsTimecourse(pmap, timepoint, procID):
    """
    Write metabolite concentrations to CSV file with proper time-course format
    
    Parameters:
        pmap (particle map): the CME particle map storing species counts data
        timepoint (int): the timepoint in seconds
        procID (int): the process ID 
    
    Returns:
        None
    """
    
    metFileName = f'../simulations/timecourse-rep-{procID}.csv'
    
    # Collect species data
    specIDs = []
    newCounts = []
    
    if int(timepoint) == -1:
        # Final timepoint
        for met in pmap.particleMap.keys():
            specIDs.append(met)
            newCounts.append(pmap.particleMap[met])
        timepoint = "final"
    else:
        for met in pmap.keys():
            specIDs.append(met)
            newCounts.append(pmap[met])
    
    # Create or append to CSV file
    if timepoint == 0:
        # Create new file with headers
        print(f"Creating new time-course CSV file: {metFileName}")
        with open(metFileName, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            # Write header row
            header = ['Species'] + [f't_{timepoint}']
            writer.writerow(header)
            # Write data
            for i, species_id in enumerate(specIDs):
                writer.writerow([species_id, newCounts[i]])
    else:
        # Append new column to existing file
        print(f"Appending timepoint {timepoint} to CSV file")
        
        # Read existing data
        try:
            existing_df = pd.read_csv(metFileName, index_col=0)
        except FileNotFoundError:
            # File doesn't exist, create new one
            print("File not found, creating new file")
            existing_df = pd.DataFrame(index=specIDs)
            
        # Add new column
        col_name = f't_{timepoint}'
        new_data = pd.Series(newCounts, index=specIDs, name=col_name)
        existing_df[col_name] = new_data
        
        # Write back to file
        existing_df.to_csv(metFileName)
    
    print(f"Saved {len(specIDs)} species at timepoint {timepoint} to {metFileName}")
    return


def calcCellVolume(pmap):
    """
    Calculate cell volume from surface area
    """
    SurfaceArea = pmap['CellSA']
    
    cellRadius = ((SurfaceArea/4/np.pi)**(1/2))*1e-9
    cellVolume = ((4/3)*np.pi*(cellRadius)**3)*(1000)
    
    # Put a ceiling on cellV growth, stop the cell volume growth when the volume has doubled
    if (cellVolume > 6.70e-17):
        cellVolume = 6.70e-17
        pmap['CellV'] = int(670)
    else:
        pmap['CellV'] = int(round(cellVolume*1e19))
    
    return cellVolume


def mMtoPart(conc,pmap):
    """
    Convert ODE concentrations to CME Particle Counts
    """
    cellVolume = calcCellVolume(pmap)
    particle = int(round((conc/1000)*NA*cellVolume))
    return particle


def writeResults(pmap,model,res,time,procid):
    """
    Write results of ODE model simulation timestep back to the CME data structure
    """
    # Get the list of metabolites
    mL = model.getMetList()

    # For loop iterating over the species and updating their counts with ODE results
    for ind in range(len(mL)):
        if (mL[ind].getID() == 'CellSA') or (mL[ind].getID() == 'CellSA_Prot') or (mL[ind].getID() == 'CellSA_Lip'):
            continue
        else:
            pmap[mL[ind].getID()] = mMtoPart(res[ind],pmap)
        
    # Handle ATP and nucleotide counters (keeping original logic)
    ATP_hydro_counters = ['ATP_translat','ATP_trsc','ATP_mRNAdeg','ATP_DNArep','ATP_transloc']
    
    NTP_counters = [['ATP_mRNA','M_atp_c'],['CTP_mRNA','M_ctp_c'],['UTP_mRNA','M_utp_c'],
                    ['GTP_mRNA','M_gtp_c'],['ATP_tRNA','M_atp_c'],['CTP_tRNA','M_ctp_c'],
                    ['UTP_tRNA','M_utp_c'],['GTP_tRNA','M_gtp_c'],['ATP_rRNA','M_atp_c'],
                    ['CTP_rRNA','M_ctp_c'],['UTP_rRNA','M_utp_c'],['GTP_rRNA','M_gtp_c']]
    
    for costID in ATP_hydro_counters:
        if 'translat' in costID:
            costCnt = pmap[costID]
            atpCnt = pmap['M_gtp_c']
            
            if costCnt > atpCnt:
                pmap[costID] = costCnt - atpCnt
                pmap['M_gdp_c'] = pmap['M_gdp_c'] + atpCnt
                pmap['M_pi_c'] = pmap['M_pi_c'] + atpCnt
                pmap['M_gtp_c'] = 0
            else:
                pmap['M_gtp_c'] = pmap['M_gtp_c'] - pmap[costID]
                pmap['M_gdp_c'] = pmap['M_gdp_c'] + pmap[costID]
                pmap['M_pi_c'] = pmap['M_pi_c'] + pmap[costID]
                pmap[costID] = 0
        else:
            costCnt = pmap[costID]
            atpCnt = pmap['M_atp_c']
            
            if costCnt > atpCnt:
                pmap[costID] = costCnt - atpCnt
                pmap['M_adp_c'] = pmap['M_adp_c'] + atpCnt
                pmap['M_pi_c'] = pmap['M_pi_c'] + atpCnt
                pmap['M_atp_c'] = 0
            else:
                pmap['M_atp_c'] = pmap['M_atp_c'] - pmap[costID]
                pmap['M_adp_c'] = pmap['M_adp_c'] + pmap[costID]
                pmap['M_pi_c'] = pmap['M_pi_c'] + pmap[costID]
                pmap[costID] = 0

    for cost in NTP_counters:
        costID = cost[0]
        metID  = cost[1]
        
        cost_count = pmap[costID]
        met_count = pmap[metID]
        
        if cost_count>met_count:
            pmap[costID] = cost_count - met_count
            pmap[metID] = 0
            pmap['M_ppi_c'] = pmap['M_ppi_c'] + met_count
        else:
            pmap[metID] = pmap[metID] - pmap[costID]
            pmap['M_ppi_c'] = pmap['M_ppi_c'] + pmap[costID]
            pmap[costID] = 0

    # Recalculate surface area every step
    from in_out import calcLipidToSA  # Import from original module
    calcLipidToSA(pmap)
    
    print("Recalculated Lipid SA")
    return