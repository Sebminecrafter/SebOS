#!/usr/bin/env python3
"""
SebOS Installer - Automated Arch Linux installation script.

This script provides an interactive TUI for installing Arch Linux with SebOS
customizations, including disk partitioning, GRUB configuration, and theming.
"""

import curses
import os
import subprocess
import shutil
import sys
import time


def run(cmd):
    try:
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print("An error occurred during the installation.")
        print(e)
        print("If you do not understand")


def root():
    if os.geteuid() != 0:
        os.execvp("sudo", ["sudo", "python3"] + sys.argv)


def boot():
    return "UEFI" if os.path.isdir("/sys/firmware/efi") else "BIOS"


def disks():
    output = subprocess.check_output(
        "lsblk -d -o NAME,SIZE,MODEL", shell=True
    ).decode().splitlines()
    return output[1:]  # Skip header row


def menu(stdscr, title, options):
    curses.curs_set(0)  # Hide cursor
    selected_index = 0
    
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, title)
        
        # Render menu options
        for index, option in enumerate(options):
            prefix = "> " if index == selected_index else "  "
            attributes = curses.A_REVERSE if index == selected_index else 0
            stdscr.addstr(index + 2, 0, prefix + option, attributes)
        
        stdscr.refresh()
        key = stdscr.getch()
        
        # Handle navigation
        if key == curses.KEY_UP:
            selected_index = (selected_index - 1) % len(options)
        elif key == curses.KEY_DOWN:
            selected_index = (selected_index + 1) % len(options)
        elif key in [10, 13]:  # Enter key
            return options[selected_index]


def main(stdscr):
    """
    Main installation workflow.
    
    Orchestrates the entire SebOS installation process including:
    - Disk selection and partitioning
    - Base system installation
    - Bootloader configuration
    - Theme customization
    
    Args:
        stdscr: The curses window object (provided by curses.wrapper).
    """
    # Initialize system checks
    root()
    boot_mode = boot()
    
    run("pacman-key --init")
    run("pacman-key ")
    
    # Display welcome screen
    stdscr.addstr(0, 0, "SebOS Installer")
    stdscr.addstr(1, 0, f"Boot Mode: {boot_mode}")
    stdscr.refresh()
    time.sleep(1)
    
    # ===== DISK SELECTION =====
    disk_options = menu(stdscr, "Select installation disk", disks())
    disk_name = disk_options.split()[0]
    disk_path = f"/dev/{disk_name}"
    
    # Confirm disk wipe
    if menu(stdscr, f"WIPE {disk_path}?", ["Cancel", "Confirm"]) != "Confirm":
        return
    
    # ===== DISK PARTITIONING =====
    run(f"wipefs -a {disk_path}")
    run(f"sgdisk --zap-all {disk_path}")
    
    if boot_mode == "UEFI":
        # UEFI partitioning (GPT with EFI and root partitions)
        run(f"parted {disk_path} --script mklabel gpt")
        run(f"parted {disk_path} --script mkpart ESP fat32 1MiB 512MiB")
        run(f"parted {disk_path} --script set 1 esp on")
        run(f"parted {disk_path} --script mkpart primary ext4 512MiB 100%")
        
        efi_partition = f"{disk_path}1"
        root_partition = f"{disk_path}2"
        
        run(f"mkfs.fat -F32 {efi_partition}")
        run(f"mkfs.ext4 {root_partition}")
        run(f"mount {root_partition} /mnt")
        run("mkdir -p /mnt/boot")
        run(f"mount {efi_partition} /mnt/boot")
    else:
        # BIOS partitioning (GPT with BIOS boot and root partitions)
        run(f"parted {disk_path} --script mklabel gpt")
        run(f"parted {disk_path} --script mkpart primary 1MiB 3MiB")
        run(f"parted {disk_path} --script set 1 bios_grub on")
        run(f"parted {disk_path} --script mkpart primary ext4 3MiB 100%")
        
        root_partition = f"{disk_path}2"
        
        run(f"mkfs.ext4 {root_partition}")
        run(f"mount {root_partition} /mnt")
    
    # ===== BASE SYSTEM INSTALLATION =====
    base_packages = [
        "base", "linux", "linux-firmware",
        "networkmanager", "sudo", "git", "nano",
        "grub", "arch-install-scripts", "fastfetch"
    ]
    run(f"pacstrap /mnt {' '.join(base_packages)}")
    
    # Generate fstab
    run("genfstab -U /mnt >> /mnt/etc/fstab")
    
    # ===== BOOTLOADER INSTALLATION =====
    if boot_mode == "UEFI":
        run("pacstrap /mnt efibootmgr")
        run(
            f"arch-chroot /mnt grub-install "
            "--target=x86_64-efi --efi-directory=/boot --bootloader-id=SebOS"
        )
    else:
        run(f"arch-chroot /mnt grub-install --target=i386-pc {disk_path}")
    
    run("arch-chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg")
    
    # ===== THEME CONFIGURATION =====
    # Copy GRUB theme files to the new installation
    run("mkdir -p /mnt/usr/share/sebos/usr/share/grub")
    run("cp -a /usr/share/sebos/usr/share/grub/ /mnt/usr/share/sebos/usr/share/")
    
    # Configure GRUB theme and settings
    src_theme = "/usr/share/sebos/usr/share/grub/themes/sebos"
    dst_theme = "/boot/grub/themes/sebos"
    grub_cfg = "/etc/default/grub"
    
    # Check if source theme exists and copy it
    run(f"arch-chroot /mnt bash -c 'if [[ -d {src_theme} ]]; then mkdir -p /boot/grub/themes && cp -a {src_theme} {dst_theme}; fi'")
    
    # Update GRUB configuration settings
    grub_settings = [
        (f"GRUB_THEME=", f'GRUB_THEME="{dst_theme}/theme.txt"'),
        ("GRUB_TIMEOUT=", "GRUB_TIMEOUT=2"),
        ("GRUB_TIMEOUT_STYLE=", "GRUB_TIMEOUT_STYLE=menu"),
        ("GRUB_COLOR_NORMAL=", 'GRUB_COLOR_NORMAL="light-green/black"'),
        ("GRUB_COLOR_HIGHLIGHT=", 'GRUB_COLOR_HIGHLIGHT="green/black"'),
    ]
    
    for key, value in grub_settings:
        # Use sed to replace or add settings
        run(f"arch-chroot /mnt sed -i 's/^#\\?{key}.*/{value}/' {grub_cfg} || arch-chroot /mnt bash -c 'echo {value} >> {grub_cfg}'")
    
    # Regenerate GRUB configuration
    run("arch-chroot /mnt grub-mkconfig -o /boot/grub/grub.cfg")
    
    # ===== POST-INSTALLATION =====
    run("arch-chroot /mnt systemctl enable NetworkManager")
    
    # Optional: Enter chroot or reboot
    if menu(stdscr, "Enter chroot before rebooting?", ["Yes", "No"]) == "Yes":
        run("arch-chroot /mnt")
    else:
        # Countdown timer before reboot
        for countdown in range(5, 0, -1):
            stdscr.clear()
            stdscr.addstr(0, 0, f"Rebooting in {countdown} seconds...")
            stdscr.refresh()
            time.sleep(1)
        run("reboot")

if __name__ == "__main__":
    # Launch the interactive TUI using curses
    curses.wrapper(main)