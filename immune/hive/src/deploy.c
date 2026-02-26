/*
 * SENTINEL IMMUNE — Deploy Orchestrator
 * 
 * SSH-based agent deployment.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pthread.h>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <unistd.h>
    #include <sys/wait.h>
#endif

#include "../include/hive.h"

#define MAX_DEPLOY_QUEUE    100
#define MAX_CREDENTIALS     50
#define DEPLOY_TIMEOUT      60

/* Credential types */
typedef enum {
    CRED_PASSWORD = 1,
    CRED_SSH_KEY,
    CRED_AGENT_FORWARD
} cred_type_t;

/* Credential entry */
typedef struct {
    uint32_t        cred_id;
    cred_type_t     type;
    char            username[64];
    char            password[256];      /* Or key path */
    char            key_passphrase[128];
    int             priority;
} credential_t;

/* Deploy target */
typedef struct {
    uint32_t        target_id;
    char            host[256];
    uint16_t        port;
    char            os_type[32];
    int             status;             /* 0=pending, 1=deploying, 2=success, 3=failed */
    uint32_t        cred_id;
    time_t          queued_at;
    time_t          started_at;
    time_t          completed_at;
    char            error[256];
} deploy_target_t;

/* Deploy context */
typedef struct {
    credential_t    credentials[MAX_CREDENTIALS];
    int             cred_count;
    
    deploy_target_t queue[MAX_DEPLOY_QUEUE];
    int             queue_count;
    int             queue_head;
    
    pthread_t       thread;
    pthread_mutex_t lock;
    int             running;
    
    char            agent_path[256];
    
    /* Statistics */
    uint64_t        total_attempts;
    uint64_t        total_success;
    uint64_t        total_failed;
} deploy_ctx_t;

/* Global context */
static deploy_ctx_t g_deploy;

/* ==================== Initialization ==================== */

int
deploy_init(const char *agent_path)
{
    memset(&g_deploy, 0, sizeof(deploy_ctx_t));
    
    pthread_mutex_init(&g_deploy.lock, NULL);
    
    if (agent_path) {
        strncpy(g_deploy.agent_path, agent_path, 
                sizeof(g_deploy.agent_path) - 1);
    } else {
        strcpy(g_deploy.agent_path, "/usr/local/sbin/immuned");
    }
    
    printf("DEPLOY: Initialized (agent: %s)\n", g_deploy.agent_path);
    return 0;
}

void
deploy_shutdown(void)
{
    if (g_deploy.running) {
        deploy_stop();
    }
    
    pthread_mutex_destroy(&g_deploy.lock);
    
    printf("DEPLOY: Stats - attempts=%lu success=%lu failed=%lu\n",
           g_deploy.total_attempts,
           g_deploy.total_success,
           g_deploy.total_failed);
}

/* ==================== Credential Management ==================== */

uint32_t
deploy_add_credential(const char *username, const char *password,
                      int type, int priority)
{
    if (g_deploy.cred_count >= MAX_CREDENTIALS)
        return 0;
    
    pthread_mutex_lock(&g_deploy.lock);
    
    uint32_t cred_id = g_deploy.cred_count + 1;
    credential_t *cred = &g_deploy.credentials[g_deploy.cred_count];
    
    cred->cred_id = cred_id;
    cred->type = type;
    cred->priority = priority;
    
    if (username) strncpy(cred->username, username, sizeof(cred->username) - 1);
    if (password) strncpy(cred->password, password, sizeof(cred->password) - 1);
    
    g_deploy.cred_count++;
    
    pthread_mutex_unlock(&g_deploy.lock);
    
    printf("DEPLOY: Added credential %u (%s)\n", cred_id, username);
    return cred_id;
}

uint32_t
deploy_add_ssh_key(const char *username, const char *key_path,
                   const char *passphrase, int priority)
{
    if (g_deploy.cred_count >= MAX_CREDENTIALS)
        return 0;
    
    pthread_mutex_lock(&g_deploy.lock);
    
    uint32_t cred_id = g_deploy.cred_count + 1;
    credential_t *cred = &g_deploy.credentials[g_deploy.cred_count];
    
    cred->cred_id = cred_id;
    cred->type = CRED_SSH_KEY;
    cred->priority = priority;
    
    if (username) strncpy(cred->username, username, sizeof(cred->username) - 1);
    if (key_path) strncpy(cred->password, key_path, sizeof(cred->password) - 1);
    if (passphrase) strncpy(cred->key_passphrase, passphrase, 
                            sizeof(cred->key_passphrase) - 1);
    
    g_deploy.cred_count++;
    
    pthread_mutex_unlock(&g_deploy.lock);
    
    printf("DEPLOY: Added SSH key credential %u\n", cred_id);
    return cred_id;
}

/* ==================== Deploy Queue ==================== */

uint32_t
deploy_queue_target(const char *host, uint16_t port, 
                    const char *os_type, uint32_t cred_id)
{
    if (g_deploy.queue_count >= MAX_DEPLOY_QUEUE)
        return 0;
    
    pthread_mutex_lock(&g_deploy.lock);
    
    uint32_t target_id = g_deploy.queue_count + 1;
    deploy_target_t *target = &g_deploy.queue[g_deploy.queue_count];
    
    target->target_id = target_id;
    target->port = port > 0 ? port : 22;
    target->status = 0;  /* Pending */
    target->cred_id = cred_id;
    target->queued_at = time(NULL);
    
    if (host) strncpy(target->host, host, sizeof(target->host) - 1);
    if (os_type) strncpy(target->os_type, os_type, sizeof(target->os_type) - 1);
    
    g_deploy.queue_count++;
    
    pthread_mutex_unlock(&g_deploy.lock);
    
    printf("DEPLOY: Queued target %u (%s)\n", target_id, host);
    return target_id;
}

/* ==================== SSH Deployment ==================== */

static int
execute_ssh_command(const char *host, uint16_t port,
                    credential_t *cred, const char *command)
{
#ifndef _WIN32
    char cmd[2048];
    
    if (cred->type == CRED_SSH_KEY) {
        snprintf(cmd, sizeof(cmd),
            "ssh -o StrictHostKeyChecking=no "
            "-o ConnectTimeout=%d "
            "-i '%s' "
            "-p %d "
            "%s@%s '%s'",
            DEPLOY_TIMEOUT,
            cred->password,  /* key path */
            port,
            cred->username,
            host,
            command
        );
    } else {
        /* sshpass for password auth */
        snprintf(cmd, sizeof(cmd),
            "sshpass -p '%s' ssh -o StrictHostKeyChecking=no "
            "-o ConnectTimeout=%d "
            "-p %d "
            "%s@%s '%s'",
            cred->password,
            DEPLOY_TIMEOUT,
            port,
            cred->username,
            host,
            command
        );
    }
    
    int result = system(cmd);
    return WEXITSTATUS(result);
#else
    /* For Windows, would use PuTTY's plink */
    printf("DEPLOY: Windows SSH not implemented\n");
    return -1;
#endif
}

static int
deploy_single_target(deploy_target_t *target, credential_t *cred)
{
    char command[1024];
    int result;
    
    printf("DEPLOY: Starting deployment to %s\n", target->host);
    
    target->status = 1;  /* Deploying */
    target->started_at = time(NULL);
    
    /* Step 1: Create directory */
    result = execute_ssh_command(target->host, target->port, cred,
        "mkdir -p /var/immune && mkdir -p /etc/immune");
    
    if (result != 0) {
        snprintf(target->error, sizeof(target->error), 
                 "Failed to create directories");
        target->status = 3;  /* Failed */
        return -1;
    }
    
    /* Step 2: Copy agent binary */
#ifndef _WIN32
    char scp_cmd[1024];
    
    if (cred->type == CRED_SSH_KEY) {
        snprintf(scp_cmd, sizeof(scp_cmd),
            "scp -o StrictHostKeyChecking=no -i '%s' -P %d "
            "%s %s@%s:/usr/local/sbin/immuned",
            cred->password,
            target->port,
            g_deploy.agent_path,
            cred->username,
            target->host
        );
    } else {
        snprintf(scp_cmd, sizeof(scp_cmd),
            "sshpass -p '%s' scp -o StrictHostKeyChecking=no -P %d "
            "%s %s@%s:/usr/local/sbin/immuned",
            cred->password,
            target->port,
            g_deploy.agent_path,
            cred->username,
            target->host
        );
    }
    
    result = system(scp_cmd);
    if (WEXITSTATUS(result) != 0) {
        snprintf(target->error, sizeof(target->error),
                 "Failed to copy agent binary");
        target->status = 3;
        return -1;
    }
#endif
    
    /* Step 3: Set permissions and start */
    snprintf(command, sizeof(command),
        "chmod +x /usr/local/sbin/immuned && "
        "/usr/local/sbin/immuned -D /var/immune &"
    );
    
    result = execute_ssh_command(target->host, target->port, cred, command);
    
    if (result != 0) {
        snprintf(target->error, sizeof(target->error),
                 "Failed to start agent");
        target->status = 3;
        return -1;
    }
    
    target->status = 2;  /* Success */
    target->completed_at = time(NULL);
    
    printf("DEPLOY: Successfully deployed to %s\n", target->host);
    return 0;
}

/* ==================== Deploy Thread ==================== */

static void*
deploy_thread(void *arg)
{
    (void)arg;
    
    while (g_deploy.running) {
        pthread_mutex_lock(&g_deploy.lock);
        
        /* Find pending target */
        deploy_target_t *target = NULL;
        credential_t *cred = NULL;
        
        for (int i = 0; i < g_deploy.queue_count; i++) {
            if (g_deploy.queue[i].status == 0) {
                target = &g_deploy.queue[i];
                
                /* Find matching credential */
                for (int j = 0; j < g_deploy.cred_count; j++) {
                    if (g_deploy.credentials[j].cred_id == target->cred_id) {
                        cred = &g_deploy.credentials[j];
                        break;
                    }
                }
                
                break;
            }
        }
        
        pthread_mutex_unlock(&g_deploy.lock);
        
        if (target && cred) {
            g_deploy.total_attempts++;
            
            int result = deploy_single_target(target, cred);
            
            if (result == 0) {
                g_deploy.total_success++;
            } else {
                g_deploy.total_failed++;
            }
        } else {
            /* No pending targets, sleep */
#ifdef _WIN32
            Sleep(1000);
#else
            sleep(1);
#endif
        }
    }
    
    return NULL;
}

/* ==================== Control ==================== */

int
deploy_start(void)
{
    if (g_deploy.running)
        return 0;
    
    g_deploy.running = 1;
    
    if (pthread_create(&g_deploy.thread, NULL, deploy_thread, NULL) != 0) {
        g_deploy.running = 0;
        return -1;
    }
    
    printf("DEPLOY: Started\n");
    return 0;
}

void
deploy_stop(void)
{
    if (!g_deploy.running)
        return;
    
    g_deploy.running = 0;
    pthread_join(g_deploy.thread, NULL);
    
    printf("DEPLOY: Stopped\n");
}

/* Statistics */
void
deploy_stats(uint64_t *attempts, uint64_t *success, uint64_t *failed)
{
    if (attempts) *attempts = g_deploy.total_attempts;
    if (success) *success = g_deploy.total_success;
    if (failed) *failed = g_deploy.total_failed;
}
