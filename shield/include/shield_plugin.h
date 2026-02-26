/*
 * SENTINEL Shield - Plugin System
 * 
 * Dynamic loading of custom guards and protocols
 */

#ifndef SHIELD_PLUGIN_H
#define SHIELD_PLUGIN_H

#include "shield_common.h"
#include "shield_guard.h"

/* Plugin types */
typedef enum plugin_type {
    PLUGIN_TYPE_GUARD,
    PLUGIN_TYPE_PROTOCOL,
    PLUGIN_TYPE_FILTER,
    PLUGIN_TYPE_EXPORTER,
} plugin_type_t;

/* Plugin info */
typedef struct plugin_info {
    char            name[64];
    char            version[16];
    char            author[64];
    char            description[256];
    plugin_type_t   type;
} plugin_info_t;

/* Plugin interface */
typedef struct plugin_interface {
    /* Required */
    shield_err_t    (*init)(void *config);
    void            (*destroy)(void);
    plugin_info_t   (*get_info)(void);
    
    /* For guards */
    guard_base_t    *(*create_guard)(void);
    
    /* For protocols */
    void            *(*create_protocol)(void);
} plugin_interface_t;

/* Loaded plugin */
typedef struct loaded_plugin {
    char                name[64];
    char                path[256];
    void                *handle;        /* dlopen handle */
    plugin_interface_t  iface;
    plugin_info_t       info;
    bool                initialized;
    struct loaded_plugin *next;
} loaded_plugin_t;

/* Plugin manager */
typedef struct plugin_manager {
    loaded_plugin_t *plugins;
    int             count;
    char            plugin_dir[256];
} plugin_manager_t;

/* API */
shield_err_t plugin_manager_init(plugin_manager_t *mgr, const char *plugin_dir);
void plugin_manager_destroy(plugin_manager_t *mgr);

shield_err_t plugin_load(plugin_manager_t *mgr, const char *path);
shield_err_t plugin_unload(plugin_manager_t *mgr, const char *name);

/* Load all plugins from directory */
int plugin_load_all(plugin_manager_t *mgr);

/* Find plugin */
loaded_plugin_t *plugin_find(plugin_manager_t *mgr, const char *name);

/* List plugins */
int plugin_list(plugin_manager_t *mgr, plugin_info_t *infos, int max_count);

#endif /* SHIELD_PLUGIN_H */
