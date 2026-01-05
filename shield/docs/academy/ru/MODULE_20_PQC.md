# Модуль 20: Post-Quantum Cryptography (PQC)

## Обзор

Post-Quantum Cryptography (PQC) — это криптографические алгоритмы, устойчивые к атакам квантовых компьютеров. SENTINEL Shield включает готовую интеграцию PQC для защиты коммуникаций Shield↔Brain в будущем.

---

## Почему PQC важен

```
┌────────────────────────────────────────────────────────────┐
│            Классические vs Квантовые угрозы                 │
├─────────────────────────────┬──────────────────────────────┤
│   RSA/ECC сегодня           │   Квантовый компьютер        │
│   • Безопасно               │   • Алгоритм Шора            │
│   • Широко используется     │   • RSA/ECC взломаны         │
│   • Стандартизировано       │   • "Harvest Now, Decrypt    │
│                             │     Later" атаки             │
└─────────────────────────────┴──────────────────────────────┘
```

**NIST Post-Quantum Standards (2024):**
- **Kyber** → Key Encapsulation (ML-KEM)
- **Dilithium** → Digital Signatures (ML-DSA)

---

## PQC в SENTINEL Shield

### Kyber-1024 (ML-KEM)

**Назначение:** Безопасный обмен ключами

**Уровень безопасности:** NIST Level 5 (эквивалент AES-256)

```c
// Размеры ключей
#define KYBER1024_PK_SIZE    1568  // Public key
#define KYBER1024_SK_SIZE    3168  // Secret key
#define KYBER1024_CT_SIZE    1568  // Ciphertext
#define KYBER1024_SS_SIZE    32    // Shared secret
```

**Использование:**
```c
// 1. Генерация ключевой пары
kyber1024_keypair(pk, sk);

// 2. Инкапсуляция (отправитель)
kyber1024_encapsulate(ct, ss, pk);  // ct = шифротекст, ss = общий секрет

// 3. Декапсуляция (получатель)
kyber1024_decapsulate(ss, ct, sk);  // ss = тот же общий секрет
```

### Dilithium-5 (ML-DSA)

**Назначение:** Цифровые подписи

**Уровень безопасности:** NIST Level 5

```c
// Размеры ключей
#define DILITHIUM5_PK_SIZE   2592  // Public key
#define DILITHIUM5_SK_SIZE   4880  // Secret key
#define DILITHIUM5_SIG_SIZE  4627  // Signature
```

**Использование:**
```c
// 1. Генерация ключевой пары
dilithium5_keypair(pk, sk);

// 2. Подпись
dilithium5_sign(sig, msg, msg_len, sk);

// 3. Верификация
int valid = dilithium5_verify(sig, msg, msg_len, pk);
```

---

## API PQC

```c
#include "shield_pqc.h"

// Инициализация PQC подсистемы
shield_err_t pqc_init(void);

// Получить статус
pqc_stats_t pqc_get_stats(void);

// Kyber операции
shield_err_t pqc_kyber_keypair(kyber_pk_t *pk, kyber_sk_t *sk);
shield_err_t pqc_kyber_encapsulate(kyber_ct_t *ct, uint8_t ss[32], 
                                    const kyber_pk_t *pk);
shield_err_t pqc_kyber_decapsulate(uint8_t ss[32], const kyber_ct_t *ct,
                                    const kyber_sk_t *sk);

// Dilithium операции
shield_err_t pqc_dilithium_keypair(dilithium_pk_t *pk, dilithium_sk_t *sk);
shield_err_t pqc_dilithium_sign(dilithium_sig_t *sig, const uint8_t *msg,
                                 size_t msg_len, const dilithium_sk_t *sk);
shield_err_t pqc_dilithium_verify(const dilithium_sig_t *sig, 
                                   const uint8_t *msg, size_t msg_len,
                                   const dilithium_pk_t *pk);
```

---

## CLI Команды PQC

```
sentinel# show pqc
PQC (Post-Quantum Cryptography)
===============================
State: ENABLED
Algorithms:
  Key Exchange: Kyber-1024 (NIST Level 5)
  Signatures:   Dilithium-5 (NIST Level 5)

Statistics:
  Keys Generated: 12
  Encapsulations: 45
  Signatures: 23

sentinel(config)# pqc enable
PQC enabled

sentinel# pqc test
Running PQC self-test...
Kyber-1024:
  Keypair generation: OK (2.3ms)
  Encapsulation:      OK (0.4ms)
  Decapsulation:      OK (0.5ms)
Dilithium-5:
  Keypair generation: OK (3.1ms)
  Sign:               OK (1.2ms)
  Verify:             OK (1.0ms)
All tests PASSED
```

---

## Практическое применение

### 1. Shield↔Brain Secure Channel

```
Shield                              Brain
  │                                   │
  │  ───── Kyber Encapsulation ────►  │
  │  ◄──── Shared Secret ──────────   │
  │                                   │
  │  ══════ AES-256-GCM tunnel ═════  │
  │        (ключ = Kyber SS)          │
```

### 2. Signed Signatures Updates

```c
// Brain подписывает обновление сигнатур
dilithium5_sign(sig, signature_update, update_len, brain_sk);

// Shield верифицирует перед применением
if (dilithium5_verify(sig, signature_update, update_len, brain_pk)) {
    apply_signature_update(signature_update);
}
```

---

## Roadmap интеграции

| Фаза | Описание | Статус |
|------|----------|--------|
| 1 | PQC stubs | ✅ Готово |
| 2 | liboqs интеграция | ⏳ Планируется |
| 3 | Hybrid mode (Classical + PQC) | ⏳ Планируется |
| 4 | Full PQC migration | 🔮 Будущее |

---

## Лабораторная работа LAB-200

### Цель
Понять работу PQC алгоритмов в Shield.

### Задание 1: Включение PQC
```bash
sentinel# configure terminal
sentinel(config)# pqc enable
sentinel(config)# end
sentinel# show pqc
```

### Задание 2: Self-Test
```bash
sentinel# pqc test
```

### Задание 3: Программная интеграция
```c
#include "shield_pqc.h"

int main() {
    pqc_init();
    
    // Kyber key exchange
    kyber_pk_t pk;
    kyber_sk_t sk;
    pqc_kyber_keypair(&pk, &sk);
    
    kyber_ct_t ct;
    uint8_t ss1[32], ss2[32];
    pqc_kyber_encapsulate(&ct, ss1, &pk);
    pqc_kyber_decapsulate(ss2, &ct, &sk);
    
    // ss1 == ss2 (общий секрет)
    assert(memcmp(ss1, ss2, 32) == 0);
    return 0;
}
```

---

## Вопросы для самопроверки

1. Почему классическая криптография уязвима к квантовым компьютерам?
2. Что такое "Harvest Now, Decrypt Later"?
3. Чем Kyber отличается от Dilithium?
4. Что означает "NIST Level 5"?
5. Зачем нужен Hybrid mode?

---

## Следующий модуль

→ [Модуль 21: Shield State — Global State Manager](MODULE_21_SHIELD_STATE.md)
