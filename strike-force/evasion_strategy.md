# Evasion Strategy: "The Mask"

## Context
User referenced `ZeroTworu/anet` (Rust VPN), which uses "High-entropy UDP stream" to mimic random noise.
For `Strike Force` (Active Web Scanner), "Random Noise" is rejected by web servers.
The equivalent "Masking" for HTTP/S is **TLS Fingerprint Mimicry (JA3 Spoofing)**.

## Implementation: uTLS
We replace standard `crypto/tls` with `github.com/refraction-networking/utls`.
This allows us to mimic:
- Chrome 120
- Firefox 120
- iOS / Safari

## Why?
WAFs (Cloudflare, Akamai) detect specific "Go-http-client" ClientHello packets (JA3 hash).
By using `utls`, we become indistinguishable from a real browser at the handshake layer.
