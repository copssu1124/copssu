"""일괄 수집기 탭 (Phase 2) — URL 여러 개를 한 번에 처리."""
import io
import json
import time
import random
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

from smartstore_auto import auto_collect, parse_smartstore_url


def _group_urls_by_store(urls):
    """URL을 store_name 기준으로 정렬하면 같은 스토어끼리 묶임."""
    decorated = []
    for u in urls:
        s, _ = parse_smartstore_url(u)
        decorated.append((s or "zzz_unknown", u))
    # 같은 스토어끼리 인접하도록 정렬
    decorated.sort(key=lambda x: x[0])
    return [(s, u) for (s, u) in decorated]


def _flatten_options(result):
    """단일 수집 결과를 옵션 행 리스트로 변환 (엑셀 옵션 상세 시트용)."""
    if not result.get("ok") or not result.get("data"):
        return []
    d = result["data"]
    base_sale = int(d.get("salePrice") or 0)
    bv = d.get("benefitsView") or {}
    base_disc = int(bv.get("discountedSalePrice") or base_sale)
    pid = result.get("product_id", "")
    name = d.get("name", "")
    rows = []
    for o in d.get("optionCombinations") or []:
        opt_price = int(o.get("price") or 0)
        names = [str(o.get(k)) for k in ("optionName1", "optionName2", "optionName3") if o.get(k)]
        opt_label = " / ".join(names) if names else "(이름 없음)"
        rows.append({
            "상품번호": pid,
            "상품명": name,
            "옵션": opt_label,
            "기본판매가": base_sale,
            "옵션가(+/-)": opt_price,
            "최종 판매가": base_sale + opt_price,
            "할인 후 최종가": base_disc + opt_price,
            "재고": o.get("stockQuantity"),
            "옵션ID": o.get("id"),
        })
    return rows


def _summary_row(result):
    """단일 수집 결과를 요약 1행으로 변환 (엑셀 요약 시트용)."""
    d = result.get("data") or {}
    base_sale = int(d.get("salePrice") or 0)
    bv = d.get("benefitsView") or {}
    base_disc = int(bv.get("discountedSalePrice") or base_sale)
    opts = d.get("optionCombinations") or []
    ch = d.get("channel") or {}
    cat = d.get("category") or {}

    prices = [base_disc + int(o.get("price") or 0) for o in opts] if opts else [base_disc]
    return {
        "상태": "✅" if result.get("ok") else "❌",
        "상품번호": result.get("product_id", ""),
        "상품명": d.get("name", ""),
        "스토어": ch.get("channelName", ""),
        "카테고리": cat.get("wholeCategoryName", ""),
        "기본판매가": base_sale,
        "즉시할인가": base_disc,
        "옵션 수": len(opts),
        "최저가": min(prices) if prices else 0,
        "최고가": max(prices) if prices else 0,
        "평균가": int(sum(prices) / len(prices)) if prices else 0,
        "URL": result.get("url", ""),
        "에러": result.get("error", "") if not result.get("ok") else "",
    }


def _build_excel(results, margin_rate, fee_rate):
    """결과 리스트 → 엑셀 BytesIO (요약 시트 + 옵션 상세 시트 + 마진 분석 시트)."""
    summary_rows = [_summary_row(r) for r in results]
    df_summary = pd.DataFrame(summary_rows)

    all_options = []
    for r in results:
        all_options.extend(_flatten_options(r))
    df_options = pd.DataFrame(all_options)

    # 마진 분석 컬럼 추가 (옵션 상세에)
    if not df_options.empty:
        df_options["기준가"] = df_options["할인 후 최종가"]
        df_options["수수료/광고비"] = (df_options["기준가"] * fee_rate / 100).round().astype(int)
        df_options["목표 마진액"] = (df_options["기준가"] * margin_rate / 100).round().astype(int)
        df_options["최적 매입가(역산)"] = df_options["기준가"] - df_options["수수료/광고비"] - df_options["목표 마진액"]

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_summary.to_excel(writer, sheet_name="요약", index=False)
        if not df_options.empty:
            df_options.to_excel(writer, sheet_name="옵션 상세 + 마진", index=False)
        # 메타 시트
        meta = pd.DataFrame({
            "항목": ["수집일시", "총 URL 수", "성공", "실패", "마진율(%)", "수수료(%)"],
            "값": [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                len(results),
                sum(1 for r in results if r.get("ok")),
                sum(1 for r in results if not r.get("ok")),
                margin_rate,
                fee_rate,
            ],
        })
        meta.to_excel(writer, sheet_name="메타", index=False)

    buf.seek(0)
    return buf.getvalue()


def render_bulk_collector_tab():
    """마스터 툴의 '일괄 수집기' 탭."""
    # 토스 다크 테마와 충돌하는 expander 화살표 SVG/Material 글자 숨김
    st.markdown(
        """
<style>
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpanderToggleIcon"] *,
details > summary svg,
details > summary [class*="material"] {
    visibility: hidden !important;
    width: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🚛 스마트스토어 일괄 수집기 V1")
    st.markdown(
        "URL 여러 개를 한 번에 처리합니다 → 진척률 표시 → 통합 엑셀(요약 + 옵션상세 + 마진) 다운로드."
    )

    # 쿠키 상태 확인 (자동 수집기 탭에서 입력한 것 공유)
    has_cookie = bool(st.session_state.get("naver_cookie_user", "").strip())
    if not has_cookie:
        st.warning(
            "⚠️ 먼저 '🚀 자동 수집기' 탭에서 본인 네이버 쿠키를 입력해주세요. "
            "쿠키 없이 일괄 수집 시 대부분 봇 차단으로 실패합니다."
        )
    else:
        st.success("✅ 쿠키 적용 중 (자동 수집기 탭에서 입력한 것 사용)")

    # 입력 영역
    input_mode = st.radio(
        "URL 입력 방식",
        ["텍스트 직접 입력 (줄별)", "CSV/엑셀 업로드"],
        horizontal=True,
        key="bulk_input_mode",
    )

    urls = []
    if input_mode == "텍스트 직접 입력 (줄별)":
        text = st.text_area(
            "스마트스토어 URL을 줄별로 붙여넣기 (한 줄에 URL 하나)",
            height=200,
            placeholder=(
                "https://smartstore.naver.com/hrbongtoo/products/414549042\n"
                "https://smartstore.naver.com/main/products/6736470093\n"
                "..."
            ),
            key="bulk_url_text",
        )
        urls = [u.strip() for u in (text or "").splitlines() if u.strip() and "smartstore" in u]
    else:
        upload = st.file_uploader(
            "URL이 들어있는 CSV 또는 엑셀 (첫 컬럼 또는 'url' 컬럼에서 자동 추출)",
            type=["csv", "xlsx"],
            key="bulk_url_file",
        )
        if upload:
            try:
                if upload.name.endswith(".csv"):
                    df_in = pd.read_csv(upload)
                else:
                    df_in = pd.read_excel(upload)
                col = "url" if "url" in df_in.columns else df_in.columns[0]
                urls = [str(u).strip() for u in df_in[col] if str(u).strip() and "smartstore" in str(u)]
                st.caption(f"📂 {len(urls)}개 URL 추출됨 (컬럼: `{col}`)")
            except Exception as e:
                st.error(f"파일 읽기 실패: {e}")

    st.caption(f"📊 추출된 URL: **{len(urls)}개**")

    # 옵션 설정
    opt_c1, opt_c2, opt_c3 = st.columns(3)
    with opt_c1:
        sleep_sec = st.slider("URL 사이 대기 시간 (초)", 1.0, 15.0, 5.0, 0.5, key="bulk_sleep",
                              help="짧으면 봇 차단(HTTP 429) 위험 증가. 같은 스토어 5초+, 여러 스토어 7초+ 권장.")
    with opt_c2:
        margin_rate = st.slider("🎯 목표 마진 (%)", 5, 80, 40, key="bulk_margin")
    with opt_c3:
        fee_rate = st.number_input("💸 수수료/광고비 (%)", 0.0, 30.0, 9.0, 0.5, key="bulk_fee")

    # 실행
    if st.button("🚀 일괄 수집 실행", use_container_width=True, type="primary",
                 disabled=(len(urls) == 0), key="bulk_run"):
        user_cookie = st.session_state.get("naver_cookie_user", "").strip() or None

        progress = st.progress(0, text="시작...")
        status_box = st.empty()
        results = []

        # 적응형 페이싱: 차단 받으면 다음 URL부터 페이싱 자동 증가
        current_pacing = sleep_sec
        consecutive_blocks = 0

        # 전역 세션 공유 (자동/일괄/키워드 수집기 모두 같은 브라우저 패턴)
        if "shared_naver_session" not in st.session_state:
            st.session_state["shared_naver_session"] = requests.Session()
        shared_session = st.session_state["shared_naver_session"]

        # 같은 스토어끼리 묶어서 처리 (스토어 전환 시 봇 차단 회피 위해 긴 휴식)
        grouped = _group_urls_by_store(urls)
        prev_store = None

        for i, (store, url) in enumerate(grouped):
            # 스토어 전환 시 긴 휴식 (다른 스토어 사이는 최소 20초)
            if prev_store and store != prev_store:
                store_switch_wait = max(20.0, current_pacing * 2.5)
                status_box.info(
                    f"🏪 스토어 전환 감지 ({prev_store} → {store}) — {store_switch_wait:.0f}초 휴식..."
                )
                time.sleep(store_switch_wait)
            prev_store = store

            progress.progress(
                (i + 1) / len(grouped),
                text=f"({i+1}/{len(grouped)}) [{store}] 페이싱 {current_pacing:.1f}초 · {url[:50]}...",
            )
            status_box.info(f"수집 중 ({store}): {url}")
            r = auto_collect(url, user_cookie=user_cookie, session=shared_session)
            results.append(r)

            # 봇 차단 받았는지 체크 (적응형 페이싱)
            if not r.get("ok") and "429" in (r.get("error") or ""):
                consecutive_blocks += 1
                # 연속 차단 시 페이싱 1.5배씩 증가 (최대 30초)
                current_pacing = min(30.0, current_pacing * 1.5)
                status_box.warning(f"⚠️ 차단 감지 — 다음 페이싱 {current_pacing:.1f}초로 자동 증가")
            else:
                consecutive_blocks = 0
                # 성공 시 페이싱 점진적 복원 (원본의 80%까지만 낮춤, 너무 빠르게 복원하지 않음)
                current_pacing = max(sleep_sec, current_pacing * 0.9)

            # 마지막 URL이 아니면 페이싱
            if i < len(grouped) - 1:
                wait = current_pacing + random.uniform(-0.5, 0.5)
                time.sleep(max(0.5, wait))

        st.session_state["bulk_results"] = results
        progress.empty()
        status_box.empty()
        # 한 번에 깔끔하게 다시 그림 (결과 누적 표시 버그 차단)
        st.rerun()

    # 결과 표시
    results = st.session_state.get("bulk_results", [])
    if not results:
        return

    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("총 URL", len(results))
    sc2.metric("성공", ok_count)
    sc3.metric("실패", fail_count, delta=f"-{fail_count}" if fail_count else None,
               delta_color="inverse" if fail_count else "normal")

    # 요약 테이블
    df_summary = pd.DataFrame([_summary_row(r) for r in results])
    if not df_summary.empty:
        st.markdown("### 📋 상품별 요약")
        st.dataframe(
            df_summary.style.format({
                "기본판매가": "{:,.0f}원",
                "즉시할인가": "{:,.0f}원",
                "최저가": "{:,.0f}원",
                "최고가": "{:,.0f}원",
                "평균가": "{:,.0f}원",
            }),
            use_container_width=True,
            height=400,
        )

    # 실패 URL 목록
    fails = [r for r in results if not r.get("ok")]
    if fails:
        with st.expander(f"❌ 실패 URL {len(fails)}개", expanded=False):
            for r in fails:
                st.markdown(f"- `{r.get('url','')}` — {r.get('error','')}")

    # 엑셀 다운로드
    margin = st.session_state.get("bulk_margin", 40)
    fee = st.session_state.get("bulk_fee", 9.0)
    excel_bytes = _build_excel(results, margin, fee)
    fname = f"smartstore_bulk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    st.download_button(
        "📥 통합 엑셀 다운로드 (요약 + 옵션상세 + 마진 분석)",
        data=excel_bytes,
        file_name=fname,
        use_container_width=True,
        type="primary",
    )

    # 결과 초기화 버튼
    if st.button("🗑️ 결과 지우기", key="bulk_clear"):
        st.session_state.pop("bulk_results", None)
        st.rerun()
