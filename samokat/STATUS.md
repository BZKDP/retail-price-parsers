# Статус парсера Самокат

Заметки по исследованию защиты Самоката. Конкретные токены, IP, идентификаторы
пользователя и адреса удалены — задаются через переменные окружения (см. `.env.example`).

## Где мы

ServicePipe блокирует прямой HTTP-запрос из Python (urllib/requests) даже при валидном
JWT — почти наверняка проверка JA3/TLS-fingerprint. Рабочая схема: перехват полного
набора заголовков из трафика мобильного приложения через mitmproxy в Termux на телефоне,
затем повтор запроса с мобильного IP и okhttp-подобным TLS-отпечатком (`curl_cffi` /
`tls-client`).

## Что готово

- Пропатченный APK Самоката, доверяющий пользовательскому CA
- PCAPdroid + PCAPdroid-mitm, CA импортирован
- TLS-дешифровка работает: виден полный JWT в HTTP-вкладке
- Правило дешифровки по приложению «Самокат», блокировка QUIC = «Всегда»
- Termux + Python + requests/mitmproxy

## Что перехватываем (значения — из env, не в репозитории)

- JWT (`SAMOKAT_JWT`) — короткоживущий, после `exp` нужно перехватывать заново
- showcase ID (`SAMOKAT_SHOWCASE_ID`)
- user ID (`SAMOKAT_USER_ID`), device_id
- набор заголовков: `authorization`, `systemversion`, `x-user-id`, `x-user-type`,
  `x-application-platform`, `x-application-version`, `x-creeper` (обрезается в UI)

## Известно что НЕ работает

- Прямой запрос из Python с мобильным IP → 403 от ServicePipe даже с валидным JWT
  (скрипт `phone_samokat_test.py`).
- PCAPdroid в режиме PCAP-файла не содержит plaintext (только зашифрованный TLS).
- UI PCAPdroid обрезает текст запроса (~1.5 КБ) — полный набор заголовков не виден.

## Следующие шаги

1. Запустить mitmproxy в Termux: `mitmweb --listen-host 0.0.0.0 --listen-port 8080`
   или `mitmdump -w flow.bin -p 8080`.
2. Установить CA mitmproxy в доверенные на телефоне.
3. Настроить Wi-Fi proxy телефона на IP ПК в LAN (`PROXY_HOST_LAN`) порт 8080
   (автоматизация — `set_proxy_v8.py`).
4. Открыть Самокат, пощёлкать — mitmweb покажет запросы с полными заголовками.
5. Экспортировать flow в JSON с фильтром `~d api.samokat.ru`.
6. Повторить запрос с мобильного IP и перехваченными заголовками. При 403 перейти на
   okhttp JA3 (`curl_cffi` / `tls-client`).

## Полезные команды

```bash
# PCAPdroid start/stop через intent
am start -e action stop  -n com.emanuelef.remote_capture/.activities.CaptureCtrl
am start -e action start -e pcap_dump_mode pcap_file -e app_filter ru.sbcs.store \
    -n com.emanuelef.remote_capture/.activities.CaptureCtrl
```

## Файлы

- `phone_samokat_test.py` — тест прямого запроса (даёт 403)
- `api_test_vps.py` — тест с RU-VPS, читает заголовки из `headers.json`
- `set_proxy_v8.py` — автомат настройки Wi-Fi proxy
- `setup_pcapdroid.py` — запуск PCAPdroid + пропуск онбординга
