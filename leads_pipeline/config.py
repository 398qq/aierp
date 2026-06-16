"""
leads_pipeline/config.py
潜在客户自动化管道 - 配置文件
"""

# 首批 3 个料号 → 各自的应用场景 + 搜索词矩阵
# 后续可扩到 25 品牌
PRODUCT_TARGETS = [
    {
        "sku": "CJC8988",
        "name": "CJC8988 音频 ADC/DAC",
        "brand": "CJC",
        "alternative_to": "MS8413 / WM8988 / PCM1808",
        "scenarios": ["蓝牙耳机", "智能音箱", "TWS耳机", "蓝牙音箱", "Soundbar", "直播声卡"],
        "search_queries_boss": [
            "蓝牙耳机 硬件工程师 深圳",
            "蓝牙耳机 嵌入式工程师 深圳",
            "TWS 硬件工程师 东莞",
            "智能音箱 硬件工程师 深圳",
            "音响 嵌入式软件工程师 深圳",
        ],
        "search_queries_tyc": [
            "蓝牙耳机 ODM",
            "音响设备制造",
            "智能音箱 工厂",
            "家用视听设备",
            "TWS耳机 工厂",
        ],
        "tyc_industries": ["C395", "C396", "C397"],  # 家用视听 / 音响设备 / 电子器件
        "tyc_regions": ["4403", "4404", "4419"],  # 深圳 / 珠海 / 东莞
    },
    {
        "sku": "HK32F0301MF4P7C-TR",
        "name": "航顺 HK32F030 Cortex-M0 MCU",
        "brand": "HK",
        "alternative_to": "STM32F030 / GD32E230",
        "scenarios": ["小家电", "智能家居", "IoT", "电动工具", "玩具"],
        "search_queries_boss": [
            "小家电 嵌入式工程师 中山",
            "智能家居 硬件工程师 深圳",
            "电动工具 嵌入式工程师 宁波",
            "IoT 嵌入式 工程师 深圳",
        ],
        "search_queries_tyc": [
            "小家电 工厂",
            "智能家居 工厂",
            "电动工具 工厂",
            "IoT 设备 制造",
        ],
        "tyc_industries": ["C385", "C386", "C387"],  # 家用电力器具 / 智能家居等
        "tyc_regions": ["4403", "4420", "4419", "3302"],  # 深圳/中山/东莞/宁波
    },
    {
        "sku": "QMI8658B",
        "name": "QST QMI8658B 6轴 IMU",
        "brand": "QST",
        "alternative_to": "MPU6050 / ICM42607",
        "scenarios": ["无人机", "扫地机器人", "平衡车", "智能穿戴", "手持云台"],
        "search_queries_boss": [
            "无人机 飞控 工程师 深圳",
            "扫地机器人 嵌入式 工程师",
            "平衡车 硬件 工程师",
            "智能穿戴 嵌入式 工程师 深圳",
        ],
        "search_queries_tyc": [
            "无人机 工厂",
            "扫地机器人 工厂",
            "平衡车 工厂",
            "智能穿戴 工厂",
        ],
        "tyc_industries": ["C396", "C397", "C398"],
        "tyc_regions": ["4403", "4419"],  # 深圳/东莞
    },
]

# 抓取源开关（先开 2 个源跑通）
ENABLED_SOURCES = {
    "boss": True,         # BOSS 直聘 + 猎聘 + 智联
    "tyc": True,          # tyc 工商
    "bid": False,         # tyc search_bids（暂关）
    "1688": False,        # 1688 询价单（暂关）
    "patent": False,      # 专利网（暂关）
}

# 去重算法
DEDUP_CONFIG = {
    "match_substring_min_len": 4,  # 子串匹配最短长度
    "name_normalize": True,         # 标准化（去地区/公司类型）
    "industry_size_filter": {
        # 过滤掉太小的
        "min_employee": 5,         # 最小参保人数
        "max_employee": 100000,    # 最大（过滤集团大厂）
        "min_capital": 10,         # 最小注册资本（万）
    },
}

# 输出配置
OUTPUT_CONFIG = {
    "digest_dir": "/home/ttdiy/.openclaw/workspace/1_业务开发/机会池/周报",
    "max_leads_per_product": 20,   # 每个料号最多出 20 家
    "confidence_threshold": 0.4,   # 最低置信度
}
