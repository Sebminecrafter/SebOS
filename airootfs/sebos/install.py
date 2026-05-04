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

def confirm(message):
    confirminput = input(message).strip().lower()
    return confirminput in ["y", "yes", "yeah", "ye"]

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
    packages = [p for p in choice.split() if p]
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
    print("Available disks:")
    result = subprocess.run(["lsblk", "-d", "-o", "NAME,SIZE"], capture_output=True, text=True)
    print(result.stdout)

    disk = input("Enter disk to use (will look like sda, nvme, etc.): ").strip()
    full_disk = f"/dev/{disk}"

    if not os.path.exists(full_disk):
        print("Invalid disk.")
        sys.exit(1)

    if not confirm(f"WARNING: This will erase ALL data on {full_disk}. Continue? (y/n): "):
        print("Aborted.")
        sys.exit(1)
    
    return full_disk

def generate_config(profile, username, password, root_password, extra, disk):
    gfx = greeter = details = None
    profiletype = "Minimal"

    passwordhash = sha512_crypt.hash(password)
    rootpasswordhash = sha512_crypt.hash(root_password)

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

def run_archinstall(silent):
    ai_args = ["archinstall", "--config", "config.json", "--creds", "creds.json"]

    if silent:
        ai_args.append("--silent")

    run(["pacman-key", "--init"])
    run(["pacman-key", "--populate"])
    run(ai_args)

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
        print("Please run this program as root. (Have you tried using sudo?)")
        sys.exit(1)

    install = choose_install_type()
    username, password = get_user_info()
    root_password = get_root_password()
    extrapkgs = choose_extra_packages()
    disk = choose_disk()

    auto = confirm("Proceed with automatic installation? (y/n): ")

    generate_config(install["profile"], username, password, root_password, extrapkgs, disk)

    run_archinstall(auto)

    apply_sebos(install["variant"])

    print("Install complete.")

if __name__ == "__main__":
    main()
