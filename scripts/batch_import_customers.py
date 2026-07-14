#!/usr/bin/env python3
"""Batch import customers from TYC data."""

import httpx
import asyncio

BASE_URL = "http://localhost:8080"
USERNAME = "admin"
PASSWORD = "admin123"

# 10 家公司数据（干帆电子商务有限公司未找到）
CUSTOMERS = [
    {
        "name": "深圳市优像达科技有限公司",
        "contact_person": "庄利民",
        "phone": "13692166366",
        "email": "3224145101@qq.com",
        "address": "深圳市龙华区大浪街道横朗社区龙泉科技工业园 1 号 512-513",
        "tax_id": "91440300334993196K",
        "level": "B",
        "notes": "摄像头模组/USB 摄像头/车载摄像头，26 人，2015 年成立，100 万实缴"
    },
    {
        "name": "深圳元捷信息技术有限公司",
        "contact_person": "刘元",
        "phone": "18823703983",
        "email": "18823703983@163.com",
        "address": "深圳市龙华区大浪街道横朗社区龙泉科技工业园 1 号 508",
        "tax_id": "91440300MA5EYCJX8G",
        "level": "C",
        "notes": "条码扫描识别设备/扫码方案，6 人，2018 年成立，曾用名：博万得"
    },
    {
        "name": "深圳市昊玥季芯片技术有限公司",
        "contact_person": "莫春凤",
        "phone": "15766534952",
        "email": "",
        "address": "深圳市龙华区大浪街道横朗社区龙泉科技工业园 1 号 502",
        "tax_id": "91440300MA5HBD6J04",
        "level": "C",
        "notes": "芯片设计研发，4 人微型，2022 年成立，30 万注册资本"
    },
    {
        "name": "深圳市立诚医疗器械有限公司",
        "contact_person": "赵成",
        "phone": "0755-21001582",
        "email": "3423200233@qq.com",
        "address": "深圳市龙华区大浪街道同胜社区龙泉科技工业园 1 号 2 层 201 室",
        "tax_id": "91440300MA5F5QAA3P",
        "level": "B",
        "notes": "医疗器械销售/租赁/维修，9 人，2018 年成立，208 万实缴"
    },
    {
        "name": "皇景光电（深圳）有限公司",
        "contact_person": "林曼倩",
        "phone": "18565711359",
        "email": "danlin_xu@himax.com.cn",
        "address": "深圳市福田区福田街道福山社区滨河大道 5020 号同心大厦 16 层",
        "tax_id": "91440300783907396P",
        "level": "A",
        "notes": "⭐重点：显示器驱动 IC/矽控液晶光阀/微型投影仪光机模块，103 人中型外资，200 万美元实缴，2006 年成立，Himax 系"
    },
    {
        "name": "富士北亚租赁（深圳）有限公司",
        "contact_person": "黄建豪",
        "phone": "17688968661",
        "email": "gjcao@nasholdings.com",
        "address": "深圳市前海深港合作区南山街道兴海大道 3044 号信利康大厦 5H85A",
        "tax_id": "91440300360016882U",
        "level": "C",
        "notes": "融资租赁/机械设备租赁，16 人，2016 年成立，3000 万美元，外资，非目标行业"
    },
    {
        "name": "深圳市炽顺供应链有限公司",
        "contact_person": "朱华秀",
        "phone": "0755-88899650",
        "email": "chishun0101@163.com",
        "address": "深圳市龙华区大浪街道同胜社区龙泉科技工业园 1 号 3 层 301",
        "tax_id": "91440300MADARH7G9C",
        "level": "C",
        "notes": "供应链管理服务，0 人参保，2024 年成立，10 万实缴，微型"
    },
    {
        "name": "深圳市诚鑫旺科技有限公司",
        "contact_person": "汪伟",
        "phone": "13923746208",
        "email": "13923746208@139.com",
        "address": "深圳市龙华区大浪街道横朗社区龙泉科技工业园 1 号 2 层",
        "tax_id": "91440300596780449M",
        "level": "B",
        "notes": "高频变压器/低频变压器/音频变压器/电感，11 人，2012 年成立，500 万注册/50 万实缴"
    },
    {
        "name": "深圳台智光电材料科技有限公司",
        "contact_person": "潘智",
        "phone": "13538082805",
        "email": "2867352416@qq.com",
        "address": "深圳市龙华区大浪街道同胜社区龙泉科技工业园 1 号 2 层",
        "tax_id": "9144030035948403XL",
        "level": "B",
        "notes": "玻璃及玻璃制品/光电材料，9 人，2015 年成立，100 万实缴"
    },
    {
        "name": "深圳市拓建数码科技有限公司",
        "contact_person": "王建平",
        "phone": "15015334632",
        "email": "3306961883@qq.com",
        "address": "深圳市龙华区大浪街道同胜社区龙泉科技工业园 1 号 203",
        "tax_id": "91440300MA5HDYQ27R",
        "level": "C",
        "notes": "电子元器件零售/集成电路芯片销售，5 人，2022 年成立，100 万实缴"
    },
]

async def login(client: httpx.AsyncClient) -> str:
    """Login and return token."""
    resp = await client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"username": USERNAME, "password": PASSWORD}
    )
    resp.raise_for_status()
    data = resp.json()
    return data["data"]["token"]

async def create_customer(client: httpx.AsyncClient, token: str, customer: dict) -> dict:
    """Create a customer, return result."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = await client.post(
        f"{BASE_URL}/api/v1/customers",
        headers=headers,
        json=customer,
        timeout=10.0
    )
    result = resp.json()
    return {
        "name": customer["name"],
        "success": resp.status_code == 201,
        "status_code": resp.status_code,
        "message": result.get("msg", ""),
        "id": result.get("data", {}).get("id") if result.get("data") else None
    }

async def main():
    async with httpx.AsyncClient() as client:
        print("🔐 登录 ERP...")
        token = await login(client)
        print(f"✅ 登录成功\n")
        
        print(f"📝 开始录入 {len(CUSTOMERS)} 家客户...\n")
        
        results = []
        for i, cust in enumerate(CUSTOMERS, 1):
            print(f"[{i}/{len(CUSTOMERS)}] {cust['name']}...", end=" ")
            result = await create_customer(client, token, cust)
            results.append(result)
            
            if result["success"]:
                print(f"✅ ID={result['id']}")
            elif "已存在" in result["message"]:
                print(f"⚠️ 已存在")
            else:
                print(f"❌ {result['message']}")
        
        # Summary
        success = sum(1 for r in results if r["success"])
        exists = sum(1 for r in results if "已存在" in r["message"])
        failed = len(results) - success - exists
        
        print(f"\n{'='*60}")
        print(f"📊 录入完成：{success} 家成功，{exists} 家已存在，{failed} 家失败")
        print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(main())
