#!/usr/bin/env python

import time
import cf
import os
import argparse

# --- Configuration ---
SOURCE_DIR = os.getcwd()
TARGET_DIR = os.getcwd()

def get_my_data(sid, ens, exp, realm, filetype, var_list, year):
    """
    Extracts data for multiple variables for a single year from JDMA-retrieved directories.
    """
    # Mapping realm names to file string identifiers
    cptstr = {'ATM': 'a', 'OCN': 'o', 'CICE': 'i'}[realm]

    # JDMA retrieves into 'u-runid/YYYYMMDDT0000Z/'
    in_dir_pattern = os.path.join(SOURCE_DIR, f"u-{sid}", f"{year}*Z")

    # Construct the file pattern (e.g., cz649o_35_mon__diaptr_*.nc)
    file_pattern = os.path.join(in_dir_pattern, f"{sid}{cptstr}_{ens}_{filetype}_*.nc")

    # Loop through each variable passed from the command line
    for var_name in var_list:
        print(f'\nProcessing Year {year} | Variable: {var_name} | Searching: {file_pattern}')

        aggregate_time = time.time()
        try:
            # Select by variable name using the ncvar% identity
            f = cf.read(file_pattern,
                        aggregate={'ncvar_identities': True, 'concatenate': False},
                        select=f'ncvar%{var_name}',
                        dask_chunks=None)

            if not f:
                print(f"❌ No data found for variable '{var_name}' in {year}")
                continue

            print(f"✅ Found {len(f)} field(s)")

            # Output directory structure: scenario/member/realm/yearly/year
            out_dir = os.path.join(TARGET_DIR, exp, str(ens), realm, 'yearly', str(year))
            os.makedirs(out_dir, exist_ok=True)

            # Standardized output name unique to this variable
            out_file_name = os.path.join(out_dir, f"{sid}{cptstr}_{ens}_{filetype}_{var_name}.nc")
            print(f'Writing to: {out_file_name}')

            write_time = time.time()
            cf.write(f, out_file_name, compress=1)
            print(f'Done | Aggregate: {time.time()-aggregate_time:.1f}s | Write: {time.time()-write_time:.1f}s')

        except Exception as e:
            print(f"💥 Failed to process variable {var_name} for year {year}: {e}")

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Extract single-year variables from JDMA-retrieved data.')

    parser.add_argument('--year', type=int, required=True, help='Year to process (e.g. 1975)')
    parser.add_argument('--runid', required=True, help='Run ID without the u- prefix (e.g. cz649)')
    parser.add_argument('--member', type=int, required=True, help='Ensemble member number')
    parser.add_argument('--scenario', required=True, help='Scenario (e.g. HIST2)')
    parser.add_argument('--realm', required=True, choices=['ATM', 'OCN', 'CICE'], help='Realm')
    parser.add_argument('--filetype', required=True, help='Type (e.g. mon__diaptr)')
    
    # CHANGED: Added nargs='+' to accept one or more space-separated variables
    parser.add_argument('--var', required=True, nargs='+', help='Var names space-separated (e.g. var1 var2)')

    args = parser.parse_args()

    get_my_data(
        sid=args.runid,
        ens=args.member,
        exp=args.scenario,
        realm=args.realm,
        filetype=args.filetype,
        var_list=args.var,  # Pass the parsed list of variables
        year=args.year
    )
