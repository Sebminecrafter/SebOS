#!/usr/bin/env python3

import json
import subprocess
import getpass
import os
import sys
import shutil

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

def get_user_info():
    username = input("Enter username: ").strip()

    while True:
        password = getpass.getpass(prompt="Enter password: ", echo_char='*')
        confirm = getpass.getpass(prompt="Confirm password: ", echo_char='*')
        if password == confirm:
            break
        print("Passwords do not match.")

    return username, password

def generate_config(profile, username, password):
    config = {
        "profile": profile,
        "bootloader": "grub",
        "packages": ["neovim", "fastfetch"],
        "users": [
            {
                "username": username,
                "password": password,
                "sudo": True
            }
        ]
    }

    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

def run_archinstall():
    run(["archinstall", "--config", "config.json"])

def apply_sebos(variant: str):
    """
    System-wide overlay model:

    /sebos/common     -> base system overrides
    /sebos/<variant>  -> profile-specific overrides

    No user-specific configuration is applied here.
    """

    common = f"{SEBOS}/common/"
    variant_path = f"{SEBOS}/{variant}/"

    # 1. Base system overlay (always applied)
    run([
        "rsync",
        "-a",
        common,
        MNT + "/"
    ])

    # 2. Profile-specific overlay (XFCE / minimal etc.)
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

    generate_config(install["profile"], username, password)

    run_archinstall()

    # Apply your custom OS layer
    apply_sebos(install["variant"], username)

    print("Install + customization complete.")

if __name__ == "__main__":
    main()
