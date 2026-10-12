# Разведка 3 магазинов (2026-05-20)

## Дикси — сложность 4/10 (легче всех)
- **Защита**: Qrator. SSR-страницы (`/`, `/catalog/`, `/product/...`) отдаются 200 OK с обычным Chrome UA. AJAX-эндпоинт `/ajax/listing-json.php` → 403 (TLS-fingerprint).
- **Главный лайфхак**: `https://dixy.ru/sitemap-iblock-1.xml` (4.7 МБ) содержит **полный список карточек товаров** `/product/<slug>-<sku>/`. Открыт anonymously.
- **Карточка товара**: JSON-LD прямо в HTML — `sku`, `name`, `brand`, `image`, `price`, плюс DOM-блоки `card__price-num` (текущая), `card__price-crossed` (старая), состав, КБЖУ, фасовка, breadcrumbs категорий.
- **Регион**: cookies `DIXY2_SM_FOREVER_BASKET`, `DIXY2_SM_d_guid`, привязка к адресу доставки (Москва по умолчанию).
- **Готовых парсеров не нашёл** — ниша свободна.
- **Стек**: `httpx` для sitemap → `curl_cffi (impersonate=chrome)` для карточек → `selectolax/lxml`. Без Playwright.

## Магнит — сложность 6/10
- **Защита**: Qrator + `document-policy: js-profiling`. SSR 200 OK с Chrome UA.
- **DNS блок субдоменов вне РФ** — `web-gateway.middle-api.magnit.ru`, `online.magnit.ru` и др. NXDOMAIN с зарубежных DNS. **VPS обязательно в РФ** (Selectel/Timeweb).
- **Каталог в HTML**: `GET /catalog` → `window.__NUXT__` JSON-блок с 605 категориями + товары. Парсится регексом/BS4.
- **API (для apps)**: `POST https://web-gateway.middle-api.magnit.ru/v3/goods` с `x-device-id`, `x-device-platform: Web`, `x-app-version`. Тело — `data=json.dumps(...)` (WAF чувствителен к Content-Length).
- **Регион**: cookie `shopCode` (например `992301`), `x_shop_type=ME` (Магнит у дома), `nmg_dt=DELIVERY_TYPE_PICKUP`.
- **Поля**: `id`, `goodsCode`, `name`, `price`, `discountPrice`, `image` (на `images-foodtech.magnit.ru`), `brand`, `weight`, `available`. Штрихкод/КБЖУ — только в детали.
- **Готовое**: `github.com/krankir/parsing_Magnit` (только акции, 2023). Хабр Q&A 1299720 — рабочий сниппет POST на `/v3/goods`.
- **Стек**: `curl_cffi` (impersonate=chrome131) + `selectolax` + Redis для cookie-jar по shopCode. Без Playwright.

## Пятёрочка — сложность 7/10 (тяжелее всех)
- **Защита**: **ServicePipe** (тот же, что положил Самокат). 5ka.ru → JS-challenge → cookies `spid/spsn/spsc`. 5d.5ka.ru/api/* → 403 без прогретой сессии. Header `X-SP-CRID` на каждом ответе.
- **Каталог-API живёт на `5d.5ka.ru`**:
  - `GET /api/catalog/v2/stores/{sap_code}/categories` — дерево
  - `GET /api/catalog/v2/stores/{sap_code}/categories/{cat_id}/products?mode=store&limit=...`
  - `GET /api/catalog/v2/stores/{sap_code}/products/{plu_id}` — карточка
- **Регион**: SAP store code (`Y232`, `Y004`, ...), определяется через `Geolocation.suggest()`.
- **Поля**: `plu`, `name`, `image_link`, `price`, `price_discount`, флаг «Х5 Клуб», бренд, наличие. Один SKU имеет разные цены `mode=store` vs `mode=delivery`.
- **Готовое open-source**: **`pip install pyaterochka_api`** ([Open-Inflation/pyaterochka_api](https://github.com/Open-Inflation/pyaterochka_api)) — async-библиотека, активно поддерживается, делает warm-up за нас.
- **Стек**: `pyaterochka_api` + Playwright/Patchright для warm-up если библиотека сломается + резидентный RU-прокси крайне желателен (ServicePipe скорит ASN — VPS из datacenter-pool может получить 403).

## Общие выводы
1. **VPS обязательно в РФ** (Магнит — DNS, Пятёрочка — ServicePipe-гео-скоринг).
2. **Регион хранится cookies/store-id** — нужна таблица `store_contexts (retailer, region, identifier, cookies_json, last_refreshed)`.
3. **Структура одинаковая**: регион → категории → товары категории → детали карточки. Можно сделать единый интерфейс `Crawler.fetch_categories/fetch_category_products/fetch_product_detail`.
4. **Темп**: ≤1 RPS на магазин, ротация UA + device-id, экспоненциальный backoff на 403/429.
5. **Цены меняются ежечасно** — нужна history-таблица `prices_history (product_id, price, discount_price, ts)` чтобы строить графики.
