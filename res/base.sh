#ssh daemon is active by default
#passwd usermod --password 123456 root
#ip a .... you know (to show ip)
#connect with ssh
loadkeys de-latin1
timedatectl set-ntp true #enable ntp (time you know)
#baba speed mirror
sed -i '1i Server = http://mirror.kudlik.space/$repo/os/$arch' /etc/pacman.d/mirrorlist
lsblk -J # ask user (/dev/sdX or /dev/nvmeXnX)
# {
#   "blockdevices": [
#      {
#         "name": "loop0",
#         "maj:min": "7:0",
#         "rm": false,
#         "size": "673.7M",
#         "ro": true,
#         "type": "loop",
#         "mountpoints": [
#             "/run/archiso/airootfs"
#         ]
#      },{
#         "name": "sda",
#         "maj:min": "8:0",
#         "rm": false,
#         "size": "64G",
#         "ro": false,
#         "type": "disk",
#         "mountpoints": [
#             null
#         ]
#      },{
#         "name": "sr0",
#         "maj:min": "11:0",
#         "rm": true,
#         "size": "846.3M",
#         "ro": false,
#         "type": "rom",
#         "mountpoints": [
#             "/run/archiso/bootmnt"
#         ]
#      }
#   ]
# }
sfdisk --delete /dev/[XXX]

parted /dev/[XXX] mkpart EFI fat32 1 1000
parted /dev/[XXX] set 1 esp on
parted /dev/[XXX] mkpart swap linux-swap 1000 48000 #48000 150% of ram
parted /dev/[XXX] mkpart linux btrfs 49000 100% #49000 quick mathsss

mkfs.fat -F32 /dev/[XXX]1
mkswap /dev/[XXX]2
swapon /dev/[XXX]2
mkfs.btrfs /dev/[XXX]3
mount /dev/[XXX]3 /mnt

btrfs su cr /mnt/@
btrfs su cr /mnt/@home
btrfs su cr /mnt/@snapshots
btrfs su cr /mnt/@var_log
umount /mnt

mount -o noatime,space_cache=v2,subvol=@ /dev/[XXX]3 /mnt
mkdir -p /mnt/{boot,home,.snapshots,var}
mkdir /mnt/var/log
mount -o noatime,space_cache=v2,subvol=@home /dev/[XXX]3 /mnt/home
mount -o noatime,space_cache=v2,subvol=@snapshots /dev/[XXX]3 /mnt/.snapshots
mount -o noatime,space_cache=v2,subvol=@var_log /dev/[XXX]3 /mnt/var/log
mount /dev/[XXX]1 /mnt/boot
#kernel select (linux linux-zen linux-lts) (intel/amd-ucode)
pacstrap /mnt base base-devel linux linux-lts linux-zen linux-firmware linux-headers linux-zen-headers linux-lts-headers vim intel-ucode
#micro you know
genfstab -U /mnt >> /mnt/etc/fstab
#arch-chroot /mnt bababascript.sh # or commands
ln -sf /usr/share/zoneinfo/Europe/Berlin /etc/localtime
hwclock --systohc
echo LANG=en_US.UTF-8 > /etc/locale.conf
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
echo KEYMAP=de-latin1 > /etc/vconsole.conf
echo [BABANAMEVONGCOMPUTER] > /etc/hostname
echo "127.0.0.1 localhost" > /etc/hosts
echo "::1 localhost" >> /etc/hosts
echo "127.0.1.1 [BABANAMEVONGCOMPUTER].localdomain [BABANAMEVONGCOMPUTER]" >> /etc/hosts
usermod --password [123456] root
#hplip for hp printers
pacman -S grub efibootmgr networkmanager network-manager-applet dialog wpa_supplicant mtools dosfstools git reflector snapper bluez bluez-utils cups xdg-utils xdg-user-dirs alsa-utils pulseaudio pulseaudio-bluetooth inetutils bash-completion openssh
sed -i 's/MODULES=()/MODULES=(btrfs)/g' /etc/mkinitcpio.conf 
mkinitcpio -P
grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=ssiOS
grub-mkconfig -o /boot/grub/grub.cfg
systemctl enable NetworkManager
systemctl enable bluetooth
systemctl enable cups
systemctl enable sshd
useradd -mG wheel [rodney]
usermod --password [123456] [rodney]
sed -i 's/# %wheel ALL=(ALL) ALL/%wheel ALL=(ALL) ALL/g' /etc/sudoers

umount /.snapshots
rm -r /.snapshots
snapper --no-dbus -v -c root create-config /
btrfs subvolume delete /.snapshots
mkdir /.snapshots
mount -a
chmod 750 /.snapshots
sed -i 's/ALLOW_USERS=""/ALLOW_USERS="[ssio]"/g' /etc/snapper/configs/root
sed -i 's/TIMELINE_LIMIT_HOURLY="10"/TIMELINE_LIMIT_HOURLY="10"/g' /etc/snapper/configs/root
sed -i 's/TIMELINE_LIMIT_DAILY="10"/TIMELINE_LIMIT_DAILY="5"/g' /etc/snapper/configs/root
sed -i 's/TIMELINE_LIMIT_WEEKLY="0"/TIMELINE_LIMIT_WEEKLY="4"/g' /etc/snapper/configs/root
sed -i 's/TIMELINE_LIMIT_MONTHLY="10"/TIMELINE_LIMIT_MONTHLY="0"/g' /etc/snapper/configs/root
sed -i 's/TIMELINE_LIMIT_YEARLY="10"/TIMELINE_LIMIT_YEARLY="0"/g' /etc/snapper/configs/root
systemctl enable snapper-timeline.timer
systemctl enable snapper-cleanup.timer

pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
pacman-key --lsign-key 3056513887B78AEB
pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst' --noconfirm
sed -i 's/#ParallelDownloads = 5/ParallelDownloads = 5\nILoveCandy/g' /etc/pacman.conf
sed -i 's/#\[multilib\]/\[multilib\]\nInclude = \/etc\/pacman.d\/mirrorlist\n\n\[chaotic-aur\]\nInclude = \/etc\/pacman.d\/chaotic-mirrorlist/g' /etc/pacman.conf
pacman -Syy
pacman -S paru rsync snap-pac-grub --noconfirm
git clone https://aur.archlinux.org/snapper-gui-git.git
#baba dependencies of snapper-gui
chmod -R 777 snapper-gui-git/
su ssio -c "cd snapper-gui-git && makepkg" 
find snapper-gui-git/ -iname "snapper-gui-git*.tar.zst" | xargs pacman -U --noconfirm
mkdir /etc/pacman.d/hooks

echo "[Trigger]" > /etc/pacman.d/hooks/50-bootbackup.hook
echo "Operation = Upgrade" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "Operation = Install" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "Operation = Remove" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "Type = Path" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "Target = usr/lib/modules/*/vmlinuz" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "[Action]" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "Depends = rsync" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "Description = Prevent fuck up vong /boot..." >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "When = PostTransaction" >> /etc/pacman.d/hooks/50-bootbackup.hook
echo "Exec = /usr/bin/rsync -a --delete /boot /.bootbackup" >> /etc/pacman.d/hooks/50-bootbackup.hook

chmod a+rx /.snapshots
chown :[SSIO] /.snapshots
snapper --no-dbus create --description clean-af-without-de-or-nvidia
pacman -S --noconfirm nvidia nvidia-utils nvidia-dkms nvidia-settings xorg libxcb qt5 sddm 
pacman -S --noconfirm plasma-meta kde-applications-meta
sed -i 's/MODULES=(btrfs)/MODULES=(btrfs nvidia nvidia_modeset nvidia_uvm nvidia_drm)/g' /etc/mkinitcpio.conf
mkinitcpio -P
sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="nvidia-drm.modeset=1 /g' /etc/default/grub
grub-mkconfig -o /boot/grub/grub.cfg
systemctl enable sddm
