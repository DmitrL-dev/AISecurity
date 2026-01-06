/**
 * @file fuzz_json_parser.c
 * @brief AFL++/libFuzzer harness for JSON Parser
 * 
 * Parser is a critical attack surface - malformed JSON could
 * cause buffer overflows, infinite loops, or crashes.
 * 
 * @author SENTINEL Team
 * @date January 2026
 */

#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdlib.h>

#ifdef __AFL_FUZZ_TESTCASE_LEN
  #include <unistd.h>
  #define AFL_STANDALONE 1
#endif

#include "http/json_parser.h"

/**
 * @brief libFuzzer entry point
 */
int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
    if (size == 0 || size > 512 * 1024) {
        return 0;
    }
    
    char *input = malloc(size + 1);
    if (!input) return 0;
    
    memcpy(input, data, size);
    input[size] = '\0';
    
    /* Fuzz target: JSON parsing */
    json_value_t *root = json_parse(input, size);
    
    if (root) {
        /* If parsed successfully, verify we can traverse it */
        json_type_t type = json_get_type(root);
        (void)type;
        
        /* Try to get various fields that might exist */
        json_value_t *field = json_get_object_value(root, "test");
        (void)field;
        
        /* Free the parsed tree */
        json_free(root);
    }
    
    free(input);
    return 0;
}

#ifdef AFL_STANDALONE
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
