#!/bin/sh
# IMMUNE Hive Download Script
# Run this on DragonFlyBSD to fetch all Hive files

HOST="http://192.168.56.1:8888"
BASE="/root/immune/hive"

echo "=== IMMUNE Hive Download ==="

# Create directories
mkdir -p $BASE/src $BASE/include $BASE/conf $BASE/bin $BASE/obj

cd $BASE

# Makefile
fetch $HOST/hive/Makefile

# Source files
cd $BASE/src
for f in main.c hive.c network.c api.c config.c herd.c alert.c scheduler.c crypto.c forensics.c quarantine.c response.c bridge.c deploy.c destruct.c discovery.c exploit.c hammer2.c hsm.c jail.c soc.c; do
    echo "Downloading $f..."
    fetch $HOST/hive/src/$f
done

# Headers
cd $BASE/include
for h in hive.h herd.h hammer2.h jail.h; do
    echo "Downloading $h..."
    fetch $HOST/hive/include/$h
done

# Config
cd $BASE/conf
fetch $HOST/hive/conf/hive.conf

# Install OpenSSL if needed
echo "Installing dependencies..."
pkg install -y openssl

# Build
echo "Building Hive..."
cd $BASE
make

echo ""
echo "=== Done ==="
echo "Run: ./bin/hived -d"
