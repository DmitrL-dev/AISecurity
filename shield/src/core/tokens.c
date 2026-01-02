/*
 * SENTINEL Shield - Token Counter Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#include "shield_tokens.h"

/* Approximate tokens per character for different tokenizers */
static const float TOKENS_PER_CHAR[] = {
    0.25f,   /* GPT-4: ~4 chars per token */
    0.25f,   /* Claude: similar to GPT-4 */
    0.25f,   /* Llama: similar */
    0.25f,   /* Mistral: similar */
    0.25f,   /* Gemini: similar */
    0.20f,   /* Simple word-based: ~5 chars per word */
};

/* Estimate tokens */
int estimate_tokens(const char *text, size_t len, tokenizer_type_t type)
{
    if (!text || len == 0) return 0;
    
    if (type > TOKENIZER_SIMPLE) {
        type = TOKENIZER_SIMPLE;
    }
    
    /* Base estimate from character count */
    int estimate = (int)(len * TOKENS_PER_CHAR[type]);
    
    /* Adjust for whitespace */
    int spaces = 0;
    int newlines = 0;
    int punctuation = 0;
    
    for (size_t i = 0; i < len; i++) {
        if (text[i] == ' ') spaces++;
        else if (text[i] == '\n') newlines++;
        else if (ispunct((unsigned char)text[i])) punctuation++;
    }
    
    /* Whitespace and punctuation often become separate tokens */
    estimate += newlines;  /* Newlines often 1 token each */
    
    /* Minimum 1 token */
    if (estimate < 1) estimate = 1;
    
    return estimate;
}

/* Initialize budget */
shield_err_t budget_init(token_budget_t *budget, int max_input, int max_output)
{
    if (!budget) return SHIELD_ERR_INVALID;
    
    memset(budget, 0, sizeof(*budget));
    budget->max_input = max_input;
    budget->max_output = max_output;
    budget->max_total = max_input + max_output;
    
    return SHIELD_OK;
}

/* Check input budget */
bool budget_check_input(token_budget_t *budget, int tokens)
{
    if (!budget) return false;
    return (budget->current_input + tokens) <= budget->max_input;
}

/* Check output budget */
bool budget_check_output(token_budget_t *budget, int tokens)
{
    if (!budget) return false;
    return (budget->current_output + tokens) <= budget->max_output;
}

/* Add to input */
void budget_add_input(token_budget_t *budget, int tokens)
{
    if (budget) {
        budget->current_input += tokens;
    }
}

/* Add to output */
void budget_add_output(token_budget_t *budget, int tokens)
{
    if (budget) {
        budget->current_output += tokens;
    }
}

/* Reset budget */
void budget_reset(token_budget_t *budget)
{
    if (budget) {
        budget->current_input = 0;
        budget->current_output = 0;
    }
}

/* Truncate to token limit */
char *truncate_to_tokens(const char *text, int max_tokens, tokenizer_type_t type)
{
    if (!text || max_tokens <= 0) return NULL;
    
    size_t len = strlen(text);
    int current_tokens = estimate_tokens(text, len, type);
    
    if (current_tokens <= max_tokens) {
        return strdup(text);
    }
    
    /* Binary search for correct length */
    size_t lo = 0;
    size_t hi = len;
    
    while (lo < hi) {
        size_t mid = (lo + hi + 1) / 2;
        int tokens = estimate_tokens(text, mid, type);
        
        if (tokens <= max_tokens) {
            lo = mid;
        } else {
            hi = mid - 1;
        }
    }
    
    /* Truncate at word boundary if possible */
    while (lo > 0 && !isspace((unsigned char)text[lo])) {
        lo--;
    }
    
    if (lo == 0) {
        lo = (size_t)(max_tokens / TOKENS_PER_CHAR[type]);
    }
    
    char *result = malloc(lo + 4);  /* +4 for "..." */
    if (!result) return NULL;
    
    memcpy(result, text, lo);
    strcpy(result + lo, "...");
    
    return result;
}
