#!/usr/bin/env python3

import json
import subprocess
import getpass
import os
import sys
from passlib.hash import sha512_crypt

MNT = "/mnt"
SEBOS = "/sebos"

def run(cmd):
    subprocess.run(cmd, check=True)

def choose_install_type():
    print("Select install type:")
    print("1) Terminal Only (TTY)")
    print("2) Xfce4")

    while True:
        choice = input("Enter choice (1-2): ").strip()
        if choice == "1":
            return {
                "profile": "minimal",
                "variant": "minimal"
            }
        elif choice == "2":
            return {
                "profile": "xfce4",
                "variant": "xfce"
            }
        else:
            print("Invalid choice.")

def choose_extra_packages():
    choice = input("Choose extra packages, seperated by spaces: ").strip()
    packages = choice.split(" ")
    return packages


def get_user_info():
    username = input("Enter username: ").strip()

    while True:
        password = getpass.getpass(prompt="Enter password: ", echo_char='*')
        confirm = getpass.getpass(prompt="Confirm password: ", echo_char='*')
        if password == confirm:
            break
        print("Passwords do not match.")

    return username, password

def choose_disk():
    print("Available disks:")
    result = subprocess.run(["lsblk", "-d", "-o", "NAME,SIZE"], capture_output=True, text=True)
    print(result.stdout)

    disk = input("Enter disk to use (e.g. sda, nvme0n1): ").strip()
    full_disk = f"/dev/{disk}"

    confirm = input(f"WARNING: This will erase ALL data on {full_disk}. Continue? (y/n): ").strip().lower()
    if not confirm.lower() in ["y", "yes", "yeah", "ye"]:
        print("Aborted.")
        sys.exit(1)

    return full_disk

def generate_config(profile, username, password, extra, disk, silent):
    gfx = greeter = details = None
    profiletype = "Minimal"

    passwordhash = sha512_crypt.hash(password)

    # Base packages
    packages = [
        "neovim",
        "fastfetch",
        "nano"
    ]
    
    packages.extend(extra)

    # Profile-specific
    if profile == "xfce4":
        gfx = "All open-source"
        greeter = "lightdm-gtk-greeter"
        profiletype = "Desktop"
        details = ["Xfce4"]
       
    # Disk config
    
    # Get disk size in bytes
    size_bytes = int(subprocess.check_output(
        ["blockdev", "--getsize64", disk]
    ).decode().strip())

    # Partition layout assumptions
    boot_size_gib = 1
    boot_size_bytes = boot_size_gib * 1024**3

    # Start offsets
    boot_start_mib = 1
    boot_start_bytes = boot_start_mib * 1024**2

    root_start_bytes = boot_start_bytes + boot_size_bytes
    root_size_bytes = size_bytes - root_start_bytes

    # Object IDs (just need to be unique integers)
    bootobjid = 1
    mainobjid = 2

    # Map to names expected in config
    disksizebytes = root_size_bytes
    startbytes = root_start_bytes

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
                            "flags": ["boot"],
                            "fs_type": "fat32",
                            "mount_options": [],
                            "mountpoint": "/boot",
                            "obj_id": bootobjid,
                            "size": {
                                "sector_size": {
                                    "unit": "B",
                                    "value": 512
                                },
                                "unit": "GiB",
                                "value": 1
                            },
                            "start": {
                                "sector_size": {
                                    "unit": "B",
                                    "value": 512
                                },
                                "unit": "MiB",
                                "value": 1
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
                                "unit": "B",
                                "value": disksizebytes
                            },
                            "start": {
                                "sector_size": {
                                    "unit": "B",
                                    "value": 512
                                },
                                "unit": "B",
                                "value": startbytes
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
            "custom_repoisitories": [],
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
        "profile_config":  {
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
        "silent": silent,
        "timezone": "UTC",
        "version": "4.3"
    }

    creds = {
        "root_enc_password": "root",
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

def run_archinstall():
    run(["archinstall", "--config", "config.json", "--creds", "creds.json"])

def apply_sebos(variant: str):
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

def main():
    if os.geteuid() != 0:
        print("Run as root.")
        sys.exit(1)

    install = choose_install_type()
    username, password = get_user_info()
    extrapkgs = choose_extra_packages()
    disk = choose_disk()

    auto = False
    proceed = input("Proceed with automatic installation? (y/n): ").strip().lower()
    if not proceed.lower() in ["y", "yes", "yeah", "ye"]:
        auto = True

    generate_config(install["profile"], username, password, extrapkgs, disk, auto)

    run_archinstall()

    apply_sebos(install["variant"])

    print("Install complete.")

if __name__ == "__main__":
    main()
