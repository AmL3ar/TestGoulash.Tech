from sqlalchemy import select
from .database import SessionLocal
from .models import Supplier

SEED = [
    dict(name="Агросервис", category="зерно, овощи и фрукты", city="Екатеринбург", region="Свердловская область и регионы",
         website="https://ekb.agrotekhservis.ru/", contact="+7 931 105-63-33",
         min_order=None, price_hint="прайс обновляется еженедельно; цена зависит от сезона и объёма",
         certificates="сертификаты качества, фитосанитарные свидетельства, декларации соответствия",
         delivery="Екатеринбург — заявлено 1 день; регионы — 2–5 дней",
         notes="Оптовые поставки агропродукции; коммерческие условия стоит перепроверить перед заказом.",
         source_url="https://ekb.agrotekhservis.ru/", data_completeness=.91, verified_contact=True),
    dict(name="DOVLAT", category="овощи и фрукты", city="Екатеринбург", region="Россия",
         website="https://dovlat.ru/", contact=None,
         min_order=None, price_hint="прайс по запросу", certificates="заявлено соответствие правилам сертификации и хранения",
         delivery="доставка в регионы России из Екатеринбурга",
         notes="Оптовые и мелкооптовые продажи; в наличии широкий ассортимент.",
         source_url="https://dovlat.ru/", data_completeness=.72, verified_contact=False),
    dict(name="ОвощОпт", category="овощи и фрукты", city="Екатеринбург", region="Свердловская область",
         website="https://овощопт.рф/", contact="+7 (912) 601-78-41",
         min_order=None, price_hint=None, certificates=None,
         delivery="доставка в день заказа или на следующий день по Екатеринбургу",
         notes="Поставщик свежих овощей и фруктов; заявляет прямые поставки от производителей.",
         source_url="https://овощопт.рф/", data_completeness=.66, verified_contact=True),
    dict(name="Триал Маркет", category="пищевая упаковка", city="Екатеринбург", region="Екатеринбург и Россия",
         website="https://ekaterinburg.trial-market.ru/pishchevaya-upakovka/", contact=None,
         min_order=None, price_hint="есть публичные цены по SKU; например цена за штуку отображается в каталоге",
         certificates=None, delivery="бесплатная доставка по Екатеринбургу при заказе от 3 000 ₽; доставка по России",
         notes="Большой каталог упаковки для HoReCa: контейнеры, коробки, соусники, плёнка и др.",
         source_url="https://ekaterinburg.trial-market.ru/pishchevaya-upakovka/", data_completeness=.79, verified_contact=False),
    dict(name="Расходные материалы", category="пищевая упаковка, одноразовая посуда, экоупаковка", city="Екатеринбург", region="УрФО, ХМАО, ЯНАО",
         website="https://rm-pack.ru/", contact="+7 (800) 333-07-08 · +7 (343) 384-07-08 · info@rm-pack.ru",
         min_order=None, price_hint="цены на сайте носят ознакомительный характер",
         certificates=None, delivery="региональные оптовые поставки; условия уточняются у поставщика",
         notes="Офис/склад в Екатеринбурге; широкий ассортимент пищевой и экоупаковки.",
         source_url="https://rm-pack.ru/", data_completeness=.83, verified_contact=True),
    dict(name="U2B", category="упаковка для HoReCa и доставки", city="Екатеринбург", region="Свердловская область",
         website="https://ekburg.u2b.ru/", contact="+7 (343) 226-09-36 · 66@u2b.ru",
         min_order=None, price_hint="публичный каталог", certificates=None,
         delivery="условия доставки зависят от заказа; доступны упаковочные материалы для пищевого направления",
         notes="Бумажная упаковка, контейнеры для горячих блюд и кондитерской продукции.",
         source_url="https://ekburg.u2b.ru/", data_completeness=.76, verified_contact=True),
    dict(name="ТД Барин", category="мясо и мясные изделия", city="Екатеринбург", region="Свердловская область",
         website="https://barin.pro/", contact="+7 (343) 207-44-00",
         min_order="крупный, средний и мелкий опт; точный MOQ уточнить", price_hint=None,
         certificates="обязательный ветконтроль; заявлен комплект документов",
         delivery="собственный автопарк рефрижераторов",
         notes="Оптовые поставки мяса; заявлены быстрая отгрузка и возврат/замена.",
         source_url="https://barin.pro/", data_completeness=.86, verified_contact=True),
    dict(name="Гросс Фуд", category="мясо, птица, HoReCa", city="Екатеринбург", region="Екатеринбург и область",
         website="https://ekat.grossfood.ru/catalog/myaso/", contact=None,
         min_order=None, price_hint="в каталоге отображаются цены за кг и наличие по складам",
         certificates="работа через «Меркурий», заявлен полный пакет документации",
         delivery="доставка по Екатеринбургу и области",
         notes="Каталог мяса для ресторанов, кафе, столовых и пищевых производств.",
         source_url="https://ekat.grossfood.ru/catalog/myaso/", data_completeness=.8, verified_contact=False),
    dict(name="СЕЛЛ-Сервис", category="кондитерские ингредиенты, какао, агар, лецитин", city="Екатеринбург", region="Свердловская область",
         website="https://ekaterinburg.sell-service.ru/catalog/industries/konditerskie_izdeliya/", contact="+7-954-353-53-53",
         min_order=None, price_hint=None, certificates="заявлено соответствие продукции требованиям качества",
         delivery=None, notes="Промышленные ингредиенты; на карточках указаны фасовки и технические характеристики.",
         source_url="https://ekaterinburg.sell-service.ru/catalog/industries/konditerskie_izdeliya/", data_completeness=.7, verified_contact=True),
]


def seed_if_empty() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Supplier.id).limit(1)) is not None:
            return
        db.add_all([Supplier(**item) for item in SEED])
        db.commit()
