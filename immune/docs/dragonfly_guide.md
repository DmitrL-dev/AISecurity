# IMMUNE — DragonFlyBSD Development Guide

> Документация для разработки IMMUNE kernel module на DragonFlyBSD

---

## Quick Start

### 1. Получение исходников

```bash
cd /usr
make src-create-shallow  # Клонирует git репо
```

Или update:
```bash
make src-update
```

### 2. Структура kernel source

```
/usr/src/sys/
├── config/              # Kernel configs (X86_64_GENERIC)
├── compile/             # Build output
├── kern/                # Core kernel code
│   ├── kern_syscall.c   # Syscall dispatch
│   ├── kern_exec.c      # Process execution
│   ├── kern_sig.c       # Signals
│   └── ...
├── sys/                 # Headers
│   ├── syscall.h        # Syscall numbers
│   ├── sysent.h         # Syscall entries
│   └── proc.h           # Process structures
└── modules/             # Loadable kernel modules (KLDs)
```

---

## Kernel Module Development

### Базовая структура KLD

```c
#include <sys/param.h>
#include <sys/module.h>
#include <sys/kernel.h>

static int
my_modevent(module_t mod, int type, void *unused)
{
    switch (type) {
    case MOD_LOAD:
        printf("Module loaded\n");
        break;
    case MOD_UNLOAD:
        printf("Module unloaded\n");
        break;
    }
    return 0;
}

static moduledata_t my_mod = {
    "mymodule",
    my_modevent,
    NULL
};

DECLARE_MODULE(mymodule, my_mod, SI_SUB_DRIVERS, SI_ORDER_MIDDLE);
```

### Makefile для KLD

```makefile
KMOD = mymodule
SRCS = mymodule.c

.include <bsd.kmod.mk>
```

### Build & Load

```bash
make -f Makefile.kmod
kldload ./mymodule.ko
kldstat | grep mymodule
kldunload mymodule
```

---

## vkernel — Виртуальный Kernel

**Ключевая фича DragonFlyBSD!**

Позволяет запускать kernel в userspace для отладки без перезагрузок.

### Компиляция vkernel

```bash
cd /usr/src
make -j4 KERNCONF=VKERNEL buildkernel
```

### Создание файловой системы

```bash
vnconfig -c vn0 /path/to/disk.img
newfs /dev/vn0s0
mount /dev/vn0s0 /mnt/vkernel
# Установить минимальную систему
```

### Запуск vkernel

```bash
vkernel -r /path/to/disk.img -m 256m -n 1
```

**Преимущества:**
- Отладка kernel кода через gdb
- Нет перезагрузок
- Изолированная среда

---

## Syscall Hooking

### Метод 1: sysent table (прямой)

```c
#include <sys/sysent.h>

/* Сохраняем оригинал */
static sy_call_t *original_read;

/* Наш хук */
static int
my_read_hook(struct thread *td, void *args)
{
    /* Логика перехвата */
    return original_read(td, args);
}

/* В MOD_LOAD: */
original_read = sysent[SYS_READ].sy_call;
sysent[SYS_READ].sy_call = my_read_hook;

/* В MOD_UNLOAD: */
sysent[SYS_READ].sy_call = original_read;
```

### Метод 2: kqueue/kevent (мониторинг)

Для наблюдения без модификации — через filesystem events.

---

## Ключевые файлы для IMMUNE

| File | Purpose |
|------|---------|
| `sys/kern/kern_exec.c` | execve() implementation |
| `sys/kern/sys_generic.c` | read/write syscalls |
| `sys/kern/uipc_syscalls.c` | Socket syscalls |
| `sys/sys/sysent.h` | Syscall entry structure |
| `sys/sys/syscall.h` | Syscall numbers |
| `sys/dev/misc/klog/` | Kernel logging |

---

## HAMMER2 Integration

HAMMER2 — криптографическая файловая система DragonFlyBSD.

**Фичи для IMMUNE:**
- Блочные чексуммы (целостность)
- Дедупликация
- Snapshots для forensics

```c
#include <sys/vfs/hammer2/hammer2.h>
```

---

## Development Flow

```
1. Редактировать код (Windows)
      │
      ▼
2. rsync → DragonFlyBSD VM
      │
      ▼
3. make -f Makefile.kmod
      │
      ▼
4. kldload ./immune.ko
      │
      ▼
5. Тест → kldunload
      │
      ▼
6. Повторить
```

---

## Docker/VM Setup

### Вариант A: QEMU/bhyve

```bash
# Host (Windows/Linux)
qemu-system-x86_64 -hda dragonfly.img -m 2G -netdev user,id=net0
```

### Вариант B: VirtualBox

1. Скачать ISO: https://www.dragonflybsd.org/download/
2. Создать VM (2GB RAM, 20GB disk)
3. Установить DragonFlyBSD
4. Настроить shared folders

---

## Roadmap для IMMUNE

| Phase | Task |
|-------|------|
| 1 | Установить DragonFlyBSD VM |
| 2 | Настроить dev environment |
| 3 | Hello World KLD |
| 4 | Базовый syscall hook |
| 5 | Интеграция с IMMUNE agent |
| 6 | SIMD pattern matching |
| 7 | Hive communication |
| 8 | vkernel тестирование |
| 9 | Production hardening |

---

## Ресурсы

- Handbook: https://www.dragonflybsd.org/docs/handbook/
- Source: https://gitweb.dragonflybsd.org/dragonfly.git
- Man pages: http://leaf.dragonflybsd.org/cgi/web-man
- Mailing list: docs@dragonflybsd.org
