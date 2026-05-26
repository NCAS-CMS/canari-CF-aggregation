import os
import sys
import cf
import netCDF4 as nc
import click
import concurrent.futures
import glob
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
            except:
                yield

def check_file_health(file_path):
    """Performs two-stage integrity and metadata check."""
    # STAGE 1: Data Integrity
    try:
        with silence_stderr():
            with nc.Dataset(file_path, mode="r") as rootgrp:
                rootgrp.set_auto_mask(False)
                for var_name in rootgrp.variables:
                    var = rootgrp.variables[var_name]
                    if var.size == 0: continue
                    _ = var[tuple(slice(0, 1) for _ in range(var.ndim))]
                    if var.size > 1:
                        _ = var[tuple(slice(-1, None) for _ in range(var.ndim))]
    except Exception:
        return (file_path, False, "FAILED: Stage 1 (Data Integrity / HDF5)")

    # STAGE 2: CF Metadata
    try:
        field = cf.read(file_path)[0]
        for c in field.coordinates():
            if field.construct(c).has_bounds():
                _ = field.construct(c).get_bounds().data.array
        return (file_path, True, "Healthy")
    except Exception:
        return (file_path, False, "FAILED: Stage 2 (CF Metadata / Coordinates)")

@click.command()
@click.option('--path', '-p', 'input_paths', multiple=True, help='Path to scan.')
@click.option('--list', '-l', 'file_list_path', type=click.Path(exists=True), help='Text file with paths.')
@click.option('--workers', '-w', default=1, help='Number of parallel workers.')
@click.option('--out', '-o', default='validation_report.txt', help='Output report file.')
def main(input_paths, file_list_path, workers, out):
    """Scan NetCDF files and generate a full Health Report (Live Logging)."""
    file_list = []

    # 1. Gather files
    for p_input in input_paths:
        target = os.path.expanduser(p_input)
        if os.path.isfile(target): file_list.append(target)
        elif os.path.isdir(target):
            for root, _, files in os.walk(target):
                for f in files:
                    if f.endswith(".nc"): file_list.append(os.path.join(root, f))

    if file_list_path:
        with open(file_list_path, 'r') as f:
            for line in f:
                p = line.strip()
                if p:
                    matches = glob.glob(p)
                    if matches:
                        file_list.extend(matches)
                    elif os.path.exists(p):
                        file_list.append(p)

    file_list = sorted(list(set(file_list))) 
    if not file_list:
        click.secho("No files found to scan!", fg='red')
        return

    click.echo(f"Found {len(file_list)} files. Scanning with {workers} worker{'s' if workers > 1 else ''}...")

    # Initialize the report file with the header
    with open(out, "w") as f_out:
        f_out.write(f"Validation Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f_out.write(f"Total files to scan: {len(file_list)}\n")
        f_out.write("-" * 50 + "\n")

    corrupt_count = 0
    
    # 2. Parallel Processing with Live Append
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(check_file_health, f): f for f in file_list}
        
        # buffering=1 ensures lines are written to disk as they are generated
        with open(out, "a", buffering=1) as f_out:
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(file_list), unit="file"):
                path, healthy, msg = future.result()
                
                if not healthy:
                    corrupt_count += 1
                
                status = "[OK]      " if healthy else "[CORRUPT]"
                f_out.write(f"{status} {path} | {msg}\n")

    # 3. Final Summary
    click.echo("-" * 40)
    summary_text = f"Complete: {corrupt_count} corrupt / {len(file_list)} total"
    click.secho(summary_text, bold=True, fg='green' if corrupt_count==0 else 'yellow')
    
    with open(out, "a") as f_out:
        f_out.write("\n" + "-" * 50 + "\n")
        f_out.write(f"Final Summary: {len(file_list) - corrupt_count} Healthy, {corrupt_count} Corrupt\n")

    click.echo(f"Full report saved to: {os.path.abspath(out)}")

if __name__ == '__main__':
    main()
