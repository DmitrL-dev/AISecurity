/*
 * SENTINEL Shield - Platform Abstraction Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_platform.h"

#ifdef SHIELD_PLATFORM_WINDOWS
    #include <windows.h>
    #include <direct.h>
    #include <io.h>
    #pragma comment(lib, "ws2_32.lib")
#else
    #include <sys/time.h>
    #include <sys/stat.h>
    #include <sys/ioctl.h>
    #include <termios.h>
    #include <time.h>
    #include <unistd.h>
#endif

/* Get time in milliseconds */
uint64_t platform_time_ms(void)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    return GetTickCount64();
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
#endif
}

/* Get time in microseconds */
uint64_t platform_time_us(void)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    LARGE_INTEGER freq, count;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&count);
    return (uint64_t)(count.QuadPart * 1000000 / freq.QuadPart);
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000 + ts.tv_nsec / 1000;
#endif
}

/* Sleep */
void platform_sleep_ms(uint32_t ms)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    Sleep(ms);
#else
    usleep(ms * 1000);
#endif
}

/* Network init */
bool platform_network_init(void)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    WSADATA wsa;
    return WSAStartup(MAKEWORD(2, 2), &wsa) == 0;
#else
    return true;
#endif
}

/* Network cleanup */
void platform_network_cleanup(void)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    WSACleanup();
#endif
}

/* Console init */
void platform_console_init(void)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    /* Enable ANSI colors on Windows 10+ */
    HANDLE hOut = GetStdHandle(STD_OUTPUT_HANDLE);
    DWORD mode = 0;
    GetConsoleMode(hOut, &mode);
    SetConsoleMode(hOut, mode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
#endif
}

/* Read line from console */
bool platform_console_readline(char *buffer, size_t size)
{
    if (!buffer || size == 0) {
        return false;
    }
    
    if (fgets(buffer, (int)size, stdin) == NULL) {
        return false;
    }
    
    /* Remove newline */
    size_t len = strlen(buffer);
    if (len > 0 && buffer[len - 1] == '\n') {
        buffer[len - 1] = '\0';
    }
    
    return true;
}

/* Write to console */
void platform_console_write(const char *text)
{
    if (text) {
        fputs(text, stdout);
        fflush(stdout);
    }
}

/* Get terminal size */
void platform_get_terminal_size(int *width, int *height)
{
    int w = 80, h = 24; /* Defaults */
    
#ifdef SHIELD_PLATFORM_WINDOWS
    CONSOLE_SCREEN_BUFFER_INFO csbi;
    if (GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &csbi)) {
        w = csbi.srWindow.Right - csbi.srWindow.Left + 1;
        h = csbi.srWindow.Bottom - csbi.srWindow.Top + 1;
    }
#else
    struct winsize ws;
    if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &ws) == 0) {
        w = ws.ws_col;
        h = ws.ws_row;
    }
#endif
    
    if (width) *width = w;
    if (height) *height = h;
}

/* Check if file exists */
bool platform_file_exists(const char *path)
{
    if (!path) return false;
    
#ifdef SHIELD_PLATFORM_WINDOWS
    return _access(path, 0) == 0;
#else
    return access(path, F_OK) == 0;
#endif
}

/* Create directory */
bool platform_mkdir(const char *path)
{
    if (!path) return false;
    
#ifdef SHIELD_PLATFORM_WINDOWS
    return _mkdir(path) == 0 || errno == EEXIST;
#else
    return mkdir(path, 0755) == 0 || errno == EEXIST;
#endif
}

/* Get config directory */
char *platform_get_config_dir(void)
{
    static char path[512];
    
#ifdef SHIELD_PLATFORM_WINDOWS
    const char *appdata = getenv("APPDATA");
    if (appdata) {
        snprintf(path, sizeof(path), "%s\\sentinel", appdata);
    } else {
        snprintf(path, sizeof(path), "C:\\sentinel");
    }
#elif defined(SHIELD_PLATFORM_MACOS)
    const char *home = getenv("HOME");
    if (home) {
        snprintf(path, sizeof(path), "%s/Library/Application Support/sentinel", home);
    } else {
        snprintf(path, sizeof(path), "/etc/sentinel");
    }
#else
    snprintf(path, sizeof(path), "/etc/sentinel");
#endif
    
    return path;
}

/* Get PID */
uint32_t platform_getpid(void)
{
#ifdef SHIELD_PLATFORM_WINDOWS
    return (uint32_t)GetCurrentProcessId();
#else
    return (uint32_t)getpid();
#endif
}

/* Get hostname */
const char *platform_get_hostname(void)
{
    static char hostname[256] = {0};
    
    if (hostname[0] == '\0') {
#ifdef SHIELD_PLATFORM_WINDOWS
        DWORD size = sizeof(hostname);
        GetComputerNameA(hostname, &size);
#else
        gethostname(hostname, sizeof(hostname));
#endif
    }
    
    return hostname;
}
