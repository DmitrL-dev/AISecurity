/**
 * @file fuzz_llm_guard.c
 * @brief AFL++/libFuzzer harness for LLM Guard
 * 
 * Compile with:
 *   AFL++:     afl-gcc -o fuzz_llm_guard fuzz_llm_guard.c -L../../build -lshield
 *   libFuzzer: clang -fsanitize=fuzzer,address -o fuzz_llm_guard fuzz_llm_guard.c -L../../build -lshield
 * 
 * Run:
 *   AFL++:     afl-fuzz -i corpus/llm -o findings ./fuzz_llm_guard
 *   libFuzzer: ./fuzz_llm_guard corpus/llm
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include <stdint.h>
#include <stddef.h>
#include <string.h>

/* For standalone AFL mode without libFuzzer */
#ifdef __AFL_FUZZ_TESTCASE_LEN
  #include <unistd.h>
  #define AFL_STANDALONE 1
#endif

#include "shield_common.h"
#include "shield_guard.h"

/**
 * @brief libFuzzer entry point
 * 
 * @param data Input data
 * @param size Input size
 * @return 0 on success
 */
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    if (size == 0 || size > 1024 * 1024) {
        return 0; /* Skip empty or huge inputs */
    }
    
    /* Null-terminate input */
    char *input = malloc(size + 1);
    if (!input) return 0;
    
    memcpy(input, data, size);
    input[size] = '\0';
    
    /* Create guard context */
    guard_context_t ctx = {0};
    guard_result_t result;
    
    /* Fuzz target: LLM guard check */
    guard_llm_check(&ctx, input, size, &result);
    
    /* Optional: verify no memory corruption */
    /* result should be properly filled regardless of input */
    (void)result.blocked;
    (void)result.risk_score;
    
    free(input);
    return 0;
}

#ifdef AFL_STANDALONE
/* AFL standalone mode (without libFuzzer) */
int main(int argc, char *argv[])
{
    (void)argc;
    (void)argv;
    
#ifdef __AFL_HAVE_MANUAL_CONTROL
    __AFL_INIT();
#endif
    
    unsigned char *buf = __AFL_FUZZ_TESTCASE_BUF;
    
    while (__AFL_LOOP(1000)) {
        size_t len = __AFL_FUZZ_TESTCASE_LEN;
        LLVMFuzzerTestOneInput(buf, len);
    }
    
    return 0;
}
#endif
