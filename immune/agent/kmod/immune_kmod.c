/*
 * SENTINEL IMMUNE — DragonFlyBSD EDR Kernel Module v2.2
 * 
 * 6 Syscall Hooks:
 * - execve: process execution blocking
 * - connect: outbound network monitoring
 * - bind: listener port monitoring
 * - open: sensitive file access
 * - fork: process creation tracking
 * - setuid: privilege escalation detection
 */

#include <sys/param.h>
#include <sys/module.h>
#include <sys/kernel.h>
#include <sys/systm.h>
#include <sys/sysctl.h>
#include <sys/sysent.h>
#include <sys/sysproto.h>
#include <sys/proc.h>
#include <sys/thread2.h>
#include <sys/errno.h>
#include <sys/malloc.h>
#include <sys/time.h>
#include <sys/socket.h>
#include <sys/socketvar.h>
#include <sys/syscall.h>
#include <netinet/in.h>

/* ==================== Configuration ==================== */

#define IMMUNE_VERSION          "2.2.0"
#define RING_BUFFER_SIZE        1024
#define MAX_PATH_LEN            256
#define RATE_LIMIT_MAX          100

/* Event types */
#define EVENT_EXEC              0x01
#define EVENT_FORK              0x02
#define EVENT_OPEN              0x40
#define EVENT_SETUID            0x80
#define EVENT_CONNECT           0x08

/* Severity levels */
#define SEV_INFO                0
#define SEV_LOW                 1
#define SEV_MEDIUM              2
#define SEV_HIGH                3
#define SEV_CRITICAL            4

/* ==================== Data Structures ==================== */

typedef struct immune_event {
    uint64_t        timestamp;
    uint32_t        event_type;
    uint32_t        severity;
    pid_t           pid;
    uid_t           uid;
    char            path[MAX_PATH_LEN];
    char            details[128];
} immune_event_t;

typedef struct immune_ring {
    immune_event_t  events[RING_BUFFER_SIZE];
    int             head;
    int             count;
    int             dropped;
} immune_ring_t;

/* ==================== Global State ==================== */

static struct lwkt_token immune_token = LWKT_TOKEN_INITIALIZER(immune_token);

/* Configuration */
static int immune_enabled = 1;
static int immune_block_mode = 1;
static int immune_monitor_network = 1;
static int immune_monitor_files = 1;
static int immune_monitor_creds = 1;
static int immune_log_level = SEV_LOW;

/* Statistics */
static uint64_t immune_events_total = 0;
static uint64_t immune_threats_detected = 0;
static uint64_t immune_threats_blocked = 0;
static uint64_t immune_events_dropped = 0;

/* Ring buffer */
static immune_ring_t event_ring;

/* Original syscalls */
static sy_call_t *original_execve = NULL;
static sy_call_t *original_connect = NULL;
static sy_call_t *original_bind = NULL;
static sy_call_t *original_fork = NULL;
static sy_call_t *original_open = NULL;
static sy_call_t *original_setuid = NULL;

/* Memory */
MALLOC_DEFINE(M_IMMUNE, "immune", "IMMUNE EDR");

/* ==================== Blocked Patterns ==================== */

static const char *exec_blocked_patterns[] = {
    "/tmp/", "/dev/shm/", "/var/tmp/",
    "nc ", "ncat", "/dev/tcp", "bash -i",
    "python -c", "perl -e", "ruby -e",
    "| sh", "|sh", ";sh", "wget ", "curl ",
    NULL
};

static const char *network_blocked_patterns[] = {
    ":4444", ":5555", ":6666", ":31337", ":12345",
    NULL
};

static const char *sensitive_files[] = {
    "/etc/shadow", "/etc/master.passwd", "/etc/passwd",
    ".ssh/id_rsa", ".ssh/authorized_keys",
    "/boot/loader.conf", "/etc/rc.conf",
    "/var/log/auth.log", "/var/log/messages",
    NULL
};

/* ==================== Helpers ==================== */

static uint64_t
get_timestamp(void)
{
    struct timeval tv;
    getmicrotime(&tv);
    return (uint64_t)tv.tv_sec * 1000000 + tv.tv_usec;
}

static int
pattern_match(const char *str, const char **patterns)
{
    int i;
    if (str == NULL) return 0;
    for (i = 0; patterns[i] != NULL; i++) {
        if (strstr(str, patterns[i]) != NULL)
            return 1;
    }
    return 0;
}

static void
log_event(uint32_t type, uint32_t severity, pid_t pid, uid_t uid,
          const char *path, const char *details)
{
    immune_event_t *event;
    
    if (severity < immune_log_level) return;
    if (event_ring.count >= RING_BUFFER_SIZE) {
        event_ring.dropped++;
        immune_events_dropped++;
        return;
    }
    
    event = &event_ring.events[event_ring.head];
    event->timestamp = get_timestamp();
    event->event_type = type;
    event->severity = severity;
    event->pid = pid;
    event->uid = uid;
    if (path) strlcpy(event->path, path, MAX_PATH_LEN);
    if (details) strlcpy(event->details, details, sizeof(event->details));
    
    event_ring.head = (event_ring.head + 1) % RING_BUFFER_SIZE;
    event_ring.count++;
    immune_events_total++;
}

/* ==================== Syscall Hooks ==================== */

static int
immune_execve(struct sysmsg *sysmsg, const struct execve_args *uap)
{
    struct thread *td = curthread;
    char path[MAX_PATH_LEN];
    
    if (!immune_enabled) 
        return original_execve(sysmsg, __DECONST(void *, uap));
    
    lwkt_gettoken(&immune_token);
    
    if (uap->fname != NULL) {
        if (copyinstr(uap->fname, path, sizeof(path), NULL) == 0) {
            if (pattern_match(path, exec_blocked_patterns)) {
                immune_threats_detected++;
                log_event(EVENT_EXEC, SEV_HIGH, td->td_proc->p_pid,
                         td->td_ucred->cr_uid, path, "Blocked exec");
                
                if (immune_block_mode) {
                    immune_threats_blocked++;
                    kprintf("IMMUNE: [BLOCKED] exec %s (pid=%d)\n",
                            path, td->td_proc->p_pid);
                    lwkt_reltoken(&immune_token);
                    return EPERM;
                }
            }
        }
    }
    
    lwkt_reltoken(&immune_token);
    return original_execve(sysmsg, __DECONST(void *, uap));
}

static int
immune_connect(struct sysmsg *sysmsg, const struct connect_args *uap)
{
    struct thread *td = curthread;
    struct sockaddr_in sin;
    char addr_str[64];
    
    if (!immune_enabled || !immune_monitor_network)
        return original_connect(sysmsg, __DECONST(void *, uap));
    
    lwkt_gettoken(&immune_token);
    
    if (uap->name != NULL && uap->namelen >= sizeof(struct sockaddr_in)) {
        if (copyin(uap->name, &sin, sizeof(sin)) == 0 && sin.sin_family == AF_INET) {
            uint8_t *ip = (uint8_t *)&sin.sin_addr.s_addr;
            ksnprintf(addr_str, sizeof(addr_str), "%d.%d.%d.%d:%d",
                     ip[0], ip[1], ip[2], ip[3], ntohs(sin.sin_port));
            
            if (pattern_match(addr_str, network_blocked_patterns)) {
                immune_threats_detected++;
                if (immune_block_mode) {
                    immune_threats_blocked++;
                    kprintf("IMMUNE: [BLOCKED] connect %s (pid=%d)\n",
                            addr_str, td->td_proc->p_pid);
                    lwkt_reltoken(&immune_token);
                    return EACCES;
                }
            }
        }
    }
    
    lwkt_reltoken(&immune_token);
    return original_connect(sysmsg, __DECONST(void *, uap));
}

static int
immune_bind(struct sysmsg *sysmsg, const struct bind_args *uap)
{
    struct thread *td = curthread;
    struct sockaddr_in sin;
    
    if (!immune_enabled || !immune_monitor_network)
        return original_bind(sysmsg, __DECONST(void *, uap));
    
    lwkt_gettoken(&immune_token);
    
    if (uap->name != NULL && uap->namelen >= sizeof(struct sockaddr_in)) {
        if (copyin(uap->name, &sin, sizeof(sin)) == 0 && sin.sin_family == AF_INET) {
            uint16_t port = ntohs(sin.sin_port);
            log_event(EVENT_CONNECT, SEV_LOW, td->td_proc->p_pid,
                     td->td_ucred->cr_uid, "", "Bind listener");
            
            if (port < 1024 && td->td_ucred->cr_uid != 0) {
                kprintf("IMMUNE: [ALERT] non-root bind to port %d\n", port);
            }
        }
    }
    
    lwkt_reltoken(&immune_token);
    return original_bind(sysmsg, __DECONST(void *, uap));
}

static int
immune_open(struct sysmsg *sysmsg, const struct open_args *uap)
{
    struct thread *td = curthread;
    char path[MAX_PATH_LEN];
    
    if (!immune_enabled || !immune_monitor_files)
        return original_open(sysmsg, __DECONST(void *, uap));
    
    lwkt_gettoken(&immune_token);
    
    if (uap->path != NULL) {
        if (copyinstr(uap->path, path, sizeof(path), NULL) == 0) {
            if (pattern_match(path, sensitive_files)) {
                log_event(EVENT_OPEN, SEV_MEDIUM, td->td_proc->p_pid,
                         td->td_ucred->cr_uid, path, "Sensitive file");
                kprintf("IMMUNE: [AUDIT] open %s (pid=%d, uid=%d)\n",
                        path, td->td_proc->p_pid, td->td_ucred->cr_uid);
            }
        }
    }
    
    lwkt_reltoken(&immune_token);
    return original_open(sysmsg, __DECONST(void *, uap));
}

static int
immune_fork(struct sysmsg *sysmsg, const struct fork_args *uap)
{
    struct thread *td = curthread;
    int result;
    
    lwkt_gettoken(&immune_token);
    log_event(EVENT_FORK, SEV_INFO, td->td_proc->p_pid,
             td->td_ucred->cr_uid, td->td_proc->p_comm, "Fork");
    lwkt_reltoken(&immune_token);
    
    result = original_fork(sysmsg, __DECONST(void *, uap));
    return result;
}

static int
immune_setuid(struct sysmsg *sysmsg, const struct setuid_args *uap)
{
    struct thread *td = curthread;
    uid_t old_uid, new_uid;
    
    if (!immune_enabled || !immune_monitor_creds)
        return original_setuid(sysmsg, __DECONST(void *, uap));
    
    lwkt_gettoken(&immune_token);
    
    old_uid = td->td_ucred->cr_uid;
    new_uid = uap->uid;
    
    /* Privilege escalation: non-root becoming root */
    if (old_uid != 0 && new_uid == 0) {
        immune_threats_detected++;
        log_event(EVENT_SETUID, SEV_CRITICAL, td->td_proc->p_pid,
                 old_uid, td->td_proc->p_comm, "Priv escalation");
        
        kprintf("IMMUNE: [CRITICAL] setuid(0) by uid=%d (pid=%d, %s)\n",
                old_uid, td->td_proc->p_pid, td->td_proc->p_comm);
        
        if (immune_block_mode) {
            immune_threats_blocked++;
            kprintf("IMMUNE: [BLOCKED] Privilege escalation denied\n");
            lwkt_reltoken(&immune_token);
            return EPERM;
        }
    } else if (old_uid != new_uid) {
        log_event(EVENT_SETUID, SEV_MEDIUM, td->td_proc->p_pid,
                 old_uid, td->td_proc->p_comm, "UID change");
        kprintf("IMMUNE: [AUDIT] setuid %d->%d (pid=%d)\n",
                old_uid, new_uid, td->td_proc->p_pid);
    }
    
    lwkt_reltoken(&immune_token);
    return original_setuid(sysmsg, __DECONST(void *, uap));
}

/* ==================== Sysctl Interface ==================== */

SYSCTL_NODE(_security, OID_AUTO, immune, CTLFLAG_RW, 0, "IMMUNE EDR");
SYSCTL_INT(_security_immune, OID_AUTO, enabled, CTLFLAG_RW, 
           &immune_enabled, 0, "Enable protection");
SYSCTL_INT(_security_immune, OID_AUTO, block_mode, CTLFLAG_RW, 
           &immune_block_mode, 0, "Block mode");
SYSCTL_INT(_security_immune, OID_AUTO, monitor_network, CTLFLAG_RW, 
           &immune_monitor_network, 0, "Monitor network");
SYSCTL_INT(_security_immune, OID_AUTO, monitor_files, CTLFLAG_RW, 
           &immune_monitor_files, 0, "Monitor files");
SYSCTL_INT(_security_immune, OID_AUTO, monitor_creds, CTLFLAG_RW, 
           &immune_monitor_creds, 0, "Monitor credentials");
SYSCTL_UQUAD(_security_immune, OID_AUTO, events_total, CTLFLAG_RD, 
             &immune_events_total, 0, "Total events");
SYSCTL_UQUAD(_security_immune, OID_AUTO, threats_detected, CTLFLAG_RD, 
             &immune_threats_detected, 0, "Threats detected");
SYSCTL_UQUAD(_security_immune, OID_AUTO, threats_blocked, CTLFLAG_RD, 
             &immune_threats_blocked, 0, "Threats blocked");
SYSCTL_INT(_security_immune, OID_AUTO, ring_count, CTLFLAG_RD, 
           &event_ring.count, 0, "Ring buffer count");

/* ==================== Module Lifecycle ==================== */

static int
immune_loader(struct module *m, int what, void *arg)
{
    int error = 0;

    switch (what) {
    case MOD_LOAD:
        kprintf("\n");
        kprintf("IMMUNE: SENTINEL IMMUNE EDR v%s\n", IMMUNE_VERSION);
        kprintf("IMMUNE: DragonFlyBSD Kernel Module\n");
        kprintf("IMMUNE: 6 syscall hooks active\n");
        kprintf("IMMUNE: Block mode: %s\n", 
                immune_block_mode ? "ENABLED" : "DISABLED");
        
        memset(&event_ring, 0, sizeof(event_ring));
        
        /* Install hooks */
        original_execve = sysent[SYS_execve].sy_call;
        sysent[SYS_execve].sy_call = (sy_call_t *)immune_execve;
        
        original_connect = sysent[SYS_connect].sy_call;
        sysent[SYS_connect].sy_call = (sy_call_t *)immune_connect;
        
        original_bind = sysent[SYS_bind].sy_call;
        sysent[SYS_bind].sy_call = (sy_call_t *)immune_bind;
        
        original_open = sysent[SYS_open].sy_call;
        sysent[SYS_open].sy_call = (sy_call_t *)immune_open;
        
        original_fork = sysent[SYS_fork].sy_call;
        sysent[SYS_fork].sy_call = (sy_call_t *)immune_fork;
        
        original_setuid = sysent[SYS_setuid].sy_call;
        sysent[SYS_setuid].sy_call = (sy_call_t *)immune_setuid;
        
        kprintf("IMMUNE: Protection ACTIVE\n\n");
        break;
        
    case MOD_UNLOAD:
        if (original_execve)
            sysent[SYS_execve].sy_call = original_execve;
        if (original_connect)
            sysent[SYS_connect].sy_call = original_connect;
        if (original_bind)
            sysent[SYS_bind].sy_call = original_bind;
        if (original_open)
            sysent[SYS_open].sy_call = original_open;
        if (original_fork)
            sysent[SYS_fork].sy_call = original_fork;
        if (original_setuid)
            sysent[SYS_setuid].sy_call = original_setuid;
        
        kprintf("IMMUNE: Unloaded. Events=%lu Threats=%lu Blocked=%lu\n",
                immune_events_total, immune_threats_detected, 
                immune_threats_blocked);
        break;
        
    default:
        error = EOPNOTSUPP;
        break;
    }
    return error;
}

static moduledata_t immune_mod = {
    "immune",
    immune_loader,
    NULL
};

DECLARE_MODULE(immune, immune_mod, SI_SUB_DRIVERS, SI_ORDER_MIDDLE);
MODULE_VERSION(immune, 2);
