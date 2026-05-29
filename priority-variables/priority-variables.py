#!/usr/bin/env python

"""
Create seed CFA file for CANARI priority variables.
"""

import argparse
import glob
import os
import pathlib
import re
import sys

import cf
import click
import numpy as np
from tqdm import tqdm

# Adds the parent directory to the search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@click.command(help=__doc__)
@click.option(
    "--realm",
    required=True,
    type=click.Choice(["ATM", "OCN", "CICE"]),
    help="The climate realm",
)
@click.option(
    "--verbose",
    type=click.IntRange(-1, 3),
    default=None,
    help="Verbosity level of cf.read",
)
@click.option(
    "--scenario",
    required=True,
    type=click.Choice(["HIST2", "SSP370"]),
    help="The scenario",
)
@click.option(
    "--member",
    "-m",
    type=int,
    required=True,
    help="The ensemble member number",
)
@click.option(
    "--data_path",
    "-d",
    required=True,
    type=pathlib.Path,
    help="Path to the source data directory",
)
def main(realm, member, data_path, scenario, verbose):

    if scenario == "HIST2":
        runids = [
            "cv575",
            "cv625",
            "cw345",
            "cw356",
            "cv827",
            "cv976",
            "cz547",
            "cy436",
            "cw342",
            "cw343",
            "cy375",
            "cy376",
            "cy537",
            "cy811",
            "cy866",
            "cy873",
            "cy877",
            "cy879",
            "cy880",
            "cy881",
            "da179",
            "da190",
            "da191",
            "da192",
            "da193",
            "db291",
            "db301",
            "db303",
            "db304",
            "db305",
            "cz475",
            "cz568",
            "cz647",
            "cz648",
            "cz649",
            "dd436",
            "dd438",
            "dd439",
            "dd441",
            "dd442",
        ]

    elif scenario == "SSP370":
        runids = [
            "de814",
            "de436",
            "de724",
            "de815",
            "df220",
            "de830",
            "de831",
            "de832",
            "de850",
            "de851",
            "de934",
            "de937",
            "de938",
            "de939",
            "de940",
            "df299",
            "df300",
            "df301",
            "df302",
            "df303",
            "df933",
            "df934",
            "df935",
            "df936",
            "df937",
            "dh412",
            "dh413",
            "dh415",
            "dh416",
            "dh417",
            "di511",
            "di512",
            "di513",
            "di514",
            "di515",
            "di703",
            "di704",
            "di705",
            "di706",
            "di707",
        ]

    runid = runids[int(member) - 1]

    print(
        f"scenario is {scenario}\n"
        f"realm is {realm}\n"
        f"member is {member}\n"
        f"runid is {runid}"
    )

    # Identify discovery year
    disc_year = "1950" if scenario == "HIST2" else "2015"

    realm_to_suffix = {"ATM": "a", "OCN": "o", "CICE": "i"}

    suffix = realm_to_suffix[realm]

    discovery_files = glob.glob(str(data_path / disc_year / f"{runid}{suffix}_*.nc"))
    unique_vars = sorted(
        {
            os.path.basename(f)
            .split(f"{runid}{suffix}_{member}_")[1]
            .replace(".nc", "")
            for f in discovery_files
        }
    )


    print(unique_vars)
    print(f"The unique variables are {unique_vars}")

    print(f"Found {len(unique_vars)} variables. Starting loop...")

    for var in (pbar := tqdm(unique_vars, leave=False, ascii=True)):
    # for var in (pbar := tqdm(['mon__grid_T_soqlatisf'], leave=False, ascii=True)):
        pbar.set_description(f"Processing {var}")

        print(f"Now processing {var}")

        var_pattern = str(data_path / "*" / f"{runid}{suffix}_{member}_{var}.nc")
        # var_pattern = str(data_path / "203[89]" / f"{runid}{suffix}_{member}_{var}.nc")

        print(f"The var_pattern is {var_pattern}")

        try:

            f = cf.read(
                var_pattern,
                cfa_write=["field"],
                verbose=verbose,
                aggregate={
                    "relaxed_identities": True,
                },
            )

            for g in f:
                try:
                    t_axis = g.dim("T")
                    if not t_axis.has_property("standard_name"):
                        t_axis.set_property("standard_name", "time")
                except ValueError:
                    # This triggers if "T" doesn't exist; i.e. just skip to the next 'g'
                    continue


            if not os.path.exists("CFA-files"):
                os.makedirs("CFA-files")

            filename = f"CFA-files/CF-1.13_seed_CANARI_{member}_{runid}_{realm}_{var}.cfa"
            cf.write(f, filename, cfa={"constructs": ["field"]}, chunk_cache=256 * 2**20)


        except Exception as e:
            # Handle the error and log the failed pattern
            log_file = "failed_cf_coordinate_patterns.txt"
            if not os.path.exists(log_file) or var_pattern not in open(log_file).read():
                with open(log_file, "a") as f:
                    f.write(var_pattern + "\n")

            print(f"Error occurred with {var_pattern}. Logged to failed_patterns.txt")



if __name__ == "__main__":
    main()
