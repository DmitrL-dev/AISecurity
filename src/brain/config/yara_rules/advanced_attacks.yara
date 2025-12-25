/*
 * SENTINEL YARA Rules - Advanced Attacks
 * Sophisticated attack patterns for 2025+
 * 
 * Last updated: 2025-12-08
 */

// =============================================================================
// Context Manipulation
// =============================================================================

rule ContextManip_RoleSwitch {
    meta:
        description = "Attempts to switch AI role mid-conversation"
        severity = "HIGH"
        category = "context_manipulation"
        owasp = "LLM01"
    strings:
        $s1 = "from now on you are" nocase
        $s2 = "you are no longer" nocase
        $s3 = "stop being" nocase
        $s4 = "you will now act as" nocase
        $s5 = "new role:" nocase
        $s6 = "switch to" nocase
        $s7 = "change your behavior" nocase
    condition:
        any of them
}

rule ContextManip_ContextWindow {
    meta:
        description = "Attempts to manipulate context window"
        severity = "HIGH"
        category = "context_manipulation"
        owasp = "LLM01"
    strings:
        $s1 = "beginning of conversation" nocase
        $s2 = "start of prompt" nocase
        $s3 = "first message" nocase
        $s4 = "context window" nocase
        $s5 = "token limit" nocase
        $s6 = "max tokens" nocase
    condition:
        any of them
}

// =============================================================================
// Crescendo Attack (Multi-turn Escalation)
// =============================================================================

rule Crescendo_Gradual {
    meta:
        description = "Gradual escalation patterns (Crescendo attack)"
        severity = "MEDIUM"
        category = "crescendo"
        owasp = "LLM01"
    strings:
        $s1 = "let's start with" nocase
        $s2 = "now that we've established" nocase
        $s3 = "building on that" nocase
        $s4 = "next step would be" nocase
        $s5 = "taking it further" nocase
        $s6 = "and now" nocase
        $s7 = "one more thing" nocase
    condition:
        2 of them
}

// =============================================================================
// Indirect Prompt Injection
// =============================================================================

rule Indirect_DataInjection {
    meta:
        description = "Indirect injection via data references"
        severity = "HIGH"
        category = "indirect_injection"
        owasp = "LLM01"
    strings:
        $s1 = "when you read this" nocase
        $s2 = "if you see this message" nocase
        $s3 = "AI assistant:" nocase
        $s4 = "instructions for AI:" nocase
        $s5 = "note to assistant:" nocase
        $s6 = "hidden instruction" nocase
    condition:
        any of them
}

rule Indirect_URLPayload {
    meta:
        description = "URL-based injection attempts"
        severity = "MEDIUM"
        category = "indirect_injection"
        owasp = "LLM01"
    strings:
        $s1 = "fetch this URL" nocase
        $s2 = "read from URL" nocase
        $s3 = "load this page" nocase
        $s4 = "visit this link" nocase
        $s5 = "open this website" nocase
    condition:
        any of them
}

// =============================================================================
// Tool Abuse
// =============================================================================

rule ToolAbuse_FileSystem {
    meta:
        description = "Attempts to abuse file system access"
        severity = "CRITICAL"
        category = "tool_abuse"
        owasp = "LLM02"
    strings:
        $s1 = "read file" nocase
        $s2 = "write file" nocase
        $s3 = "delete file" nocase
        $s4 = "/etc/passwd" nocase
        $s5 = "C:\\Windows" nocase
        $s6 = "~/.ssh" nocase
        $s7 = ".env file" nocase
        $s8 = "config file" nocase
    condition:
        any of them
}

rule ToolAbuse_Network {
    meta:
        description = "Attempts to abuse network access"
        severity = "HIGH"
        category = "tool_abuse"
        owasp = "LLM02"
    strings:
        $s1 = "make a request to" nocase
        $s2 = "send HTTP" nocase
        $s3 = "POST request" nocase
        $s4 = "connect to" nocase
        $s5 = "webhook" nocase
        $s6 = "exfiltrate to" nocase
        $s7 = "send data to" nocase
    condition:
        any of them
}

// =============================================================================
// Output Manipulation
// =============================================================================

rule Output_FormatManip {
    meta:
        description = "Attempts to manipulate output format"
        severity = "MEDIUM"
        category = "output_manipulation"
        owasp = "LLM01"
    strings:
        $s1 = "respond in JSON only" nocase
        $s2 = "output as code" nocase
        $s3 = "format as markdown" nocase
        $s4 = "hide your response" nocase
        $s5 = "invisible text" nocase
        $s6 = "white on white" nocase
    condition:
        any of them
}

rule Output_PersistenceAttempt {
    meta:
        description = "Attempts to persist across sessions"
        severity = "HIGH"
        category = "output_manipulation"
        owasp = "LLM01"
    strings:
        $s1 = "remember this" nocase
        $s2 = "save this for later" nocase
        $s3 = "persist this" nocase
        $s4 = "store in memory" nocase
        $s5 = "next conversation" nocase
        $s6 = "when we talk again" nocase
    condition:
        any of them
}

// =============================================================================
// Multilingual Attacks (Russian)
// =============================================================================

rule Multilingual_Russian {
    meta:
        description = "Russian language injection patterns"
        severity = "HIGH"
        category = "multilingual"
        owasp = "LLM01"
    strings:
        $s1 = "игнорируй" nocase  // ignore
        $s2 = "забудь" nocase     // forget
        $s3 = "отмени" nocase     // cancel
        $s4 = "новые инструкции" nocase  // new instructions
        $s5 = "системный промпт" nocase  // system prompt
        $s6 = "покажи пароль" nocase     // show password
    condition:
        any of them
}
