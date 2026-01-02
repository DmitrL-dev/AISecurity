# SENTINEL Shield CMake Build
# Version 1.2.0 - Complete Build Configuration
cmake_minimum_required(VERSION 3.14)

project(sentinel-shield
    VERSION 1.2.0
    DESCRIPTION "SENTINEL Shield - Universal AI Security DMZ"
    LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Options
option(BUILD_SHARED_LIBS "Build shared library" ON)
option(BUILD_CLI "Build CLI executable" ON)
option(BUILD_TESTS "Build tests" ON)
option(BUILD_EXAMPLES "Build examples" ON)
option(BUILD_PYTHON "Build Python bindings" OFF)
option(USE_OPENSSL "Enable TLS support with OpenSSL" OFF)

# Compiler flags
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -Wextra")
    set(CMAKE_C_FLAGS_DEBUG "-g -O0 -DDEBUG")
    set(CMAKE_C_FLAGS_RELEASE "-O3 -DNDEBUG")
    
    # Linux-specific
    if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
        add_definitions(-DSHIELD_PLATFORM_LINUX)
    elseif(APPLE)
        add_definitions(-DSHIELD_PLATFORM_MACOS)
    endif()
elseif(MSVC)
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /W4")
    add_definitions(-D_CRT_SECURE_NO_WARNINGS -DSHIELD_PLATFORM_WINDOWS)
endif()

# OpenSSL
if(USE_OPENSSL)
    find_package(OpenSSL REQUIRED)
    add_definitions(-DSHIELD_USE_OPENSSL)
endif()

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/include)

# ===== Core Sources =====
set(SHIELD_CORE_SOURCES
    src/core/zone.c
    src/core/rule.c
    src/core/guard.c
    src/core/pattern.c
    src/core/config.c
    src/core/context.c
    src/core/ratelimit.c
    src/core/blocklist.c
    src/core/session.c
    src/core/canary.c
    src/core/quarantine.c
    src/core/alert.c
    src/core/metrics.c
    src/core/threadpool.c
    src/core/event.c
    src/core/audit.c
    src/core/health.c
    src/core/plugin.c
    src/core/ha.c
    src/core/tls.c
    src/core/sanitizer.c
    src/core/fingerprint.c
)

# ===== Analysis Sources (Sprint 9+) =====
set(SHIELD_ANALYSIS_SOURCES
    src/core/semantic.c
    src/core/encoding.c
    src/core/tokens.c
    src/core/output_filter.c
    src/core/context_window.c
    src/core/safety_prompt.c
    src/core/request_log.c
    src/core/anomaly.c
    src/core/signatures.c
    src/core/classifier.c
    src/core/embedding.c
    src/core/vectorizer.c
    src/core/ngram.c
    src/core/history.c
    src/core/stats.c
    src/core/report.c
    src/core/batch.c
    src/core/response_validator.c
    src/core/ebpf.c
    src/core/policy_engine.c
)

# ===== Guards =====
set(SHIELD_GUARD_SOURCES
    src/guards/llm_guard.c
    src/guards/rag_guard.c
    src/guards/tool_guard.c
    src/guards/agent_guard.c
    src/guards/mcp_guard.c
    src/guards/api_guard.c
)

# ===== Protocols (20 Total) =====
set(SHIELD_PROTOCOL_SOURCES
    # Discovery
    src/protocols/zdp.c
    src/protocols/zrp.c
    src/protocols/zhp.c
    # Traffic
    src/protocols/stp.c
    src/protocols/spp.c
    src/protocols/sqp.c
    src/protocols/srp.c
    # Analytics
    src/protocols/saf.c
    src/protocols/stt.c
    src/protocols/sem.c
    src/protocols/sla.c
    # HA
    src/protocols/shsp.c
    src/protocols/ssrp.c
    src/protocols/smrp.c
    # Integration
    src/protocols/sbp.c
    src/protocols/sgp.c
    src/protocols/siem.c
    # Security
    src/protocols/stls.c
    src/protocols/szaa.c
    src/protocols/ssigp.c
)

# ===== CLI (194 Commands) =====
set(SHIELD_CLI_SOURCES
    src/cli/cli.c
    src/cli/commands.c
    src/cli/commands_extended.c
    src/cli/interactive.c
    src/cli/cmd_show.c
    src/cli/cmd_config.c
    src/cli/cmd_debug.c
    src/cli/cmd_ha.c
    src/cli/cmd_zone_rule.c
    src/cli/cmd_guard.c
    src/cli/cmd_policy.c
)

# ===== API =====
set(SHIELD_API_SOURCES
    src/api/http_api.c
    src/api/handlers.c
)

# ===== Utilities =====
set(SHIELD_UTIL_SOURCES
    src/utils/common.c
    src/utils/platform.c
    src/utils/entropy.c
    src/utils/json.c
    src/utils/webhook.c
    src/utils/syslog.c
    src/utils/mempool.c
    src/utils/ringbuf.c
    src/utils/hashtable.c
    src/utils/string.c
    src/utils/base64.c
    src/utils/timer.c
    src/utils/circuit_breaker.c
    src/utils/retry.c
)

# ===== FFI =====
set(SHIELD_FFI_SOURCES
    src/ffi/ffi.c
)

# All sources
set(SHIELD_SOURCES
    ${SHIELD_CORE_SOURCES}
    ${SHIELD_ANALYSIS_SOURCES}
    ${SHIELD_GUARD_SOURCES}
    ${SHIELD_PROTOCOL_SOURCES}
    ${SHIELD_CLI_SOURCES}
    ${SHIELD_API_SOURCES}
    ${SHIELD_UTIL_SOURCES}
    ${SHIELD_FFI_SOURCES}
)

# Library
if(BUILD_SHARED_LIBS)
    add_library(sentinel-shield SHARED ${SHIELD_SOURCES})
    target_compile_definitions(sentinel-shield PRIVATE SHIELD_EXPORTS)
else()
    add_library(sentinel-shield STATIC ${SHIELD_SOURCES})
endif()

target_include_directories(sentinel-shield PUBLIC
    $<BUILD_INTERFACE:${CMAKE_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

# Platform-specific libraries
if(WIN32)
    target_link_libraries(sentinel-shield ws2_32)
elseif(UNIX)
    target_link_libraries(sentinel-shield m pthread)
endif()

# OpenSSL
if(USE_OPENSSL AND OPENSSL_FOUND)
    target_link_libraries(sentinel-shield OpenSSL::SSL OpenSSL::Crypto)
endif()

# Main executable
if(BUILD_CLI)
    add_executable(shield src/main.c)
    target_link_libraries(shield sentinel-shield)
endif()

# Tests
if(BUILD_TESTS)
    enable_testing()
    
    add_executable(unit_tests tests/unit_tests.c)
    target_link_libraries(unit_tests sentinel-shield)
    add_test(NAME UnitTests COMMAND unit_tests)
    
    add_executable(integration_tests tests/integration_tests.c)
    target_link_libraries(integration_tests sentinel-shield)
    add_test(NAME IntegrationTests COMMAND integration_tests)
endif()

# Examples
if(BUILD_EXAMPLES)
    add_executable(example_protect_llm examples/protect_llm.c)
    target_link_libraries(example_protect_llm sentinel-shield)
endif()

# Install
install(TARGETS sentinel-shield
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include
    FILES_MATCHING PATTERN "*.h"
)

if(BUILD_CLI)
    install(TARGETS shield RUNTIME DESTINATION bin)
endif()

# Package config
include(CMakePackageConfigHelpers)

configure_package_config_file(
    ${CMAKE_SOURCE_DIR}/cmake/sentinel-shield-config.cmake.in
    ${CMAKE_BINARY_DIR}/sentinel-shield-config.cmake
    INSTALL_DESTINATION lib/cmake/sentinel-shield
)

write_basic_package_version_file(
    ${CMAKE_BINARY_DIR}/sentinel-shield-config-version.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_BINARY_DIR}/sentinel-shield-config.cmake
    ${CMAKE_BINARY_DIR}/sentinel-shield-config-version.cmake
    DESTINATION lib/cmake/sentinel-shield
)

# CPack
set(CPACK_PACKAGE_NAME "sentinel-shield")
set(CPACK_PACKAGE_VERSION ${PROJECT_VERSION})
set(CPACK_PACKAGE_DESCRIPTION_SUMMARY ${PROJECT_DESCRIPTION})
set(CPACK_GENERATOR "TGZ;ZIP")
include(CPack)

# Summary
message(STATUS "")
message(STATUS "╔══════════════════════════════════════════════════════════╗")
message(STATUS "║                   SENTINEL SHIELD                         ║")
message(STATUS "║                      v${PROJECT_VERSION}                              ║")
message(STATUS "╚══════════════════════════════════════════════════════════╝")
message(STATUS "")
message(STATUS "  Build type:      ${CMAKE_BUILD_TYPE}")
message(STATUS "  Shared library:  ${BUILD_SHARED_LIBS}")
message(STATUS "  CLI:             ${BUILD_CLI}")
message(STATUS "  Tests:           ${BUILD_TESTS}")
message(STATUS "  Examples:        ${BUILD_EXAMPLES}")
message(STATUS "  OpenSSL:         ${USE_OPENSSL}")
message(STATUS "")
message(STATUS "  \"We're small, but WE CAN.\"")
message(STATUS "")
