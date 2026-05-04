"""
Helper functions for shell commands and utilities
"""

import subprocess


def shell_command(cmd):
    """
    Execute a shell command and return output
    
    Args:
        cmd (str): Shell command to execute
        
    Returns:
        str: Command output, or empty string on error
    """
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Command timed out"
    except Exception as e:
        return f"Error: {e}"
