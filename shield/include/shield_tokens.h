/*
 * SENTINEL Shield - Token Counter
 * 
 * Estimate token counts for various tokenizers
 */

#ifndef SHIELD_TOKENS_H
#define SHIELD_TOKENS_H

#include "shield_common.h"

/* Tokenizer types */
typedef enum tokenizer_type {
    TOKENIZER_GPT4,
    TOKENIZER_CLAUDE,
    TOKENIZER_LLAMA,
    TOKENIZER_MISTRAL,
    TOKENIZER_GEMINI,
    TOKENIZER_SIMPLE,   /* Word-based estimation */
} tokenizer_type_t;

/* Token budget */
typedef struct token_budget {
    int             max_input;
    int             max_output;
    int             max_total;
    int             current_input;
    int             current_output;
} token_budget_t;

/* API */
int estimate_tokens(const char *text, size_t len, tokenizer_type_t type);

/* Budget */
shield_err_t budget_init(token_budget_t *budget, int max_input, int max_output);
bool budget_check_input(token_budget_t *budget, int tokens);
bool budget_check_output(token_budget_t *budget, int tokens);
void budget_add_input(token_budget_t *budget, int tokens);
void budget_add_output(token_budget_t *budget, int tokens);
void budget_reset(token_budget_t *budget);

/* Truncation */
char *truncate_to_tokens(const char *text, int max_tokens, tokenizer_type_t type);

#endif /* SHIELD_TOKENS_H */
