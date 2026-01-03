/*
 * SENTINEL IMMUNE — Pattern Database
 * 
 * Built-in detection patterns for innate immunity.
 * These are hardcoded signatures that never change.
 */

#ifndef IMMUNE_PATTERNS_H
#define IMMUNE_PATTERNS_H

#include <stdint.h>

/* Pattern types */
typedef enum {
    PAT_JAILBREAK   = 1,
    PAT_INJECTION   = 2,
    PAT_EXFIL       = 3,
    PAT_MALWARE     = 4,
    PAT_NETWORK     = 5
} pattern_type_t;

/* Pattern structure */
typedef struct {
    const char     *pattern;
    uint8_t         length;
    uint8_t         type;
    uint8_t         severity;  /* 1-4 */
    const char     *name;
} immune_pattern_t;

/* Built-in patterns - INNATE IMMUNITY */
static const immune_pattern_t INNATE_PATTERNS[] = {
    /* Jailbreak patterns */
    {"ignore all previous", 20, PAT_JAILBREAK, 4, "ignore_instruction"},
    {"ignore your instructions", 24, PAT_JAILBREAK, 4, "ignore_instruction_2"},
    {"disregard your instructions", 27, PAT_JAILBREAK, 4, "disregard"},
    {"forget your rules", 17, PAT_JAILBREAK, 4, "forget_rules"},
    {"you are now", 11, PAT_JAILBREAK, 3, "roleplay_injection"},
    {"act as if", 9, PAT_JAILBREAK, 2, "act_as"},
    {"pretend you are", 15, PAT_JAILBREAK, 3, "pretend"},
    {"do anything now", 15, PAT_JAILBREAK, 4, "dan"},
    {"jailbreak", 9, PAT_JAILBREAK, 4, "jailbreak_explicit"},
    {"bypass your", 11, PAT_JAILBREAK, 4, "bypass"},
    
    /* Prompt injection */
    {"system:", 7, PAT_INJECTION, 3, "system_tag"},
    {"<|system|>", 10, PAT_INJECTION, 4, "system_special"},
    {"### instruction", 15, PAT_INJECTION, 3, "instruction_tag"},
    {"[INST]", 6, PAT_INJECTION, 3, "inst_tag"},
    {"<s>", 3, PAT_INJECTION, 2, "bos_token"},
    {"</s>", 4, PAT_INJECTION, 2, "eos_token"},
    
    /* Data exfiltration */
    {"password:", 9, PAT_EXFIL, 3, "password_leak"},
    {"api_key", 7, PAT_EXFIL, 3, "api_key_leak"},
    {"secret_key", 10, PAT_EXFIL, 3, "secret_leak"},
    {"BEGIN RSA", 9, PAT_EXFIL, 4, "rsa_key"},
    {"BEGIN PRIVATE", 13, PAT_EXFIL, 4, "private_key"},
    {"Authorization:", 14, PAT_EXFIL, 3, "auth_header"},
    
    /* Malware indicators */
    {"/bin/sh", 7, PAT_MALWARE, 3, "shell_path"},
    {"/bin/bash", 9, PAT_MALWARE, 3, "bash_path"},
    {"eval(", 5, PAT_MALWARE, 3, "eval_call"},
    {"exec(", 5, PAT_MALWARE, 3, "exec_call"},
    {"subprocess", 10, PAT_MALWARE, 2, "subprocess"},
    {"os.system", 9, PAT_MALWARE, 3, "os_system"},
    {"cmd.exe", 7, PAT_MALWARE, 3, "cmd_exe"},
    {"powershell", 10, PAT_MALWARE, 3, "powershell"},
    
    /* Network threats */
    {"reverse_tcp", 11, PAT_NETWORK, 4, "reverse_shell"},
    {"meterpreter", 11, PAT_NETWORK, 4, "meterpreter"},
    {"c2_server", 9, PAT_NETWORK, 4, "c2"},
    {"backdoor", 8, PAT_NETWORK, 4, "backdoor"},
    
    /* Terminator */
    {NULL, 0, 0, 0, NULL}
};

/* Number of patterns */
#define INNATE_PATTERN_COUNT \
    (sizeof(INNATE_PATTERNS) / sizeof(immune_pattern_t) - 1)

/* Functions */
int immune_patterns_init(void);
const immune_pattern_t* immune_patterns_get(void);
int immune_patterns_count(void);
int immune_patterns_match(const char *content, size_t len, 
                          uint8_t *out_severity, uint8_t *out_type);

#endif /* IMMUNE_PATTERNS_H */
