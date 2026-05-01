import cf

# 1. Read files into a list
in_files = [
    'CF-1.13_seed_CANARI_1_cv575_atmos_1950.cfa',
    'CF-1.13_seed_CANARI_1_cv575_atmos_1951.cfa'
]

# 2. Aggregate on read (cleanest way)
combined = cf.read(in_files, aggregate=True)

# 3. Write with relaxed options to bypass the AggregationError
cf.write(
    combined,
    'combined_output.nc',
    cfa={
        "constructs": ["field"],
        "strict": False  # This replaces relaxed_identities in your version
    },
    chunk_cache=4 * 2**20
)
