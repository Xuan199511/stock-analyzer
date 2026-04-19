"""Section 1: 公司基本資料."""
from __future__ import annotations

from .schemas import BusinessSegment, CompanyBasic
from .sources import yf as yf_src


_SECTOR_ZH = {
    "Technology":             "科技",
    "Financial Services":     "金融服務",
    "Healthcare":             "醫療保健",
    "Consumer Cyclical":      "非必需消費",
    "Consumer Defensive":     "必需消費",
    "Industrials":            "工業",
    "Energy":                 "能源",
    "Basic Materials":        "原物料",
    "Utilities":              "公用事業",
    "Real Estate":            "房地產",
    "Communication Services": "通訊服務",
}

_INDUSTRY_ZH = {
    # Technology
    "Semiconductors":                        "半導體",
    "Semiconductor Equipment & Materials":   "半導體設備與材料",
    "Software - Application":                "應用軟體",
    "Software - Infrastructure":             "基礎架構軟體",
    "Information Technology Services":       "資訊科技服務",
    "Computer Hardware":                     "電腦硬體",
    "Consumer Electronics":                  "消費性電子",
    "Electronic Components":                 "電子零組件",
    "Electronics & Computer Distribution":   "電子與電腦通路",
    "Scientific & Technical Instruments":    "科學與技術儀器",
    "Solar":                                 "太陽能",
    "Communication Equipment":               "通訊設備",
    # Communication Services
    "Internet Content & Information":        "網路內容與資訊",
    "Telecom Services":                      "電信服務",
    "Entertainment":                         "娛樂",
    "Broadcasting":                          "廣播",
    "Electronic Gaming & Multimedia":        "電子遊戲與多媒體",
    "Advertising Agencies":                  "廣告代理",
    "Publishing":                            "出版",
    # Consumer
    "Internet Retail":                       "網路零售",
    "Specialty Retail":                      "專業零售",
    "Apparel Retail":                        "服飾零售",
    "Apparel Manufacturing":                 "服飾製造",
    "Auto Manufacturers":                    "汽車製造",
    "Auto Parts":                            "汽車零件",
    "Auto & Truck Dealerships":              "汽車與卡車經銷",
    "Packaging & Containers":                "包裝與容器",
    "Restaurants":                           "餐飲",
    "Packaged Foods":                        "包裝食品",
    "Beverages - Non-Alcoholic":             "非酒精飲料",
    "Beverages - Wineries & Distilleries":   "酒類釀造",
    "Beverages - Brewers":                   "啤酒釀造",
    "Tobacco":                               "菸草",
    "Household & Personal Products":         "家用與個人用品",
    "Footwear & Accessories":                "鞋類與配件",
    "Luxury Goods":                          "奢侈品",
    "Leisure":                               "休閒用品",
    "Travel Services":                       "旅遊服務",
    "Lodging":                               "旅宿",
    "Gambling":                              "博弈",
    "Grocery Stores":                        "食品零售",
    "Discount Stores":                       "量販零售",
    "Department Stores":                     "百貨商場",
    # Financial
    "Banks - Regional":                      "區域銀行",
    "Banks - Diversified":                   "綜合銀行",
    "Capital Markets":                       "資本市場",
    "Asset Management":                      "資產管理",
    "Insurance - Life":                      "壽險",
    "Insurance - Property & Casualty":       "產險",
    "Insurance - Diversified":               "綜合保險",
    "Insurance - Reinsurance":               "再保險",
    "Insurance - Specialty":                 "專業保險",
    "Insurance Brokers":                     "保險經紀",
    "Credit Services":                       "信用服務",
    "Financial Data & Stock Exchanges":      "金融數據與證交所",
    "Financial Conglomerates":               "金融綜合集團",
    # Healthcare
    "Biotechnology":                         "生物科技",
    "Drug Manufacturers - General":          "大型製藥",
    "Drug Manufacturers - Specialty & Generic": "專科與學名藥廠",
    "Medical Devices":                       "醫療器材",
    "Medical Instruments & Supplies":        "醫療儀器與耗材",
    "Medical Care Facilities":               "醫療照護機構",
    "Medical Distribution":                  "醫藥通路",
    "Diagnostics & Research":                "診斷與研究",
    "Health Information Services":           "健康資訊服務",
    "Healthcare Plans":                      "健保方案",
    "Pharmaceutical Retailers":              "醫藥零售",
    # Industrials
    "Aerospace & Defense":                   "航太與國防",
    "Airlines":                              "航空",
    "Airports & Air Services":               "機場與航空服務",
    "Railroads":                             "鐵路",
    "Trucking":                              "貨運",
    "Marine Shipping":                       "海運",
    "Integrated Freight & Logistics":        "綜合物流",
    "Engineering & Construction":            "工程與營建",
    "Building Products & Equipment":         "建材與設備",
    "Industrial Distribution":               "工業通路",
    "Farm & Heavy Construction Machinery":   "農用與重型機械",
    "Specialty Industrial Machinery":        "特殊工業機械",
    "Specialty Business Services":           "專業商業服務",
    "Staffing & Employment Services":        "人力資源服務",
    "Consulting Services":                   "顧問服務",
    "Security & Protection Services":        "安全防護服務",
    "Rental & Leasing Services":             "租賃服務",
    "Waste Management":                      "廢棄物管理",
    "Pollution & Treatment Controls":        "汙染防治",
    "Electrical Equipment & Parts":          "電力設備與零件",
    "Tools & Accessories":                   "工具與配件",
    "Metal Fabrication":                     "金屬加工",
    "Conglomerates":                         "多角化集團",
    # Energy / Materials
    "Oil & Gas Integrated":                  "整合石油天然氣",
    "Oil & Gas E&P":                         "油氣探勘與生產",
    "Oil & Gas Midstream":                   "油氣中游",
    "Oil & Gas Refining & Marketing":        "煉油與銷售",
    "Oil & Gas Equipment & Services":        "油氣設備與服務",
    "Oil & Gas Drilling":                    "油氣鑽探",
    "Thermal Coal":                          "動力煤",
    "Uranium":                               "鈾礦",
    "Steel":                                 "鋼鐵",
    "Copper":                                "銅",
    "Aluminum":                              "鋁",
    "Gold":                                  "黃金",
    "Silver":                                "白銀",
    "Other Precious Metals & Mining":        "貴金屬與採礦",
    "Other Industrial Metals & Mining":      "工業金屬與採礦",
    "Chemicals":                             "化學",
    "Specialty Chemicals":                   "特用化學",
    "Agricultural Inputs":                   "農業投入",
    "Lumber & Wood Production":              "木材與木製品",
    "Paper & Paper Products":                "紙類與紙製品",
    "Coking Coal":                           "焦煤",
    # Utilities
    "Utilities - Regulated Electric":        "受監管電力",
    "Utilities - Regulated Gas":             "受監管天然氣",
    "Utilities - Regulated Water":           "受監管水務",
    "Utilities - Diversified":               "綜合公用事業",
    "Utilities - Renewable":                 "再生能源",
    "Utilities - Independent Power Producers": "獨立發電業者",
    # Real Estate
    "REIT - Industrial":     "工業型 REIT",
    "REIT - Residential":    "住宅型 REIT",
    "REIT - Retail":         "零售型 REIT",
    "REIT - Office":         "辦公型 REIT",
    "REIT - Healthcare":     "醫療型 REIT",
    "REIT - Hotel & Motel":  "旅宿型 REIT",
    "REIT - Specialty":      "特殊型 REIT",
    "REIT - Mortgage":       "抵押型 REIT",
    "REIT - Diversified":    "綜合型 REIT",
    "Real Estate Services":  "房地產服務",
    "Real Estate - Development": "房地產開發",
    "Real Estate - Diversified": "綜合房地產",
    # Textiles (common for TW)
    "Textile Manufacturing": "紡織製造",
    "Recreational Vehicles": "休閒車輛",
    "Furnishings, Fixtures & Appliances": "家具與家電",
    "Resorts & Casinos":     "度假村與賭場",
    "Education & Training Services": "教育訓練服務",
    "Personal Services":     "個人服務",
}


def _translate(val: str | None, table: dict) -> str | None:
    if not val:
        return val
    return table.get(val, val)


def analyze_company(symbol: str, market: str) -> CompanyBasic:
    info = yf_src.fetch_info(symbol, market)

    name        = info.get("longName") or info.get("shortName") or symbol
    industry_en = info.get("industry") or info.get("sector") or "N/A"
    sub_en      = info.get("industryDisp") or info.get("sector") or None
    description = (info.get("longBusinessSummary") or "").strip()

    industry     = _translate(industry_en, _INDUSTRY_ZH) if industry_en != "N/A" else "N/A"
    industry     = _translate(industry,    _SECTOR_ZH)
    sub_industry = _translate(sub_en,      _INDUSTRY_ZH)
    sub_industry = _translate(sub_industry, _SECTOR_ZH) if sub_industry else None

    # yfinance doesn't expose segment breakdowns for TW; leave empty and let
    # LLM fill in from description text in Phase 5.
    segments: list[BusinessSegment] = []

    return CompanyBasic(
        symbol=symbol,
        name=name,
        market=market.upper(),
        industry=industry,
        sub_industry=sub_industry,
        business_segments=segments,
        top_customers=None,
        supply_chain_position="N/A",
        description=description,
    )
