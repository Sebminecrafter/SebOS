#!/usr/bin/env python3

import json
import re
import subprocess
import getpass
import os
import sys
import termios
import tty
from passlib.hash import sha512_crypt

MNT = "/mnt"
SEBOS = "/sebos"
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

PACKAGE_NAME_RE = re.compile(r"^[a-z0-9@._+-]+$")

def run(cmd):
    subprocess.run(cmd, check=True)

def load_packages_file(path):
    packages = []
    if not os.path.exists(path):
        return packages

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            if not PACKAGE_NAME_RE.fullmatch(line):
                raise ValueError(f"Invalid package name in {path}: {line}")
            packages.append(line)
    return packages

def profile_name(profile: str):
    return "xfce" if profile == "xfce4" else profile

def get_packages(profile: str):
    packages = load_packages_file(os.path.join(SCRIPT_DIR, f"{profile_name(profile)}.packages"))
    packages.extend(load_packages_file(os.path.join(SCRIPT_DIR, f"common.packages")))
    return packages

def get_postinstall_packages(variant: str):
    packages = load_packages_file(os.path.join(SCRIPT_DIR, f"{variant}.postinstall.packages"))
    packages.extend(load_packages_file(os.path.join(SCRIPT_DIR, f"common.postinstall.packages")))
    return packages

def run_chroot(cmd):
    if isinstance(cmd, str):
        cmd = [cmd]
    subprocess.run(["arch-chroot", MNT, *cmd], check=True)

def interactive_menu(options: list, prompt: str = "Select:"):
    if not options:
        raise ValueError("Options list cannot be empty")

    selected = 0

    def render():
        sys.stdout.write("\r")  # return to start of line
        line = prompt + " "
        for i, opt in enumerate(options):
            if i == selected:
                line += f"\x1b[7m[{opt}]\x1b[0m "
            else:
                line += f"{opt} "
        sys.stdout.write(line)
        sys.stdout.write("\x1b[K")  # clear to end of line
        sys.stdout.flush()

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        render()
        while True:
            ch = sys.stdin.read(1)

            if ch == "\x1b":
                ch += sys.stdin.read(2)
                if ch == "\x1b[C":  # right
                    selected = (selected + 1) % len(options)
                elif ch == "\x1b[D":  # left
                    selected = (selected - 1) % len(options)

            elif ch in ("\r", "\n"):
                sys.stdout.write("\r\n")
                return selected

            elif ch == "l":
                selected = (selected + 1) % len(options)
            elif ch == "h":
                selected = (selected - 1) % len(options)

            render()

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def confirm(message: str):
    return interactive_menu(["Yes", "No"], message) == 0

def choose_install_type():
    choice = interactive_menu(
        ["Xfce4", "Terminal Only (TTY)"],
        "Select install type:"
    )
    if choice == 0:
        return {
            "profile": "xfce4",
            "variant": "xfce"
        }
    else:
        return {
            "profile": "minimal",
            "variant": "minimal"
        }

def choose_extra_packages():
    while True:
        choice = input("Choose extra packages, separated by spaces (Enter/Return to skip): ").strip()
        packages = [p for p in choice.split() if p]
        invalid = [p for p in packages if not bool(PACKAGE_NAME_RE.fullmatch(p))]

        if invalid:
            print(f"Invalid package name(s): {', '.join(invalid)}")
            print("Package names may only contain lowercase letters, digits, and @ . _ + -")
            continue

        return packages

def install_sound_theme():
    theme_repo = "https://github.com/cadecomposer/modern-minimal-ui-sounds.git"
    theme_name = "modern-minimal-ui-sounds"
    target_path = f"{MNT}/usr/share/sounds/{theme_name}"

    # Clone to temp
    run(["git", "clone", "--depth", "1", theme_repo, "/tmp/modern-minimal-ui-sounds"])

    # Copy into target system
    run(["mkdir", "-p", f"{MNT}/usr/share/sounds"])
    run(["cp", "-r", "/tmp/modern-minimal-ui-sounds", target_path])

def install_yay(username: str):
    yay_repo = "https://aur.archlinux.org/yay.git"
    
    # Clone into chroot temp directory
    run_chroot(["git", "clone", yay_repo, "/tmp/yay"])
    
    # Build and install as the regular user
    run_chroot(["bash", "-c", f"cd /tmp/yay && sudo -u {username} makepkg -si --noconfirm"])
    
    # Cleanup
    run_chroot(["rm", "-rf", "/tmp/yay"])

def get_user_info():
    username = input("Enter username: ").strip()
    
    def get_pass(p: str): return getpass.getpass(prompt=p, echo_char="*")

    while True:
        password = get_pass("Enter password: ")
        confirm = get_pass("Confirm password: ")
        if password == confirm:
            break
        print("Passwords do not match.")

    return username, password

def get_root_password():
    print("The root account is an administrator, which is used for high privelege tasks or in emergencies.")
    print("This password should be secure and not given to anyone. Don't forget it!")
    while True:
        password = getpass.getpass(prompt="Enter root password: ", echo_char='*')
        confirm = getpass.getpass(prompt="Confirm root password: ", echo_char='*')
        if password == confirm:
            return password
        print("Passwords do not match.")

def choose_disk():
    # Get disks in a parseable format (no headers, key=value)
    result = subprocess.run(
        ["lsblk", "-d", "-n", "-P", "-o", "NAME,SIZE"],
        capture_output=True,
        text=True,
        check=True
    )

    disks = []
    labels = []

    for line in result.stdout.strip().splitlines():
        parts = dict(p.split("=", 1) for p in line.split())
        name = parts["NAME"].strip('"')
        size = parts["SIZE"].strip('"')

        path = f"/dev/{name}"
        disks.append(path)
        labels.append(f"{name} ({size})")

    if not disks:
        print("No disks found. (Something is definitely wrong here)")
        sys.exit(1)

    idx = interactive_menu(labels, "Select disk (←/→, Enter):")
    full_disk = disks[idx]

    if not confirm(f"WARNING: This will erase ALL data on {full_disk}. Continue? "):
        print("Aborted.")
        sys.exit(1)
    
    return full_disk

def generate_config(profile: str, username: str, password: str, root_password: str, extra: list, disk: str):
    gfx = greeter = details = None
    profiletype = "Minimal"

    passwordhash = sha512_crypt.hash(password)
    rootpasswordhash = sha512_crypt.hash(root_password)

    # Packages
    packages = []    
    packages.extend(extra)
    packages.extend(get_packages(profile))

    # Profile-specific
    if profile == "xfce4":
        gfx = "All open-source"
        greeter = "lightdm-gtk-greeter"
        profiletype = "Desktop"
        details = ["Xfce4"]
    # Disk config
    
    # Get disk size in MiB (aligned)
    size_mib = int(subprocess.check_output(
        ["blockdev", "--getsize64", disk]
    ).decode().strip()) // (1024 * 1024)
    
    if size_mib < 2048:
        print("Disk too small.")
        sys.exit(1)

    boot_size_mib = 1024  # 1 GiB
    boot_start_mib = 1

    root_start_mib = boot_start_mib + boot_size_mib
    root_size_mib = max(1024, size_mib - root_start_mib - 8)

    # Object IDs (just need to be unique integers)
    bootobjid = 1
    mainobjid = 2

    config = {
        "app_config": {
            "audio_config": {
                "audio": "pipewire"
            },
            "bluetooth_config": {
                "enabled": True
            },
            "firewall_config": {
                "firewall": "ufw"
            },
            "fonts_config": {
                "fonts": [
                    "noto-fonts",
                    "noto-fonts-emoji",
                    "noto-fonts-cjk",
                    "ttf-liberation",
                    "ttf-dejavu"
                ]
            },
            "print_service_config": {
                "enabled": True
            }
        },
        "archinstall-language": "English",
        "auth_config": {},
        "bootloader_config": {
            "bootloader": "Grub",
            "removable": True,
            "uki": False
        },
        "custom_commands": [],
        "disk_config": {
            "btrfs_options": {
                "snapshot_config": None
            },
            "config_type": "default_layout",
            "device_modifications": [
                {
                    "device": disk,
                    "partitions": [
                        {
                            "btrfs": [],
                            "dev_path": None,
                            "flags": ["boot", "esp"],
                            "fs_type": "fat32",
                            "mount_options": [],
                            "mountpoint": "/boot/efi",
                            "obj_id": bootobjid,
                            "size": {
                                "sector_size": {
                                    "unit": "B",
                                    "value": 512
                                },
                                "unit": "MiB",
                                "value": boot_size_mib
                            },
                            "start": {
                               "sector_size": {
                                    "unit": "B",
                                    "value": 512
                                },
                                "unit": "MiB",
                                "value": boot_start_mib
                            },
                            "status": "create",
                            "type": "primary"
                        },
                        {
                            "btrfs": [],
                            "dev_path": None,
                            "flags": [],
                            "fs_type": "ext4",
                            "mount_options": [],
                            "mountpoint": "/",
                            "obj_id": mainobjid,
                            "size": {
                                "sector_size": {
                                    "unit": "B",
                                    "value": 512
                                },
                                "unit": "MiB",
                                "value": root_size_mib
                            },
                            "start": {
                                "sector_size": {
                                    "unit": "B",
                                    "value": 512
                                },
                                "unit": "MiB",
                                "value": root_start_mib
                            },
                            "status": "create",
                            "type": "primary"
                        }
                    ],
                    "wipe": True
                }
            ]
        },
        "hostname": "sebos",
        "kernels": ["linux"],
        "locale_config": {
            "kb_layout": "us",
            "sys_enc": "UTF-8",
            "sys_lang": "en_US.UTF-8"
        },
        "mirror_config": {
            "custom_repositories": [],
            "custom_servers": [],
            "mirror_regions": {},
            "optional_repositories": []
        },
        "network_config": {
            "type": "nm"
        },
        "ntp": True,
        "packages": packages,
        "pacman_config": {
            "color": True,
            "parallel_downloads": 5
        },
        "profile_config": {
            "gfx_driver": gfx,
            "greeter": greeter,
            "profile": {
                "custom_settings": {},
                "details": details,
                "main": profiletype
            }
        },
        "script": None,
        "services": [],
        "swap": {
            "algorithm": "zstd",
            "enabled": True
        },
        "timezone": "UTC",
        "version": "4.3"
    }

    creds = {
        "root_enc_password": rootpasswordhash,
        "users": [
            {
                "username": username,
                "enc_password": passwordhash,
                "sudo": True
            }
        ]
    }

    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

    with open("creds.json", "w") as f:
        json.dump(creds, f, indent=2)

def run_archinstall(silent: bool):
    ai_args = ["archinstall", "--config", "config.json", "--creds", "creds.json"]

    if silent:
        ai_args.append("--silent")

    run(["pacman-key", "--init"])
    run(["pacman-key", "--populate"])
    run(ai_args)

def apply_sebos(variant: str, username: str):
    common = f"{SEBOS}/common/"
    variant_path = f"{SEBOS}/{variant}/"

    run([
        "rsync",
        "-a",
        common,
        MNT + "/"
    ])

    if os.path.exists(variant_path):
        run([
            "rsync",
            "-a",
            variant_path,
            MNT + "/"
        ])

    # Copy skel into the already-created user's home
    home = f"{MNT}/home/{username}"
    skel = f"{MNT}/etc/skel/"
    if os.path.exists(home) and os.path.exists(skel):
        run(["rsync", "-a", skel, home + "/"])
        run_chroot(["chown", "-R", f"{username}:{username}", f"/home/{username}"])
    
    postinstall = get_postinstall_packages(variant)

    if postinstall:
        run_chroot(["pacman", "-S", "--noconfirm", *postinstall])

    if variant == "xfce":
        install_sound_theme()
    
    install_yay(username)

def main():
    if os.geteuid() != 0:
        print("Please run this program as root. (Have you tried using sudo?)")
        sys.exit(1)

    install = choose_install_type()
    username, password = get_user_info()
    root_password = get_root_password()
    extrapkgs = choose_extra_packages()
    disk = choose_disk()

    auto = confirm("Proceed with automatic installation? ")

    generate_config(install["profile"], username, password, root_password, extrapkgs, disk)

    try:
        run_archinstall(auto)
    except Exception:
        if confirm("An error occured during the install, try again?"):
            try:
                run_archinstall(auto)
            except Exception:
                print("An error occurred again. Aborting.")
        else:
            sys.exit(1)

    apply_sebos(install["variant"], username)

    print("Install complete.")

if __name__ == "__main__":
    main()
