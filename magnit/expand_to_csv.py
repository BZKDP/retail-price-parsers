"""
Раскладывает массивы characteristics / storage_conditions из products.jsonl
в отдельные столбцы с русскими заголовками. Пишет:
  out/products_flat.csv        — UTF-8 без BOM
  out/products_flat_excel.csv  — UTF-8 с BOM (для Excel)

Запуск:  python expand_to_csv.py
"""

import csv
import json
import pathlib
from collections import Counter

ROOT = pathlib.Path(__file__).parent
JSONL = ROOT / "out" / "products.jsonl"
OUT_PLAIN = ROOT / "out" / "products_flat.csv"
OUT_EXCEL = ROOT / "out" / "products_flat_excel.csv"

# Базовые колонки + их русские названия (порядок важен — он же порядок в CSV)
BASE_COLS = [
    ("sku",          "Артикул"),
    ("name",         "Название"),
    ("brand",        "Бренд"),
    ("manufacturer", "Производитель"),
    ("weight",       "Вес (JSON-LD)"),
    ("price",        "Цена"),
    ("currency",     "Валюта"),
    ("categories",   "Категории"),
    ("description",  "Описание"),
    ("additional_info", "Доп. информация"),
    ("rating_value", "Рейтинг"),
    ("rating_count", "Кол-во оценок"),
    ("review_count", "Кол-во отзывов"),
    ("shop_address", "Адрес магазина"),
    ("image",        "Картинка"),
    ("url",          "Ссылка"),
]


def collect_dynamic_columns(records: list[dict]) -> tuple[list[str], list[str]]:
    """Собираем уникальные имена характеристик и условий хранения,
    отсортированные по частоте (самые частые — слева)."""
    chars = Counter()
    storage = Counter()
    for r in records:
        for it in r.get("characteristics") or []:
            n = (it.get("name") or "").strip()
            if n:
                chars[n] += 1
        for it in r.get("storage_conditions") or []:
            n = (it.get("name") or "").strip()
            if n:
                storage[n] += 1
    return [n for n, _ in chars.most_common()], [n for n, _ in storage.most_common()]


def value_for(items: list[dict], key: str) -> str:
    if not items:
        return ""
    for it in items:
        if (it.get("name") or "").strip() == key:
            return str(it.get("value") or "")
    return ""


def main() -> None:
    records = [json.loads(line) for line in JSONL.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(f"Загружено товаров: {len(records)}")

    char_names, storage_names = collect_dynamic_columns(records)
    print(f"Уникальных характеристик: {len(char_names)}")
    print(f"Уникальных условий хранения: {len(storage_names)}")

    # Уберём из characteristics те имена, что уже есть как базовые колонки
    DUP = {"Бренд", "Производитель", "Артикул", "Вес, кг"}
    char_cols = [n for n in char_names if n not in DUP]

    base_keys = [k for k, _ in BASE_COLS]
    base_labels = [lbl for _, lbl in BASE_COLS]
    header = base_labels + char_cols + storage_names

    rows = []
    for r in records:
        row = []
        for k in base_keys:
            v = r.get(k)
            if isinstance(v, list):
                v = " / ".join(map(str, v))
            row.append("" if v is None else v)
        for n in char_cols:
            row.append(value_for(r.get("characteristics") or [], n))
        for n in storage_names:
            row.append(value_for(r.get("storage_conditions") or [], n))
        rows.append(row)

    # plain
    with OUT_PLAIN.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    # with BOM for Excel
    OUT_EXCEL.write_bytes(b"\xef\xbb\xbf" + OUT_PLAIN.read_bytes())

    print(f"\nКолонок: {len(header)}")
    print(f"Строк:   {len(rows)}")
    print(f"  -> {OUT_PLAIN}")
    print(f"  -> {OUT_EXCEL}")
    print("\nПервые 15 колонок:")
    for c in header[:15]:
        print("  ", c)
    if len(header) > 15:
        print(f"  ... и ещё {len(header) - 15}")


if __name__ == "__main__":
    main()
