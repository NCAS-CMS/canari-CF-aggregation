#!/usr/bin/env python

"""
Create seed CFA file which is then subsequently grown and arranged.
"""

import argparse
import os
import click
import pathlib
import re
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
    "--data_path",
    "-d",
    required=True,
    type=pathlib.Path,
    help="Path to the source data directory",
)

def main(runid, realm, member, testing, startyear, data_path):


    target_suffix = startyear + "01"
    pattern = f"{runid}{realm[0]}_{member}_*{target_suffix}*.nc"

    # Combine into your glob path
    files = str(data_path / pattern)

    print(f"\nReading {realm} files: {files}")

    # 2. Use the .glob() method to find the actual files
    # This returns a list of Path objects
    actual_files = list(data_path.glob(pattern))

    # 3. Print the actual filenames (not the glob string)

    if actual_files:
        print(f"\nReading {realm} files:")
        for f in actual_files:
            print(f" - {f.name}")
    else:
        print(f"\nNo files found for {realm} matching: {pattern}")

    f = cf.read(files, aggregate=False, cfa_write=["field", "field_ancillary"])

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

        if t is not None:
            fa = cf.FieldAncillary(
                data=cf.Data.full(t.get_size(), str(startyear) + "01")
            )

            fa.long_name = "JDMA_batch_numbers"
            fa.data._nc_set_aggregation_write_status(True)

            g.set_construct(fa, axes="T")

        else:
            pass

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
    [g.del_property("name") for g in f if g.has_property("name")]

    for field in f:
        field.data.replace_directory(
            os.path.dirname(list(field.data.get_filenames())[0]),
            "",
            normalise=False,
        )

    filename = f"CF-1.13_seed_CANARI_{member}_{runid}_{realm}.cfa"
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
