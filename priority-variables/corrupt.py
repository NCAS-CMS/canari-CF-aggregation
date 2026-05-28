import os
import netCDF4 as nc
from tqdm import tqdm
import concurrent.futures

scenario = "SSP370"
realm = "CICE"
member = "16"

base_dir = f"/gws/ssde/j25b/canari/shared/large-ensemble/priority/{scenario}/{member}/{realm}/yearly/"
output_file = f"final_corrupt_list-{scenario}-{realm}-{member}.txt"
num_workers = 4


def check_integrity(file_path):
    """Checks the first and last element of every variable in a file."""
    try:
        with nc.Dataset(file_path, mode="r") as rootgrp:
            rootgrp.set_auto_mask(False)
            for var_name in rootgrp.variables:
                var = rootgrp.variables[var_name]
                if var.size == 0:
                    continue

                # Use a small slice instead of just [0] to ensure chunk de-compression
                _ = var[tuple(slice(0, 1) for _ in range(var.ndim))]

                # Check the tail
                if var.size > 1:
                    last_idx = tuple(slice(-1, None) for _ in range(var.ndim))
                    _ = var[last_idx]
        return None
    except Exception as e:
        return (file_path, str(e))


# 1. Gather files
print(f"Searching for NetCDF files in {base_dir}...")
file_list = [
    os.path.join(r, f)
    for r, d, fs in os.walk(base_dir)
    for f in fs
    if f.endswith(".nc")
]

corrupt_files = []

print(f"Found {len(file_list)} files. Starting scan with {num_workers} workers...")

# 2. Use ThreadPoolExecutor
with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
    future_to_file = {executor.submit(check_integrity, f): f for f in file_list}

    # Open the file once and append as we find errors
    with open(output_file, "w") as f_out:
        for future in tqdm(
            concurrent.futures.as_completed(future_to_file),
            total=len(file_list),
            unit="file",
            leave=True,
        ):
            res = future.result()
            if res:
                file_path, error_msg = res
                corrupt_files.append(res)

                # Write to the local text file immediately
                f_out.write(f"{file_path}\n")
                f_out.flush()  # Ensure it writes to disk even if script crashes later

                tqdm.write(f"\n[CORRUPT] {file_path}")
                tqdm.write(f"   Error: {error_msg}")

# 3. Final Report
print(f"\nScan complete. Found {len(corrupt_files)} corrupt files.")
if corrupt_files:
    print(
        f"The list of corrupt files has been saved to: {os.path.abspath(output_file)}"
    )
