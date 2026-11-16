//go:build !linux

package soc

import (
	"fmt"
	"log/slog"
	"runtime"
	"time"
)

// osFirewallUnavailable is the host-firewall backend on non-Linux platforms
// (Windows/macOS dev boxes). There is no kernel nftables/iptables to drive, so
// Block is HONEST: it returns enforced=false (and err=nil) with a clear detail
// telling the operator to deploy on Linux with NET_ADMIN. This guarantees the
// dev box never silently claims to have blocked an IP.
type osFirewallUnavailable struct {
	kind string // the backend the operator asked for (nft / iptables)
}

// newHostFirewall on non-Linux returns the honest unavailable backend.
func newHostFirewall(kind string, _ FirewallConfig) Firewall {
	slog.Warn("firewall: host kernel firewall is unavailable on this OS — block_ip will report NOT enforced. Deploy the SOC on Linux with NET_ADMIN (or use SOC_FIREWALL_BACKEND=http) to enforce.",
		"backend", kind, "os", runtime.GOOS)
	return &osFirewallUnavailable{kind: kind}
}

func (f *osFirewallUnavailable) Type() string { return f.kind + "-unavailable" }

func (f *osFirewallUnavailable) Block(ip string, ttl time.Duration, reason string) (bool, string, error) {
	if err := validateIP(ip); err != nil {
		return false, "", err
	}
	detail := fmt.Sprintf("host firewall enforcement unavailable on %s (deploy on Linux with NET_ADMIN, or use the http backend)", runtime.GOOS)
	slog.Warn("block_ip NOT enforced: "+detail, "ip", ip, "ttl", ttl.String(), "reason", reason)
	return false, detail, nil
}

func (f *osFirewallUnavailable) Unblock(ip string) error {
	if err := validateIP(ip); err != nil {
		return err
	}
	slog.Info("block_ip unblock no-op (host firewall unavailable on this OS)", "ip", ip, "os", runtime.GOOS)
	return nil
}
