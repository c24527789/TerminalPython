
import subprocess
import json

def run_command(command):
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )

        return json.loads(result.stdout)

    except (subprocess.CalledProcessError,
            FileNotFoundError,
            PermissionError,
            json.JSONDecodeError) as error:

        print("Command failed:", error)
        return

def get_links():
    return run_command(["ip", "-json", "link", "show"])

def get_addresses():
    return run_command(["ip", "-json", "address", "show"])

def get_routes():
    return run_command(["ip", "-json", "route", "show"])