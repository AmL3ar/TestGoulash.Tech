import csv
from io import BytesIO, StringIO

import xlsxwriter

from ..models import Supplier


HEADERS = [
    "Поставщик",
    "Категория",
    "Город",
    "Регион",
    "Контакт",
    "MOQ",
    "Цена",
    "Документы",
    "Доставка",
    "Заметки",
    "Сайт",
    "Источник",
    "Проверено",
]


def rows(suppliers: list[Supplier]) -> list[list[str]]:
    return [
        [
            supplier.name,
            supplier.category,
            supplier.city,
            supplier.region,
            supplier.contact or "",
            supplier.min_order or "",
            supplier.price_hint or "",
            supplier.certificates or "",
            supplier.delivery or "",
            supplier.notes or "",
            supplier.website,
            supplier.source_url,
            (
                supplier.source_checked_at.strftime("%d.%m.%Y %H:%M")
                if supplier.source_checked_at
                else ""
            ),
        ]
        for supplier in suppliers
    ]


def make_csv(suppliers: list[Supplier]) -> bytes:
    stream = StringIO()
    writer = csv.writer(stream, delimiter=";")
    writer.writerow(HEADERS)
    writer.writerows(rows(suppliers))
    return ("\ufeff" + stream.getvalue()).encode("utf-8")


def make_xlsx(suppliers: list[Supplier]) -> bytes:
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True})
    sheet = workbook.add_worksheet("Поставщики")
    header = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#173F2B",
            "font_color": "#C9F06C",
            "border": 1,
        }
    )
    body = workbook.add_format(
        {
            "text_wrap": True,
            "valign": "top",
            "border": 1,
        }
    )

    for col, value in enumerate(HEADERS):
        sheet.write(0, col, value, header)

    for row_index, row in enumerate(rows(suppliers), start=1):
        for col_index, value in enumerate(row):
            sheet.write(row_index, col_index, value, body)

    widths = [24, 24, 18, 24, 28, 24, 28, 36, 36, 32, 34, 34, 18]
    for index, width in enumerate(widths):
        sheet.set_column(index, index, width)

    sheet.freeze_panes(1, 0)
    sheet.autofilter(0, 0, max(len(suppliers), 1), len(HEADERS) - 1)
    workbook.close()
    return output.getvalue()
