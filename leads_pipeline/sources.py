"""
leads_pipeline/sources.py
多源抓取 - BOSS / tyc / bid / 1688 / patent
"""
import re
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from config import ENABLED_SOURCES, PRODUCT_TARGETS

# 复用 tyc-mcp 已经搜过的结果作为缓存
_TYC_CACHE: Dict[str, Any] = {}


def normalize_company_name(name: str) -> str:
    """标准化公司名（去地区/公司类型/括号）"""
    n = name
    # 去括号内容
    n = re.sub(r"[\(（][^)）]*[\)）]", "", n)
    # 去地区前缀
    for kw in ['深圳市', '广州市', '东莞市', '广东', '上海', '北京', '江苏', '浙江', '惠州', '佛山',
               '中山', '珠海', '四川', '湖北', '湖南', '江西', '安徽', '福建', '山东', '陕西',
               '辽宁', '云南', '广西', '海南', '河北', '山西', '河南', '内蒙古', '宁夏', '新疆',
               '西藏', '青海', '香港', '重庆', '天津', '南京', '苏州', '无锡', '常州', '杭州',
               '宁波', '温州', '青岛', '济南', '厦门', '泉州', '福州']:
        n = n.replace(kw, '')
    # 去公司类型后缀
    for kw in ['科技股份有限公司', '股份有限公司', '有限责任公司', '有限公司', '科技公司',
               '实业有限公司', '实业有限公司', '公司', '企业', '有限合伙']:
        n = n.replace(kw, '')
    return n.strip()


# ============================================================
# 数据源 1: BOSS 直聘 / 猎聘 / 智联（web_search 搜公司名）
# ============================================================
def fetch_boss_leads(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从招聘平台抓潜在客户（用 web_search）"""
    if not ENABLED_SOURCES["boss"]:
        return []
    leads = []
    # 由于没有 BOSS 专用 API，用 web_search 模拟
    for query in product.get("search_queries_boss", [])[:3]:  # 每个料号最多 3 个查询
        try:
            # 此处调用 web_search（实际由调用方传入）
            # 这里只生成 query 列表，由 run_leads.py 真正抓取
            leads.append({
                "source": "boss",
                "query": query,
                "scenario": product["scenarios"][0] if product["scenarios"] else "",
                "raw": None,  # 占位
            })
        except Exception as e:
            print(f"  [boss] {query} failed: {e}")
    return leads


# ============================================================
# 数据源 2: tyc 工商（直接调 API）
# ============================================================
def fetch_tyc_leads(product: Dict[str, Any], tyc_call) -> List[Dict[str, Any]]:
    """从 tyc 抓潜在客户"""
    if not ENABLED_SOURCES["tyc"]:
        return []
    leads = []
    for query in product.get("search_queries_tyc", [])[:3]:
        try:
            cache_key = f"tyc_search:{query}"
            if cache_key in _TYC_CACHE:
                result_md = _TYC_CACHE[cache_key]
            else:
                result = tyc_call(query=query, page=1, page_size=20)
                # result 是结构化数据，但 tyc-mcp 工具返回 Markdown
                # 简化处理：让调用方传入 tyc-mcp 实际结果
                _TYC_CACHE[cache_key] = result
                result_md = result
            
            # 解析 markdown 表格 - 调用方处理
            leads.append({
                "source": "tyc",
                "query": query,
                "result": result_md,
            })
        except Exception as e:
            print(f"  [tyc] {query} failed: {e}")
    return leads


# ============================================================
# 数据源 3-5: 其他源（占位，后续启用）
# ============================================================
def fetch_bid_leads(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not ENABLED_SOURCES["bid"]:
        return []
    return []


def fetch_1688_leads(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not ENABLED_SOURCES["1688"]:
        return []
    return []


def fetch_patent_leads(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not ENABLED_SOURCES["patent"]:
        return []
    return []


# ============================================================
# 主入口
# ============================================================
def fetch_all_sources(product: Dict[str, Any], tyc_call=None) -> Dict[str, List[Dict]]:
    """并行抓取所有源"""
    results = {"boss": [], "tyc": [], "bid": [], "1688": [], "patent": []}
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_boss_leads, product): "boss",
            executor.submit(fetch_tyc_leads, product, tyc_call): "tyc",
            executor.submit(fetch_bid_leads, product): "bid",
            executor.submit(fetch_1688_leads, product): "1688",
            executor.submit(fetch_patent_leads, product): "patent",
        }
        for fut in as_completed(futures):
            source = futures[fut]
            try:
                results[source] = fut.result()
            except Exception as e:
                print(f"  [{source}] failed: {e}")
    return results
