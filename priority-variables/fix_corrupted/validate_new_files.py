import cf
import click
import glob
import os

def check_file_health(filepath):
    """Performs the actual coordinate and data check."""
    try:
        # Initial metadata read
        field = cf.read(filepath)[0]
        
        # Force read coordinates/bounds to catch 'filter returned failure'
        for c in field.coordinates():
            if field.construct(c).has_bounds():
                 _ = field.construct(c).get_bounds().data.array
        
        click.secho(f"✅ {filepath}: Healthy", fg='green')
        return True
    except Exception as e:
        click.secho(f"❌ {filepath}: CORRUPT! ({e})", fg='red', bold=True)
        return False

@click.command()
# 'multiple=True' allows you to use the flag several times
# 'required=True' ensures the user doesn't forget it
@click.option('--path', '-p', 'paths', 
              multiple=True, 
              required=True,
              help='Path to file or wildcard (e.g. --path "/data/*.nc")')
def main(paths):
    """
    Check NetCDF files for corruption by explicitly passing paths via --path.
    """
    total = 0
    corrupt = 0

    # Because of multiple=True, 'paths' is a tuple of all --path inputs
    for p_input in paths:
        # Manually expand glob because shell expansion doesn't always 
        # work inside quotes/options
        expanded_paths = glob.glob(os.path.expanduser(p_input))
        
        if not expanded_paths:
            click.echo(f"No files found matching: {p_input}")
            continue

        for p in sorted(expanded_paths):
            total += 1
            if not check_file_health(p):
                corrupt += 1

    click.echo("-" * 20)
    click.secho(f"Scan complete. Found {corrupt} corrupt files out of {total}.", 
                bold=True, fg='yellow' if corrupt > 0 else 'green')

if __name__ == '__main__':
    main()
