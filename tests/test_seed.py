import pytest
import click
from seed import runid_format

def test_runid_format_valid():
    """Test that valid LLNNN strings (2 letters, 3 numbers) pass."""
    assert runid_format(None, None, "ab123") == "ab123"
    assert runid_format(None, None, "XY999") == "XY999"

def test_runid_format_invalid():
    """Test that invalid strings raise the Click BadParameter exception."""
    # Fails if it's too long
    with pytest.raises(click.BadParameter):
        runid_format(None, None, "abc123")
    
    # Fails if numbers and letters are swapped
    with pytest.raises(click.BadParameter):
        runid_format(None, None, "12abc")
        
    # Fails if it contains special characters
    with pytest.raises(click.BadParameter):
        runid_format(None, None, "ab!12")
