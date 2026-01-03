/*
 * SENTINEL IMMUNE — Hive Scheduler
 * 
 * Periodic task execution.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <pthread.h>

#include "../include/hive.h"

#define MAX_TASKS   50

/* Task callback */
typedef void (*task_callback_t)(void *arg);

/* Scheduled task */
typedef struct {
    uint32_t        task_id;
    char            name[64];
    task_callback_t callback;
    void            *arg;
    int             interval_sec;
    time_t          last_run;
    time_t          next_run;
    int             enabled;
    int             run_count;
} scheduled_task_t;

/* Scheduler context */
typedef struct {
    scheduled_task_t    tasks[MAX_TASKS];
    int                 task_count;
    
    pthread_t           thread;
    pthread_mutex_t     lock;
    int                 running;
    
    immune_hive_t       *hive;
} scheduler_ctx_t;

/* Global context */
static scheduler_ctx_t g_scheduler;

/* ==================== Built-in Tasks ==================== */

/* Task: Check agent heartbeats */
static void
task_check_heartbeats(void *arg)
{
    immune_hive_t *hive = (immune_hive_t *)arg;
    if (!hive) return;
    
    time_t now = time(NULL);
    
    pthread_mutex_lock(&hive->agents_lock);
    
    for (uint32_t i = 1; i < MAX_AGENTS; i++) {
        if (!hive->agents[i].active)
            continue;
        
        if (hive->agents[i].status == AGENT_STATUS_ONLINE) {
            time_t elapsed = now - hive->agents[i].last_heartbeat;
            
            if (elapsed > HEARTBEAT_TIMEOUT) {
                hive->agents[i].status = AGENT_STATUS_OFFLINE;
                hive->stats.agents_online--;
                hive->stats.agents_offline++;
                
                printf("SCHEDULER: Agent %u went offline\n", i);
            }
        }
    }
    
    pthread_mutex_unlock(&hive->agents_lock);
}

/* Task: Save state */
static void
task_save_state(void *arg)
{
    immune_hive_t *hive = (immune_hive_t *)arg;
    if (!hive) return;
    
    hive_save_state(hive);
}

/* Task: Print status */
static void
task_print_status(void *arg)
{
    immune_hive_t *hive = (immune_hive_t *)arg;
    if (!hive) return;
    
    hive_print_status(hive);
}

/* Task: Cleanup old data */
static void
task_cleanup(void *arg)
{
    (void)arg;
    /* Would clean up old threats, logs, etc. */
    printf("SCHEDULER: Cleanup task executed\n");
}

/* ==================== Scheduler Thread ==================== */

static void*
scheduler_thread(void *arg)
{
    (void)arg;
    
    while (g_scheduler.running) {
        time_t now = time(NULL);
        
        pthread_mutex_lock(&g_scheduler.lock);
        
        for (int i = 0; i < g_scheduler.task_count; i++) {
            scheduled_task_t *task = &g_scheduler.tasks[i];
            
            if (!task->enabled)
                continue;
            
            if (now >= task->next_run) {
                /* Execute task */
                if (task->callback) {
                    task->callback(task->arg);
                    task->run_count++;
                }
                
                task->last_run = now;
                task->next_run = now + task->interval_sec;
            }
        }
        
        pthread_mutex_unlock(&g_scheduler.lock);
        
        /* Sleep 1 second */
#ifdef _WIN32
        Sleep(1000);
#else
        sleep(1);
#endif
    }
    
    return NULL;
}

/* ==================== Initialization ==================== */

int
scheduler_init(immune_hive_t *hive)
{
    memset(&g_scheduler, 0, sizeof(scheduler_ctx_t));
    
    g_scheduler.hive = hive;
    pthread_mutex_init(&g_scheduler.lock, NULL);
    
    /* Add default tasks */
    scheduler_add_task("heartbeat_check", task_check_heartbeats, hive, 30);
    scheduler_add_task("save_state", task_save_state, hive, 300);
    scheduler_add_task("cleanup", task_cleanup, NULL, 3600);
    
    printf("SCHEDULER: Initialized with %d tasks\n", g_scheduler.task_count);
    return 0;
}

void
scheduler_shutdown(void)
{
    if (g_scheduler.running) {
        scheduler_stop();
    }
    
    pthread_mutex_destroy(&g_scheduler.lock);
    
    printf("SCHEDULER: Shutdown complete\n");
}

/* ==================== Task Management ==================== */

uint32_t
scheduler_add_task(const char *name, task_callback_t callback,
                   void *arg, int interval_sec)
{
    if (g_scheduler.task_count >= MAX_TASKS)
        return 0;
    
    pthread_mutex_lock(&g_scheduler.lock);
    
    uint32_t task_id = g_scheduler.task_count + 1;
    scheduled_task_t *task = &g_scheduler.tasks[g_scheduler.task_count];
    
    task->task_id = task_id;
    if (name) strncpy(task->name, name, sizeof(task->name) - 1);
    task->callback = callback;
    task->arg = arg;
    task->interval_sec = interval_sec;
    task->last_run = 0;
    task->next_run = time(NULL) + interval_sec;
    task->enabled = 1;
    task->run_count = 0;
    
    g_scheduler.task_count++;
    
    pthread_mutex_unlock(&g_scheduler.lock);
    
    printf("SCHEDULER: Added task %s (every %d sec)\n", name, interval_sec);
    return task_id;
}

int
scheduler_remove_task(uint32_t task_id)
{
    pthread_mutex_lock(&g_scheduler.lock);
    
    for (int i = 0; i < g_scheduler.task_count; i++) {
        if (g_scheduler.tasks[i].task_id == task_id) {
            g_scheduler.tasks[i].enabled = 0;
            pthread_mutex_unlock(&g_scheduler.lock);
            return 0;
        }
    }
    
    pthread_mutex_unlock(&g_scheduler.lock);
    return -1;
}

int
scheduler_enable_task(uint32_t task_id, int enabled)
{
    pthread_mutex_lock(&g_scheduler.lock);
    
    for (int i = 0; i < g_scheduler.task_count; i++) {
        if (g_scheduler.tasks[i].task_id == task_id) {
            g_scheduler.tasks[i].enabled = enabled;
            pthread_mutex_unlock(&g_scheduler.lock);
            return 0;
        }
    }
    
    pthread_mutex_unlock(&g_scheduler.lock);
    return -1;
}

/* ==================== Control ==================== */

int
scheduler_start(void)
{
    if (g_scheduler.running)
        return 0;
    
    g_scheduler.running = 1;
    
    if (pthread_create(&g_scheduler.thread, NULL, 
                       scheduler_thread, NULL) != 0) {
        g_scheduler.running = 0;
        return -1;
    }
    
    printf("SCHEDULER: Started\n");
    return 0;
}

void
scheduler_stop(void)
{
    if (!g_scheduler.running)
        return;
    
    g_scheduler.running = 0;
    pthread_join(g_scheduler.thread, NULL);
    
    printf("SCHEDULER: Stopped\n");
}

/* Run a task immediately */
int
scheduler_run_now(uint32_t task_id)
{
    pthread_mutex_lock(&g_scheduler.lock);
    
    for (int i = 0; i < g_scheduler.task_count; i++) {
        if (g_scheduler.tasks[i].task_id == task_id) {
            scheduled_task_t *task = &g_scheduler.tasks[i];
            
            if (task->callback) {
                task->callback(task->arg);
                task->run_count++;
                task->last_run = time(NULL);
            }
            
            pthread_mutex_unlock(&g_scheduler.lock);
            return 0;
        }
    }
    
    pthread_mutex_unlock(&g_scheduler.lock);
    return -1;
}

/* List tasks */
void
scheduler_list_tasks(void)
{
    printf("\n=== SCHEDULED TASKS ===\n");
    
    pthread_mutex_lock(&g_scheduler.lock);
    
    for (int i = 0; i < g_scheduler.task_count; i++) {
        scheduled_task_t *task = &g_scheduler.tasks[i];
        
        printf("[%u] %s: interval=%ds, runs=%d, %s\n",
               task->task_id,
               task->name,
               task->interval_sec,
               task->run_count,
               task->enabled ? "ENABLED" : "disabled");
    }
    
    pthread_mutex_unlock(&g_scheduler.lock);
    
    printf("=======================\n\n");
}
