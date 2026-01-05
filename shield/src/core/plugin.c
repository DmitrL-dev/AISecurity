/*
 * SENTINEL Shield - Plugin System Implementation
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "shield_common.h"
#include "shield_plugin.h"
#include "shield_platform.h"

#ifdef SHIELD_PLATFORM_WINDOWS
#include <windows.h>
#define dlopen(path, flags) LoadLibraryA(path)
#define dlsym(handle, name) GetProcAddress(handle, name)
#define dlclose(handle) FreeLibrary(handle)
#define dlerror() "LoadLibrary failed"
#else
#include <dlfcn.h>
#include <dirent.h>
#endif

/* Initialize plugin manager */
shield_err_t plugin_manager_init(plugin_manager_t *mgr, const char *plugin_dir)
{
    if (!mgr) {
        return SHIELD_ERR_INVALID;
    }
    
    memset(mgr, 0, sizeof(*mgr));
    
    if (plugin_dir) {
        strncpy(mgr->plugin_dir, plugin_dir, sizeof(mgr->plugin_dir) - 1);
    } else {
        /* Default plugin directory */
#ifdef SHIELD_PLATFORM_WINDOWS
        strncpy(mgr->plugin_dir, ".\\plugins", sizeof(mgr->plugin_dir) - 1);
#else
        strncpy(mgr->plugin_dir, "./plugins", sizeof(mgr->plugin_dir) - 1);
#endif
    }
    
    return SHIELD_OK;
}

/* Destroy plugin manager */
void plugin_manager_destroy(plugin_manager_t *mgr)
{
    if (!mgr) {
        return;
    }
    
    loaded_plugin_t *plugin = mgr->plugins;
    while (plugin) {
        loaded_plugin_t *next = plugin->next;
        
        if (plugin->initialized && plugin->iface.destroy) {
            plugin->iface.destroy();
        }
        
        if (plugin->handle) {
            dlclose(plugin->handle);
        }
        
        free(plugin);
        plugin = next;
    }
    
    mgr->plugins = NULL;
    mgr->count = 0;
}

/* Load plugin */
shield_err_t plugin_load(plugin_manager_t *mgr, const char *path)
{
    if (!mgr || !path) {
        return SHIELD_ERR_INVALID;
    }
    
    /* Load dynamic library */
    void *handle = dlopen(path, RTLD_NOW);
    if (!handle) {
        LOG_ERROR("Failed to load plugin %s: %s", path, dlerror());
        return SHIELD_ERR_IO;
    }
    
    /* Get interface function */
    typedef plugin_interface_t (*get_interface_fn)(void);
    get_interface_fn get_interface = (get_interface_fn)dlsym(handle, "shield_plugin_interface");
    
    if (!get_interface) {
        LOG_ERROR("Plugin %s has no shield_plugin_interface", path);
        dlclose(handle);
        return SHIELD_ERR_INVALID;
    }
    
    plugin_interface_t iface = get_interface();
    
    if (!iface.get_info) {
        LOG_ERROR("Plugin %s has no get_info function", path);
        dlclose(handle);
        return SHIELD_ERR_INVALID;
    }
    
    plugin_info_t info = iface.get_info();
    
    /* Check if already loaded */
    if (plugin_find(mgr, info.name)) {
        LOG_WARN("Plugin %s already loaded", info.name);
        dlclose(handle);
        return SHIELD_ERR_EXISTS;
    }
    
    /* Create plugin entry */
    loaded_plugin_t *plugin = calloc(1, sizeof(loaded_plugin_t));
    if (!plugin) {
        dlclose(handle);
        return SHIELD_ERR_NOMEM;
    }
    
    strncpy(plugin->name, info.name, sizeof(plugin->name) - 1);
    strncpy(plugin->path, path, sizeof(plugin->path) - 1);
    plugin->handle = handle;
    plugin->iface = iface;
    plugin->info = info;
    
    /* Initialize */
    if (iface.init) {
        shield_err_t err = iface.init(NULL);
        if (err != SHIELD_OK) {
            LOG_ERROR("Plugin %s init failed", info.name);
            dlclose(handle);
            free(plugin);
            return err;
        }
    }
    
    plugin->initialized = true;
    
    /* Add to list */
    plugin->next = mgr->plugins;
    mgr->plugins = plugin;
    mgr->count++;
    
    LOG_INFO("Loaded plugin: %s v%s (%s)", info.name, info.version, info.description);
    
    return SHIELD_OK;
}

/* Unload plugin */
shield_err_t plugin_unload(plugin_manager_t *mgr, const char *name)
{
    if (!mgr || !name) {
        return SHIELD_ERR_INVALID;
    }
    
    loaded_plugin_t **pp = &mgr->plugins;
    while (*pp) {
        if (strcmp((*pp)->name, name) == 0) {
            loaded_plugin_t *plugin = *pp;
            *pp = plugin->next;
            
            if (plugin->initialized && plugin->iface.destroy) {
                plugin->iface.destroy();
            }
            
            if (plugin->handle) {
                dlclose(plugin->handle);
            }
            
            LOG_INFO("Unloaded plugin: %s", name);
            
            free(plugin);
            mgr->count--;
            return SHIELD_OK;
        }
        pp = &(*pp)->next;
    }
    
    return SHIELD_ERR_NOTFOUND;
}

/* Load all plugins from directory */
int plugin_load_all(plugin_manager_t *mgr)
{
    if (!mgr) {
        return 0;
    }
    
    int loaded = 0;
    
#ifdef SHIELD_PLATFORM_WINDOWS
    char pattern[280];
    snprintf(pattern, sizeof(pattern), "%s\\*.dll", mgr->plugin_dir);
    
    WIN32_FIND_DATAA fd;
    HANDLE hFind = FindFirstFileA(pattern, &fd);
    
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            char path[280];
            snprintf(path, sizeof(path), "%s\\%s", mgr->plugin_dir, fd.cFileName);
            if (plugin_load(mgr, path) == SHIELD_OK) {
                loaded++;
            }
        } while (FindNextFileA(hFind, &fd));
        FindClose(hFind);
    }
#else
    DIR *dir = opendir(mgr->plugin_dir);
    if (dir) {
        struct dirent *entry;
        while ((entry = readdir(dir)) != NULL) {
            size_t len = strlen(entry->d_name);
            if (len > 3 && strcmp(entry->d_name + len - 3, ".so") == 0) {
                char path[280];
                snprintf(path, sizeof(path), "%s/%s", mgr->plugin_dir, entry->d_name);
                if (plugin_load(mgr, path) == SHIELD_OK) {
                    loaded++;
                }
            }
        }
        closedir(dir);
    }
#endif
    
    return loaded;
}

/* Find plugin */
loaded_plugin_t *plugin_find(plugin_manager_t *mgr, const char *name)
{
    if (!mgr || !name) {
        return NULL;
    }
    
    loaded_plugin_t *plugin = mgr->plugins;
    while (plugin) {
        if (strcmp(plugin->name, name) == 0) {
            return plugin;
        }
        plugin = plugin->next;
    }
    
    return NULL;
}

/* List plugins */
int plugin_list(plugin_manager_t *mgr, plugin_info_t *infos, int max_count)
{
    if (!mgr || !infos) {
        return 0;
    }
    
    int count = 0;
    loaded_plugin_t *plugin = mgr->plugins;
    
    while (plugin && count < max_count) {
        infos[count++] = plugin->info;
        plugin = plugin->next;
    }
    
    return count;
}
