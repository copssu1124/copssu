"""
SmartStore Auto Collector (Phase 1: 단일 URL 자동 수집)
=========================================================
URL 한 개만 던지면:
1) URL → store_name + product_id 파싱
2) 페이지 HTML에서 channel_uid 추출
3) i/v2/channels/{uid}/products/{pid} API 호출 → 전체 옵션 JSON 수집

V21 분석기(an_find_options 등)에 그대로 먹일 수 있는 JSON을 반환합니다.

작성: 2026-05-26
"""
import os
import re
import time
import random
import requests
from typing import Optional, Tuple, Dict, Any

# .env 로딩 (app.py에서 이미 했어도 안전하게 한 번 더)
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass


def sanitize_cookie(raw: Optional[str]) -> str:
    """cURL을 통째로 붙여넣어도 동작하도록 쿠키 문자열 자동 정제.

    지원하는 입력 형태:
      1) 'NNB=...; NAC=...; ...' (이미 깔끔한 쿠키 문자열)
      2) "curl 'url' -H '...' -b 'NNB=...; ...'" (cURL 통째)
      3) 줄바꿈/백슬래시/탭이 섞인 cURL
    """
    if not raw:
        return ""
    s = raw.strip()

    # cURL 명령어가 통째로 들어온 경우 → -b '...' 또는 --cookie '...' 안의 값만 추출
    m = re.search(r"(?:-b|--cookie)\s+['\"]([^'\"]+)['\"]", s)
    if m:
        s = m.group(1)

    # 줄바꿈/CR/탭/백슬래시 제거 (requests가 거부하는 문자들)
    s = s.replace("\r", "").replace("\n", " ").replace("\t", " ").replace("\\", "")

    # 연속 공백 정리, 양옆 trim
    s = re.sub(r"\s+", " ", s).strip()

    return s


def _get_naver_cookie(user_cookie: Optional[str] = None) -> Optional[str]:
    """쿠키 우선순위: 함수 인자(사용자 입력) > env NAVER_COOKIE > None.
    cURL 통째 붙여넣기도 자동 정제해서 처리.
    """
    if user_cookie:
        c = sanitize_cookie(user_cookie)
        if c:
            return c
    c = sanitize_cookie(os.environ.get("NAVER_COOKIE", ""))
    return c if c else None


# --------------------------------------------------------------------------
# 기본 헤더 (Chrome 모방). User-Agent는 자주 바꿔주는 편이 안전.
# --------------------------------------------------------------------------
_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)

_PAGE_HEADERS = {
    "accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "accept-encoding": "gzip, deflate, br",
    "cache-control": "max-age=0",
    "user-agent": _DEFAULT_UA,
    "upgrade-insecure-requests": "1",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
}

_API_HEADERS_BASE = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "user-agent": _DEFAULT_UA,
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-service-type": "NONE",
}


# --------------------------------------------------------------------------
# 1단계: URL 파싱
# --------------------------------------------------------------------------
_URL_PATTERNS = [
    # https://smartstore.naver.com/{store}/products/{pid}
    re.compile(r"smartstore\.naver\.com/([^/?#]+)/products/(\d+)"),
    # https://m.smartstore.naver.com/{store}/products/{pid}
    re.compile(r"m\.smartstore\.naver\.com/([^/?#]+)/products/(\d+)"),
    # https://brand.naver.com/{store}/products/{pid}
    re.compile(r"brand\.naver\.com/([^/?#]+)/products/(\d+)"),
]


def parse_smartstore_url(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    스마트스토어/브랜드스토어 URL에서 store_name, product_id 추출.

    Returns:
        (store_name, product_id) or (None, None)
    """
    if not url:
        return None, None
    for pat in _URL_PATTERNS:
        m = pat.search(url)
        if m:
            return m.group(1), m.group(2)
    return None, None


# --------------------------------------------------------------------------
# 2단계: 페이지 HTML → channel_uid 추출
# --------------------------------------------------------------------------
_CHANNEL_UID_PATTERNS = [
    re.compile(r'"channelUid"\s*:\s*"([^"]+)"'),
    re.compile(r'channelUid["\']?\s*[:=]\s*["\']([^"\']+)["\']'),
]


def fetch_channel_uid(store_name: str, product_id: Optional[str] = None,
                     session: Optional[requests.Session] = None,
                     timeout: int = 15,
                     warmup: bool = True,
                     max_retries: int = 3,
                     user_cookie: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    스토어 메인 또는 상품 페이지에서 channel_uid 추출.

    봇 탐지 회피 전략:
      1) 세션 워밍업: 스토어 메인을 먼저 GET 해서 쿠키 자연스럽게 받기
      2) Referer 단계적으로 세팅 (메인 → 상품)
      3) 429 발생시 지수 백오프로 재시도

    Returns:
        (channel_uid, error_message)
    """
    sess = session or requests.Session()

    store_main_url = f"https://smartstore.naver.com/{store_name}"
    if product_id:
        page_url = f"https://smartstore.naver.com/{store_name}/products/{product_id}"
    else:
        page_url = store_main_url

    # 쿠키 우선순위: 사용자 입력 > env NAVER_COOKIE
    cookie = _get_naver_cookie(user_cookie)

    # --- Step A: 세션 워밍업 (스토어 메인 페이지 먼저 방문해서 쿠키 받기) ---
    if warmup and product_id:
        warmup_headers = dict(_PAGE_HEADERS)
        # 첫 방문은 외부에서 온 것처럼
        warmup_headers["sec-fetch-site"] = "none"
        if cookie:
            warmup_headers["cookie"] = cookie
        try:
            sess.get(store_main_url, headers=warmup_headers, timeout=timeout)
        except requests.exceptions.RequestException:
            # 워밍업 실패해도 본 요청은 시도
            pass
        time.sleep(random.uniform(0.8, 1.5))

    # --- Step B: 본 페이지 요청 (재시도 포함) ---
    headers = dict(_PAGE_HEADERS)
    if warmup and product_id:
        # 워밍업 후의 자연스러운 referer
        headers["referer"] = store_main_url + "/"
        headers["sec-fetch-site"] = "same-origin"
    if cookie:
        headers["cookie"] = cookie

    last_err = None
    for attempt in range(max_retries):
        try:
            resp = sess.get(page_url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                html = resp.text
                for pat in _CHANNEL_UID_PATTERNS:
                    m = pat.search(html)
                    if m:
                        return m.group(1), None
                return None, "HTML에서 channelUid를 찾지 못함 (페이지 구조 변경 가능성)"
            elif resp.status_code == 429:
                # 봇 차단 — 더 긴 지수 백오프 (5/15/45초) + 랜덤 지터
                # 네이버 IP 차단은 보통 30초~1분 후 풀리므로 마지막 시도는 45초+
                wait = (3 ** attempt) * 5 + random.uniform(1.0, 4.0)
                last_err = f"HTTP 429 (봇 차단), {wait:.1f}초 대기 후 재시도 ({attempt+1}/{max_retries})"
                time.sleep(wait)
                continue
            else:
                last_err = f"페이지 응답 코드 {resp.status_code}"
                if 500 <= resp.status_code < 600:
                    # 서버 에러는 짧게 대기 후 재시도
                    time.sleep(2)
                    continue
                return None, last_err

        except requests.exceptions.Timeout:
            last_err = "페이지 요청 타임아웃"
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            return None, f"페이지 요청 실패: {e}"

    return None, last_err or "알 수 없는 페이지 요청 실패"


# --------------------------------------------------------------------------
# 3단계: 옵션 API 호출
# --------------------------------------------------------------------------
def fetch_product_options(channel_uid: str, product_id: str,
                          store_name: str,
                          session: Optional[requests.Session] = None,
                          timeout: int = 15,
                          user_cookie: Optional[str] = None) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    스마트스토어 v2 옵션 API 호출.

    엔드포인트:
        https://smartstore.naver.com/i/v2/channels/{channel_uid}/products/{product_id}?withWindow=false

    Returns:
        (json_data, error_message)
    """
    sess = session or requests.Session()
    api_url = (
        f"https://smartstore.naver.com/i/v2/channels/{channel_uid}"
        f"/products/{product_id}?withWindow=false"
    )

    headers = dict(_API_HEADERS_BASE)
    headers["referer"] = f"https://smartstore.naver.com/{store_name}/products/{product_id}"
    headers["x-client-lct"] = f"/{store_name}/products/{product_id}"

    # 쿠키 우선순위: 사용자 입력 > env NAVER_COOKIE
    cookie = _get_naver_cookie(user_cookie)
    if cookie:
        headers["cookie"] = cookie

    try:
        resp = sess.get(api_url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            try:
                return resp.json(), None
            except ValueError:
                return None, "응답을 JSON으로 파싱 실패"
        elif resp.status_code == 404:
            # v2가 안 되면 v1 폴백 시도
            api_url_v1 = api_url.replace("/i/v2/", "/i/v1/")
            resp_v1 = sess.get(api_url_v1, headers=headers, timeout=timeout)
            if resp_v1.status_code == 200:
                try:
                    return resp_v1.json(), None
                except ValueError:
                    return None, "v1 폴백 응답 JSON 파싱 실패"
            return None, f"v2/v1 모두 실패 (v2={resp.status_code}, v1={resp_v1.status_code})"
        else:
            return None, f"API 응답 코드 {resp.status_code}"

    except requests.exceptions.Timeout:
        return None, "API 요청 타임아웃"
    except requests.exceptions.RequestException as e:
        return None, f"API 요청 실패: {e}"


# --------------------------------------------------------------------------
# 통합 함수: URL 하나로 완성
# --------------------------------------------------------------------------
def auto_collect(url: str, sleep_sec: float = 0.5,
                 user_cookie: Optional[str] = None,
                 session: Optional[requests.Session] = None) -> Dict[str, Any]:
    """
    스마트스토어 URL 하나로 옵션 JSON까지 자동 수집.

    Args:
        url: 사용자가 입력하는 스마트스토어 상품 URL
        sleep_sec: 페이지 fetch와 API 호출 사이 대기 시간 (봇 차단 회피)

    Returns:
        {
            "ok": bool,
            "url": str,
            "store_name": str | None,
            "product_id": str | None,
            "channel_uid": str | None,
            "data": dict | None,      # 옵션 데이터 JSON (V21 파서 입력용)
            "error": str | None,
            "steps": [str]            # 진행 로그
        }
    """
    result = {
        "ok": False,
        "url": url,
        "store_name": None,
        "product_id": None,
        "channel_uid": None,
        "data": None,
        "error": None,
        "steps": [],
    }

    # 세션 — 외부에서 주입되면 재사용 (봇 차단 회피에 핵심), 아니면 새로 생성
    if session is None:
        session = requests.Session()

    # 쿠키 적용 상태 표시
    eff_cookie = _get_naver_cookie(user_cookie)
    if eff_cookie:
        src = "사용자 입력" if user_cookie else "환경변수(.env)"
        result["steps"].append(f"🍪 쿠키 적용됨 ({src}) — 로그인 상태로 요청")
    else:
        result["steps"].append("⚠️ 쿠키 없음 (비로그인 시도 → 봇 차단 가능성 매우 높음)")

    # Step 1: URL 파싱
    store_name, product_id = parse_smartstore_url(url)
    if not store_name or not product_id:
        result["error"] = "URL에서 store와 productId를 추출하지 못했습니다."
        result["steps"].append("❌ URL 파싱 실패")
        return result

    result["store_name"] = store_name
    result["product_id"] = product_id
    result["steps"].append(f"✅ URL 파싱: store={store_name}, productId={product_id}")

    # Step 2: 페이지 fetch → channelUid 추출
    time.sleep(sleep_sec * random.uniform(0.7, 1.3))  # 약간의 지터
    channel_uid, err = fetch_channel_uid(store_name, product_id, session=session, user_cookie=user_cookie)
    if not channel_uid:
        result["error"] = f"channelUid 추출 실패: {err}"
        result["steps"].append(f"❌ channelUid 추출 실패: {err}")
        return result

    result["channel_uid"] = channel_uid
    result["steps"].append(f"✅ channelUid 추출: {channel_uid}")

    # Step 3: 옵션 API 호출
    time.sleep(sleep_sec * random.uniform(0.7, 1.3))
    data, err = fetch_product_options(
        channel_uid, product_id, store_name, session=session, user_cookie=user_cookie
    )
    if not data:
        result["error"] = f"옵션 API 호출 실패: {err}"
        result["steps"].append(f"❌ 옵션 API 실패: {err}")
        return result

    result["data"] = data
    result["ok"] = True
    result["steps"].append(
        f"✅ 옵션 데이터 수집 완료 "
        f"(옵션 조합 {len(data.get('optionCombinations', []) or [])}개)"
    )
    return result


# --------------------------------------------------------------------------
# CLI 테스트용
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python smartstore_auto.py <스마트스토어 상품 URL>")
        sys.exit(1)

    test_url = sys.argv[1]
    print(f"\n[테스트] {test_url}\n")
    r = auto_collect(test_url)

    for step in r["steps"]:
        print("  " + step)

    print()
    if r["ok"]:
        d = r["data"]
        print("=== 수집 결과 요약 ===")
        print(f"  상품명: {d.get('name')}")
        print(f"  기본 판매가: {d.get('salePrice'):,}원")
        bv = d.get("benefitsView") or {}
        if bv.get("discountedSalePrice"):
            print(f"  즉시할인가: {bv['discountedSalePrice']:,}원")
        opts = d.get("optionCombinations") or []
        print(f"  옵션 조합: {len(opts)}개")
        if opts:
            sample = opts[0]
            print(f"  예시 옵션[0]: {sample.get('optionName1')} / {sample.get('optionName2')} "
                  f"(옵션가 {sample.get('price')}, 재고 {sample.get('stockQuantity')})")

        # 옵션 데이터 파일로 저장 (V21 파서 테스트용)
        out_path = "fetched_options.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        print(f"\n  → 전체 응답이 {out_path}에 저장됨 (V21에 붙여넣기 테스트 가능)")
    else:
        print(f"❌ 실패: {r['error']}")
