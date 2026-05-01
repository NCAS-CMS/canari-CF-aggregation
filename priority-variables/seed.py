#!/usr/bin/env python

"""
Create seed CFA file which is then subsequently grown and arranged.
"""

import argparse
import os
import numpy as np
import click
import pathlib
import re
import sys
# Adds the parent directory to the search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import runid_format
import click

import cf



@click.command(help=__doc__)
@click.option(
    "--runid",
    callback=runid_format,
    required=True,
    help="Run ID in format letter-letter-number-number-number",
)
@click.option(
    "--realm",
    required=True,
    type=click.Choice(["atmos", "ocean", "ice"]),
    help="The climate realm",
)
@click.option(
    "--member",
    "-m",
    type=int,
    required=True,
    help="The ensemble member number",
)
@click.option(
    "--testing",
    "-t",
    required=False,
    default="no",
    type=click.Choice(["yes", "no"]),  # This is the "Click way"
    help="Is this a test run? (default: no)",
)
@click.option(
     "--startyear",
    required=True,
    help="Starting year of the simulation.",
)

@click.option(
     "--endyear",
    required=True,
    help="End year of the simulation.",
)
@click.option(
    "--data_path",
    "-d",
    required=True,
    type=pathlib.Path,
    help="Path to the source data directory",
)

def main(runid, realm, member, testing, data_path ,  startyear, endyear):

    years = np.arange(int(startyear), int(endyear)+1)
    
    # Create the list of patterns targeting the subfolders
    search_patterns = [str(data_path / f"{year}/*.nc") for year in years]

    # Debug: Print matches for each year to ensure the paths are correct
    import glob
    print(f"\nScanning directories for years: {years}")
    for pattern in search_patterns:
        matches = glob.glob(pattern)
        print(f" - Pattern: {pattern} | Files found: {len(matches)}")

    # Read the data using the list of patterns
    # Using aggregate=False and cfa_write as per your workflow
    f = cf.read(search_patterns, aggregate=False, cfa_write=["field", "field_ancillary"])

    # Proceed with your analysis using the FieldList 'f'

    if realm == "ice":
        # Add missing time axes to ice variables
        print(f"Adding missing time axes to {realm} variables")

        time = f.select("ncvar%vvel")[0].coord("T")

        for g in f:
            if g.nc_get_variable() in ("Tinz", "Tsnz"):
                print(f"Inserting T coord: {g.nc_get_variable()}")
                axis = cf.DomainAxis(1)
                axis.nc_set_dimension("time")

                axis_key = g.set_construct(axis)
                g.insert_dimension(axis_key, 0, inplace=True)
                g.set_construct(time, axes=axis_key)

        # Get rid of fields which shouldn't be there!
        print(len(f))
        f = cf.FieldList(
            [
                g
                for g in f
                if g.nc_get_variable()
                not in (
                    "VGRDi",
                    "VGRDs",
                )
            ]
        )
        print(len(f))

    if realm == "atmos" and testing == 'yes':
        print(f"Subsetting {realm} fields to create a CFA file for testing")
        f = f.select(
            "ncvar%m01s00i002_2",
            "ncvar%m01s00i003",
            "ncvar%m01s00i024",
            "ncvar%m01s00i024_2",
            "ncvar%m01s03i226_2",
        )

    for i, g in enumerate(f):
        t = g.domain_axis("T", default=None)

        # if t is not None:
        #     fa = cf.FieldAncillary(
        #         data=cf.Data.full(t.get_size(), str(year) + "01")
        #     )

        #     fa.long_name = "This field contains 2 numbers separated by an underscore: [JDMA batch numbers] _ [Externals IDs], e.g. 3203_33076. The latter can be obtained from the command --- jdma batch [former] ---, where former is 3203 in this example."
        #     fa.data._nc_set_aggregation_write_status(True)

        #     g.set_construct(fa, axes="T")

        # else:
        #     pass

    # Set time axes as unlimited to facilitate growing the file to the
    # entire simulation length
    print("Setting time axes as unlimited")
    for i, g in enumerate(f):
        t = g.domain_axis("T", default=None)
        if t is None:
            continue

        t.nc_set_unlimited(True)
        print(i, repr(g))

    # Remove redundant 'name' property which points to the path of the
    # original raw data from the CANARI simulations.
    # [g.del_property("name") for g in f if g.has_property("name")]

    # for field in f:
    #     field.data.replace_directory(
    #         os.path.dirname(list(field.data.get_filenames())[0]),
    #         "",
    #         normalise=False,
    #     )

    filename = f"CF-1.13_seed_CANARI_{member}_{runid}_{realm}_{years[0]}-{years[-1]}.cfa"
    if realm == "atmos" and testing == 'yes':
        filename = f"testing_{filename}"

    print(f"Writing CFA file,", filename)
    cf.write(
        f,
        filename,
        cfa={"constructs": ["field", "field_ancillary"]},
        chunk_cache=4 * 2**20,
    )

if __name__ == "__main__":
    main()
