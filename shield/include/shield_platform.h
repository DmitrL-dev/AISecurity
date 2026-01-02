/*
 * SENTINEL Shield - Platform Abstraction Layer
 * 
 * Cross-platform support for Windows, Linux, macOS
 */

#ifndef SHIELD_PLATFORM_H
#define SHIELD_PLATFORM_H

#include <stdint.h>
#include <stdbool.h>

/* Platform detection */
#if defined(_WIN32) || defined(_WIN64)
    #define SHIELD_PLATFORM_WINDOWS 1
    #define SHIELD_PLATFORM_NAME "Windows"
#elif defined(__linux__)
    #define SHIELD_PLATFORM_LINUX 1
    #define SHIELD_PLATFORM_NAME "Linux"
#elif defined(__APPLE__)
    #define SHIELD_PLATFORM_MACOS 1
    #define SHIELD_PLATFORM_NAME "macOS"
#else
    #define SHIELD_PLATFORM_UNKNOWN 1
    #define SHIELD_PLATFORM_NAME "Unknown"
#endif

/* Socket types */
#ifdef SHIELD_PLATFORM_WINDOWS
    #include <winsock2.h>
    #include <ws2tcpip.h>
    typedef SOCKET socket_t;
    #define INVALID_SOCKET_VALUE INVALID_SOCKET
    #define socket_close(s) closesocket(s)
    #define socket_errno WSAGetLastError()
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
    #include <arpa/inet.h>
    #include <netdb.h>
    #include <unistd.h>
    #include <errno.h>
    typedef int socket_t;
    #define INVALID_SOCKET_VALUE (-1)
    #define socket_close(s) close(s)
    #define socket_errno errno
#endif

/* Time functions */
uint64_t platform_time_ms(void);
uint64_t platform_time_us(void);
void platform_sleep_ms(uint32_t ms);

/* Network initialization */
bool platform_network_init(void);
void platform_network_cleanup(void);

/* Console */
void platform_console_init(void);
bool platform_console_readline(char *buffer, size_t size);
void platform_console_write(const char *text);

/* Terminal size */
void platform_get_terminal_size(int *width, int *height);

/* File system */
bool platform_file_exists(const char *path);
bool platform_mkdir(const char *path);
char *platform_get_config_dir(void);

/* Process */
uint32_t platform_getpid(void);
const char *platform_get_hostname(void);

#endif /* SHIELD_PLATFORM_H */
