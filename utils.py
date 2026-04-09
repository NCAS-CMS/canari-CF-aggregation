import re
import click

def runid_format(ctx, param, value):
    """Validates the LLNNN run ID format."""
    pattern = r"^[a-zA-Z]{2}[0-9]{3}$"
    if not re.match(pattern, value):
        raise click.BadParameter(f"'{value}' is not LLNNN format (e.g., ab123)")
    return value

def find_delta_from_size1_bounds(bounds, realm, ncvar):
    """Calculates time step delta from coordinate bounds."""
    seconds_in_month = 2592000
    lb = bounds[0, 0]
    ub = bounds[0, 1]
    
    if ub > lb:
        delta = ub - lb
    elif ub < lb:
        raise ValueError(f"{realm} {ncvar}: Upper bound ({ub}) < lower bound ({lb})")
    elif lb == seconds_in_month:
        delta = seconds_in_month
    else:
        raise ValueError(f"{realm} {ncvar}: Upper bound ({ub}) = lower bound ({lb})")
        
    return delta

