# battery-manager

[日本語](README.md) | **English**

Keep a laptop battery within a charge window by switching a **TP-Link Tapo P110M** smart plug on and off.

Lithium-ion cells age faster the longer they sit near 100%. Laptops whose firmware exposes a charge threshold can cap this in the BIOS — many cannot, including Macs running Linux. This closes that gap from the other side: it cuts mains power at the wall instead of at the battery controller.

```
battery >= battery_max  →  plug OFF  (discharge)
battery <= battery_min  →  plug ON   (charge)
otherwise               →  leave the plug alone
```

The script is stateless. Each run reads the current level and decides, so it is safe to schedule and safe to interrupt.

## Requirements

- Linux with `/sys/class/power_supply/BAT*` (a `upower` fallback is used if `capacity` is unreadable)
- **Python 3.11+** (required by the `tapo` library)
- A Tapo P110M / P110 / P115 reachable on the LAN
- [`tapo`](https://github.com/mihai-dinculescu/tapo) ≥ 0.8.8 (MIT) — the only third-party dependency

## Setup

```bash
git clone https://github.com/mirute02/battery-manager.git
cd battery-manager
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

mkdir -p ~/.config/battery-manager
cp config.example.json ~/.config/battery-manager/config.json
chmod 600 ~/.config/battery-manager/config.json
$EDITOR ~/.config/battery-manager/config.json
```

## Configuration

`~/.config/battery-manager/config.json` — **outside the repository**, so credentials are never committed. (`config.json` is also listed in `.gitignore`, in case a copy ever lands in the checkout.)

| Key | Required | Default | Meaning |
|---|---|---|---|
| `tapo_email` | ✅ | — | Tapo account e-mail |
| `tapo_password` | ✅ | — | Tapo account password |
| `device_ip` | ✅ | — | Plug's LAN address (give it a DHCP reservation) |
| `battery_max` | | `80` | Cut power at or above this % |
| `battery_min` | | `40` | Restore power at or below this % |
| `battery_name` | | `BAT0` | Directory under `/sys/class/power_supply` |

`device_ip` must be a **private address literal** — a hostname or a public address is refused, so a typo cannot send your Tapo credentials off-network. See [docs/security.md](docs/security.md).

Find your battery with `ls /sys/class/power_supply/`. Some laptops use `BAT1`.

The script refuses to start — without touching the plug — if the config is missing, a value is still `YOUR_…`, a required key is absent, a threshold is not a whole number, `battery_name` is not a non-empty string, or the thresholds are not `0 < battery_min < battery_max <= 100`.

## Run

```bash
.venv/bin/python battery-manager.py
# Battery: 75% | Status: Full | Plug: unchanged
```

### Schedule it

`~/.config/systemd/user/battery-manager.service`

```ini
[Unit]
Description=Battery charge manager

[Service]
Type=oneshot
ExecStart=%h/battery-manager/.venv/bin/python %h/battery-manager/battery-manager.py
```

`~/.config/systemd/user/battery-manager.timer`

```ini
[Unit]
Description=Run battery-manager every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now battery-manager.timer
```

## Design notes

**It fails closed.** If the battery level cannot be read, the script exits non-zero *before* connecting to the plug. An earlier version returned `-1` on failure, which compared as "below the lower limit" and switched charging **on** — exactly the wrong answer on a machine where `BAT0` does not exist.

**Credentials stay out of the repo.** The Tapo account password is a real credential; it lives only in `~/.config/battery-manager/config.json`. Set it to mode `600`.

**The plug is not a battery controller.** Cutting mains power stops charging, but the laptop then runs on battery. Set `battery_min` high enough that you are not repeatedly deep-cycling the cell — the defaults (40/80) aim at that.

**No plug connection when the level is in range.** When the battery sits between `battery_min` and `battery_max`, the script exits without contacting the plug. Most scheduled runs take this path, so a plug that is briefly offline causes no spurious failure.

**It only talks to your own network.** `device_ip` is restricted to a private address literal, and hostnames are refused so DNS is not in the trust path.

**It checks what it is about to switch.** Before sending `on`/`off` it asks the device for its model and refuses anything that is not a P110 / P110M / P115, so a mistyped `device_ip` that lands on a bulb or a different plug does nothing.

**Connections time out.** When an action *is* needed, the `tapo` client gives up after 30 seconds, so a plug that is off the network fails the run cleanly instead of hanging a scheduler.

## Tests

```bash
pip install pytest
python -m pytest tests/ -q
```

34 tests, none of which contact a plug or the network. CI runs them on Python 3.11-3.13.

## Security

[docs/security.md](docs/security.md) sets out what is protected, what is not — the Tapo password is stored in plain text, and that is the main limitation — and what was deliberately left undone.

## Related

- [tvremocon](https://github.com/mirute02/tvremocon) — an Android widget that drives a TV through a Tapo infrared hub, using the same LAN-only KLAP protocol.

## Licence

MIT — see [LICENSE](LICENSE). Dependency licences are listed in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

`tapo` is MIT-licensed. Tapo is a trademark of TP-Link; this project is not affiliated with or endorsed by TP-Link.
