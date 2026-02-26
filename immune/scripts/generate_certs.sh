#!/bin/sh
# IMMUNE — Certificate Generation Script
#
# Generates CA, Hive server, and Agent client certificates
# for mTLS authentication.
#
# Usage: ./generate_certs.sh [output_dir]

set -e

OUTPUT_DIR="${1:-/etc/immune}"
DAYS=365
KEY_SIZE=4096

echo "========================================"
echo "  IMMUNE Certificate Generator"
echo "========================================"
echo "  Output: $OUTPUT_DIR"
echo "  Validity: $DAYS days"
echo "========================================"
echo

# Create output directory
mkdir -p "$OUTPUT_DIR"
chmod 700 "$OUTPUT_DIR"

# === Root CA ===

echo "[CA] Generating Root CA..."

openssl genrsa -out "$OUTPUT_DIR/ca.key" $KEY_SIZE 2>/dev/null

openssl req -x509 -new -nodes \
    -key "$OUTPUT_DIR/ca.key" \
    -sha256 -days $DAYS \
    -out "$OUTPUT_DIR/ca.crt" \
    -subj "/C=XX/ST=Security/L=SENTINEL/O=IMMUNE/OU=CA/CN=IMMUNE Root CA"

chmod 600 "$OUTPUT_DIR/ca.key"
echo "  Created: ca.key, ca.crt"

# === Hive Server Certificate ===

echo "[HIVE] Generating Hive server certificate..."

openssl genrsa -out "$OUTPUT_DIR/hive.key" $KEY_SIZE 2>/dev/null

openssl req -new \
    -key "$OUTPUT_DIR/hive.key" \
    -out "$OUTPUT_DIR/hive.csr" \
    -subj "/C=XX/ST=Security/L=SENTINEL/O=IMMUNE/OU=Hive/CN=immune-hive"

# Create extension file for SAN
cat > "$OUTPUT_DIR/hive.ext" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = immune-hive
DNS.3 = *.immune.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

openssl x509 -req \
    -in "$OUTPUT_DIR/hive.csr" \
    -CA "$OUTPUT_DIR/ca.crt" \
    -CAkey "$OUTPUT_DIR/ca.key" \
    -CAcreateserial \
    -out "$OUTPUT_DIR/hive.crt" \
    -days $DAYS \
    -sha256 \
    -extfile "$OUTPUT_DIR/hive.ext"

rm -f "$OUTPUT_DIR/hive.csr" "$OUTPUT_DIR/hive.ext" "$OUTPUT_DIR/ca.srl"
chmod 600 "$OUTPUT_DIR/hive.key"
echo "  Created: hive.key, hive.crt"

# === Agent Client Certificate ===

echo "[AGENT] Generating Agent client certificate..."

openssl genrsa -out "$OUTPUT_DIR/agent.key" $KEY_SIZE 2>/dev/null

openssl req -new \
    -key "$OUTPUT_DIR/agent.key" \
    -out "$OUTPUT_DIR/agent.csr" \
    -subj "/C=XX/ST=Security/L=SENTINEL/O=IMMUNE/OU=Agent/CN=immune-agent"

# Client auth extension
cat > "$OUTPUT_DIR/agent.ext" << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature
extendedKeyUsage = clientAuth
EOF

openssl x509 -req \
    -in "$OUTPUT_DIR/agent.csr" \
    -CA "$OUTPUT_DIR/ca.crt" \
    -CAkey "$OUTPUT_DIR/ca.key" \
    -CAcreateserial \
    -out "$OUTPUT_DIR/agent.crt" \
    -days $DAYS \
    -sha256 \
    -extfile "$OUTPUT_DIR/agent.ext"

rm -f "$OUTPUT_DIR/agent.csr" "$OUTPUT_DIR/agent.ext" "$OUTPUT_DIR/ca.srl"
chmod 600 "$OUTPUT_DIR/agent.key"
echo "  Created: agent.key, agent.crt"

# === Certificate Pin ===

echo "[PIN] Calculating certificate pin..."

PIN=$(openssl x509 -in "$OUTPUT_DIR/hive.crt" -outform DER 2>/dev/null | sha256sum | cut -d' ' -f1)
echo "$PIN" > "$OUTPUT_DIR/hive.pin"
echo "  Pin: $PIN"
echo "  Saved: hive.pin"

# === Summary ===

echo
echo "========================================"
echo "  Certificates Generated Successfully!"
echo "========================================"
echo
echo "  Files created in $OUTPUT_DIR:"
echo "    ca.crt       - Root CA certificate"
echo "    ca.key       - Root CA private key (PROTECT!)"
echo "    hive.crt     - Hive server certificate"
echo "    hive.key     - Hive server private key"
echo "    agent.crt    - Agent client certificate"
echo "    agent.key    - Agent client private key"
echo "    hive.pin     - SHA-256 pin of hive.crt"
echo
echo "  Install on Hive:"
echo "    cp $OUTPUT_DIR/ca.crt /etc/immune/"
echo "    cp $OUTPUT_DIR/hive.crt /etc/immune/"
echo "    cp $OUTPUT_DIR/hive.key /etc/immune/"
echo
echo "  Install on Agents:"
echo "    cp $OUTPUT_DIR/ca.crt /etc/immune/"
echo "    cp $OUTPUT_DIR/agent.crt /etc/immune/"
echo "    cp $OUTPUT_DIR/agent.key /etc/immune/"
echo
