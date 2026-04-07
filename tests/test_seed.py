import pytest
import pathlib
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from seed import main, runid_format

@pytest.fixture
def mock_cf_field():
    """ Creates a fake Field object that satisfies seed.py logic """
    field = MagicMock()
    
    # 1. Mock properties used in loops/if-statements
    field.has_property.return_value = False
    field.nc_get_variable.return_value = "m01s00i002_2"
    
    # 2. Mock domain axis (None skips the JDMA and Unlimited axis logic)
    field.domain_axis.return_value = None 
    
    # 3. Mock the internal data/filename handling
    field.data.get_filenames.return_value = ["/work/data/file.nc"]
    field.data.replace_directory.return_value = None
    
    # 4. Mock the .select() method to return itself in a list
    field.select.return_value = [field]
    
    return field

@patch('cf.read')
@patch('cf.write')
@patch('seed.pathlib.Path.glob')
def test_atmos_testing_logic(mock_glob, mock_write, mock_read, mock_cf_field, tmp_path):
    """Test that 'testing' mode correctly filters atmos fields and writes the file."""
    
    # Setup the mock behavior
    mock_glob.return_value = [pathlib.Path("test_file.nc")]
    
    # Instead of a plain list, we give the mock_read a MagicMock that acts like a FieldList
    mock_field_list = MagicMock()
    # This allows the script to iterate over it: for i, g in enumerate(f)
    mock_field_list.__iter__.return_value = [mock_cf_field]
    # This allows the script to call f.select(...)
    mock_field_list.select.return_value = [mock_cf_field]
    
    mock_read.return_value = mock_field_list

    runner = CliRunner()
    result = runner.invoke(main, [
        '--runid', 'ab123',
        '--realm', 'atmos',
        '--member', '1',
        '--testing', 'yes',
        '--startyear', '1950',
        '--data_path', str(tmp_path)
    ])

    # Print error details if the test fails for easier debugging
    if result.exit_code != 0:
        print(f"DEBUG - Output: {result.output}")
        if result.exception:
            print(f"DEBUG - Exception: {result.exception}")
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

    # Assertions
    assert result.exit_code == 0
    assert "Subsetting atmos fields" in result.output
    
    # Verify cf.write was called
    assert mock_write.called

def test_runid_validation():
    """Test the LLNNN regex validation directly."""
    # Should pass
    assert runid_format(None, None, "cy866") == "cy866"
    assert runid_format(None, None, "ab123") == "ab123"
    
    # Should fail
    import click
    with pytest.raises(click.BadParameter):
        runid_format(None, None, "123ab")
    with pytest.raises(click.BadParameter):
        runid_format(None, None, "abc12")
