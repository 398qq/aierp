---
name: brand-intel
description: Fetch and analyze brand intelligence data from aierp backend — brand health, co-purchase recommendations, customer penetration
user-invocable: true
argument-hint: <brand_name>
---

# Brand Intelligence Skill

Fetch and analyze brand intelligence data from the aierp system.

## Task

Analyze the specified brand and return structured intelligence data.

## How to Find Brand Data

### 1. Brand Health Assessment

```bash
cd /home/ttdiy/aierp/backend
python3 -c "
import asyncio
from app.services.brand_intel_service import assess_brand_risk
async def main():
    result = await assess_brand_risk('品牌名')
    print(result)
asyncio.run(main())
"
```

### 2. Co-purchase Brand Recommendations

```bash
cd /home/ttdiy/aierp/backend
python3 -c "
import asyncio
from app.services.brand_intel_service import recommend_brands
async def main():
    result = await recommend_brands('品牌名')
    print(result)
asyncio.run(main())
"
```

### 3. Customer Penetration

```bash
cd /home/ttdiy/aierp/backend
python3 -c "
import asyncio
from app.services.brand_intel_service import get_brand_customer_penetration
async def main():
    result = await get_brand_customer_penetration('品牌名')
    print(result)
asyncio.run(main())
"
```

## Output Format

Return structured JSON with:
- `health_score`: 0-100 integer
- `risk_level`: "Low" | "Medium" | "High" | "Critical"
- `top_suppliers`: list of {name, product_count, share_percentage}
- `shared_customers`: count of overlapping customers
- `candidate_brands`: top 3 recommended brands with scores

## Notes

- All functions require `brand_name` as first argument
- Results are cached in PostgreSQL, refresh via API call to `/api/v1/ai/brand/...`
- Some brands may have no data — report "暂无数据" rather than fabricating
