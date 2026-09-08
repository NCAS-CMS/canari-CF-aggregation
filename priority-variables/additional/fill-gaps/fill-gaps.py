import os
import re

base_dir = "/gws/ssde/j25b/canari/shared/large-ensemble/priority/HIST2"
output_file = "missing_in_18.txt"

def scan_member_folder(member_dir):
    file_map = {}
    member_path = os.path.join(base_dir, member_dir)
    prefix_len = len(member_path)
    
    for root, _, filenames in os.walk(member_path):
        rel_dir = root[prefix_len:].lstrip("/")
        for f in filenames:
            norm_f = re.sub(r"^([^_]*_){2}", "", f)
            norm_path = os.path.join(rel_dir, norm_f)
            file_map[norm_path] = os.path.join(root, f)
            
    return file_map

print("Scanning folder 1...")
map1 = scan_member_folder("1")

print("Scanning folder 18...")
map18 = scan_member_folder("18")

# Count summary
print("-" * 40)
print(f"Total files in Folder 1 : {len(map1)}")
print(f"Total files in Folder 18: {len(map18)}")
print(f"Difference              : {len(map1) - len(map18)}")
print("-" * 40)

# Get full paths of files present in 1 but missing in 18
missing_keys = sorted(set(map1.keys()) - set(map18.keys()))
missing_paths = [map1[k] for k in missing_keys]

with open(output_file, "w") as out:
    for path in missing_paths:
        out.write(path + "\n")

print(f"Saved {len(missing_paths)} missing full file paths to: {output_file}")
