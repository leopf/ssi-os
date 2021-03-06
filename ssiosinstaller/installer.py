from typing import List
from ssiosinstaller.context import ExecContext
from ssiosinstaller.util import *
import inquirer
import json

def install_custom_mirrors(context: ExecContext, in_system: bool):
    for custom_mirror in context.config["custom_pacman_mirrors"]:
        if custom_mirror.find("$repo") == -1 or custom_mirror.find("$arch") == -1:
            print("skipped custom mirror due to invalid format: ", custom_mirror)
            continue

        command = "sed -i '1i Server = {}' /etc/pacman.d/mirrorlist".format(custom_mirror)
        if in_system:
            context.exec_chroot(command)
        else:
            context.exec_no_err(command)

def promt_primary_disk(context: ExecContext):
    disk_list_out = context.exec_no_err("lsblk -J")
    disk_list = json.loads(disk_list_out["stdout"])
    disk_options = [ bd for bd in disk_list["blockdevices"] if bd["type"] == "disk" ]

    question_map = {}
    for disk in disk_options:
        options_text = "{0} ({1})".format(disk["name"], disk["size"])
        question_map[options_text] = disk["name"]

    questions = [
    inquirer.List('primary_disk',
                    message="What disk do  you want to install the OS on?",
                    choices=list(question_map.keys()),
                ),
    ]
    answers = inquirer.prompt(questions)
    context.primary_disk = question_map[answers["primary_disk"]]

def set_user_password(context: ExecContext, username: str, password: str):
    context.exec_chroot("usermod --password $(openssl passwd {0}) {1}".format(password, username))

def setup_primary_disk(context: ExecContext):
    context.exec_no_err("sgdisk -Z /dev/{0}".format(context.primary_disk))
    context.exec_no_err("sgdisk -a 2048 -o /dev/{0}".format(context.primary_disk))
    context.exec_no_err("sgdisk -n 1::+1M --typecode=1:ef02 --change-name=1:'BIOSBOOT' /dev/{0}".format(context.primary_disk))
    context.exec_no_err("sgdisk -n 2::+1G --typecode=2:ef00 --change-name=2:'EFIBOOT' /dev/{0}".format(context.primary_disk))
    
    context.memory_size_mb = find_memory_size(context)
    memory_150_p = int(context.memory_size_mb * 1.5)
    print("swap size: ", memory_150_p, "MB")

    context.exec_no_err("sgdisk -n 3::+{0}M --typecode=3:8200 --change-name=3:'SWAP' /dev/{1}".format(memory_150_p, context.primary_disk))
    context.exec_no_err("sgdisk -n 4::-0 --typecode=4:8300 --change-name=4:'ROOT' /dev/{0}".format(context.primary_disk))
    
    context.exec_no_err("sgdisk -A 1:set:2 /dev/{0}".format(context.primary_disk))

    context.exec_no_err("mkfs.fat -F32 /dev/{0}".format(context.get_primary_disk_partition(2)))
    context.exec_no_err("mkswap /dev/{0}".format(context.get_primary_disk_partition(3)))
    context.exec_no_err("swapon /dev/{0}".format(context.get_primary_disk_partition(3)))
    context.exec_no_err("mkfs.btrfs /dev/{0}".format(context.get_primary_disk_partition(4)))
    context.exec_no_err("mount /dev/{0} /mnt".format(context.get_primary_disk_partition(4)))

    context.exec_no_err("btrfs su cr /mnt/@")
    context.exec_no_err("btrfs su cr /mnt/@home")
    context.exec_no_err("btrfs su cr /mnt/@snapshots")
    context.exec_no_err("btrfs su cr /mnt/@var_log")
    context.exec_no_err("umount /mnt")

    context.exec_no_err("mount -o noatime,space_cache=v2,subvol=@ /dev/{0} /mnt".format(context.get_primary_disk_partition(4)))

    context.exec_no_err("mkdir -p /mnt/{boot,home,.snapshots,var}")
    context.exec_no_err("mkdir /mnt/var/log")

    context.exec_no_err("mount -o noatime,space_cache=v2,subvol=@home /dev/{0} /mnt/home".format(context.get_primary_disk_partition(4)))
    context.exec_no_err("mount -o noatime,space_cache=v2,subvol=@snapshots /dev/{0} /mnt/.snapshots".format(context.get_primary_disk_partition(4)))
    context.exec_no_err("mount -o noatime,space_cache=v2,subvol=@var_log /dev/{0} /mnt/var/log".format(context.get_primary_disk_partition(4)))
    context.exec_no_err("mount /dev/{0} /mnt/boot".format(context.get_primary_disk_partition(2)))

def pacman_install(context: ExecContext, packages: List[str]):
    context.exec_chroot("pacman -S {} --noconfirm".format(" ".join(packages)))

def install_pacstrap_packages(context: ExecContext):
    kernel_headers = [ k + "-headers" for k in context.config["kernels"] ]
    ucode = None

    res = context.exec_no_err("lscpu")

    if is_amd_processor(res["stdout"]):
        ucode = "amd-ucode"

    if is_intel_processor(res["stdout"]):
        ucode = "intel-ucode"

    if ucode is None:
        raise "Processor type not found!"

    packages = [ "base", "base-devel", "linux-firmware", "vim", ucode ] + context.config["kernels"] + kernel_headers

    context.exec_no_err("pacstrap /mnt {}".format(" ".join(packages)))

def paru_install(context: ExecContext, packages: List[str]):
    context.exec_chroot("mkdir /var/paru_temp")
    context.exec_chroot("chmod -R 777 /var/paru_temp")
    context.exec_chroot_as_user("cd /var/paru_temp && paru -S {} --noconfirm".format(" ".join(packages)))
    context.exec_chroot("rm -r /var/paru_temp")

def install(context: ExecContext):
    promt_primary_disk(context)

    context.exec_no_err("timedatectl set-ntp true")

    install_custom_mirrors(context, False)
    context.exec_no_err("sed -i 's/#ParallelDownloads = 5/ParallelDownloads = 10\\nILoveCandy/g' /etc/pacman.conf")

    setup_primary_disk(context)

    install_pacstrap_packages(context)

    # general setup
    context.exec_no_err("genfstab -U /mnt >> /mnt/etc/fstab")

    install_custom_mirrors(context, True)
    context.exec_chroot("sed -i 's/#ParallelDownloads = 5/ParallelDownloads = 10\\nILoveCandy/g' /etc/pacman.conf")
    context.exec_chroot("localectl set-keymap {0}".format(context.config["key_layout"]))
    context.exec_chroot("ln -sf /usr/share/zoneinfo/{} /etc/localtime".format(context.config["timezone"]))
    context.exec_chroot("hwclock --systohc")
    context.exec_chroot("echo LANG={}.UTF-8 > /etc/locale.conf".format(context.config["lang"]))
    context.exec_chroot('echo "{}.UTF-8 UTF-8" > /etc/locale.gen'.format(context.config["lang"]))
    context.exec_chroot("locale-gen")
    context.exec_chroot("echo KEYMAP={} > /etc/vconsole.conf".format(context.config["key_layout"]))

    context.exec_chroot("echo {} > /etc/hostname".format(context.config["computer_name"]))
    context.exec_chroot('echo "127.0.0.1 localhost" > /etc/hosts')
    context.exec_chroot('echo "::1 localhost" >> /etc/hosts')
    context.exec_chroot('echo "127.0.1.1 {0}.localdomain {0}" >> /etc/hosts'.format(context.config["computer_name"]))

    set_user_password(context, "root", context.config["root_password"])
    pacman_install(context, [
        "grub",
        "efibootmgr",
        "networkmanager",
        "network-manager-applet",
        "dialog",
        "wpa_supplicant",
        "mtools",
        "dosfstools",
        "git",
        "reflector",
        "snapper", 
        "bluez", 
        "bluez-utils",
        "cups",
        "xdg-utils",
        "xdg-user-dirs",
        "alsa-utils",
        "pulseaudio",
        "pulseaudio-bluetooth",
        "inetutils",
        "bash-completion",
        "openssh"
    ])

    context.exec_chroot("sed -i 's/MODULES=()/MODULES=(btrfs)/g' /etc/mkinitcpio.conf")
    context.exec_chroot("mkinitcpio -P")
    context.exec_chroot("grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=ssiOS")
    context.exec_chroot("grub-mkconfig -o /boot/grub/grub.cfg")

    context.exec_chroot("systemctl enable NetworkManager")
    context.exec_chroot("systemctl enable bluetooth")
    context.exec_chroot("systemctl enable cups")
    context.exec_chroot("systemctl enable sshd")

    context.exec_chroot("useradd -mG wheel {}".format(context.config["username"]))
    set_user_password(context, context.config["username"], context.config["user_password"])

    context.exec_chroot("umount /.snapshots")
    context.exec_chroot("rm -r /.snapshots")
    context.exec_chroot("snapper --no-dbus -v -c root create-config /")
    context.exec_chroot("btrfs subvolume delete /.snapshots")
    context.exec_chroot("mkdir /.snapshots")
    context.exec_chroot("mount -a")
    context.exec_chroot("chmod 750 /.snapshots")

    context.exec_chroot("sed -i 's/ALLOW_USERS=\"\"/ALLOW_USERS=\"{}\"/g' /etc/snapper/configs/root".format(context.config["username"]))
    context.exec_chroot("sed -i 's/TIMELINE_LIMIT_HOURLY=\"10\"/TIMELINE_LIMIT_HOURLY=\"10\"/g' /etc/snapper/configs/root")
    context.exec_chroot("sed -i 's/TIMELINE_LIMIT_DAILY=\"10\"/TIMELINE_LIMIT_DAILY=\"5\"/g' /etc/snapper/configs/root")
    context.exec_chroot("sed -i 's/TIMELINE_LIMIT_WEEKLY=\"0\"/TIMELINE_LIMIT_WEEKLY=\"4\"/g' /etc/snapper/configs/root")
    context.exec_chroot("sed -i 's/TIMELINE_LIMIT_MONTHLY=\"10\"/TIMELINE_LIMIT_MONTHLY=\"0\"/g' /etc/snapper/configs/root")
    context.exec_chroot("sed -i 's/TIMELINE_LIMIT_YEARLY=\"10\"/TIMELINE_LIMIT_YEARLY=\"0\"/g' /etc/snapper/configs/root")

    context.exec_chroot("systemctl enable snapper-timeline.timer")
    context.exec_chroot("systemctl enable snapper-cleanup.timer")

    context.exec_chroot("pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com")
    context.exec_chroot("pacman-key --lsign-key 3056513887B78AEB")
    context.exec_chroot("pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst' --noconfirm")
    context.exec_chroot("sed -i 's/#\\[multilib\\]/\\[multilib\\]\\nInclude = \\/etc\\/pacman.d\\/mirrorlist\\n\\n\\[chaotic-aur\\]\\nInclude = \\/etc\\/pacman.d\\/chaotic-mirrorlist/g' /etc/pacman.conf")
    context.exec_chroot("pacman -Syy")

    context.exec_chroot("sed -i 's/# %wheel ALL=(ALL) NOPASSWD: ALL/%wheel ALL=(ALL) NOPASSWD: ALL/g' /etc/sudoers")

    pacman_install(context, [
        "paru",
        "rsync",
        "snap-pac-grub",
    ])

    paru_install(context, [
        "snapper-gui",
        "google-chrome"
    ] + context.config["additional_packages"])

    context.exec_chroot("sed -i 's/%wheel ALL=(ALL) NOPASSWD: ALL/# %wheel ALL=(ALL) NOPASSWD: ALL/g' /etc/sudoers")
    context.exec_chroot("sed -i 's/# %wheel ALL=(ALL) ALL/%wheel ALL=(ALL) ALL/g' /etc/sudoers")

    context.exec_chroot("mkdir /etc/pacman.d/hooks")

    context.exec_chroot('echo "[Trigger]" > /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "Operation = Upgrade" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "Operation = Install" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "Operation = Remove" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "Type = Path" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "Target = usr/lib/modules/*/vmlinuz" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "[Action]" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "Depends = rsync" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "Description = Prevent fuck up vong /boot..." >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "When = PostTransaction" >> /etc/pacman.d/hooks/50-bootbackup.hook')
    context.exec_chroot('echo "Exec = /usr/bin/rsync -a --delete /boot /.bootbackup" >> /etc/pacman.d/hooks/50-bootbackup.hook')

    context.exec_chroot('chmod a+rx /.snapshots')
    context.exec_chroot('chown :{} /.snapshots'.format(context.config["username"]))
    context.exec_chroot('snapper --no-dbus create --description clean-af-without-de-or-nvidia')
    
    pacman_install(context, [
        "nvidia",
        "nvidia-utils",
        "nvidia-dkms",
        "nvidia-settings",
        "xorg",
        "libxcb",
        "qt5",
        "sddm",
        "dolphin",
        "kitty",
        "plasma-meta"
    ])

    context.exec_chroot("sed -i 's/MODULES=(btrfs)/MODULES=(btrfs nvidia nvidia_modeset nvidia_uvm nvidia_drm)/g' /etc/mkinitcpio.conf")
    context.exec_chroot("mkinitcpio -P")
    context.exec_chroot("sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT=\"/GRUB_CMDLINE_LINUX_DEFAULT=\"nvidia-drm.modeset=1 /g' /etc/default/grub")
    context.exec_chroot("grub-mkconfig -o /boot/grub/grub.cfg")
    context.exec_chroot("systemctl enable sddm")
    context.exec_chroot("localectl set-keymap {0}".format(context.config["key_layout"]))


    # context.exec_no_err("reboot")






    





    


