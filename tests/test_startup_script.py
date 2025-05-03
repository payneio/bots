"""Tests for the startup script sourcing feature."""
import os
import tempfile
from pathlib import Path

from bots.core import source_script


def test_source_script_sets_environment_variables():
    """Test that source_script correctly sets environment variables from a startup.sh script."""
    # Create a temporary script file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
        temp_file.write("""#!/bin/bash
export TEST_VAR="From startup script"
export CUSTOM_PATH="/custom/test/path"
""")
        script_path = Path(temp_file.name)
    
    try:
        # Clear any existing environment variables
        if "TEST_VAR" in os.environ:
            del os.environ["TEST_VAR"]
        if "CUSTOM_PATH" in os.environ:
            del os.environ["CUSTOM_PATH"]
        
        # Source the script
        source_script(script_path, debug=True)
        
        # Check that environment variables were set
        assert "TEST_VAR" in os.environ
        assert os.environ["TEST_VAR"] == "From startup script"
        assert "CUSTOM_PATH" in os.environ
        assert os.environ["CUSTOM_PATH"] == "/custom/test/path"
    
    finally:
        # Clean up
        if os.path.exists(script_path):
            os.unlink(script_path)


def test_source_script_handles_nonexistent_file():
    """Test that source_script correctly handles a nonexistent file."""
    # Create a path that doesn't exist
    nonexistent_path = Path("/nonexistent/startup.sh")
    
    # This should not raise an exception
    source_script(nonexistent_path, debug=True)


def test_source_script_handles_non_zero_exit_code():
    """Test that source_script handles a script that exits with non-zero status."""
    # Create a temporary script file that exits with error
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as temp_file:
        temp_file.write("""#!/bin/bash
export BEFORE_ERROR="This should be set"
exit 1
export AFTER_ERROR="This should not be set"
""")
        script_path = Path(temp_file.name)
    
    try:
        # Clear any existing environment variables
        if "BEFORE_ERROR" in os.environ:
            del os.environ["BEFORE_ERROR"]
        if "AFTER_ERROR" in os.environ:
            del os.environ["AFTER_ERROR"]
        
        # Source the script
        source_script(script_path, debug=True)
        
        # The function should not raise an exception
        # Variables set before the error should be captured
        assert "BEFORE_ERROR" not in os.environ
        assert "AFTER_ERROR" not in os.environ
    
    finally:
        # Clean up
        if os.path.exists(script_path):
            os.unlink(script_path)