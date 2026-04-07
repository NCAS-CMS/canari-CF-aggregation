#!/usr/bin/env python

"""
Appends data to an existing seed CFA file.
"""

import click
import argparse
import pathlib
import re
import shutil
import sys

import cf
import netCDF4
import numpy as np
from tqdm import tqdm


def runid_format(ctx, param, value):
    pattern = r"^[a-zA-Z]{2}[0-9]{3}$"
    
    # We still use the same logic, just a different way to report errors
    if not re.match(pattern, value):
        raise click.BadParameter(f"'{value}' is not LLNNN format (e.g., ab123)")
        
    return value
def find_delta_from_size1_bounds(bounds, realm, ncvar):
    """For size 1 coordinates, find the cell size from the bounds."""

    seconds_in_month = 2592000
    lb = bounds[0, 0]
    ub = bounds[0, 1]
    if ub > lb:
        delta = ub - lb
    elif ub < lb:
        raise ValueError(f"{realm} {ncvar}: Upper bound ({ub}) < lower bound ({lb})")
    elif lb == seconds_in_month:
        # Assume monthly instantaneous data measured in seconds
        delta = seconds_in_month
    else:
        raise ValueError(f"{realm} {ncvar}: Upper bound ({ub}) = lower bound ({lb})")

    return delta


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
@click.option("--n_years", "-ny", required=True, type=int, help='Number of years in simulation.')

def main(runid, realm, member, testing, n_years):

    n_months = n_years * 12

    filename = f"CF-1.13_seed_CANARI_{member}_{runid}_{realm}.cfa"


    if testing == 'yes':
        filename = f"testing_{filename}"

    p = pathlib.Path(filename)
    s = "s" if n_years != 1 else ""
    dst = p.with_name(f"{p.stem}_{n_years}year{s}.cfa".replace("seed", "grown"))

    print(f"Creating backup: {dst}")
    shutil.copy2(filename, dst)

    filename = str(dst)

    print(f"Opening file for growth: {filename}")
    cfa = netCDF4.Dataset(filename, "a")
    original = {}

    # NetCDF variable names of time, and time bounds variables
    time_coordinates = []
    time_bounds = []

    for ncvar, x in cfa.variables.items():
        attrs = x.ncattrs()

        # Detect time variables (i.e. containing "since" in units)
        if "units" in attrs and "since" in x.units.lower():
            # Exit if data is, say, decadal means, rather than 'raw' model output
            if "climatology" in attrs:
                sys.exit(1)

            time_coordinates.append(ncvar)

            # Strict 360-day check
            if "calendar" not in attrs or x.calendar != "360_day":
                print(f"FATAL: {ncvar} is not 360_day.")
                sys.exit(1)

            # Bounds variable on time
            if "bounds" in attrs:
                time_bounds.append(x.bounds)

    # Finalise as tuples
    time_coordinates = tuple(time_coordinates)
    time_bounds = tuple(time_bounds)

    bounds_map = {c: b for c, b in zip(time_coordinates, time_bounds)}

    for ncvar, x in cfa.variables.items():
        if (
            ncvar in time_coordinates
            or ncvar in time_bounds
            or ncvar.startswith("fragment_map")
            or ncvar.startswith("fragment_uris")
            or ncvar.startswith("fragment_unique_values")
        ):
            original[ncvar] = x[...]

    for ncvar, x in tqdm(cfa.variables.items()):
        if ncvar not in original:
            continue

        old = original[ncvar]
        new = None

        if ncvar in time_coordinates:
            # Grow the time coordinates
            if old.shape[0] == 1:
                bounds = original[bounds_map[ncvar]]
                delta = find_delta_from_size1_bounds(bounds, realm, ncvar)
            else:
                delta = old[1] - old[0]

            steps = np.arange(n_months * old.shape[0]) * delta
            new = old[0] + steps
        elif ncvar in time_bounds:
            # Grow the time bounds
            if old.shape[0] == 1:
                delta = find_delta_from_size1_bounds(old, realm, ncvar)
            else:
                delta = old[1, 0] - old[0, 0]

            steps = np.arange(n_months * old.shape[0]) * delta
            lower = old[0, 0] + steps
            upper = old[0, 1] + steps

            new = np.stack((lower, upper), axis=-1)
        elif (
            ncvar.startswith("fragment_map")
            and cfa.dimensions[x.dimensions[1]].isunlimited()
        ):
            # Grow the CFA map variable
            new = np.tile(old, n_months)
            new[1:, 1:] = np.ma.masked

        elif (
            ncvar.startswith("fragment_unique_values")
            and cfa.dimensions[x.dimensions[0]].isunlimited()
        ):
            # Grow the CFA unique values
            new = np.tile(old, n_months)

        elif (
            # Grow the CFA location variable
            ncvar.startswith("fragment_uris")
            and cfa.dimensions[x.dimensions[0]].isunlimited()
        ):
            # Grow the CFA file variable
            name0 = old.item(0)
            new = []

            if realm == "ice":
                # Date stamps for ice files
                i = len(name0) - 20
                base = name0[:i]
                y0 = int(name0[i : i + 4])
                m0 = int(name0[i + 4 : i + 6])
                d0 = int(name0[i + 6 : i + 8])
                y1 = int(name0[i + 9 : i + 13])
                m1 = int(name0[i + 13 : i + 15])
                d1 = int(name0[i + 15 : i + 17])
                dt0 = cf.dt(y0, m0, d0, calendar="360_day")
                dt1 = cf.dt(y1, m1, d1, calendar="360_day")

                for n in range(0, n_months * 30, 30):
                    days = cf.D(n)

                    new0 = dt0 + days
                    new0 = (
                        f"{str(new0.year).zfill(2)}{str(new0.month).zfill(2)}"
                        f"{str(new0.day).zfill(2)}"
                    )

                    new1 = dt1 + days
                    new1 = (
                        f"{str(new1.year).zfill(2)}{str(new1.month).zfill(2)}"
                        f"{str(new1.day).zfill(2)}"
                    )

                    new.append(f"{base}{new0}-{new1}.nc")
            else:
                # Date stamps for atmos and ocean files
                i = len(name0) - 16
                base = name0[:i]
                y0 = int(name0[i : i + 4])
                m0 = int(name0[i + 4 : i + 6])
                d0 = 1
                y1 = int(name0[i + 7 : i + 11])
                m1 = int(name0[i + 11 : i + 13])
                d1 = 1
                dt0 = cf.dt(y0, m0, d0, calendar="360_day")
                dt1 = cf.dt(y1, m1, d1, calendar="360_day")

                for n in range(0, n_months * 30, 30):
                    days = cf.D(n)

                    new0 = dt0 + days
                    new0 = f"{str(new0.year).zfill(2)}{str(new0.month).zfill(2)}"

                    new1 = dt1 + days
                    new1 = f"{str(new1.year).zfill(2)}{str(new1.month).zfill(2)}"

                    new.append(f"{base}{new0}-{new1}.nc")

            new = np.array(new).reshape((len(new),) + old.shape[1:])

        # Set the new data
        if new is not None:
            x[...] = new
            cfa.sync()
            del new
        del old


if __name__ == "__main__":
    main()

