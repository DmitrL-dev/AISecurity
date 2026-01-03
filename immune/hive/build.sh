#!/bin/sh
# IMMUNE Hive Build Script
# Works around BSD make tab issues

CC="cc"
CFLAGS="-Wall -Wextra -O2 -I./include -I/usr/local/include -pthread"
LDFLAGS="-L/usr/local/lib -lpthread -lssl -lcrypto"

echo "=== IMMUNE Hive Build ==="

mkdir -p bin obj

# Compile each file
for f in main hive network api config herd alert scheduler crypto forensics quarantine response bridge deploy destruct discovery exploit hammer2 hsm jail soc sentinel correlate playbook; do
    echo "Compiling $f.c..."
    $CC $CFLAGS -c src/$f.c -o obj/$f.o
    if [ $? -ne 0 ]; then
        echo "FAILED: $f.c"
        exit 1
    fi
done

# Link
echo "Linking..."
$CC $CFLAGS -o bin/hived obj/*.o $LDFLAGS

if [ $? -eq 0 ]; then
    echo ""
    echo "=== SUCCESS ==="
    echo "Binary: bin/hived"
    ls -la bin/hived
else
    echo "LINK FAILED"
    exit 1
fi
