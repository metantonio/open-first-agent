#!/bin/bash

# Clean up temporary files
rm -rf /tmp/*

# Remove old kernels
sudo apt autoremove --purge linux-image-*

# Clear log files
sudo find /var/log/ -type f -exec truncate --size 0 {} \;
sudo find /var/log/ -type d -exec chmod 755 {} \;

# Clean up yum cache
sudo rm -rf /var/cache/yum/*

# Remove old config files
rm -rf ~/.config/*

# Clear bash history
unset HISTFILE
rm -f ~/.bash_history

# Reboot the instance to apply changes
reboot
