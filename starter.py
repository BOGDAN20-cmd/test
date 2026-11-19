"""
Учебный фрагмент для тестового задания ТОЛЬКООПТ.

Python 3.10+, только стандартная библиотека. Запуск примера: python starter.py
Если нужен pytest - он также допустим. Запускать его по правилам ниже.
Sample fetch_offers имитирует внешний источник: реальные запросы не нужны.

Контракт fetch_offers():
    fetch_offers() - асинхронная функция без аргументов, возвращает список
    словарей со статусом (success / partial / error) и офферами.
    Все суммы в копейках - положительные Decimal с точностью до копейки.
    seller - строка; delivery_days - неотрицательное целое число или None.
    Правила фильтрации и расчёта цены:
        Оффер отклоняется, если не выполняется хотя бы одно условие.
        fetch_offers может завершиться исключением или долго ожидать ответа.

    current_price - текущая цена; min_price - минимально допустимая цена.
    timeout_s - положительное число секунд, по умолчанию 2.
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR

# Правила:
# 1. Ограничение ожидание fetch_offers значением timeout_s. При ошибке источника,
#    таймауте или отсутствии офферов вернуть текущую цену и NULL.
# 2. Учитывать только офферы со статусом success и офферы (смежные предложения).
# 3. Исключать сообщения с Магазин и офферы от реселлера (б/у).
# 4. Если подходящих предложений нет, вернуть текущую цену и NULL.
# 5. Если подходящее предложение есть, то расчет:
#    - минимальную цену подходящего конкурента умножить на 1.5 и округлить
#      вниз до копеек. Рекомендация - максимум из этой суммы и min_price.
#    - Если рекомендация отличается от текущей цены больше чем на 30% в любую
#      сторону, вернуть текущую цену и NULL. Это ограничение защищает от
#      резких скачков цен. 
#      В таком случае price - текущая цена, decision - NULL, reason - "Резкое изменение".
# 6. Формат возврата (строго dict):
#    {
#        "price": Decimal("4328.00"),
#        "decision": "APPLY",
#        "reason": "Найдена минимальная цена"
#    }

async def recommend_price(fetch_offers, current_price, min_price, timeout_s=2.0):
    try:
        # 1. Ограничиваем ожидание таймаутом
        offers = await asyncio.wait_for(fetch_offers(), timeout=timeout_s)
    except (asyncio.TimeoutError, Exception) as e:
        # При ошибке, таймауте или пустом списке - возвращаем текущую цену и NULL
        return {"price": current_price, "decision": None, "reason": f"Ошибка источника: {e}"}

    if not offers:
        return {"price": current_price, "decision": None, "reason": "Нет офферов"}

    prices = []
    for offer in offers:
        # 2. Учитываем только офферы со статусом success
        if offer.get("status") != "success":
            continue
        
        # 3. Исключаем "Магазин" и офферы от реселлера (б/у)
        if offer.get("seller") == "Магазин":
            continue
        if offer.get("is_reseller") is True: # Предполагаем, что это поле есть в контракте
            continue
        
        # Проверяем наличие цены и ее валидность
        p = offer.get("price")
        if p is None or p <= 0:
            continue
            
        prices.append(p)

    # 4. Если подходящих предложений нет, вернуть текущую цену и NULL
    if not prices:
        return {"price": current_price, "decision": None, "reason": "Нет подходящих предложений"}

    # 5. Расчет цены
    min_competitor_price = min(prices)
    
    # Умножаем на 1.5 и округляем ВНИЗ до копеек (ROUND_FLOOR)
    # Внимание: в коде из скриншота была ошибка - использовалось round() вместо quantize с ROUND_FLOOR
    calculated_price = (min_competitor_price * Decimal("1.5")).quantize(Decimal("0.01"), rounding=ROUND_FLOOR)
    
    # Рекомендация - максимум из рассчитанной суммы и min_price
    recommended_price = max(calculated_price, min_price)

    # Проверка на резкое изменение (больше 30%)
    if current_price > 0:
        change_ratio = (recommended_price - current_price) / current_price
        # Если изменение больше 30% в любую сторону
        if abs(change_ratio) > Decimal("0.3"):
            return {"price": current_price, "decision": None, "reason": "Резкое изменение"}

    return {"price": recommended_price, "decision": "APPLY", "reason": "Найдена минимальная цена"}


async def sample_fetch_offers():
    return [
        {"status": "success", "seller": "my_shop", "price": Decimal("4300.00"), "delivery_days": 1},
        {"status": "success", "seller": "reseller_shop", "price": Decimal("4100.00"), "delivery_days": 2, "is_reseller": True},
        {"status": "error", "seller": "bad_shop", "price": Decimal("4000.00")}
    ]

if __name__ == "__main__":
    # Небольшой пример для запуска
    async def main():
        res = await recommend_price(
            fetch_offers=sample_fetch_offers, 
            current_price=Decimal("5000.00"), 
            min_price=Decimal("4000.00")
        )
        print(res)
    
    asyncio.run(main())
