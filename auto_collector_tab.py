"""자동 수집기 탭 (Phase 1) — 마스터 툴 새 탭 UI"""
import json
import streamlit as st
import pandas as pd

from smartstore_auto import auto_collect, sanitize_cookie

# localStorage (브라우저 저장) — 쿠키 영구 보관용
try:
    from streamlit_local_storage import LocalStorage
    _LOCAL_STORAGE_OK = True
except Exception:
    _LOCAL_STORAGE_OK = False


def _get_local_storage():
    """LocalStorage 인스턴스를 한 번만 생성 (cache_resource)."""
    if not _LOCAL_STORAGE_OK:
        return None
    if "_local_storage_instance" not in st.session_state:
        st.session_state["_local_storage_instance"] = LocalStorage()
    return st.session_state["_local_storage_instance"]


def _calc_final_prices(data):
    base_sale = int(data.get("salePrice") or 0)
    bv = data.get("benefitsView") or {}
    base_discounted = int(bv.get("discountedSalePrice") or base_sale)

    opts = data.get("optionCombinations") or []
    rows = []
    for o in opts:
        opt_price = int(o.get("price") or 0)
        names = []
        for k in ("optionName1", "optionName2", "optionName3"):
            v = o.get(k)
            if v not in (None, ""):
                names.append(str(v))
        opt_label = " / ".join(names) if names else "(이름 없음)"
        rows.append({
            "옵션": opt_label,
            "기본판매가": base_sale,
            "옵션가(+/-)": opt_price,
            "최종 판매가": base_sale + opt_price,
            "할인 후 최종가": base_discounted + opt_price,
            "재고": o.get("stockQuantity"),
            "옵션ID": o.get("id"),
        })
    return base_sale, base_discounted, rows


def render_auto_collector_tab():
    # 토스 다크 테마 + Streamlit 아이콘 충돌 → 화살표 SVG/text 자체를 숨김
    # (헤더 텍스트 클릭은 어디서든 가능하므로 UX 영향 없음)
    st.markdown(
        """
<style>
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpanderToggleIcon"] *,
details > summary svg,
details > summary [class*="material"],
button[kind="headerNoPadding"] svg,
button[kind="headerNoPadding"] [class*="material"] {
    visibility: hidden !important;
    width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🚀 스마트스토어 자동 수집기 V1")
    st.markdown(
        "URL 한 개만 입력하면 → 페이지 분석 → channelUid 추출 → 옵션 API 자동 호출 → "
        "기본가 + 옵션가(+/-) 자동 계산까지 한 번에 처리합니다."
    )

    # === [클라우드 공유용] 본인 네이버 쿠키 입력 ===
    # localStorage에서 자동 로드 (브라우저에 저장된 쿠키 복원)
    ls = _get_local_storage()
    if ls and "naver_cookie_user" not in st.session_state:
        try:
            saved = ls.getItem("naver_cookie_saved")
            if saved:
                st.session_state["naver_cookie_user"] = saved
        except Exception:
            pass

    has_cookie = bool(st.session_state.get("naver_cookie_user", "").strip())
    status_emoji = "✅" if has_cookie else "⚠️"
    status_text = "쿠키 입력됨 (로그인 상태)" if has_cookie else "쿠키 미입력 (필수)"

    with st.expander(f"🔐 내 네이버 쿠키 입력  ·  {status_emoji} {status_text}", expanded=not has_cookie):
        st.caption(
            "네이버 봇 차단을 우회하려면 본인 로그인 쿠키가 필요합니다. "
            "한 번 입력하면 이 세션 동안 유지됩니다 (서버에 저장 안 됨, 메모리만)."
        )
        cookie_input = st.text_area(
            "쿠키 문자열 붙여넣기",
            value=st.session_state.get("naver_cookie_user", ""),
            height=120,
            placeholder="NNB=...; NAC=...; NID_AUT=...; NID_SES=...; ...",
            key="naver_cookie_textarea",
        )
        c_save, c_clear = st.columns([1, 1])
        with c_save:
            if st.button("💾 쿠키 저장 (영구)", use_container_width=True, key="ck_save"):
                cleaned = sanitize_cookie(cookie_input)
                if not cleaned:
                    st.error("쿠키를 추출하지 못했습니다. 입력 내용을 다시 확인해주세요.")
                else:
                    st.session_state["naver_cookie_user"] = cleaned
                    # localStorage에도 저장 (브라우저 영구 보관)
                    if ls:
                        try:
                            ls.setItem("naver_cookie_saved", cleaned)
                        except Exception:
                            pass
                    was_curl = (cookie_input or "").strip().startswith("curl ")
                    msg = "쿠키 저장 완료. 만료(2~4주) 전까지 자동 로드됩니다."
                    if was_curl:
                        msg += " (cURL에서 쿠키만 자동 추출됨)"
                    st.success(msg)
                    st.rerun()
        with c_clear:
            if st.button("🗑️ 쿠키 삭제", use_container_width=True, key="ck_clear"):
                st.session_state["naver_cookie_user"] = ""
                # localStorage에서도 삭제
                if ls:
                    try:
                        ls.deleteItem("naver_cookie_saved")
                    except Exception:
                        pass
                st.info("쿠키 삭제됨 (브라우저 저장도 함께 정리됨).")
                st.rerun()

        st.caption(
            "💡 cURL을 통째로 붙여넣어도 OK — 자동으로 쿠키만 추출합니다. "
            "추출 방법은 아래 가이드를 참고하세요."
        )

    # 가이드 expander — 메인 expander 밖으로 분리 (Streamlit 중첩 제약 회피)
    with st.expander("📖 쿠키 추출 가이드 (5분 작업)", expanded=False):
        st.markdown(
            "**처음 한 번만** 본인 PC에서 따라 하세요. 한 번 추출한 쿠키는 보통 2~4주 동안 유효합니다.\n\n"
            "1. 본인 브라우저(크롬 추천)에서 **네이버에 로그인된 상태**로 접속\n"
            "2. 아무 스마트스토어 상품 페이지 방문 (예: smartstore.naver.com/hrbongtoo/products/414549042)\n"
            "3. **F12** 눌러 개발자 도구 열기\n"
            "4. **Network** 탭 클릭 → 페이지 새로고침 (**F5**)\n"
            "5. Network 탭의 검색창에 `bulk` 또는 `products/` 입력\n"
            "6. 결과 중 하나 클릭 → **우클릭 → 복사 → cURL로 복사 (bash)**\n"
            "7. 그걸 위 입력란에 통째로 붙여넣고 **💾 쿠키 저장** (자동으로 쿠키만 추출됨)\n\n"
            "⚠️ 쿠키는 본인 계정 식별 정보입니다. 신뢰하는 사람과만 공유하시고, "
            "절대 공개적인 곳에 올리지 마세요. 만료되면 (보통 2~4주) 다시 추출하세요."
        )

    # 쿠키 없으면 진행 차단 (편의를 위해 경고만, 실행은 가능)
    if not has_cookie:
        st.warning(
            "⚠️ 본인 쿠키를 먼저 저장해주세요. 쿠키 없이 실행하면 네이버 봇 차단(HTTP 429)으로 실패할 가능성이 매우 높습니다."
        )

    col_input, col_action = st.columns([3, 1])
    with col_input:
        url = st.text_input(
            "스마트스토어 상품 URL",
            placeholder="예: https://smartstore.naver.com/hrbongtoo/products/414549042",
            key="auto_collect_url",
        )
    with col_action:
        st.markdown("&nbsp;")
        do_run = st.button("🔍 자동 수집 실행", use_container_width=True, key="auto_collect_run")

    if not do_run:
        return
    if not url or not url.strip():
        st.warning("URL을 먼저 입력해 주세요.")
        return

    user_cookie = st.session_state.get("naver_cookie_user", "").strip() or None
    with st.spinner("📡 자동 수집 중..."):
        result = auto_collect(url.strip(), user_cookie=user_cookie)

    with st.expander("📋 진행 로그", expanded=not result["ok"]):
        for step in result["steps"]:
            st.markdown(f"- {step}")

    if not result["ok"]:
        st.error(f"수집 실패: {result['error']}")
        st.info("해결 팁: 잠시 후 재시도, URL 재확인, 또는 .env의 NAVER_COOKIE 갱신")
        return

    data = result["data"]

    st.success("✅ 수집 완료!")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("상품번호", result["product_id"])
    c2.metric("기본 판매가", f"{int(data.get('salePrice') or 0):,}원")
    bv = data.get("benefitsView") or {}
    if bv.get("discountedSalePrice"):
        ratio = bv.get("discountedRatio") or 0
        c3.metric("즉시할인가", f"{int(bv['discountedSalePrice']):,}원",
                  delta=f"-{ratio}%" if ratio else None)
    else:
        c3.metric("즉시할인가", "-")
    c4.metric("옵션 조합 수", f"{len(data.get('optionCombinations') or [])}개")

    # 상품 기본 정보 — 2x2 컬럼 (다크 테마 충돌 회피)
    with st.expander("📦 상품 기본 정보", expanded=True):
        ch = data.get("channel") or {}
        cat = data.get("category") or {}
        origin = data.get("originAreaInfo") or {}
        pdi = data.get("productDeliveryInfo") or {}
        i1, i2 = st.columns(2)
        with i1:
            st.markdown("**📝 상품명**")
            st.write(data.get("name") or "-")
            st.markdown("**🏪 스토어**")
            st.write(f"{ch.get('channelName', '-')} ({ch.get('accountId', '-')})")
            st.markdown("**📍 원산지**")
            st.write(origin.get("content") or "-")
        with i2:
            st.markdown("**📂 카테고리**")
            st.write(cat.get("wholeCategoryName") or "-")
            st.markdown("**🚚 배송**")
            st.write(f"{(pdi.get('deliveryCompany') or {}).get('name', '-')}  ·  "
                     f"기본료 {int(pdi.get('baseFee') or 0):,}원")
            policy = pdi.get("deliveryFeePolicyText")
            if policy:
                st.caption(policy)
            st.markdown("**🔗 상품 URL**")
            st.write(data.get("productUrl") or result["url"])

    base_sale, base_disc, rows = _calc_final_prices(data)
    if not rows:
        st.info("이 상품은 옵션이 없는 단품입니다.")
        return

    df = pd.DataFrame(rows)
    st.markdown("### 🎛️ 옵션 테이블 + 마진 분석 (V21 통합)")
    st.caption(f"기본판매가 {base_sale:,}원, 즉시할인가 {base_disc:,}원 기준 + 마진율·수수료로 옵션별 최적 매입가 역산.")

    # === 마진 분석 입력 (V21 흡수) ===
    mc1, mc2, mc3 = st.columns(3)
    with mc1:
        margin_rate = st.slider("🎯 목표 마진 (%)", 5, 80, 40, key="ac_margin")
    with mc2:
        fee_rate = st.number_input("💸 수수료/광고비 합계 (%)", 0.0, 30.0, 9.0, 0.5, key="ac_fee")
    with mc3:
        price_base = st.radio("기준가", ["할인가 적용", "정가 기준"], horizontal=True, key="ac_price_base")

    # 마진 분석 컬럼 추가
    price_col = "할인 후 최종가" if price_base == "할인가 적용" else "최종 판매가"
    df["기준가"] = df[price_col]
    df["수수료/광고비"] = (df["기준가"] * fee_rate / 100).round().astype(int)
    df["목표 마진액"] = (df["기준가"] * margin_rate / 100).round().astype(int)
    df["최적 매입가(역산)"] = df["기준가"] - df["수수료/광고비"] - df["목표 마진액"]
    df["실 마진율"] = (df["목표 마진액"] / df["기준가"] * 100).round(1)

    # 필터
    opts = data.get("optionCombinations") or []
    if opts and opts[0].get("optionName1"):
        op1_values = sorted({(o.get("optionName1") or "") for o in opts})
        op1_filter = st.multiselect("선택1 (그룹) 필터", op1_values, default=[])
        if op1_filter:
            df = df[df["옵션"].apply(lambda s: any(g in s.split(" / ")[0] for g in op1_filter))]

    sort_col = st.selectbox(
        "정렬 기준",
        ["옵션", "옵션가(+/-)", "최종 판매가", "할인 후 최종가", "최적 매입가(역산)", "재고"],
        index=4,
    )
    asc = st.checkbox("오름차순", value=True)
    df = df.sort_values(by=sort_col, ascending=asc)

    show_cols = [
        "옵션", "기본판매가", "옵션가(+/-)", "최종 판매가", "할인 후 최종가",
        "기준가", "수수료/광고비", "목표 마진액", "최적 매입가(역산)", "실 마진율",
        "재고",
    ]
    df_show = df[show_cols]

    st.dataframe(
        df_show.style.format({
            "기본판매가": "{:,.0f}원",
            "옵션가(+/-)": "{:+,.0f}원",
            "최종 판매가": "{:,.0f}원",
            "할인 후 최종가": "{:,.0f}원",
            "기준가": "{:,.0f}원",
            "수수료/광고비": "{:,.0f}원",
            "목표 마진액": "{:,.0f}원",
            "최적 매입가(역산)": "{:,.0f}원",
            "실 마진율": "{:.1f}%",
            "재고": "{:,.0f}",
        }),
        use_container_width=True, height=500,
    )

    if len(df) > 0:
        sm1, sm2, sm3 = st.columns(3)
        sm1.metric("최저 매입가 (역산)", f"{int(df['최적 매입가(역산)'].min()):,}원")
        sm2.metric("최고 매입가 (역산)", f"{int(df['최적 매입가(역산)'].max()):,}원")
        sm3.metric("평균 매입가 (역산)", f"{int(df['최적 매입가(역산)'].mean()):,}원")
        st.caption(
            f"💡 베트남 소싱 시 위 매입가 범위 내로 들어와야 마진 {margin_rate}% "
            f"(수수료/광고 {fee_rate}% 차감 후) 확보 가능."
        )

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        csv = df_show.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            "📥 옵션+마진 분석 CSV 다운로드",
            data=csv,
            file_name=f"smartstore_{result['product_id']}_margin.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_d2:
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        st.download_button(
            "📥 원본 API 응답(JSON) 다운로드",
            data=json_str.encode("utf-8"),
            file_name=f"smartstore_{result['product_id']}_raw.json",
            mime="application/json",
            use_container_width=True,
        )

    st.caption("✅ V21 마진 분석 통합 + 브라우저에 쿠키 영구 저장(만료 전까지 자동 로드).")
