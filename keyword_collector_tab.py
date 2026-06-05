"""키워드 자동 수집기 탭 (Phase 3) — 키워드 → 네이버 쇼핑 검색 → 스마트스토어 자동 분석."""
import io
import os
import re
import json
import time
import random
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

from smartstore_auto import auto_collect
from bulk_collector_tab import _flatten_options, _summary_row, _build_excel


_SHOP_API_URL = "https://openapi.naver.com/v1/search/shop.json"
_SMARTSTORE_RE = re.compile(r"smartstore\.naver\.com/([^/?#]+)/products/(\d+)")
_BRAND_RE = re.compile(r"brand\.naver\.com/([^/?#]+)/products/(\d+)")


def _get_naver_api_keys():
    """env에서 CLIENT_ID_N / CLIENT_SECRET_N 키 쌍 모두 수집 (1~5번)."""
    pairs = []
    for i in range(1, 10):
        cid = os.environ.get(f"CLIENT_ID_{i}", "").strip()
        csec = os.environ.get(f"CLIENT_SECRET_{i}", "").strip()
        if cid and csec:
            pairs.append((cid, csec))
    return pairs


def search_naver_shop(keyword, display=20, sort="sim", start=1):
    """네이버 쇼핑 검색 API 호출.

    Returns:
        (items, error_message)
    """
    pairs = _get_naver_api_keys()
    if not pairs:
        return None, ".env에 CLIENT_ID_1 / CLIENT_SECRET_1이 없습니다."

    last_err = None
    for cid, csec in pairs:
        headers = {
            "X-Naver-Client-Id": cid,
            "X-Naver-Client-Secret": csec,
        }
        params = {
            "query": keyword,
            "display": min(100, max(1, display)),
            "start": max(1, start),
            "sort": sort,
        }
        try:
            resp = requests.get(_SHOP_API_URL, headers=headers, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("items", []), None
            elif resp.status_code == 429:
                # 키 쿼터 초과 → 다음 키 시도
                last_err = f"키 {cid[:8]}... 쿼터 초과, 다음 키 시도"
                continue
            else:
                last_err = f"API 응답 코드 {resp.status_code}: {resp.text[:200]}"
        except requests.exceptions.RequestException as e:
            last_err = f"요청 실패: {e}"
            continue
    return None, last_err or "모든 API 키 실패"


def _strip_html(s):
    """검색 결과 title의 <b>...</b> 같은 태그 제거."""
    if not s:
        return ""
    return re.sub(r"<[^>]+>", "", str(s))


def _classify_items(items):
    """검색 결과를 스마트스토어/브랜드스토어/기타 로 분류."""
    smartstore = []
    brand = []
    others = []
    for it in items:
        link = it.get("link", "")
        title = _strip_html(it.get("title", ""))
        item_info = {
            "title": title,
            "link": link,
            "lprice": int(it.get("lprice") or 0),
            "mallName": it.get("mallName", ""),
            "productId": it.get("productId", ""),
            "image": it.get("image", ""),
            "category": it.get("category4") or it.get("category3") or "",
        }
        if _SMARTSTORE_RE.search(link):
            smartstore.append(item_info)
        elif _BRAND_RE.search(link):
            brand.append(item_info)
        else:
            others.append(item_info)
    return smartstore, brand, others


def render_keyword_collector_tab():
    """마스터 툴의 '키워드 수집기' 탭."""
    # CSS — expander 화살표 깨짐 차단
    st.markdown(
        """
<style>
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpanderToggleIcon"] *,
details > summary svg,
details > summary [class*="material"] {
    visibility: hidden !important;
    width: 0 !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🔍 스마트스토어 키워드 자동 수집기 V1")
    st.markdown(
        "키워드 한 단어로 → 네이버 쇼핑 검색 → 스마트스토어 상위 N개 자동 분석 → 통합 엑셀."
    )

    # 쿠키 + API 키 확인
    has_cookie = bool(st.session_state.get("naver_cookie_user", "").strip())
    api_keys = _get_naver_api_keys()

    status_c1, status_c2 = st.columns(2)
    with status_c1:
        if has_cookie:
            st.success("✅ 네이버 쿠키 OK (자동 수집기 탭에서 입력한 것)")
        else:
            st.warning("⚠️ 쿠키 미입력 — 자동 수집기 탭에서 먼저 입력해주세요")
    with status_c2:
        if api_keys:
            st.success(f"✅ 네이버 검색 API 키 {len(api_keys)}개 (.env에서 로드)")
        else:
            st.error("❌ .env에 CLIENT_ID_1 / CLIENT_SECRET_1 필요")

    # 검색 입력
    st.markdown("#### 1️⃣ 키워드 검색")
    kw_c1, kw_c2, kw_c3 = st.columns([3, 1, 1])
    with kw_c1:
        keyword = st.text_input(
            "키워드",
            placeholder="예: 택배봉투, 야자매트, 보행매트",
            key="kw_query",
        )
    with kw_c2:
        display = st.number_input("검색 개수", 5, 100, 30, 5, key="kw_display",
                                   help="네이버 API 최대 100개")
    with kw_c3:
        sort = st.selectbox("정렬",
                            ["sim", "date", "asc", "dsc"],
                            format_func=lambda x: {
                                "sim": "정확도순", "date": "최신순",
                                "asc": "가격오름", "dsc": "가격내림"
                            }[x],
                            key="kw_sort")

    if st.button("🔎 검색 실행", use_container_width=True,
                 disabled=(not api_keys or not keyword.strip()), key="kw_search"):
        with st.spinner("네이버 쇼핑 검색 중..."):
            items, err = search_naver_shop(keyword.strip(), display=display, sort=sort)
        if err:
            st.error(f"검색 실패: {err}")
        else:
            st.session_state["kw_items"] = items or []
            st.session_state["kw_keyword_used"] = keyword.strip()
            st.rerun()

    items = st.session_state.get("kw_items", [])
    if not items:
        return

    # 검색 결과 분류
    smartstore_items, brand_items, others = _classify_items(items)

    st.markdown("#### 2️⃣ 검색 결과")
    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("총 결과", len(items))
    rc2.metric("스마트스토어", len(smartstore_items))
    rc3.metric("브랜드스토어", len(brand_items))
    rc4.metric("기타 (분석 불가)", len(others))

    if not smartstore_items and not brand_items:
        st.warning("스마트스토어/브랜드스토어 상품이 없습니다. 다른 키워드로 검색해보세요.")
        return

    # 분석 대상 미리보기
    target_items = smartstore_items + brand_items
    df_preview = pd.DataFrame([
        {
            "상품명": it["title"],
            "스토어": it["mallName"],
            "가격": it["lprice"],
            "카테고리": it["category"],
            "URL": it["link"],
        }
        for it in target_items
    ])
    st.dataframe(
        df_preview.style.format({"가격": "{:,.0f}원"}),
        use_container_width=True, height=300,
    )

    # 일괄 분석 옵션
    st.markdown("#### 3️⃣ 일괄 자동 분석")
    opt_c1, opt_c2, opt_c3 = st.columns(3)
    with opt_c1:
        sleep_sec = st.slider("URL 사이 대기 (초)", 1.0, 15.0, 7.0, 0.5, key="kw_sleep",
                              help="여러 스토어 섞임 → 7초+ 권장")
    with opt_c2:
        margin_rate = st.slider("🎯 목표 마진 (%)", 5, 80, 40, key="kw_margin")
    with opt_c3:
        fee_rate = st.number_input("💸 수수료/광고비 (%)", 0.0, 30.0, 9.0, 0.5, key="kw_fee")

    if st.button(f"🚀 {len(target_items)}개 상품 자동 분석 실행",
                 use_container_width=True, type="primary",
                 disabled=(not has_cookie or not target_items),
                 key="kw_run"):
        user_cookie = st.session_state.get("naver_cookie_user", "").strip() or None

        progress = st.progress(0, text="시작...")
        status_box = st.empty()
        results = []
        current_pacing = sleep_sec

        # 단일 세션 공유 (봇 차단 회피 핵심)
        shared_session = requests.Session()

        for i, it in enumerate(target_items):
            url = it["link"]
            progress.progress(
                (i + 1) / len(target_items),
                text=f"({i+1}/{len(target_items)}) 페이싱 {current_pacing:.1f}초 · {it['title'][:50]}",
            )
            status_box.info(f"분석 중: {it['title']} ({it['mallName']})")
            r = auto_collect(url, user_cookie=user_cookie, session=shared_session)
            results.append(r)

            # 적응형 페이싱
            if not r.get("ok") and "429" in (r.get("error") or ""):
                current_pacing = min(30.0, current_pacing * 1.5)
                status_box.warning(f"⚠️ 차단 감지 → 페이싱 {current_pacing:.1f}초로 자동 증가")
            else:
                current_pacing = max(sleep_sec, current_pacing * 0.9)

            if i < len(target_items) - 1:
                wait = current_pacing + random.uniform(-0.5, 0.5)
                time.sleep(max(0.5, wait))

        st.session_state["kw_results"] = results
        progress.empty()
        status_box.empty()
        # 결과 누적 표시 버그 차단
        st.rerun()
        st.rerun()

    # 결과 표시
    results = st.session_state.get("kw_results", [])
    if not results:
        return

    st.markdown("#### 4️⃣ 분석 결과")
    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("총 분석", len(results))
    sc2.metric("성공", ok_count)
    sc3.metric("실패", fail_count,
               delta=f"-{fail_count}" if fail_count else None,
               delta_color="inverse" if fail_count else "normal")

    df_summary = pd.DataFrame([_summary_row(r) for r in results])
    if not df_summary.empty:
        st.markdown("##### 📋 상품별 요약")
        st.dataframe(
            df_summary.style.format({
                "기본판매가": "{:,.0f}원",
                "즉시할인가": "{:,.0f}원",
                "최저가": "{:,.0f}원",
                "최고가": "{:,.0f}원",
                "평균가": "{:,.0f}원",
            }),
            use_container_width=True, height=400,
        )

    fails = [r for r in results if not r.get("ok")]
    if fails:
        with st.expander(f"❌ 실패 {len(fails)}개", expanded=False):
            for r in fails:
                st.markdown(f"- `{r.get('url','')}` — {r.get('error','')}")

    # 엑셀 다운로드
    margin = st.session_state.get("kw_margin", 40)
    fee = st.session_state.get("kw_fee", 9.0)
    excel_bytes = _build_excel(results, margin, fee)
    keyword_used = st.session_state.get("kw_keyword_used", "키워드")
    fname = f"smartstore_keyword_{keyword_used}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    st.download_button(
        "📥 통합 엑셀 다운로드 (검색 결과 + 옵션 상세 + 마진 분석)",
        data=excel_bytes,
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )

    if st.button("🗑️ 결과 지우기", key="kw_clear"):
        st.session_state.pop("kw_results", None)
        st.session_state.pop("kw_items", None)
        st.rerun()
