import pytest
from decimal import Decimal
from starter import recommend_price

# 1. Обычный расчет (успешный сценарий)
@pytest.mark.asyncio
async def test_recommend_price_success():
    async def mock_fetch():
        return [
            {"status": "success", "seller": "shop1", "price": Decimal("2000.00")},
            {"status": "success", "seller": "shop2", "price": Decimal("3000.00")},
        ]
    
    result = await recommend_price(
        fetch_offers=mock_fetch, 
        current_price=Decimal("3000.00"), 
        min_price=Decimal("1000.00")
    )
    
    # min_price конкурента = 2000, * 1.5 = 3000, max(3000, 1000) = 3000
    assert result["price"] == Decimal("3000.00")
    assert result["decision"] == "APPLY"

# 2. Сбой или граничный случай (таймаут источника)
@pytest.mark.asyncio
async def test_recommend_price_timeout():
    import asyncio
    async def mock_fetch():
        await asyncio.sleep(3) # Дольше чем timeout_s
        return [{"status": "success", "seller": "shop1", "price": Decimal("2000.00")}]
    
    result = await recommend_price(
        fetch_offers=mock_fetch, 
        current_price=Decimal("3000.00"), 
        min_price=Decimal("1000.00"),
        timeout_s=0.1 # Устанавливаем маленький таймаут
    )
    
    assert result["price"] == Decimal("3000.00")
    assert result["decision"] is None
    assert "Ошибка источника" in result["reason"]

# 3. Граничный случай: резкое изменение цены (больше 30%)
@pytest.mark.asyncio
async def test_recommend_price_sharp_change():
    async def mock_fetch():
        return [
            # 2000 * 1.5 = 3000
            {"status": "success", "seller": "shop1", "price": Decimal("2000.00")},
        ]
    
    # Текущая цена 1000, новая 3000. Изменение 200% > 30%
    result = await recommend_price(
        fetch_offers=mock_fetch, 
        current_price=Decimal("1000.00"), 
        min_price=Decimal("500.00")
    )
    
    assert result["price"] == Decimal("1000.00") # Остается текущей
    assert result["decision"] is None
    assert result["reason"] == "Резкое изменение"
