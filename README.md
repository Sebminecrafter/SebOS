# SebOS
## An amazing Arch distro.

SebOS uses a custom installer to bring a customized, amazing Arch experience, with no extra skill needed!

___

## Getting an ISO

You can get a SebOS ISO in two ways:

Downloading the latest ISO from [releases](https://github.com/Sebminecrafter/SebOS/releases), or building it yourself

### How to build an ISO

> [!IMPORTANT]
> This guide assumes that you are running Arch Linux (or similar) and `sudo`.

First, clone the SebOS repository: `git clone https://github.com/Sebminecrafter/SebOS.git`  
Then, cd into it: `cd SebOS`  
Make sure you have `mkarchiso` installed too,
it can be installed with `sudo pacman -S archiso`  
And finally make the ISO: `sudo mkarchiso -vrw /tmp/sebos-tmp -o . .`

Here's a full working script:
```bash
sudo pacman -S --needed archiso
git clone https://github.com/Sebminecrafter/SebOS.git
cd SebOS
sudo mkarchiso -vrw /tmp/sebos-tmp -o . .
```
