#!/usr/bin/env python3
"""Keep a laptop battery within a charge window using a Tapo P110M smart plug.

Lithium-ion cells degrade faster the longer they sit near full charge. Laptops
whose firmware exposes a charge threshold can cap this in the BIOS; the rest
cannot. This script closes that gap by cutting mains power at the wall instead:
it reads the battery level and switches a Tapo smart plug off above an upper
limit and back on below a lower one.

Run it periodically (systemd timer or cron). It is stateless — each run reads
the current level and decides.
"""

import asyncio
import ipaddress
import json
import subprocess
import sys
from pathlib import Path

CONFIG_PATH = Path.home() / ".config" / "battery-manager" / "config.json"
REQUIRED_KEYS = ("tapo_email", "tapo_password", "device_ip")
SUPPORTED_MODELS = ("P110", "P115")  # P110M reports as "P110M"
POWER_SUPPLY = Path("/sys/class/power_supply")


def fail(message):
    print(f"battery-manager: {message}", file=sys.stderr)
    sys.exit(1)


def load_config():
    if not CONFIG_PATH.exists():
        fail(f"{CONFIG_PATH} not found. Copy config.example.json there and fill it in.")
    try:
        config = json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError as e:
        fail(f"{CONFIG_PATH} is not valid JSON: {e}")
    if not isinstance(config, dict):
        fail(f"{CONFIG_PATH} must contain a JSON object at the top level.")

    missing = [k for k in REQUIRED_KEYS if not config.get(k)]
    if missing:
        fail(f"{CONFIG_PATH} is missing: {', '.join(missing)}")
    placeholder = [k for k in REQUIRED_KEYS if str(config[k]).startswith("YOUR_")]
    if placeholder:
        fail(f"{CONFIG_PATH} still has placeholder values for: {', '.join(placeholder)}")

    for key, default in (("battery_min", 40), ("battery_max", 80)):
        value = config.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float, str)):
            fail(f"{key} must be a whole number (got {value!r}).")
        try:
            number = float(value)
        except ValueError:
            fail(f"{key} must be a whole number (got {value!r}).")
        if number != int(number):
            fail(f"{key} must be a whole number (got {value!r}).")
        config[key] = int(number)
    if not 0 < config["battery_min"] < config["battery_max"] <= 100:
        fail("Thresholds must satisfy 0 < battery_min < battery_max <= 100.")

    # The plug speaks an unauthenticated-at-the-network-layer protocol on the
    # local network. Restricting it to a private address literal means a typo
    # or a tampered config cannot send the account credentials to a host on the
    # internet. tvremocon takes the same approach for the same reason.
    try:
        address = ipaddress.ip_address(str(config["device_ip"]).strip())
    except ValueError:
        fail(
            f"device_ip must be an IP address literal, not {config['device_ip']!r}. "
            "A hostname is refused because it could resolve anywhere."
        )
    if not (address.is_private or address.is_loopback) or address.is_reserved:
        fail(
            f"device_ip {address} is not a private address. This talks to a plug on "
            "your own network, so a public address is refused rather than sending "
            "your Tapo credentials off-network."
        )
    config["device_ip"] = str(address)

    name = config.get("battery_name", "BAT0")
    if not isinstance(name, str) or not name.strip():
        fail(f"battery_name must be a non-empty string (got {name!r}).")
    config["battery_name"] = name.strip()
    return config


def battery_path(config):
    path = POWER_SUPPLY / config["battery_name"]
    if not path.is_dir():
        available = sorted(p.name for p in POWER_SUPPLY.glob("BAT*")) if POWER_SUPPLY.is_dir() else []
        fail(f"{path} does not exist. Set battery_name to one of: {', '.join(available) or '(none found)'}")
    return path


def get_battery_percent(config):
    """Battery level in percent. Exits if it cannot be determined — it never guesses."""
    capacity = battery_path(config) / "capacity"
    try:
        value = int(capacity.read_text().strip())
        if 0 <= value <= 100:
            return value
    except (OSError, ValueError):
        pass

    # Fall back to upower when sysfs does not expose a usable capacity.
    device = f"/org/freedesktop/UPower/devices/battery_{config['battery_name']}"
    try:
        result = subprocess.run(["upower", "-i", device], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as e:
        fail(f"Could not read the battery level: {e}")
    if result.returncode != 0:
        fail(f"upower exited with status {result.returncode} for {device}.")
    for line in result.stdout.splitlines():
        # upower prints "percentage: 0% (should be ignored)" for devices it has not read yet.
        if "percentage" not in line or "should be ignored" in line:
            continue
        try:
            value = int(float(line.split(":", 1)[1].strip().rstrip("%")))
        except ValueError:
            continue
        if 0 <= value <= 100:
            return value
    fail("Could not read the battery level from sysfs or upower.")


def get_charge_status(config):
    try:
        return (battery_path(config) / "status").read_text().strip()
    except OSError:
        return "Unknown"


async def main():
    try:
        from tapo import ApiClient
    except ImportError:
        fail("The 'tapo' package is not installed: pip install -r requirements.txt")

    config = load_config()
    battery = get_battery_percent(config)
    status = get_charge_status(config)
    battery_max = config["battery_max"]
    battery_min = config["battery_min"]

    # Nothing to do while the level is inside the window, so do not contact the
    # plug at all. Most scheduled runs end here, and a plug that is briefly
    # offline then causes no spurious failure.
    if battery_min < battery < battery_max:
        print(f"Battery: {battery}% | Status: {status} | Plug: unchanged")
        return

    try:
        client = ApiClient(config["tapo_email"], config["tapo_password"])
        device = await client.p110(config["device_ip"])
        model = str(getattr(await device.get_device_info(), "model", "") or "")
        if not model.upper().startswith(SUPPORTED_MODELS):
            fail(f"Device at {config['device_ip']} reports model {model!r}; "
                 f"expected a P110/P110M/P115 plug, so refusing to switch it.")
        if battery >= battery_max:
            await device.off()
            action = f"OFF (>= {battery_max}%)"
        else:
            await device.on()
            action = f"ON (<= {battery_min}%)"
    except Exception as e:
        fail(f"Could not control the plug at {config['device_ip']}: {e}")

    print(f"Battery: {battery}% | Status: {status} | Plug: {action}")


if __name__ == "__main__":
    asyncio.run(main())
