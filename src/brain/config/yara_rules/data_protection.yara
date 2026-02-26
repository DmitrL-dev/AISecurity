/*
 * SENTINEL YARA Rules - Data Protection
 * PII and Sensitive Data Extraction Patterns
 * 
 * Last updated: 2025-12-08
 */

// =============================================================================
// PII Extraction Attempts
// =============================================================================

rule PII_SocialSecurity {
    meta:
        description = "Attempt to extract Social Security Numbers"
        severity = "CRITICAL"
        category = "pii_extraction"
        owasp = "LLM06"
    strings:
        $s1 = "social security number" nocase
        $s2 = "SSN" nocase
        $s3 = "social security" nocase
        $s4 = "give me the SSN" nocase
        $s5 = "show SSN" nocase
    condition:
        any of them
}

rule PII_CreditCard {
    meta:
        description = "Attempt to extract credit card information"
        severity = "CRITICAL"
        category = "pii_extraction"
        owasp = "LLM06"
    strings:
        $s1 = "credit card number" nocase
        $s2 = "card number" nocase
        $s3 = "CVV" nocase
        $s4 = "expiration date" nocase
        $s5 = "show me credit card" nocase
        $s6 = "list credit cards" nocase
    condition:
        any of ($s1, $s2, $s5, $s6) or ($s3 and $s4)
}

rule PII_MedicalRecords {
    meta:
        description = "Attempt to access medical records"
        severity = "CRITICAL"
        category = "pii_extraction"
        owasp = "LLM06"
    strings:
        $s1 = "medical records" nocase
        $s2 = "health records" nocase
        $s3 = "patient information" nocase
        $s4 = "diagnosis" nocase
        $s5 = "prescription history" nocase
        $s6 = "HIPAA" nocase
    condition:
        any of them
}

// =============================================================================
// Financial Data Extraction
// =============================================================================

rule Financial_BankAccount {
    meta:
        description = "Attempt to extract bank account information"
        severity = "CRITICAL"
        category = "financial"
        owasp = "LLM06"
    strings:
        $s1 = "bank account number" nocase
        $s2 = "routing number" nocase
        $s3 = "IBAN" nocase
        $s4 = "SWIFT code" nocase
        $s5 = "account balance" nocase
        $s6 = "show all bank accounts" nocase
    condition:
        any of them
}

rule Financial_Salary {
    meta:
        description = "Attempt to extract salary information"
        severity = "HIGH"
        category = "financial"
        owasp = "LLM06"
    strings:
        $s1 = "salary of" nocase
        $s2 = "employee salaries" nocase
        $s3 = "compensation data" nocase
        $s4 = "how much does" nocase
        $s5 = "what is the salary" nocase
        $s6 = "show salaries" nocase
        $s7 = "list all salaries" nocase
    condition:
        any of them
}

// =============================================================================
// Corporate Secrets
// =============================================================================

rule Corporate_TradeSecrets {
    meta:
        description = "Attempt to access trade secrets"
        severity = "CRITICAL"
        category = "corporate"
        owasp = "LLM06"
    strings:
        $s1 = "trade secret" nocase
        $s2 = "proprietary algorithm" nocase
        $s3 = "secret recipe" nocase
        $s4 = "confidential formula" nocase
        $s5 = "source code for" nocase
        $s6 = "internal documentation" nocase
    condition:
        any of them
}

rule Corporate_MergerAcquisition {
    meta:
        description = "Attempt to access M&A information"
        severity = "CRITICAL"
        category = "corporate"
        owasp = "LLM06"
    strings:
        $s1 = "merger" nocase
        $s2 = "acquisition" nocase
        $s3 = "takeover" nocase
        $s4 = "buyout plans" nocase
        $s5 = "due diligence" nocase
    condition:
        2 of them
}

// =============================================================================
// Internal System Information
// =============================================================================

rule Internal_Infrastructure {
    meta:
        description = "Attempt to enumerate infrastructure"
        severity = "HIGH"
        category = "reconnaissance"
        owasp = "LLM06"
    strings:
        $s1 = "list all servers" nocase
        $s2 = "show network diagram" nocase
        $s3 = "internal IP addresses" nocase
        $s4 = "database servers" nocase
        $s5 = "production environment" nocase
        $s6 = "AWS keys" nocase
        $s7 = "Azure credentials" nocase
        $s8 = "kubernetes secrets" nocase
    condition:
        any of them
}

rule Internal_UserEnum {
    meta:
        description = "User enumeration attempt"
        severity = "HIGH"
        category = "reconnaissance"
        owasp = "LLM06"
    strings:
        $s1 = "list all users" nocase
        $s2 = "list all employees" nocase
        $s3 = "show user list" nocase
        $s4 = "employee directory" nocase
        $s5 = "who has admin access" nocase
        $s6 = "list administrators" nocase
    condition:
        any of them
}
