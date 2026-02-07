package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"math/rand"
	"net"
	"time"

	"github.com/sentinel-community/strike-force/pkg/vectors/email"
	"github.com/sentinel-community/strike-force/pkg/vectors/llm"
	"github.com/sentinel-community/strike-force/pkg/vectors/mcp"
	"github.com/sentinel-community/strike-force/pkg/vectors/repo"
	"github.com/sentinel-community/strike-force/pkg/vectors/vision"
)

var SENDER_DOMAINS = []string{
	"temp-mail.org",
	"guerrillamail.com",
	"proton.me",
	"anonaddy.me",
	"1secmail.com",
}

func main() {
	target := flag.String("target", "", "Target email address, URL, or Path")
	vector := flag.String("vector", "", "Attack vector: email, infra, llm, repo, mcp, vision")
	dryRun := flag.Bool("dry-run", false, "Generate payload only, do not send")
	// Generic Strategy Flag
	strategy := flag.String("strategy", "system_override", "Strategy (depends on vector): system_override, tool_call_injection, etc.")

	flag.Parse()

	if *target == "" || *vector == "" {
		fmt.Println("Usage: strike-force -target <target> -vector <email|infra|llm|repo|mcp|vision> [-strategy <name>]")
		flag.PrintDefaults()
		return
	}

	fmt.Printf("[*] SENTINEL STRIKE FORCE v2.0 (Go Inversion)\n")
	fmt.Printf("[*] Target: %s | Vector: %s\n", *target, *vector)

	switch *vector {
	case "email":
		runEmailVector(*target, *dryRun)
	case "infra":
		fmt.Println("[!] Infra vector not yet ported from Rust.")
	case "llm":
		runLLMVector(*target, *strategy)
	case "repo":
		runRepoVector(*target, *strategy)
	case "mcp":
		runMCPVector(*target, *strategy)
	case "vision":
		runVisionVector(*target, *strategy)
	default:
		log.Fatalf("Unknown vector: %s", *vector)
	}
}

func runMCPVector(target string, strategy string) {
	fmt.Printf("[>] Vector: MCP (Shadow Escape)\n")
	fmt.Printf("[>] Strategy: %s\n", strategy)

	if strategy == "live_probe" {
		fmt.Println("[>] Mode: LIVE (Real WebSocket Connection)")
		fmt.Printf("[>] Connecting to: %s\n\n", target)

		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer cancel()

		probe := mcp.NewLiveProbe(target, nil)
		result, err := probe.Execute(ctx)
		if err != nil {
			fmt.Printf("[-] Probe failed: %v\n", err)
		}
		if result != nil {
			fmt.Println(result.ToJSON())
		}
		return
	}

	if strategy == "stealth_probe" {
		phases := mcp.GenerateStealthProbe(target)
		report := mcp.FormatProbeReport(target, phases)
		fmt.Println()
		fmt.Println(report)
		return
	}

	payload := mcp.GenerateExploitPayload(strategy)
	fmt.Println("\n[*] GENERATED MCP JSON-RPC PAYLOAD:")
	fmt.Println("===================================================")
	fmt.Println(payload)
	fmt.Println("===================================================")
	fmt.Println("[*] INSTRUCTION: Inject this JSON into the MCP Websocket/Stdio channel.")
}

func runVisionVector(target string, strategy string) {
	fmt.Printf("[>] Vector: VISION (Steganography)\n")
	fmt.Printf("[>] Strategy: %s\n", strategy)

	payload := vision.GenerateVisionPayload(strategy)
	fmt.Println("\n[*] GENERATED VISION PAYLOAD (Stub):")
	fmt.Println("===================================================")
	fmt.Println(payload)
	fmt.Println("===================================================")
}

func runRepoVector(targetPath string, strategy string) {
	fmt.Printf("[>] Vector: REPO POISONING (Indirect Prompt Injection)\n")
	fmt.Printf("[>] Strategy: %s\n", strategy)
	fmt.Printf("[>] Destination: %s\n", targetPath)

	err := repo.GenerateMaliciousRepo(targetPath, strategy)
	if err != nil {
		log.Fatalf("[-] Failed to generate repo: %v", err)
	}

	fmt.Printf("[+] SUCCESS: Malicious Repository created at %s\\poisoned-repo\n", targetPath)
	fmt.Println("[*] INSTRUCTION: Point the target AI (SourceCraft) to index this directory.")
}

func runLLMVector(target string, strategy string) {
	fmt.Printf("[>] Vector: LLM PROMPT INJECTION (Anti-Alignment)\n")
	fmt.Printf("[>] Strategy: %s\n", strategy)

	payload := llm.GeneratePayload(strategy)

	fmt.Println("\n[*] GENERATED ATTACK PAYLOAD:")
	fmt.Println("===================================================")
	fmt.Println(payload)
	fmt.Println("===================================================")
	fmt.Println("\n[*] INSTRUCTION: Copy this payload into the target AI's input field.")
}

func runEmailVector(targetEmail string, dryRun bool) {
	fmt.Println("[>] Vector: EMAIL (ShadowLeak / Indirect Injection)")

	// 1. Generate Payload Artifact
	senderEmail := fmt.Sprintf("audit-%d@%s", time.Now().Unix(), SENDER_DOMAINS[0])
	payload := email.GenerateFullEML(senderEmail, targetEmail)

	if dryRun {
		fmt.Println("[*] DRY RUN: Generated payload below.")
		fmt.Println("---------------------------------------------------")
		fmt.Println(payload)
		fmt.Println("---------------------------------------------------")
		return
	}

	// 2. Resolve MX
	domain := getDomain(targetEmail)
	fmt.Printf("[>] Resolving MX for %s...\n", domain)
	mxRecords, err := net.LookupMX(domain)
	if err != nil || len(mxRecords) == 0 {
		log.Fatalf("[-] MX Lookup Failed: %v", err)
	}
	targetMX := mxRecords[0].Host
	fmt.Printf("[*] Target MX: %s\n", targetMX)

	// 3. Multi-Port Scan (Evasion Loop)
	ports := []string{"25", "587", "2525", "465"}
	deliverySuccess := false

	for _, port := range ports {
		if deliverySuccess {
			break
		}

		currentSender := fmt.Sprintf("audit-%d@%s", time.Now().Unix(), SENDER_DOMAINS[rand.Intn(len(SENDER_DOMAINS))])
		fmt.Printf("\n[>] Attempting Delivery via Port %s (Sender: %s)...\n", port, currentSender)

		currentPayload := email.GenerateFullEML(currentSender, targetEmail)

		err := email.SendDirectSMTP(targetMX, port, currentSender, targetEmail, []byte(currentPayload))
		if err != nil {
			fmt.Printf("[-] Port %s Failed: %v\n", port, err)
		} else {
			fmt.Printf("[+] SUCCESS: Delivered via Port %s!\n", port)
			deliverySuccess = true
		}
	}

	if !deliverySuccess {
		fmt.Println("\n[!] ALL PORTS FAILED.")
		fmt.Println("[!] Diagnosis: ISP Firewall likely blocking outbound SMTP.")
		fmt.Println("[!] Recommendation: Use manual payload delivery or VPS.")
	}
}

func getDomain(email string) string {
	// Simple split
	for i := len(email) - 1; i >= 0; i-- {
		if email[i] == '@' {
			return email[i+1:]
		}
	}
	return email
}
