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
    total = 0
    corrupt = 0

    for p_input in paths:
        # Expand wildcards if user provided them (e.g. *)
        expanded_input = glob.glob(os.path.expanduser(p_input))
        
        for item in expanded_input:
            if os.path.isfile(item):
                # It's a single file, check it
                total += 1
                if not check_file_health(item):
                    corrupt += 1
            elif os.path.isdir(item):
                # It's a folder, find all .nc files inside recursively
                for root, dirs, files in os.walk(item):
                    for file in files:
                        if file.endswith(".nc"):
                            full_path = os.path.join(root, file)
                            total += 1
                            if not check_file_health(full_path):
                                corrupt += 1

    click.echo("-" * 20)
    click.secho(f"Scan complete. Found {corrupt} corrupt files out of {total}.", 
                bold=True, fg='yellow' if corrupt > 0 else 'green')

if __name__ == '__main__':
    main()
