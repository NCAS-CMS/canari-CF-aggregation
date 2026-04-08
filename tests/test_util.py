import pytest
import click
import numpy as np
from utils import runid_format, find_delta_from_size1_bounds

# --- RunID Tests ---
def test_runid_valid():
    assert runid_format(None, None, "ab123") == "ab123"

def test_runid_invalid():
    with pytest.raises(click.BadParameter):
        runid_format(None, None, "123ab")

# --- Delta Logic Tests ---
def test_delta_standard():
    bounds = np.array([[100, 130]])
    assert find_delta_from_size1_bounds(bounds, "atmos", "time") == 30

def test_delta_instantaneous():
    sec = 2592000
    bounds = np.array([[sec, sec]])
    assert find_delta_from_size1_bounds(bounds, "atmos", "time") == sec

