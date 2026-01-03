#!/bin/sh
# IMMUNE DragonFlyBSD Setup Script

echo "=== IMMUNE Setup ==="

# Enable SSH password auth
echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config
echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config
service sshd restart

# Get kernel sources (minimal)
echo "Downloading kernel sources..."
cd /usr
fetch https://gitweb.dragonflybsd.org/dragonfly.git/snapshot/HEAD.tar.gz
tar -xzf HEAD.tar.gz
mv dragonfly-HEAD src

# Build immune module
echo "Building IMMUNE..."
cd /root/immune/agent/kmod
make

echo "=== Done ==="
echo "Now run: kldload ./immune.ko"
