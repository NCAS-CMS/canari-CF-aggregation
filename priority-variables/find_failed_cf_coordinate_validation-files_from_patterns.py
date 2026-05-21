import cf
import glob
import os
from tqdm import tqdm

# Configuration
input_file = "failed_cf_coordinate_patterns.txt"
output_file = "failed_files.txt"

# 1. Read patterns
if not os.path.exists(input_file):
    print(f"Error: {input_file} not found.")
    exit(1)

with open(input_file, "r") as f:
    patterns = [line.strip() for line in f if line.strip()]

# 2. Setup output
if os.path.exists(output_file):
    os.remove(output_file)

print(f"Reading patterns from {input_file}...")

# 3. Iterate with Progress Bars
# Outer loop for the high-level patterns
for pattern in tqdm(patterns, desc="Total Progress", unit="pattern"):
    files = sorted(glob.glob(pattern))
    
    if not files:
        continue
        
    # Inner loop for the files within each pattern
    # leave=False keeps the terminal clean by removing the inner bar when done
    for f in tqdm(files, desc=f"  Checking {pattern.split('/')[-1][:20]}...", leave=False, unit="file"):
        try:
            fields = cf.read(f)
            if not fields:
                raise ValueError("Empty file")
            
            field = fields[0]
            
            # The 'Coordinate Test' that catches the corruption
            for c in field.coordinates():
                coord = field.construct(c)
                if coord.has_bounds():
                    # Triggers the actual read/decompression
                    _ = coord.get_bounds().data.array
            
        except Exception:
            # Silent logging to the file so the progress bar isn't interrupted
            with open(output_file, "a") as err_log:
                err_log.write(f"{f}\n")

print(f"\n✅ Done. Results saved to: {output_file}")
