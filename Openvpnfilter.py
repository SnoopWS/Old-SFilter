import asyncio
import subprocess

CLIENTS_FILE = "clients.txt"

async def read_clients_file():
    with open(CLIENTS_FILE, "r") as f:
        lines = f.readlines()
        valid_ips = set()
        for line in lines:
            ip = line.strip()
            valid_ips.add(ip)
        return valid_ips

async def get_non_whitelisted_ips(valid_ips):
    proc = await asyncio.create_subprocess_shell("netstat -an | grep ':1194'", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    non_whitelisted_ips = set()
    for line in stdout.decode().split("\n"):
        if line:
            ip = line.split()[4].split(":")[0]
            if ip not in valid_ips:
                non_whitelisted_ips.add(ip)

    return non_whitelisted_ips

async def update_iproute_rules(ips_to_block):
    for ip in ips_to_block:
        route_check = await asyncio.create_subprocess_exec("ip", "route", "get", ip, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = await route_check.communicate()
        if not stdout.startswith(b"blackhole"):
            print(f"Blackholing IP: {ip}")
            await asyncio.create_subprocess_exec("sudo", "ip", "route", "add", "blackhole", ip)
            print(f"Terminating existing connections to IP: {ip}")
            proc = await asyncio.create_subprocess_shell(f"sudo ss -K dst {ip} dport = 1194", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await proc.communicate()
            if stderr:
                print(f"Error while killing connections to {ip}: {stderr.decode()}")

async def main():
    while True:
        valid_ips = await read_clients_file()
        non_whitelisted_ips = await get_non_whitelisted_ips(valid_ips)
        await update_iproute_rules(non_whitelisted_ips)
        await asyncio.sleep(5)

asyncio.run(main())