import argparse
import subprocess
import json
import socket


# Run Linux commands
def run_command(command):
    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    return json.loads(result.stdout)


# Collect network information
def collect_network():

    network = {}

    network["hostname"] = socket.gethostname()

    links = run_command(["ip", "-json", "link", "show"])
    addresses = run_command(["ip", "-json", "address", "show"])
    routes = run_command(["ip", "-json", "route", "show"])

    if links is None or addresses is None or routes is None:
        raise RuntimeError("Could not collect network data")

    network["interfaces"] = []

    for link in links:

        interface = {
            "name": link.get("ifname"),
            "mtu": link.get("mtu"),
            "mac": link.get("address"),
            "state": link.get("operstate"),
            "flags": link.get("flags", []),
            "ip_addresses": []
        }

        for address in addresses:

            if address.get("ifname") == interface["name"]:

                for ip in address.get("addr_info", []):
                    interface["ip_addresses"].append(
                        ip.get("local")
                    )

        network["interfaces"].append(interface)

    network["routes"] = []

    for route in routes:

        network["routes"].append({
            "destination": route.get("dst", "default"),
            "gateway": route.get("gateway"),
            "interface": route.get("dev")
        })

    return network


# Display network information
def display_network(network):

    print("Hostname:", network["hostname"])

    for interface in network["interfaces"]:
        print("\nInterface:", interface["name"])
        print("MTU:", interface["mtu"])
        print("MAC:", interface["mac"])
        print("State:", interface["state"])
        print("Flags:", interface["flags"])
        print("IP Addresses:", interface["ip_addresses"])

    print("\nRoutes:")

    for route in network["routes"]:
        print("Destination:", route["destination"])
        print("Gateway:", route["gateway"])
        print("Interface:", route["interface"])


# Save network information to JSON
def save_json(network, filename):

    with open(filename, "w") as file:
        json.dump(network, file, indent=4)

    print("\nSaved to", filename)


# Main program
def main():

    parser = argparse.ArgumentParser(
        description="Local Network Monitoring Tool"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="local_network.json",
        help="Output JSON filename"
    )

    args = parser.parse_args()

    try:
        network = collect_network()

        display_network(network)

        save_json(network, args.output)

    except (RuntimeError, OSError) as error:
        print("Error:", error)


if __name__ == "__main__":
    main()