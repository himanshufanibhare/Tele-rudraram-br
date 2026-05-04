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


def reboot_system():
    """
    Reboot the Raspberry Pi system
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Use direct sudo reboot command
        subprocess.Popen("sudo reboot", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "🔄 System reboot initiated...\nThe Raspberry Pi will reboot now."
    except Exception as e:
        return False, f"⚠️ Error rebooting system: {e}"
