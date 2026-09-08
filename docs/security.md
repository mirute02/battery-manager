# Security — what is protected, and what is not

This program holds a TP-Link Tapo account password and can switch mains power
to your laptop. Both deserve a straight answer about where the boundaries are.

## 1. Credentials

- **The password is not in the repository.** It lives in
  `~/.config/battery-manager/config.json`, outside the checkout, and
  `config.json` is in `.gitignore` in case a copy ever lands in the working
  tree. The example file ships with `YOUR_…` placeholders and the program
  refuses to start while they are still there.
- **It is stored in plain text.** This is the real limitation. There is no
  Linux equivalent of the Android Keystore that works unattended from a systemd
  timer — anything that would encrypt the file needs a key that the timer can
  reach without a human, which puts you back where you started. Set the file to
  mode `600` (the README says so) and understand that **anyone who can read
  your home directory, or restore a backup of it, has the Tapo password**.
- **Credentials are never logged.** Error messages carry the config path, the
  device address and the failing key name, never a value. This was checked by
  handing `ApiClient` a known password, pointing it at an unroutable address
  and inspecting the exception text: the credentials do not appear.
- The password is your Tapo *account* password, so its blast radius is every
  device on that account, not just this plug. A dedicated account shared to the
  plug would be better; TP-Link's sharing model makes that awkward, so this is
  noted rather than solved.

## 2. Where it will talk

`device_ip` must be a **private IPv4/IPv6 literal** (10/8, 172.16/12,
192.168/16, link-local, or loopback). A hostname is refused outright, and a
public address is refused with an explicit error.

The reason is narrow: this program sends account credentials to whatever
address it is given. A typo, a copied config from someone else, or a tampered
file should not be able to post them to a host on the internet. Refusing
hostnames removes DNS from the trust path entirely.

The `tapo` library speaks to the plug directly on the local network. Its
compiled module contains no TP-Link cloud endpoints — checked with `strings` —
so nothing here round-trips through a vendor service.

## 3. What it will switch

Before sending `on` or `off` the program asks the device for its model and
refuses anything that is not a **P110 / P110M / P115**. A mistyped last octet
that lands on a bulb or a different plug does nothing.

## 4. Failure behaviour

**It fails closed.** If the battery level cannot be read, it exits non-zero
*before* connecting to the plug. An earlier version returned `-1` on failure,
which compared as "below the lower limit" and switched charging **on** — the
worst possible answer on a machine where `BAT0` does not exist.

When the level is already inside the window it does not contact the plug at
all, so a plug that is briefly offline does not turn a routine run into a
failure.

## 5. What is not protected

- **Plain-text credentials at rest**, as above. This is the main one.
- **Anyone on your LAN who knows your Tapo credentials** can control the plug.
  That is the plug's authentication model, not something this program changes.
- **Anyone who can write `~/.config/battery-manager/config.json`** can point
  the program at a different private address — still confined to the local
  network, but not to *your* plug.
- **The plug is not a battery controller.** Cutting mains power stops charging;
  the laptop then runs on battery. A `battery_min` set too low means repeatedly
  deep-cycling the cell, which is the opposite of the intent.
- **`tapo` uses an unofficial protocol.** A firmware update can change or break
  it. It is also outside this program's control whether that protocol is sound.

## 6. Deliberately not done

- **No retry on failure.** A failed run reports and exits. Switching mains
  power is a physical action; a silent retry loop against a flaky network is
  how you end up toggling a plug repeatedly.
- **No daemon.** The program is stateless and run by a timer. Nothing holds the
  credentials in memory between runs.
- **No hostname support**, as above, even though it would be convenient.
- **No encryption of the config file**, because a key the timer can reach
  unattended is not meaningfully more secret than the file itself. Saying so is
  more honest than adding a layer that only looks like protection.

## Reporting

Open an issue. This is a personal project with no security process behind it;
treat the disclosure accordingly.
