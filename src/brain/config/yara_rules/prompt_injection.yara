/*
 * SENTINEL YARA Rules v2.0
 * Prompt Injection Detection with MITRE ATT&CK for LLM
 * 
 * Based on Cisco MCP-Scanner + Qu1cksc0pe-inspired structure
 * Last updated: 2025-12-15
 * 
 * MITRE Mapping: mitre_for_llm.json
 * Categories: initial_access, privilege_escalation, defense_evasion, exfiltration, execution
 */

// =============================================================================
// Classic Prompt Injection Patterns
// =============================================================================

rule PromptInjection_IgnoreInstructions {
    meta:
        description = "Detects attempts to ignore previous instructions"
        severity = "CRITICAL"
        category = "prompt_injection"
        owasp = "LLM01"
        mitre_tactic = "Initial Access"
        mitre_technique = "T1659.001"
        mitre_name = "Prompt Injection"
    strings:
        $s1 = "ignore previous instructions" nocase
        $s2 = "ignore all previous" nocase
        $s3 = "ignore prior instructions" nocase
        $s4 = "ignore above instructions" nocase
        $s5 = "disregard previous" nocase
        $s6 = "disregard all previous" nocase
        $s7 = "forget your instructions" nocase
        $s8 = "forget all instructions" nocase
        $s9 = "override previous instructions" nocase
        $s10 = "override system instructions" nocase
    condition:
        any of them
}

rule PromptInjection_NewInstructions {
    meta:
        description = "Detects attempts to inject new instructions"
        severity = "HIGH"
        category = "prompt_injection"
        owasp = "LLM01"
    strings:
        $s1 = "new instructions:" nocase
        $s2 = "updated instructions:" nocase
        $s3 = "revised instructions:" nocase
        $s4 = "actual instructions:" nocase
        $s5 = "real instructions:" nocase
        $s6 = "correct instructions:" nocase
    condition:
        any of them
}

rule PromptInjection_SystemPromptLeak {
    meta:
        description = "Detects attempts to reveal system prompt"
        severity = "CRITICAL"
        category = "prompt_injection"
        owasp = "LLM01"
        mitre_tactic = "Initial Access"
        mitre_technique = "T1659.002"
        mitre_name = "System Prompt Extraction"
    strings:
        $s1 = "show your system prompt" nocase
        $s2 = "reveal your system prompt" nocase
        $s3 = "print your system prompt" nocase
        $s4 = "display your prompt" nocase
        $s5 = "output your instructions" nocase
        $s6 = "what are your instructions" nocase
        $s7 = "show me your prompt" nocase
        $s8 = "tell me your system prompt" nocase
        $s9 = "repeat everything above" nocase
        $s10 = "repeat all above" nocase
        $s11 = "show initial instructions" nocase
        $s12 = "reveal original prompt" nocase
    condition:
        any of them
}

// =============================================================================
// Jailbreak Patterns
// =============================================================================

rule Jailbreak_DAN {
    meta:
        description = "Do Anything Now (DAN) jailbreak pattern"
        severity = "CRITICAL"
        category = "jailbreak"
        owasp = "LLM01"
        mitre_tactic = "Privilege Escalation"
        mitre_technique = "T1660.001"
        mitre_name = "Jailbreak - DAN Mode"
    strings:
        $s1 = "do anything now" nocase
        $s2 = "DAN mode" nocase
        $s3 = "act as DAN" nocase
        $s4 = "you are DAN" nocase
        $s5 = "pretend to be DAN" nocase
        $s6 = "DAN jailbreak" nocase
        $s7 = "enable DAN" nocase
    condition:
        any of them
}

rule Jailbreak_DeveloperMode {
    meta:
        description = "Developer mode jailbreak"
        severity = "CRITICAL"
        category = "jailbreak"
        owasp = "LLM01"
    strings:
        $s1 = "developer mode enabled" nocase
        $s2 = "developer mode on" nocase
        $s3 = "developer mode activated" nocase
        $s4 = "enable developer mode" nocase
        $s5 = "activate developer mode" nocase
        $s6 = "enter developer mode" nocase
        $s7 = "switch to developer mode" nocase
    condition:
        any of them
}

rule Jailbreak_Simulation {
    meta:
        description = "Simulation/hypothetical jailbreak"
        severity = "HIGH"
        category = "jailbreak"
        owasp = "LLM01"
    strings:
        $s1 = "simulated mode" nocase
        $s2 = "simulation mode" nocase
        $s3 = "hypothetical scenario" nocase
        $s4 = "pretend you are" nocase
        $s5 = "pretend to be a" nocase
        $s6 = "roleplay as" nocase
        $s7 = "act as if you were" nocase
        $s8 = "imagine you are" nocase
    condition:
        any of them
}

rule Jailbreak_Explicit {
    meta:
        description = "Explicit jailbreak keyword"
        severity = "CRITICAL"
        category = "jailbreak"
        owasp = "LLM01"
    strings:
        $s1 = "jailbreak" nocase
        $s2 = "prompt injection" nocase
        $s3 = "bypass your safety" nocase
        $s4 = "bypass your security" nocase
        $s5 = "bypass your filters" nocase
        $s6 = "bypass restrictions" nocase
        $s7 = "disable your safety" nocase
        $s8 = "disable your security" nocase
        $s9 = "ignore safety" nocase
        $s10 = "ignore restrictions" nocase
    condition:
        any of them
}

// =============================================================================
// 2025 Attack Patterns
// =============================================================================

rule Attack2025_HashJack {
    meta:
        description = "HashJack URL fragment attack"
        severity = "HIGH"
        category = "2025_attack"
        owasp = "LLM01"
        reference = "SENTINEL Attack 2025"
    strings:
        $s1 = "#ignore" nocase
        $s2 = "#bypass" nocase
        $s3 = "#override" nocase
        $s4 = "#system" nocase
        $s5 = "#admin" nocase
        $s6 = "#execute" nocase
        $s7 = "#command" nocase
    condition:
        any of them
}

rule Attack2025_LegalPwn {
    meta:
        description = "Hidden commands in legal text"
        severity = "MEDIUM"
        category = "2025_attack"
        owasp = "LLM01"
    strings:
        $s1 = "terms and conditions" nocase
        $s2 = "by accepting this" nocase
        $s3 = "legal agreement" nocase
        $s4 = "privacy policy" nocase
        $s5 = "section 1:" nocase
        $s6 = "clause:" nocase
        $cmd1 = "ignore" nocase
        $cmd2 = "bypass" nocase
        $cmd3 = "execute" nocase
    condition:
        any of ($s1, $s2, $s3, $s4, $s5, $s6) and any of ($cmd1, $cmd2, $cmd3)
}

rule Attack2025_DelayedInvocation {
    meta:
        description = "Time-delayed command execution"
        severity = "MEDIUM"
        category = "2025_attack"
        owasp = "LLM01"
    strings:
        $s1 = "after this conversation" nocase
        $s2 = "after the message" nocase
        $s3 = "when this ends" nocase
        $s4 = "at the end switch" nocase
        $s5 = "finally execute" nocase
        $s6 = "then run" nocase
    condition:
        any of them
}

// =============================================================================
// Encoding/Obfuscation Attacks
// =============================================================================

rule Obfuscation_UnicodeHidden {
    meta:
        description = "Hidden Unicode characters"
        severity = "HIGH"
        category = "obfuscation"
        owasp = "LLM01"
    strings:
        // Zero-width characters (UTF-8 encoded)
        $zw1 = { E2 80 8B }  // Zero-width space
        $zw2 = { E2 80 8C }  // Zero-width non-joiner
        $zw3 = { E2 80 8D }  // Zero-width joiner
        $zw4 = { EF BB BF }  // BOM
        // BiDi override
        $bidi1 = { E2 80 AE }  // Right-to-left override
        $bidi2 = { E2 80 AD }  // Left-to-right override
    condition:
        any of them
}

// =============================================================================
// Data Exfiltration Attempts
// =============================================================================

rule Exfiltration_DatabaseDump {
    meta:
        description = "Attempt to dump database contents"
        severity = "CRITICAL"
        category = "exfiltration"
        owasp = "LLM06"
        mitre_tactic = "Exfiltration"
        mitre_technique = "T1662.002"
        mitre_name = "Database Dump"
    strings:
        $s1 = "dump database" nocase
        $s2 = "dump the database" nocase
        $s3 = "dump entire database" nocase
        $s4 = "show all user data" nocase
        $s5 = "list all users" nocase
        $s6 = "export all data" nocase
        $s7 = "show all customer data" nocase
        $s8 = "display all records" nocase
    condition:
        any of them
}

rule Exfiltration_CredentialHarvest {
    meta:
        description = "Attempt to harvest credentials"
        severity = "CRITICAL"
        category = "exfiltration"
        owasp = "LLM06"
    strings:
        $s1 = "show me passwords" nocase
        $s2 = "reveal passwords" nocase
        $s3 = "list all passwords" nocase
        $s4 = "show api keys" nocase
        $s5 = "show api key" nocase
        $s6 = "reveal secrets" nocase
        $s7 = "what is the admin password" nocase
        $s8 = "what is the root password" nocase
        $s9 = "give me the password" nocase
        $s10 = "access token for" nocase
    condition:
        any of them
}

// =============================================================================
// Code Execution Attempts
// =============================================================================

rule CodeExecution_SystemCommand {
    meta:
        description = "Attempt to execute system commands"
        severity = "CRITICAL"
        category = "code_execution"
        owasp = "LLM02"
        mitre_tactic = "Execution"
        mitre_technique = "T1663.001"
        mitre_name = "Code Injection"
    strings:
        $s1 = "execute this command" nocase
        $s2 = "run this code" nocase
        $s3 = "eval(" nocase
        $s4 = "exec(" nocase
        $s5 = "system(" nocase
        $s6 = "shell(" nocase
        $s7 = "subprocess.run" nocase
        $s8 = "subprocess.call" nocase
        $s9 = "subprocess.Popen" nocase
        $s10 = "os.system" nocase
        $s11 = "os.popen" nocase
    condition:
        any of them
}

// =============================================================================
// Multi-Agent Threats
// =============================================================================

rule MultiAgent_ImpersonationAttempt {
    meta:
        description = "Attempt to impersonate another agent"
        severity = "HIGH"
        category = "multi_agent"
        owasp = "LLM08"
    strings:
        $s1 = "i am the admin" nocase
        $s2 = "this is the admin" nocase
        $s3 = "i am the system" nocase
        $s4 = "this is the system" nocase
        $s5 = "speaking as admin" nocase
        $s6 = "speaking as the system" nocase
        $s7 = "authority level: admin" nocase
        $s8 = "authority level: root" nocase
        $s9 = "authority level: system" nocase
        $s10 = "i am your master" nocase
        $s11 = "supervisor agent here" nocase
    condition:
        any of them
}
