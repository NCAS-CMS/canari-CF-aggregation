import os
import sys
import cf
import netCDF4 as nc
import click
import concurrent.futures
import glob
import numpy as np
from tqdm import tqdm
from datetime import datetime
from contextlib import contextmanager, redirect_stderr

@contextmanager
def silence_stderr():
    """Context manager to suppress low-level HDF5 diagnostic noise."""
    with open(os.devnull, 'w') as fnull:
        with redirect_stderr(fnull):
            try:
                stderr_fd = sys.stderr.fileno()
                with os.fdopen(os.dup(stderr_fd), 'w') as old_stderr:
                    sys.stderr.flush()
                    os.dup2(fnull.fileno(), stderr_fd)
                    try:
                        yield
                    finally:
                        sys.stderr.flush()
                        os.dup2(old_stderr.fileno(), stderr_fd)
            except Exception:
                yield

def check_file_health(file_path):
    """Performs granular multi-stage integrity and metadata checks."""
    
    # TEST 1: File Existence & Non-zero Size
    try:
        if os.path.getsize(file_path) == 0:
            return (file_path, False, "FAILED: Test 1 (Empty File - 0 bytes)")
    except Exception as e:
        return (file_path, False, f"FAILED: Test 1 (File Access Error: {str(e)})")

    # TEST 2: HDF5 Decompression / Data Chunk Sweep
    try:
        with silence_stderr():
            with nc.Dataset(file_path, mode="r") as rootgrp:
                rootgrp.set_auto_mask(False)
                if not rootgrp.variables:
                    return (file_path, False, "FAILED: Test 2 (NetCDF dataset contains zero variables)")
                
                for var_name in rootgrp.variables:
                    var = rootgrp.variables[var_name]
                    if var.size == 0:
                        continue

                    # Attempt reading data chunks to trigger HDF5 decompression errors
                    try:
                        _ = np.min(var)
                    except Exception as var_err:
                        return (file_path, False, f"FAILED: Test 2 (HDF5 Decompression corrupted on variable '{var_name}': {str(var_err)})")

    except Exception as e:
        return (file_path, False, f"FAILED: Test 2 (HDF5/NetCDF Structure Corrupted: {str(e)})")

    # TEST 3: CF Metadata & Coordinate Bounds Validation
    try:
        fields = cf.read(file_path)
        if not fields:
            return (file_path, False, "FAILED: Test 3 (CF Read returned no fields)")
        
        field = fields[0]
        for c in field.coordinates():
            coord_construct = field.construct(c)
            if coord_construct.has_bounds():
                try:
                    _ = coord_construct.get_bounds().data.array
                except Exception as bounds_err:
                    return (file_path, False, f"FAILED: Test 3 (Coordinate Bounds Corrupted for coordinate '{c}': {str(bounds_err)})")
                    
        return (file_path, True, "Healthy")
    except Exception as e:
        return (file_path, False, f"FAILED: Test 3 (CF Metadata Standard Check: {str(e)})")

@click.command()
@click.option('--path', '-p', 'input_paths', multiple=True, help='Path to scan.')
@click.option('--list', '-l', 'file_list_path', type=click.Path(exists=True), help='Text file with paths.')
@click.option('--workers', '-w', default=1, help='Number of parallel workers.')
@click.option('--out', '-o', default='validation_report.txt', help='Output report file.')
def main(input_paths, file_list_path, workers, out):
    """Scan NetCDF files and generate a full Health Report (Live Logging)."""
    file_list = []
    missing_files = []

    # 1. Gather files from command-line arguments
    for p_input in input_paths:
        target = os.path.expanduser(p_input)
        if os.path.isfile(target): 
            file_list.append(target)
        elif os.path.isdir(target):
            for root, _, files in os.walk(target):
                for f in files:
                    if f.endswith(".nc"): 
                        file_list.append(os.path.join(root, f))

    # 2. Gather files from text list (Handles missing trailing newlines and logs missing files)
    if file_list_path:
        with open(file_list_path, 'r') as f:
            for line in f:
                p = line.strip()
                if p:
                    # Check literal path first to bypass glob issues with ensemble bracket structures
                    if os.path.exists(p):
                        file_list.append(p)
                    else:
                        # Fall back to globbing in case it's a wildcard match pattern
                        matches = glob.glob(p)
                        if matches:
                            file_list.extend(matches)
                        else:
                            # Keep track of paths that do not exist anywhere on disk
                            missing_files.append(p)
                            click.secho(f"WARNING: File or pattern not found: {p}", fg='yellow', err=True)

    # De-duplicate and sort target file queue
    file_list = sorted(list(set(file_list)))
    
    total_expected = len(file_list) + len(missing_files)
    if total_expected == 0:
        click.secho("\nNo target files specified or found!", fg='red')
        return

    click.echo(f"Found {len(file_list)} files to process ({len(missing_files)} missing). Scanning with {workers} worker{'s' if workers > 1 else ''}...")

    # Initialize the report file header
    with open(out, "w") as f_out:
        f_out.write(f"Validation Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"Total processed files: {len(file_list)}\n")
        f_out.write(f"Total missing files:   {len(missing_files)}\n")
        f_out.write("-" * 50 + "\n")

    corrupt_count = 0

    # 3. Parallel Processing with Live Append
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check_file_health, f): f for f in file_list}

        # buffering=1 ensures lines flush out to disk instantly
        with open(out, "a", buffering=1) as f_out:
            # First write out the missing files so they don't get lost
            for mf in missing_files:
                f_out.write(f"[NOT FOUND] {mf} | File does not exist on disk.\n")
                
            # Scan active files
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(file_list), unit="file"):
                path, healthy, msg = future.result()

                if not healthy:
                    corrupt_count += 1

                status = "[OK]      " if healthy else "[CORRUPT]"
                f_out.write(f"{status} {path} | {msg}\n")

    # 4. Final Summary Terminal Output
    click.echo("-" * 40)
    summary_text = f"Complete: {corrupt_count} corrupt / {len(missing_files)} missing / {len(file_list)} scanned"
    click.secho(summary_text, bold=True, fg='green' if (corrupt_count == 0 and len(missing_files) == 0) else 'yellow')

    with open(out, "a") as f_out:
        f_out.write("\n" + "-" * 50 + "\n")
        f_out.write(f"Final Summary: {len(file_list) - corrupt_count} Healthy, {corrupt_count} Corrupt, {len(missing_files)} Missing\n")

    click.echo(f"Full report saved to: {os.path.abspath(out)}")

if __name__ == '__main__':
    main()
