# SebOS
## An amazing Arch distro.

SebOS uses a custom installer to bring a customized, amazing Arch experience, with no extra skill needed!

---

## Obtaining a disc image

You can get a SebOS disc image (ISO) in two ways:

 - Downloading the latest .ISO file from [releases](https://github.com/Sebminecrafter/SebOS/releases)
 - Building an ISO from source

### How to build an ISO

> [!NOTE]
> This guide assumes that you are running Arch Linux (or similar) and using the privelege escalator `sudo`.

First, clone the SebOS repository: `git clone https://github.com/Sebminecrafter/SebOS.git`  
Then, cd into it: `cd SebOS`

> [!TIP]
> You'll need to use the `mkarchiso` command, it can be installed with `sudo pacman -S archiso`

And finally make the ISO: `sudo mkarchiso -vrw /tmp/sebos-tmp -o . .`

Here's a full working script:
`````bash
sudo pacman -S --needed archiso
git clone https://github.com/Sebminecrafter/SebOS.git
cd SebOS
sudo mkarchiso -vrw /tmp/sebos-tmp -o . .
`````
