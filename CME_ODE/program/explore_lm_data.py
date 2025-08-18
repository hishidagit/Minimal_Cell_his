#!/usr/bin/env python3
"""
Script to explore contents of .lm simulation files
"""

import sys
import os
from pySTDLM import PostProcessing as pp
import pandas as pd

# Path to your simulation file
simsFolder = '../simulations/'
fn = 'out-1.lm'
filepath = simsFolder + fn

print(f"Exploring contents of: {filepath}")
print("=" * 50)

try:
    # Open the LM file
    fh = pp.openLMFile(filepath)
    
    # 1. Get list of all species (chemicals, proteins, genes, etc.)
    spec_list = pp.getSpecies(fh)
    print(f"\nTotal number of species tracked: {len(spec_list)}")
    print("\nFirst 20 species:")
    for i, species in enumerate(spec_list[:20]):
        print(f"  {i:3d}: {species}")
    
    if len(spec_list) > 20:
        print(f"  ... and {len(spec_list)-20} more species")
    
    # 2. Show different categories of species
    print("\n" + "="*50)
    print("SPECIES CATEGORIES:")
    
    # Metabolites (M_...)
    metabolites = [s for s in spec_list if s.startswith('M_')]
    print(f"\nMetabolites (M_*): {len(metabolites)}")
    for met in metabolites[:10]:
        print(f"  {met}")
    if len(metabolites) > 10:
        print(f"  ... and {len(metabolites)-10} more")
    
    # Proteins (M_PTN_...)
    proteins = [s for s in spec_list if s.startswith('M_PTN_')]
    print(f"\nProteins (M_PTN_*): {len(proteins)}")
    for ptn in proteins[:10]:
        print(f"  {ptn}")
    if len(proteins) > 10:
        print(f"  ... and {len(proteins)-10} more")
    
    # RNA (M_RNA_...)
    rnas = [s for s in spec_list if s.startswith('M_RNA_')]
    print(f"\nRNAs (M_RNA_*): {len(rnas)}")
    for rna in rnas[:5]:
        print(f"  {rna}")
    if len(rnas) > 5:
        print(f"  ... and {len(rnas)-5} more")
    
    # Genes (*_gene)
    genes = [s for s in spec_list if s.endswith('_gene')]
    print(f"\nGenes (*_gene): {len(genes)}")
    for gene in genes[:5]:
        print(f"  {gene}")
    if len(genes) > 5:
        print(f"  ... and {len(genes)-5} more")
    
    # Cell properties
    cell_props = [s for s in spec_list if 'Cell' in s]
    print(f"\nCell properties: {len(cell_props)}")
    for prop in cell_props:
        print(f"  {prop}")
    
    # Counter species (for tracking costs)
    counters = [s for s in spec_list if '_cost' in s or 'ATP_' in s or 'UTP_' in s]
    print(f"\nCounter species: {len(counters)}")
    for counter in counters[:10]:
        print(f"  {counter}")
    if len(counters) > 10:
        print(f"  ... and {len(counters)-10} more")
    
    # 3. Get a sample trace for one species to see time course data
    print("\n" + "="*50)
    print("SAMPLE TIME COURSE DATA:")
    
    if 'M_atp_c' in spec_list:
        atp_trace = pp.getSpecieTrace(fh, 'M_atp_c')
        print(f"\nATP particle counts over time (first 10 points):")
        for i, count in enumerate(atp_trace[:10]):
            print(f"  Time point {i}: {count} particles")
        print(f"  Total time points: {len(atp_trace)}")
    
    # 4. Show simulation metadata
    print("\n" + "="*50)
    print("SIMULATION INFO:")
    print(f"File size: {os.path.getsize(filepath)} bytes")
    
    # Save species list to file for reference
    with open('../simulations/species_list.txt', 'w') as f:
        f.write("Species tracked in simulation:\n")
        f.write("="*40 + "\n")
        for i, species in enumerate(spec_list):
            f.write(f"{i:3d}: {species}\n")
    
    print(f"\nComplete species list saved to: ../simulations/species_list.txt")
    
    # Create a summary DataFrame
    summary_data = {
        'Category': ['Total Species', 'Metabolites', 'Proteins', 'RNAs', 'Genes', 'Cell Properties', 'Counters'],
        'Count': [len(spec_list), len(metabolites), len(proteins), len(rnas), len(genes), len(cell_props), len(counters)]
    }
    summary_df = pd.DataFrame(summary_data)
    print(f"\nSUMMARY:")
    print(summary_df.to_string(index=False))
    
except Exception as e:
    print(f"Error reading file: {e}")
    print("\nMake sure:")
    print("1. The file path is correct")
    print("2. You're running from the correct directory")
    print("3. The virtual environment with pyLM is activated")