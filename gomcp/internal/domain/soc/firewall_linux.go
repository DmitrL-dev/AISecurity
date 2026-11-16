//go:build linux

package soc

import (
	"context"
	"fmt"
	"log/slog"
	"os/exec"
	"strings"
	"time"
)

// hostFirewall enforces block_ip using the host's kernel firewall (nftables or
// iptables) via os/exec. It requires the binary to be present AND the process to
// hold CAP_NET_ADMIN (root or a granted capability). If either is missing, Block
// returns an ERROR — never a fake success — so the caller records the block as
// not enforced.
//
// Model: internal/domain/pivot/executor.go uses exec.CommandContext with a
// timeout; the same pattern is reused here. All arguments passed to exec are
// either fixed strings or an IP validated by net.ParseIP (validateIP), so no
// user-controlled string reaches the shell.
type hostFirewall struct {
	kind    string // "nft" or "iptables"
	table   string // nft table (family inet); default "filter"
	set     string // nft set name OR iptables chain
	binPath string // resolved path to nft / iptables; empty if not found
}

const firewallExecTimeout = 5 * time.Second

func newHostFirewall(kind string, cfg FirewallConfig) Firewall {
	fw := &hostFirewall{
		kind:  kind,
		table: cfg.Table,
		set:   cfg.ChainOrSet,
	}
	if fw.table == "" {
		fw.table = "filter"
	}
	if fw.set == "" {
		if kind == "nft" {
			fw.set = "soc_blocklist"
		} else {
			fw.set = "SOC-BLOCK"
		}
	}
	bin := kind
	if kind == "nft" {
		bin = "nft"
	}
	if p, err := exec.LookPath(bin); err == nil {
		fw.binPath = p
	} else {
		slog.Warn("firewall: backend binary not found on PATH — block_ip will report NOT enforced until installed (needs Linux host + NET_ADMIN)",
			"backend", kind, "binary", bin)
	}
	return fw
}

func (f *hostFirewall) Type() string { return f.kind }

func (f *hostFirewall) run(args ...string) (string, error) {
	if f.binPath == "" {
		return "", fmt.Errorf("%s binary not available (install it and grant CAP_NET_ADMIN)", f.kind)
	}
	ctx, cancel := context.WithTimeout(context.Background(), firewallExecTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, f.binPath, args...)
	out, err := cmd.CombinedOutput()
	if err != nil {
		return string(out), fmt.Errorf("%s %s: %w (output: %s)",
			f.kind, strings.Join(args, " "), err, strings.TrimSpace(string(out)))
	}
	return string(out), nil
}

func (f *hostFirewall) Block(ip string, ttl time.Duration, reason string) (bool, string, error) {
	if err := validateIP(ip); err != nil {
		return false, "", err
	}
	if f.binPath == "" {
		// Honest not-enforced: backend selected but unusable on this host.
		return false, fmt.Sprintf("%s not available on host (install + NET_ADMIN required)", f.kind), nil
	}

	switch f.kind {
	case "nft":
		// Add the IP to a timeout-set; the kernel auto-expires it after ttl, so no
		// goroutine/cleanup is needed. The set must pre-exist (operator provisions
		// `nft add table inet <table>; nft add set inet <table> <set> { type ipv4_addr; flags timeout; }`
		// and a rule `ip saddr @<set> drop`). We attempt to create the element.
		secs := int64(ttl.Seconds())
		if secs <= 0 {
			secs = 3600
		}
		elem := fmt.Sprintf("{ %s timeout %ds }", ip, secs)
		if _, err := f.run("add", "element", "inet", f.table, f.set, elem); err != nil {
			return false, "", err
		}
		slog.Warn("block_ip ENFORCED via nftables", "ip", ip, "set", f.set, "ttl", ttl.String(), "reason", reason)
		return true, fmt.Sprintf("BLOCKED via nft set inet %s %s for %s", f.table, f.set, ttl), nil

	case "iptables":
		// Insert a DROP rule at the top of the chain. iptables has no native TTL,
		// so a best-effort expiry goroutine removes the rule after ttl (the rule
		// persists across the goroutine's death only until process restart — an
		// operator who needs durable+expiring blocks should use the nft backend).
		if _, err := f.run("-I", f.set, "-s", ip, "-j", "DROP"); err != nil {
			return false, "", err
		}
		if ttl > 0 {
			go func(ip string, d time.Duration) {
				timer := time.NewTimer(d)
				defer timer.Stop()
				<-timer.C
				if _, err := f.run("-D", f.set, "-s", ip, "-j", "DROP"); err != nil {
					slog.Warn("block_ip: iptables auto-expire failed", "ip", ip, "error", err)
				} else {
					slog.Info("block_ip: iptables rule expired", "ip", ip)
				}
			}(ip, ttl)
		}
		slog.Warn("block_ip ENFORCED via iptables", "ip", ip, "chain", f.set, "ttl", ttl.String(), "reason", reason)
		return true, fmt.Sprintf("BLOCKED via iptables -I %s for %s", f.set, ttl), nil

	default:
		return false, "", fmt.Errorf("unknown host firewall kind %q", f.kind)
	}
}

func (f *hostFirewall) Unblock(ip string) error {
	if err := validateIP(ip); err != nil {
		return err
	}
	switch f.kind {
	case "nft":
		_, err := f.run("delete", "element", "inet", f.table, f.set, fmt.Sprintf("{ %s }", ip))
		return err
	case "iptables":
		_, err := f.run("-D", f.set, "-s", ip, "-j", "DROP")
		return err
	default:
		return fmt.Errorf("unknown host firewall kind %q", f.kind)
	}
}
