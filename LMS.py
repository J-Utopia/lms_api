import requests
import re
import time

# =====================
# SIMPLE TTL CACHE
# =====================
_CACHE = {}
_CACHE_TTL = 300  # 5분 (초)

# =====================
# API URLs
# =====================
PRODUCT_URL = "https://b2c-api.modetour.com/Package/GetProductAllInfoById?productId="
SCHEDULE_URL = "https://b2c-api.modetour.com/Package/GetScheduleTabData?groupNumber="

# =====================
# VISA KEYWORDS (OR)
# =====================
VISA_PATTERN = re.compile("출입국|서류|비자|입국|신고서|작성|온라인|안내")

# =====================
# COMMON
# =====================
def fetch_json(url: str) -> dict:
    res = requests.get(url, timeout=10)
    res.raise_for_status()
    return res.json()


def clean_text(value) -> str:
    if not value:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)   # HTML 제거
    text = re.sub(r"\s+", " ", text)       # 공백 정리
    return text.strip()

# =====================
# VISA (Schedule API)
# =====================
def extract_visa_from_schedule(schedule_json: dict) -> dict | None:
    schedule_items = schedule_json.get("result", {}).get("scheduleItemList", [])

    for day_idx, day in enumerate(schedule_items):
        actions = day.get("ortherActions") or day.get("otherActions") or []
        for action in actions:
            summary = clean_text(action.get("summaryDes"))
            detail = clean_text(action.get("detailDes"))
            merged = f"{summary} {detail}"

            if merged and VISA_PATTERN.search(merged):
                return {
                    "dayIndex": day_idx + 1,
                    "summaryDes": summary,
                    "detailDes": detail
                }
    return None

# =====================
# REAL LOGIC (NO CACHE)
# =====================
def _fetch_combined_product_info(input_id: int) -> dict:
    product_json = fetch_json(f"{PRODUCT_URL}{input_id}")
    schedule_json = fetch_json(f"{SCHEDULE_URL}{input_id}")

    content = product_json.get("content", {})

    result = {
        # 1) 지역정보
        "region": {
            "category1": content.get("category1"),
            "category2": content.get("category2"),
            "category3": content.get("category3"),
        },

        # 2) 상품명
        "productName": content.get("productName"),

        # 3) 공항미팅
        "meeting": {
            "meetingPlaceCode": content.get("meetingPlaceCode"),
            "meetingTime": content.get("meetingTime"),
            "meetingPlace2": content.get("meetingPlace2"),
        },

        # 4) 항공정보
        "flight": {
            "departureAirlineName": content.get("departureAirlineName"),
            "arrivalAirlineName": content.get("arrivalAirlineName"),
            "departure": {
                "departureFlight": content.get("departureFlight"),
                "departureTime": content.get("departureTime"),
                "localArrivalTime": content.get("localArrivalTime"),
            },
            "arrival": {
                "arrivalFlight": content.get("arrivalFlight"),
                "localDepartureTime": content.get("localDepartureTime"),
                "arrivalTime": content.get("arrivalTime"),
            },
        },

        # 6) 비자정보 (일정 API 기준)
        "visa_from_schedule": extract_visa_from_schedule(schedule_json),
    }

    return result

# =====================
# CACHE WRAPPER (PUBLIC)
# =====================
def fetch_combined_product_info(input_id: int) -> dict:
    now = time.time()

    # 캐시 히트
    if input_id in _CACHE:
        cached_data, cached_time = _CACHE[input_id]
        if now - cached_time < _CACHE_TTL:
            return cached_data

    # 캐시 미스
    data = _fetch_combined_product_info(input_id)
    _CACHE[input_id] = (data, now)
    return data
