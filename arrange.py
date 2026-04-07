#!/usr/bin/env python

"""
Adds in JDMA batch numbers.
"""

import os
import pathlib
import shutil
import sys
from datetime import datetime

import click
import netCDF4
import numpy as np
from dateutil.relativedelta import relativedelta
from tqdm import tqdm


@click.command(help=__doc__)
@click.option('--realm', required=True, type=click.Choice(['atmos', 'ocean', 'ice']))
@click.option('--member', '-m', type=int, required=True, help='Ensemble member')
@click.option('--testing', '-t', default='no', type=click.Choice(['yes', 'no']))
@click.option('--n_years', '-ny', required=True, type=int)
@click.option('--scenario', '-s', required=True, type=click.Choice(['hist2', 'ssp370']))

def main(realm, member, testing, n_years, scenario):

    batch_and_external_ids = np.genfromtxt(
        os.path.expanduser(
            f"~/canari/docs/{scenario}/combined2.md"
        ),
        dtype=str,
    )

    runids = np.genfromtxt(
        "/home/users/jonnyhtw/canari/docs/" + scenario + "/runids",
        dtype=None,
        encoding="utf-8",
        names=["member", "runid"],
    )

    if scenario == "hist2" and member >= 13:
        runid_of_seed = "cy537"
        member_of_seed = "13"

    else:
        runid_of_seed = runids["runid"][np.where(runids["member"] == 1)].item()[2:]
        member_of_seed = "1"

    runid = runids["runid"][np.where(runids["member"] == member)].item()[2:]

    print(
        f"Creating CFA file for u-{runid} from the pre-existing "
        f"template file for {runid_of_seed}."
    )

    # dtype='U' tells numpy to treat lines as Unicode strings
    batch_file_array = np.genfromtxt(
        "/home/users/jonnyhtw/canari/docs/"
        + scenario
        + "/"
        + str(member)
        + "-"
        + runid
        + ".md",
        dtype="U",
        delimiter="\n",
    )

    indices = np.where(np.char.find(batch_file_array, "jdma batch") != -1)[0]

    if len(indices) > 0:
        start_idx = indices[0] + 1

        jdma_lines = batch_file_array[start_idx:]

        # Remove the trailing ``` if it exists
        jdma_lines = np.array([line for line in jdma_lines if "```" not in line])

    else:
        print("Search string 'jdma batch' not found.")
        sys.exit(1)

    split_components = [line.split() for line in jdma_lines]

    # Assumes the batch numbers are in the 2nd column (indexing from 0) and the
    # cycle points (u-cv575/19500101) are in the 5th.
    jdma_batches = np.char.replace(np.array(split_components)[:, [1, 4]], "u-", "")

    for jdma_batch in jdma_batches:
        if len(jdma_batch) == 1:
            sys.exit(1)
        else:
            jdma_batch[1] = jdma_batch[1].split("/")[1][0:6]

    batch_ids = jdma_batches[:, 0]

    seasons = jdma_batches[:, 1]
    quarter_map = {
        "01": "01",
        "02": "01",
        "03": "01",
        "04": "04",
        "05": "04",
        "06": "04",
        "07": "07",
        "08": "07",
        "09": "07",
        "10": "10",
        "11": "10",
        "12": "10",
    }

    s = "s" if n_years != 1 else ""
    filename = (
        f"CF-1.13_grown_CANARI_{member_of_seed}_{runid_of_seed}_"
        f"{realm}_{n_years}year{s}.cfa"
    )

    if testing == 'yes':
        filename = f"testing_{filename}"

    p = pathlib.Path(filename)
    new_name = f"{p.stem}_batches.cfa"
    new_name = new_name.replace(f"_{member_of_seed}_", "_" + str(member) + "_")
    new_name = new_name.replace(runid_of_seed, runid)
    dst = p.with_name(new_name)

    _ = shutil.copy2(filename, dst)

    cfa = netCDF4.Dataset(dst, "r+")

    for ncvar, x in tqdm(cfa.variables.items(), total=len(cfa.variables.items())):
        if ncvar.startswith("fragment_unique_values"):
            values = x[:].flatten().tolist()

            start_str = values[0]
            start_date = datetime.strptime(start_str, "%Y%m")

            # Generate consecutive months starting from the start_date
            new_values = [
                (start_date + relativedelta(months=i)).strftime("%Y%m")
                for i in range(x.shape[0])
            ]

            values = new_values

            quarter_arr = np.array(
                [value[:-2] + quarter_map[value[-2:]] for value in new_values]
            )
            id_map = dict(zip(seasons, batch_ids))

            new_data = [str(id_map.get(i, 'MISSING')) for i in quarter_arr]

            for i, val in tqdm(enumerate(new_data), total=len(new_data),disable=True):
                x[i] = val
                row_idx = np.where(batch_and_external_ids == val)[0][0]
                element = batch_and_external_ids[row_idx, 1]

                x[i]+='_'+str(element)

        """
        Now need to rename the files (i.e. fragment_uris) using the correct runid
        """

        if ncvar.startswith("fragment_uris"):
            data = x[:]

            fixed_data = np.char.replace(data.astype(str), runid_of_seed, runid)

            x[:] = fixed_data

    cfa.close()

if __name__ == "__main__":
    main()
