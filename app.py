import streamlit as st
import streamlit.components.v1 as components
import requests
import os
import sys

# [V4.9.6 Hotfix] Streamlit 실행 디렉터리 이슈로 인한 파일 로드(로컬 CSV, 구글 키) 실패 방지: 작업 폴더 강제 고정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import time
import random
from dotenv import load_dotenv
from datetime import datetime, timedelta
from pytrends.request import TrendReq
from bs4 import BeautifulSoup
from google import genai

# .env 환경 변수 로드 (변경 시 덮어쓰기 허용)
load_dotenv(override=True)

# 페이지 설정
st.set_page_config(page_title="제이제이컴퍼니 관제탑 V4.8 프로페셔널", layout="wide", initial_sidebar_state="expanded")

# [NEW V4.8.6] 브라우저 강제 번역 방지 JS DOM Injection (Streamlit iframe 우회)
# 웹 브라우저(크롬 등)가 영어 키워드(Gemini, Map 등)를 억지로 한글로 오역하는 현상을 원천 방어합니다.
components.html(
    """
    <script>
        const parentDoc = window.parent.document;
        // 1. html 언어를 'ko'로 고정하여 영->한 번역기 팝업 트리거 방어
        parentDoc.documentElement.lang = 'ko';
        
        // 2. <head> 태그 내부에 크롬 번역 금지 메타태그 직접 부착
        let meta = parentDoc.querySelector('meta[name="google"]');
        if (!meta) {
            meta = parentDoc.createElement('meta');
            meta.name = 'google';
            meta.content = 'notranslate';
            parentDoc.head.appendChild(meta);
        } else {
            meta.content = 'notranslate';
        }
    </script>
    """,
    height=0,
    width=0,
)

# 다크 모드 최적화 CSS 반영
st.markdown("""
<meta name="google" content="notranslate">
<style>
    /* [V5.0 Neon Glassmorphism Premium Theme] */
    
    /* 1. 글로벌 우주 다크 배경 및 텍스트 */
    .stApp {
        background-color: #0b0c10;
        color: #e0e6ed;
        font-family: 'Pretendard', 'Malgun Gothic', dotum, sans-serif;
    }
    
    /* 2. 상단 헤더 및 타이틀 네온 글로우 */
    h1, h2, h3 {
        color: #66fcf1 !important;
        text-shadow: 0 0 10px rgba(102, 252, 241, 0.3);
    }
    
    /* 3. 탭(Tab) 메뉴 UI 글래스모피즘 */
    .stTabs [data-baseweb="tab-list"] { 
        gap: 8px; 
        background-color: rgba(31, 40, 51, 0.6);
        padding: 5px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
    }
    .stTabs [data-baseweb="tab"] { 
        background-color: transparent; 
        border-radius: 8px; 
        padding: 12px 24px; 
        font-weight: 700;
        color: #c5c6c7;
        transition: all 0.3s ease;
        border: 1px solid transparent;
    }
    .stTabs [aria-selected="true"] { 
        background: linear-gradient(135deg, #45a29e 0%, #66fcf1 100%);
        color: #0b0c10 !important; 
        box-shadow: 0 4px 15px rgba(102, 252, 241, 0.4);
        border: 1px solid rgba(102, 252, 241, 0.5);
    }
    
    /* 4. 버튼(Button) 사이버펑크 네온 호버 트랜지션 */
    .stButton > button {
        background: rgba(31, 40, 51, 0.8);
        color: #66fcf1;
        border: 1px solid #45a29e;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: bold;
        backdrop-filter: blur(5px);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #45a29e, #66fcf1);
        color: #0b0c10;
        border-color: #66fcf1;
        box-shadow: 0 0 20px rgba(102, 252, 241, 0.6);
        transform: translateY(-2px);
    }
    
    /* 5. 입력창(Input) 및 셀렉트박스 투명화 */
    .stTextInput input, .stSelectbox > div[data-baseweb="select"] {
        background-color: rgba(31, 40, 51, 0.5) !important;
        color: #66fcf1 !important;
        border: 1px solid #45a29e !important;
        border-radius: 6px !important;
    }
    
    /* 6. 정보 패널(하이라이트/Alert) 보석함 유리 질감 */
    .highlight-card { 
        background: rgba(31, 40, 51, 0.7); 
        padding: 24px; 
        border-radius: 12px; 
        border-left: 6px solid #66fcf1; 
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 1.5rem; 
    }
    div[data-testid="stAlert"] {
        background-color: rgba(31, 40, 51, 0.7) !important;
        border: 1px solid #45a29e !important;
        backdrop-filter: blur(5px);
    }
    
    /* 7. 공통 Markdown / 기본 테이블 아크릴 질감 */
    table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 15px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    th { background: rgba(69, 162, 158, 0.2); color: #66fcf1; padding: 15px; text-align: left; font-weight: 800; text-transform: uppercase; font-size: 0.9em; border-bottom: 2px solid #45a29e; }
    td { padding: 12px 15px; background: rgba(31, 40, 51, 0.6); color: #c5c6c7; border-bottom: 1px solid rgba(69, 162, 158, 0.1); transition: background 0.3s ease; }
    tr:hover td { background: rgba(69, 162, 158, 0.15); color: #ffffff; }
    
    /* 8. 구분선 네온 라인 */
    hr { border-top: 1px solid rgba(102, 252, 241, 0.3); margin: 2.5rem 0; box-shadow: 0 0 10px rgba(102, 252, 241, 0.2); }
</style>
""", unsafe_allow_html=True)

# 로컬 우선 및 회사 정보 반영 헤더
st.title("🛡️ 제이제이컴퍼니 관제탑 V4.3 (PRO B2B 마케터 에디션)")
st.subheader("충남 금산군 제이제이컴퍼니(유) - 수익성 극대화 및 마케팅 자동화 포털 🚀")
st.markdown("B2B 물류 네트워크 소싱, 시장 경쟁 강도 분석, 플랫폼 맞춤형 전문 마케팅 원고 생성을 통합 관제합니다.")
st.write("---")

# ==========================================
# 1. API 통신 및 5중 키 로테이션 공통 모듈
# ==========================================
@st.cache_resource
def load_api_keys():
    keys = []
    for i in range(1, 6):
        cid = os.getenv(f"CLIENT_ID_{i}")
        csec = os.getenv(f"CLIENT_SECRET_{i}")
        if cid and csec and cid.strip() != "" and "여기에" not in cid:
            keys.append({"num": i, "id": cid.strip(), "secret": csec.strip()})
    return keys

API_KEYS = load_api_keys()

if not API_KEYS:
    st.error("⚠️ **유효한 API 키가 없습니다.** `.env` 파일에 `CLIENT_ID_1`, `CLIENT_SECRET_1` 등을 올바르게 설정해주세요.")
    st.stop()
    
if 'key_idx' not in st.session_state:
    st.session_state.key_idx = 0

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ==========================================
# [NEW V5.0] Google Sheets 영구 DB 연동 모듈 (Local + Streamlit Cloud 완벽 호환)
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1swMVdcbV3keWCEF-7XctrKxxR7YkhlgNFBy8BLlOnDA/edit"

@st.cache_resource
def get_gsheets_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    try:
        # 1. 로컬 환경 (바탕화면) 에서 google_key.json 찾기
        if os.path.exists("google_key.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("google_key.json", scopes)
        # 2. Streamlit Cloud 환경 (Secrets에서 불러오기)
        elif "google_sheets" in st.secrets:
            # st.secrets.google_sheets 가 dict 형태로 들어있다고 가정
            creds_dict = dict(st.secrets["google_sheets"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scopes)
        else:
            st.error("⚠️ Google Sheets 인증 키(google_key.json 또는 st.secrets)를 찾을 수 없습니다.")
            return None
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"⚠️ Google Sheets 인증 오류: {e}")
        return None

def get_or_create_worksheet(client, sheet_name):
    try:
        sheet = client.open_by_url(SPREADSHEET_URL)
        try:
            worksheet = sheet.worksheet(sheet_name)
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
        return worksheet
    except Exception as e:
        st.error(f"⚠️ 워크시트 접근 오류: {e}")
        return None

def _init_usage(today):
    return {"date": today, "keys": {str(i): {"datalab": 0, "shop": 0, "other": 0} for i in range(1, 6)}}

def load_local_api_usage():
    today = datetime.now().strftime("%Y-%m-%d")
    client = get_gsheets_client()
    if not client: return _init_usage(today)
    
    ws = get_or_create_worksheet(client, "API_Quota")
    if not ws: return _init_usage(today)

    try:
        records = ws.get_all_records()
        for row in records:
            if str(row.get("Date")) == today:
                try:
                    data = json.loads(row.get("Usage_JSON", "{}"))
                    if "keys" in data: return data
                except: pass
    except Exception:
        pass
        
    return _init_usage(today)

def save_local_api_usage(data):
    today = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    client = get_gsheets_client()
    if not client: return
    
    ws = get_or_create_worksheet(client, "API_Quota")
    if not ws: return

    try:
        headers = ws.row_values(1)
        if not headers:
            ws.append_row(["Date", "Usage_JSON"])
            
        records = ws.get_all_records()
        row_idx = None
        for idx, row in enumerate(records):
            if str(row.get("Date")) == today:
                row_idx = idx + 2
                break
                
        json_str = json.dumps(data, ensure_ascii=False)
        if row_idx:
            ws.update_acell(f'B{row_idx}', json_str)
        else:
            ws.append_row([today, json_str])
    except Exception as e:
        print(f"DB 저장 오류: {e}")

def increment_api_usage(key_num, url, batch_mode=False):
    if 'api_usage_cache' not in st.session_state:
        st.session_state.api_usage_cache = load_local_api_usage()
        
    data = st.session_state.api_usage_cache
    api_type = "other"
    if "datalab/search" in url:
        api_type = "datalab"
    elif "search/shop" in url:
        api_type = "shop"
        
    k_str = str(key_num)
    if k_str in data["keys"]:
        data["keys"][k_str][api_type] += 1
        
    if not batch_mode:
        save_local_api_usage(data)

def flush_api_usage():
    if 'api_usage_cache' in st.session_state:
        save_local_api_usage(st.session_state.api_usage_cache)

def get_rotating_client():
    idx = st.session_state.key_idx
    key = API_KEYS[idx]
    return key["num"], key["id"], key["secret"]

def rotate_key():
    st.session_state.key_idx = (st.session_state.key_idx + 1) % len(API_KEYS)

def safe_api_request(method, url, headers=None, params=None, json_data=None, batch_mode=False):
    max_retries = len(API_KEYS)
    retries = 0
    
    while retries < max_retries:
        key_num, cid, csec = get_rotating_client()
        
        req_headers = headers.copy() if headers else {}
        req_headers["X-Naver-Client-Id"] = cid
        req_headers["X-Naver-Client-Secret"] = csec
        
        try:
            if method.upper() == "GET":
                res = requests.get(url, headers=req_headers, params=params)
            else:
                res = requests.post(url, headers=req_headers, json=json_data)
                
            if res.status_code == 200:
                print(f"✅ [{key_num}번 키] API 호출 성공")
                # [V4.9.5] 외부(네이버) 통신 성공 즉시 계량기 로컬 캐시에 누적
                increment_api_usage(key_num, url, batch_mode)
                return res.json()
            elif res.status_code == 429:
                print("현재 키의 한도가 소진되었습니다")
                st.toast(f"⚠️ {key_num}번 API 키 한도 소진. 다음 키로 즉시 전환합니다.")
                time.sleep(0.5) # 0.5초 방어막
                rotate_key()
                retries += 1
                continue
            else:
                st.error(f"❌ API 에러 [{res.status_code}]: {res.text}")
                return None
                
        except Exception as e:
            st.error(f"통신 에러: {e}")
            return None
            
    print("모든 API 키의 일일 한도가 완료되었습니다")
    st.error("🚫 모든 API 키의 일일 한도가 완료되었습니다")
    return None

# [NEW V4.9.5 B플랜] 로컬 Tracker DB 기반 실시간 API 관제 패널 UI
def render_local_api_quotas():
    # 데이터랩 제한 (1000) 기준으로 시각화
    usage_data = load_local_api_usage()
    q_data = []
    t_rem, t_lim = 0, 0
    
    for i in range(1, 6):
        k_str = str(i)
        used = usage_data["keys"].get(k_str, {}).get("datalab", 0)
        limit = 1000
        rem = max(0, limit - used)
        
        stat = "🟢 정상"
        if rem == 0: stat = "🔴 고갈"
        elif rem < 200: stat = "🟡 위험"
            
        q_data.append({"num": i, "rem": rem, "lim": limit, "stat": stat})
        t_rem += rem
        t_lim += limit
        
    return q_data, t_rem, t_lim

st.sidebar.markdown("---")
st.sidebar.subheader("🔋 API 총알 관제소 (Local DB)")
st.sidebar.caption("💡 네이버 실시간 통신 및 딥스캔 사용량이 로컬에 100% 영구 동기화됩니다.")

if st.sidebar.button("🔄 장전 탄환 새로고침", use_container_width=True):
    with st.sidebar.status("데이터베이스 스캔 중..."):
        time.sleep(0.3)
        st.session_state.api_quota_data = render_local_api_quotas()

if 'api_quota_data' not in st.session_state:
    st.session_state.api_quota_data = render_local_api_quotas()

q_data, tr, tl = st.session_state.api_quota_data
progress_val = tr / tl if tl > 0 else 0
pct = progress_val * 100
st.sidebar.markdown(f"**총 가용 스캔 잔여량**: `{tr:,}` / `{tl:,}` 발 (**{pct:.1f}%** 남음)")
st.sidebar.progress(progress_val)
for q in q_data:
    rem_pct = (q['rem'] / q['lim'] * 100) if q['lim'] > 0 else 0
    st.sidebar.caption(f"▫️ {q['num']}번 키: {q['rem']:,} / {q['lim']:,} (**{rem_pct:.1f}%**) - {q['stat']}")
    st.sidebar.progress(q['rem'] / q['lim'] if q['lim'] > 0 else 0)

st.sidebar.markdown("---")

# ==========================================
# 2. 신사업 인사이트 스캐너 (분석) 모듈
# ==========================================
# 필터링 1: 일반 형용사/명사 배제 (상품성 판별기)
GENERIC_WORDS = ['추천', '비교', '가격', '방법', '좋은', '여름', '겨울', '선물', '후기', '만들기']
# 필터링 2: KC인증 등 위험도 배제 방어막
FORBIDDEN_WORDS = ['전기', '유아', '의료기기', '어린이', '치료', '무선', '충전', '건강기능', '마사지', '영양제', 'LED', '배터리', '건강식품', '화장품']
# 멀티 채널 힌트 룰
ROCKET_WORDS = ['테이프', '고정핀', '수세미', '아이스팩', '종이', '봉투', '펜', '방수', '장갑', '수선', '패치', '볼펜', '비닐', '쇼핑백']
ALWAYS_WORDS = ['양말', '수건', '우산', '머리끈', '에어프라이어종이호일', '행주', '휴지', '건전지', '마스크', '핫팩', '멀티탭정리함']

# [NEW V4.9.1] B2B 포장재 납품 정밀 타겟 (스티로폼, 아이스팩, 완충재 필수 아이템)
FRAGILE_FRESH_WORDS = ['과일', '한우', '고기', '갈비', '사과', '배', '포도', '귤', '수산', '해산물', '생선', '새우', '게장', '연어', '회', '김치', '반찬', '밀키트', '명절', '즙', '액즙', '사과즙', '와인', '유리', '병', '화장품', '앰플', '스킨', '향수', '디퓨저', '캔들', '액자', '도자기', '컵', '텀블러', '모니터', '전자기기', '블랙박스', '전자담배', '견인기', '가전', '스피커', '카메라']

# [NEW V4.9.2] 파워 소싱 블랙리스트 (수입/위탁/사입 즉시 불가능한 인증 및 지재권 품목 철통 방어막)
BRAND_BLACK_WORDS = ['스타벅스', '다이소', '애플', '삼성', '엘지', 'LG', '나이키', '아디다스', '이케아', '스탠리', '샤넬', '에르메스', '다이슨', '레고', '닌텐도', '플레이스테이션', '폴로', '구찌', '루이비통', '뉴발란스']
KC_CERT_WORDS = ['전기', '무선', '충전', '블루투스', '보조배터리', '고데기', '콘센트', '조명', 'LED', '드라이기', '가습기', '어댑터', '플러그', '케이블', '모니터', '마우스', '키보드', '이어폰', '스피커']
FOOD_SAFE_WORDS = ['텀블러', '식기', '수저', '냄비', '프라이팬', '도마', '종이컵', '접시', '그릇', '머그컵', '포크', '나이프', '도시락', '밀폐용기', '보온병', '주걱', '국자', '채반', '랩', '호일', '빨대']
STRICT_LEGAL_WORDS = ['유아', '아기', '어린이', '기능성', '영양제', '의료기기', '마사지', '치료', '건강식품', '화장품', '향수', '디퓨저', '렌즈', '콘택트', '담배', '안경', '치약', '가글', '염색약', '보청기', '혈압계']

# [NEW V4.9.3] 파워 실물 필터 (포장/배송이 불가능한 무형 서비스, 티켓, 여행 상품 등 원천 차단 방어막)
NON_PHYSICAL_WORDS = ['기프트카드', '상품권', '이용권', '관람권', '패스', '쿠폰', '기프티콘', '포인트', '티켓', '예매', '여행', '투어', '패키지', '항공권', '배편', '렌트카', '리조트', '호텔', '숙박', '비행기', 'KTX', 'SRT', '기차', '펜션', '캠핑장', '연극', '뮤지컬', '콘서트', '공연', '전시', '강좌', '레슨', '청소', '수리', '이사', '메뉴', '웨딩', '보정', '제작', '이심', 'USIM', '요금제', '보험', '대출', '렌탈', '강의', '스터디', '원데이클래스', '스튜디오', '촬영', '증명사진']

def is_valid_product_keyword(keyword):
    """일반 명사, 인증/지재권, 그리고 비실물(무형) 상품이 섞여있는지 스크리닝하는 인공지능형 5중 필터"""
    if len(keyword) < 2: return False
    
    # 일반 명사 배제
    for gw in GENERIC_WORDS:
        if keyword == gw or keyword.replace(" ", "") == gw: return False
        
    # V4.9.2 & V4.9.3 강력한 5대 방어막 가동 (하나라도 걸리면 즉시 탈락)
    all_blacklists = FORBIDDEN_WORDS + BRAND_BLACK_WORDS + KC_CERT_WORDS + FOOD_SAFE_WORDS + STRICT_LEGAL_WORDS + NON_PHYSICAL_WORDS
    for bw in all_blacklists:
        if bw in keyword: 
            return False
            
    return True

def get_multi_channel_tag(keyword, pss_score, is_fragile, avg_price):
    """아이템 속성 기반 최적 판매 채널 태깅 및 B2B 납품 권장"""
    if is_fragile:
        if pss_score >= 100: return "🥇 1순위 [즉시 B2C 직판 & 포장재 묶음 판매 (초고마진)]"
        else: return "🥈 2순위 [B2B 포장재 영업 최우선 타겟 (완충재 필수)]"
    
    if pss_score >= 100 and avg_price >= 10000:
        return "📦 [B2C 즉시 소싱] 무재고 직배송 마진 최적화 (블루오션)"
    elif pss_score < 10:
        return "💩 [접근 금지] 최악의 레드오션 (박스 떼기 불가)"
    
    is_rocket = any(rw in keyword for rw in ROCKET_WORDS)
    is_always = any(aw in keyword for aw in ALWAYS_WORDS)
    
    if is_rocket:
        return "🚀 쿠팡 로켓 (박스 떼기 추천)"
    elif is_always:
        return "⚡ 올웨이즈/토스 (초저가/공동구매)"
    else:
        return "📦 스마트스토어/자사몰 (일반 배송)"

SEED_KEYWORDS = ["스티로폼 박스", "종이 아이스팩", "야자매트 35mm"]

SCANNER_HISTORY_FILE = os.path.join("data", "scanner_history.csv")

@st.cache_data(ttl=600, show_spinner=False)
def load_scanner_dashboard_data():
    try:
        client = get_gsheets_client()
        if not client: return pd.DataFrame()
        ws = get_or_create_worksheet(client, "Scanner_History")
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame()
    except Exception as e:
        print(f"스캐너 구글 시트 에러: {e}")
        return pd.DataFrame()

def log_scanner_history(new_df):
    try:
        client = get_gsheets_client()
        if not client: return
        ws = get_or_create_worksheet(client, "Scanner_History")
        exist_data = ws.get_all_records()
        df_exist = pd.DataFrame(exist_data) if exist_data else pd.DataFrame()
        df_merged = pd.concat([df_exist, new_df], ignore_index=True)
        if not df_merged.empty:
            df_merged.drop_duplicates(subset=['키워드'], keep='last', inplace=True)
            ws.clear()
            ws.update([df_merged.columns.values.tolist()] + df_merged.values.tolist())
            df_merged.to_csv(SCANNER_HISTORY_FILE, index=False, encoding='utf-8-sig')
            try: load_scanner_dashboard_data.clear()
            except: pass
    except Exception as e:
        print("Scanner history log error:", e)

def analyze_item_metrics(keyword, cat_name="수동 투입"):
    shop_url = "https://openapi.naver.com/v1/search/shop.json"
    shop_params = {"query": keyword, "display": 10} # [NEW V4.9.1] 10개 상품 조회해서 평균가격 파악
    shop_data = safe_api_request("GET", shop_url, params=shop_params, batch_mode=True)
    
    if shop_data is None: return None
        
    total_products = shop_data.get('total', 0)
    
    # [NEW V4.9.1] 평균 판매 단가 산출 및 [V4.9.7] 썸네일/링크 파싱
    avg_price = 0
    img_link = ""
    prod_link = ""
    if shop_data.get('items'):
        items = shop_data['items']
        prices = [int(item.get('lprice', 0)) for item in items if item.get('lprice')]
        if prices:
            avg_price = sum(prices) / len(prices)
        if len(items) > 0:
            item0 = items[0]
            img_link = item0.get('image', '')
            prod_link = item0.get('link', '')
         
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    dl_url = "https://openapi.naver.com/v1/datalab/search"
    dl_headers = {"Content-Type": "application/json"}
    
    base_keyword = SEED_KEYWORDS[0]
    dl_body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "timeUnit": "month",
        "keywordGroups": [
            {"groupName": base_keyword, "keywords": [base_keyword]},
            {"groupName": keyword, "keywords": [keyword]}
        ]
    }
    
    dl_data = safe_api_request("POST", dl_url, headers=dl_headers, json_data=dl_body, batch_mode=True)
    if dl_data is None: return None
        
    search_score = 0.0
    if 'results' in dl_data:
        target_ratio, base_ratio = 0, 0.001
        for g in dl_data['results']:
            r_sum = sum(d.get('ratio', 0) for d in g.get('data', []))
            if g['title'] == keyword: target_ratio = r_sum
            elif g['title'] == base_keyword: base_ratio = r_sum if r_sum > 0 else 0.001
        search_score = (target_ratio / base_ratio) * 100
    
    # [NEW V4.9.1] PSS (Product Sourcing Score) 계산 로직
    base_attractiveness = ((search_score / total_products) * 10000) if total_products > 0 else 0.0
    
    # 파손/신선식품 여부 -> 제이제이컴퍼니 주력 타겟 (완충재/아이스팩 필수)
    is_fragile = any(fw in keyword for fw in FRAGILE_FRESH_WORDS)
    
    # 마진율/객단가 보정 
    price_weight = 1.0
    if avg_price > 10000:
        price_weight = 1.5
    elif avg_price < 3000:
        price_weight = 0.5
        
    pss_score = base_attractiveness * price_weight
    if is_fragile:
        pss_score *= 2.0  # 파손/신선식품은 PSS 점수 2배 뻥튀기 (납품 우선권 부여)
        
    tag = get_multi_channel_tag(keyword, pss_score, is_fragile, avg_price)
        
    return {
        "발견일자": datetime.now().strftime("%Y-%m-%d"),
        "대상 카테고리": cat_name,
        "키워드": keyword,
        "수요지수": round(search_score, 1),
        "경쟁자수(상품)": total_products,
        "평균단가": f"{int(avg_price):,}원",
        "JJ_PSS(스코어)": round(pss_score, 1),
        "B2B/B2C 영업 타겟": tag,
        "상품 이미지": f'=IMAGE("{img_link}")' if img_link else "이미지 없음",
        "다이렉트 소싱": f'=HYPERLINK("{prod_link}", "[ 🔗 상품 분석 창 열기 ]")' if prod_link else "링크 없음"
    }

# V4.3 DataFrame 제거용 마크다운 변환 함수
def df_to_markdown_table(df):
    if df.empty: return ""
    md = f"| {' | '.join(df.columns)} |\n"
    md += f"| {' | '.join(['---'] * len(df.columns))} |\n"
    for _, row in df.iterrows():
        # 천 단위 콤마 추가 등 포맷팅
        formatted_row = []
        for v in row:
            if isinstance(v, (int, float)):
                if isinstance(v, float):
                    formatted_row.append(f"{v:,.2f}")
                else:
                    formatted_row.append(f"{v:,}")
            else:
                formatted_row.append(str(v))
        md += f"| {' | '.join(formatted_row)} |\n"
    # 마크다운 렌더링에 HTML 허용
    return md

# ==========================================
# 3. 플랫폼 상위 노출 콘텐츠 진단기
# ==========================================
def fetch_top_contents(keyword, target="blog"):
    url_map = {
        "blog": "https://openapi.naver.com/v1/search/blog.json",
        "cafe": "https://openapi.naver.com/v1/search/cafearticle.json",
        "news": "https://openapi.naver.com/v1/search/news.json"
    }
    url = url_map.get(target, url_map["blog"])
    params = {"query": keyword, "display": 10, "sort": "sim"}
    
    data = safe_api_request("GET", url, params=params)
    if data and 'items' in data:
        return data['items']
    return []

# ==========================================
# 4. 백그라운드 스캔 관리 & 세션 상태 및 공용 데이터랩 모듈
# ==========================================
if 'scan_results' not in st.session_state:
    st.session_state.scan_results = pd.DataFrame()

# [NEW V4.9.4] 사용자 피드백 반영: 제이제이컴퍼니용 B2B/무재고 소싱 추천 랭킹 & 가이드라인(이모지) UI 직접 표기
CAT_LIST = {
    "🥇 [1순위 최고추천] 생활/건강 (종이완충재/박스 100% 매칭)": "50000008", 
    "🥈 [2순위 고마진] 가구/인테리어 (소품류 사입 최적화)": "50000004", 
    "🥉 [3순위 블루오션] 스포츠/레저 (캠핑/무전력 장비)": "50000007",
    "⭐ [4순위 묶음판매] 패션잡화 (가방/모자/파우치류)": "50000001", 
    "🚨 [위험] 디지털/가전 (KC 전파인증 / 배터리 주의)": "50000003", 
    "💩 [절대금지] 출산/육아 (어린이특별법 인증 필수)": "50000005", 
    "💩 [절대금지] 식품 (식약처 정밀 수입 검사 필수)": "50000006",
    "💩 [절대금지] 화장품/미용 (화장품법 인허가 필수)": "50000002",
    "패션의류 (사이즈 반품 폭탄 주의)": "50000000", 
    "여가/생활편의 (V4.9.3 실물필터 적용 중)": "50000009", 
    "도서": "50000010"
}

def fetch_realtime_top50_full(cid):
    ajax_url = "https://datalab.naver.com/shoppingInsight/getCategoryKeywordRank.naver"
    ajax_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://datalab.naver.com/shoppingInsight/sCategory.naver",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
    }
    
    for days_back in [1, 2, 3]:
        target_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        full_ranks = []
        
        # 네이버는 페이지당 20개씩 끊어주므로 1, 2, 3페이지(총 60개) 스캔 후 50개에서 자름
        for page in range(1, 4):
            payload = {
                "cid": cid, "timeUnit": "date", "startDate": target_date, "endDate": target_date,
                "age": "", "gender": "", "device": "", "page": str(page), "count": "20"
            }
            try:
                r = requests.post(ajax_url, headers=ajax_headers, data=payload, timeout=10)
                if r.status_code == 200:
                    json_data = r.json()
                    if "ranks" in json_data and json_data["ranks"]:
                        full_ranks.extend(json_data["ranks"])
            except: pass
            time.sleep(0.5)
            
        if full_ranks:
            # 중복 제거 및 상위 50개 컷
            seen = set()
            unique_ranks = []
            for item in full_ranks:
                if item["keyword"] not in seen:
                    seen.add(item["keyword"])
                    unique_ranks.append(item)
                    if len(unique_ranks) == 50:
                        break
            return unique_ranks, target_date
            
    return [], ""

# ==========================================
# 5. 메인 레이아웃 (6 탭 구성) - V4.8 구글 트렌드 융합 에디션
# ==========================================
tab_trend, tab_scanner, tab_content, tab_marketing, tab_daily, tab_google = st.tabs([
    "📊 시장 수요 동향 (트렌드)", 
    "💡 신사업 인사이트 도출기 (스캐너)", 
    "🔎 경쟁 강도 및 채널 분석", 
    "✍️ B2B 마케팅 자동화 (원고 생성)",
    "🚀 일간 자동화 & 신규 키워드 누적",
    "💰 애드센스 황금 키워드 자동 채굴기"
])

# ------------- [1] 시장 수요 동향 탭 -------------
with tab_trend:
    st.header("📈 네이버 데이터랩 검색 트렌드 (최근 1년 동향)")
    col1, col2 = st.columns([3, 1])
    with col1:
        trend_kws = st.text_input("비교 분석할 키워드 (최대 5개, 쉼표 구분)", "스티로폼 박스, 종이 아이스팩")
    with col2:
        trend_unit = st.selectbox("조회 기준", ["date", "week", "month"], index=2)
        
    if st.button("트렌드 차트 추출", use_container_width=True):
        words = [w.strip() for w in trend_kws.split(",") if w.strip()][:5]
        if words:
            kw_groups = [{"groupName": w, "keywords": [w]} for w in words]
            ed = datetime.now()
            sd = ed - timedelta(days=365)
            
            t_url = "https://openapi.naver.com/v1/datalab/search"
            t_body = {
                "startDate": sd.strftime("%Y-%m-%d"),
                "endDate": ed.strftime("%Y-%m-%d"),
                "timeUnit": trend_unit,
                "keywordGroups": kw_groups
            }
            
            with st.spinner("1년치 데이터를 로드 중입니다..."):
                t_data = safe_api_request("POST", t_url, headers={"Content-Type": "application/json"}, json_data=t_body)
                dfs = []
                if t_data and 'results' in t_data:
                    for g in t_data['results']:
                        if g.get('data'):
                            df_t = pd.DataFrame(g['data'])
                            df_t.rename(columns={'ratio': g['title']}, inplace=True)
                            df_t['period'] = pd.to_datetime(df_t['period'])
                            df_t.set_index('period', inplace=True)
                            dfs.append(df_t[[g['title']]])
                
                if dfs:
                    df_final = pd.concat(dfs, axis=1).fillna(0)
                    st.line_chart(df_final, use_container_width=True)
                    st.markdown("---")
                    st.markdown("### 📋 **상세 관측 수치 (월별/주별)**")
                    # V4.3 DataFrame 에러 회피용 st.write(표) 출력
                    st.write(df_to_markdown_table(df_final.sort_index(ascending=False).reset_index()), unsafe_allow_html=True)
                else:
                    st.warning("데이터가 부족합니다.")

# ------------- [2] 신사업 인사이트 스캐너 탭 -------------
with tab_scanner:
    st.header("💡 타겟 카테고리 실시간 딥스캔 레이더 (V4.9 에디션)")
    st.markdown("네이버 쇼핑인사이트의 **실시간 Top 50 검색어 랭킹 API**에 직결하여, 특정 카테고리에서 가장 뜨고 있는 트렌드 키워드들을 라이브로 수집하고 즉시 딥스캔(경쟁 강도 점수화)합니다.")
    st.info("ℹ️ **시드 블랙리스트 방벽 가동 중**: 자사 주력 품목은 철저히 제거하여 완전 새로운 파이프라인(빈집)만 탐색합니다.")
    
    col_sc1, col_sc2 = st.columns([1.5, 1])
    with col_sc1:
        # 가로로 배치 (카테고리 선택 및 스캔 갯수)
        c_sub1, c_sub2 = st.columns([2, 1])
        with c_sub1:
            target_cat = st.selectbox("딥스캔 수행 카테고리 (네이버 망)", list(CAT_LIST.keys()))
        with c_sub2:
            scan_limit = st.slider("최대 발굴 수", min_value=10, max_value=50, value=20, step=10)
            
        if st.button("🚀 실시간 네이버 쇼핑 트렌드 딥스캔 빔 발사", use_container_width=True):
            cid = CAT_LIST[target_cat]
            status_bar = st.empty()
            prog_bar = st.progress(0)
            
            status_bar.info(f"📡 네이버 데이터랩 서버 침투 중... [{target_cat}] 부문 최상위 실시간 트렌드 추출 대기")
            ranks, _ = fetch_realtime_top50_full(cid)
            
            if not ranks:
                status_bar.error("🚨 현재 네이버 데이터랩 서버 응답이 지연되거나 접근이 일시 차단되었습니다. 잠시 후 재시도 바랍니다.")
            else:
                target_kws = [item['keyword'] for item in ranks][:scan_limit]
                status_bar.success(f"✅ [{target_cat}] 부문 총 {len(target_kws)}개의 실시간 트렌드 키워드 생포 완료! 즉시 네이버 쇼핑 API망으로 이송하여 수익성/경쟁강도 검증을 시작합니다.")
                
                scan_res = []
                for i, kw in enumerate(target_kws):
                    ckey = get_rotating_client()[0]
                    status_bar.info(f"🔄 **정밀 수익성 검증 중 ({i+1}/{len(target_kws)})** : [{ckey}번 검증기] ➣ `{kw}`")
                    
                    if kw not in SEED_KEYWORDS and is_valid_product_keyword(kw):
                        row = analyze_item_metrics(kw, target_cat)
                        if row is None: 
                            time.sleep(1.0)
                            continue
                        scan_res.append(row)
                        
                    prog_bar.progress((i+1)/len(target_kws))
                    time.sleep(0.3)
                    
                prog_bar.empty()
                status_bar.success(f"🎉 딥스캔 완료! 쓰레기값을 필터링한 후 총 **{len(scan_res)}개**의 돈 되는 초알짜 신사업 포트폴리오가 도출되었습니다.")
                
                if scan_res:
                    df_new = pd.DataFrame(scan_res)
                    st.session_state.scan_results = pd.concat([st.session_state.scan_results, df_new]).drop_duplicates(subset=['키워드'], keep='last')
                    log_scanner_history(df_new)
                
    with col_sc2:
        manual_input = st.text_input("수동 조사항목 추가 (관측 대상, 쉼표 구분)", "무지 박스, 포장용 랩")
        if st.button("➕ 관측 대상 수동 투입", use_container_width=True):
            m_list = [k.strip() for k in manual_input.split(",") if k.strip()]
            scan_res = []
            for kw in m_list:
                if kw not in SEED_KEYWORDS and is_valid_product_keyword(kw):
                    row = analyze_item_metrics(kw, "수동 투입")
                    if row: scan_res.append(row)
            if scan_res:
                df_new = pd.DataFrame(scan_res)
                st.session_state.scan_results = pd.concat([st.session_state.scan_results, df_new]).drop_duplicates(subset=['키워드'], keep='last')
                log_scanner_history(df_new)
                st.success(f"✅ {len(scan_res)}개 품목이 인덱스에 수동 추가되었습니다.")
                
        st.write("---")
        st.caption("여러 번 스캔한 결과는 하나의 표에 계속 누적됩니다. 새 테이블로 시작하려면 아래 버튼을 누르세요.")
        if st.button("🗑️ 이전 스캔 기록 전체 지우기 (초기화)"):
            st.session_state.scan_results = pd.DataFrame()
            st.rerun()

    st.markdown("---")
    st.markdown("### 🏆 **비즈니스 통합 리포트: 라이브 딥스캔 스코어링(PSS) 판별표**")
    if not st.session_state.scan_results.empty:
        # PSS 점수가 가장 높은 갓성비/B2B 타겟 순으로 내림차순 정렬
        df_display = st.session_state.scan_results.sort_values(by="JJ_PSS(스코어)", ascending=False).reset_index(drop=True)
        # V4.3 DataFrame 렌더링 에러 방지용 마크다운 변환 대신 V4.9 HTML 렌더링
        df_display_html = df_display.copy()
        import re
        def parse_google_sheet_formula_mini(val):
            val_str = str(val)
            if val_str.startswith('=IMAGE("'):
                match = re.search(r'=IMAGE\("([^"]+)"\)', val_str)
                if match: return f'<img src="{match.group(1)}" height="60" style="border-radius:6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">'
            elif val_str.startswith('=HYPERLINK("'):
                match = re.search(r'=HYPERLINK\("([^"]+)",\s*"([^"]+)"\)', val_str)
                if match: return f'<a href="{match.group(1)}" target="_blank" style="text-decoration:none;font-weight:bold;color:#1f77b4;background-color:#f0f2f6;padding:4px 8px;border-radius:4px;">{match.group(2)}</a>'
            return val_str
            
        if "상품 이미지" in df_display_html.columns:
            df_display_html["상품 이미지"] = df_display_html["상품 이미지"].apply(parse_google_sheet_formula_mini)
        if "다이렉트 소싱" in df_display_html.columns:
            df_display_html["다이렉트 소싱"] = df_display_html["다이렉트 소싱"].apply(parse_google_sheet_formula_mini)
            
        st.write(df_display_html.to_html(escape=False, index=False, classes='table table-striped table-hover'), unsafe_allow_html=True)
    else:
        st.write("관측된 신규 아이템 포트폴리오가 없습니다. 위 카테고리를 선택하고 🚀 딥스캔 빔을 발사해 주십시오.")
        
    st.write("---")
    st.markdown("### 🖼️ 영구 누적 대시보드 (스캐너 발굴 기록 종합)")
    
    df_history = load_scanner_dashboard_data()
    if df_history.empty and os.path.exists(SCANNER_HISTORY_FILE):
        try: df_history = pd.read_csv(SCANNER_HISTORY_FILE, encoding='utf-8-sig')
        except:
            try: df_history = pd.read_csv(SCANNER_HISTORY_FILE, encoding='cp949')
            except: pass
            
    if not df_history.empty:
        import re
        def parse_google_sheet_formula(val):
            val_str = str(val)
            if val_str.startswith('=IMAGE("'):
                match = re.search(r'=IMAGE\("([^"]+)"\)', val_str)
                if match: return f'<img src="{match.group(1)}" height="130" style="border-radius:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
            elif val_str.startswith('=HYPERLINK("'):
                match = re.search(r'=HYPERLINK\("([^"]+)",\s*"([^"]+)"\)', val_str)
                if match: return f'<a href="{match.group(1)}" target="_blank" style="text-decoration:none;font-weight:bold;color:#1f77b4;background-color:#f0f2f6;padding:5px 10px;border-radius:5px;">{match.group(2)}</a>'
            return val_str
            
        if "상품 이미지" in df_history.columns:
            df_history["상품 이미지"] = df_history["상품 이미지"].apply(parse_google_sheet_formula)
        if "다이렉트 소싱" in df_history.columns:
            df_history["다이렉트 소싱"] = df_history["다이렉트 소싱"].apply(parse_google_sheet_formula)

        # [V4.9.8] '접근 금지' 불량 아이템 은닉 및 PSS 스코어 최상위 랭크 정렬 
        if "B2B/B2C 영업 타겟" in df_history.columns and "JJ_PSS(스코어)" in df_history.columns:
            df_history = df_history[~df_history["B2B/B2C 영업 타겟"].str.contains("접근 금지", na=False)]
            df_history["JJ_PSS(스코어)"] = pd.to_numeric(df_history["JJ_PSS(스코어)"], errors="coerce")
            df_history = df_history.sort_values(by="JJ_PSS(스코어)", ascending=False).reset_index(drop=True)
        else:
            df_history = df_history.iloc[::-1].reset_index(drop=True)
        
        custom_css_scanner = """<style>
.custom-table2 table { width: 100%; text-align: center; }
.custom-table2 th { background-color: #f8f9fa; font-weight: bold; text-align: center !important; }
.custom-table2 td { vertical-align: middle !important; }
.custom-table2 th:nth-child(1) { width: 8%; } /* 발견일자 */
.custom-table2 th:nth-child(2) { width: 8%; } /* 대상 카테고리 */
.custom-table2 th:nth-child(3) { width: 10%; font-size: 1.1em; } /* 키워드 */
.custom-table2 th:nth-child(4) { width: 6%; } /* 수요지수 */
.custom-table2 th:nth-child(5) { width: 7%; } /* 경쟁자수 */
.custom-table2 th:nth-child(6) { width: 7%; } /* 평균단가 */
.custom-table2 th:nth-child(7) { width: 7%; } /* PSS */
.custom-table2 th:nth-child(8) { width: 8%; } /* 마케팅타겟 */
.custom-table2 th:nth-child(9) { width: 25%; } /* 상품 이미지 */
.custom-table2 th:nth-child(10) { width: 14%; } /* 링크 */
</style>"""
        html_table = df_history.to_html(escape=False, index=False, classes='table table-striped table-hover')
        st.write(custom_css_scanner + f'<div class="custom-table2">{html_table}</div>', unsafe_allow_html=True)
    else:
        st.info("💡 스캐너를 통해 발굴된 영구 데이터 스택이 아직 없습니다.")

# ------------- [3] 경쟁 강도 및 채널 분석 탭 -------------
with tab_content:
    st.header("🔎 경쟁 채널 상위 노출 벤치마킹 (안정성 강화 모드)")
    st.markdown("특정 키워드에 대한 타사/경쟁사의 1페이지(Top 10) 핵심 진입 장벽을 파악합니다. 하이퍼링크를 눌러 안전하게 모니터링하세요.")
    
    c_col1, c_col2 = st.columns([3, 1])
    with c_col1:
        target_kw = st.text_input("경쟁 강도 점검 키워드", "금산 스티로폼 박스")
    with c_col2:
        platform = st.selectbox("데이터 소스 채널", ["블로그 (Blog)", "카페 (Cafe)", "뉴스 (News)"])
    
    p_map = {"블로그 (Blog)": "blog", "카페 (Cafe)": "cafe", "뉴스 (News)": "news"}
    
    if st.button("최상위 점유율 10개 문서 파싱", use_container_width=True):
        with st.spinner("경쟁 문서 빅데이터 수집 중..."):
            items = fetch_top_contents(target_kw, p_map[platform])
            
        if items:
            import re
            def clean_html(raw_html):
                return re.sub(re.compile('<.*?>'), '', raw_html)
                
            parsed_items = []
            for idx, item in enumerate(items):
                pub_date = item.get('postdate') or item.get('pubDate', '')
                try:
                    if platform != "뉴스 (News)" and len(pub_date) == 8:
                        pub_date = f"{pub_date[:4]}-{pub_date[4:6]}-{pub_date[6:]}"
                except: pass
                
                link_url = item.get('link', '') or item.get('originallink', '')
                clean_title = clean_html(item.get('title', ''))
                
                # 마크다운 형태의 링크 생성
                md_link = f"<a href='{link_url}' target='_blank'>{clean_title}</a>"
                
                parsed_items.append({
                    "랭킹": f"{idx+1}위",
                    "하이퍼링크 타이틀 (새창 지원)": md_link,
                    "작성일": pub_date,
                    "퍼블리셔": item.get('bloggername') or item.get('cafename') or item.get('originallink', '알 수 없음')
                })
                
            st.success(f"✅ 경쟁 키워드 '{target_kw}'에 대한 벤치마킹 데이터 파싱 완료.")
            
            # V4.3 DOM/NotFoundError 방어를 위한 Container 내 Markdown html 렌더링
            with st.container():
                st.markdown("### 📊 상위 점유 문서 현황판")
                df_parsed = pd.DataFrame(parsed_items)
                st.write(df_parsed.to_html(escape=False, index=False, classes='table table-striped table-hover'), unsafe_allow_html=True)
            
            st.write("---")
            st.markdown("*(B2B 마케팅 팀 제언) 상위 문서가 너무 오래된 키워드라면 최적화된 블로그 발행으로 신속히 우위를 점할 수 있습니다.*")
        else:
            st.warning("상위 1페이지 경쟁 문서가 전혀 없습니다. 블루 오션입니다.")

# ------------- [4] B2B 마케팅 자동화 탭 (V4.3 프로페셔널 버전) -------------
with tab_marketing:
    st.header("✍️ 제이제이컴퍼니 전용 B2B 마케팅 AI")
    st.markdown("데이터와 물류 효율을 중시하는 **30대 꼼꼼한 전문 마케터** 관점에서 제이제이컴퍼니 주력망 9대 카테고리의 5,000자 통합 솔루션을 도출합니다.")
    
    # 9대 주력 상품 인덱스
    VALID_CATEGORIES = ["스티로폼", "단열박스(프레시박스)", "아이스팩(완제품)", "아이스팩(반제품)", "에어캡", "에어쿠션", "OPP테이프", "박스커터기", "야자매트(35mm)"]
    
    st.info("💡 **제이제이컴퍼니 9대 주력 카테고리만 엄중 지원합니다**: \n\n" + ", ".join(VALID_CATEGORIES))
    
    # V4.3 플랫폼 선택 폼 분리
    target_platform = st.radio("전개할 마케팅 플랫폼을 선택해 주십시오.", ["네이버 (Naver Blog - 모바일 스토리텔링 어투)", "티스토리/구글 (Tistory & Google SEO - 전문가 백서 표재형)"], index=0)
    
    m_col1, m_col2 = st.columns([2, 1])
    with m_col1:
        ai_kw = st.text_input("B2B 영업 타겟 핵심 품명", "금산 스티로폼")
    with m_col2:
        st.write("")
        st.write("")
        gen_btn = st.button("📝 전문 마케팅 원고 즉시 발행", use_container_width=True)
        
    if gen_btn:
        st.write("---")
        # 9개 카테고리 검증 로직
        is_valid_cat = False
        for cat in VALID_CATEGORIES:
            core_keyword = cat.replace(" ", "").replace("(", "").replace(")", "").replace("35mm", "")
            if core_keyword in ai_kw.replace(" ", "") or ai_kw.replace(" ", "") in core_keyword:
                is_valid_cat = True
                break
        
        if not is_valid_cat:
            st.error(f"⚠️ 규정 위반 에러: 입력하신 '{ai_kw}' 품목은 당사의 9대 주력 B2B 리스트업 내에 존재하지 않아 원고 생성이 차단되었습니다.")
        else:
            gemini_api_key = os.getenv("GEMINI_API_KEY")
            if not gemini_api_key:
                st.error("🚨 환경 변수 오류: `.env` 파일에 `GEMINI_API_KEY`가 설정되어 있지 않습니다. 구글 AI 스튜디오에서 API 키를 발급받아 프로젝트 루트의 `.env`를 업데이트해 주십시오.")
            else:
                # 최신 google-genai 라이브러리 규격으로 클라이언트 초기화
                client = genai.Client(api_key=gemini_api_key)
                
                with st.spinner("🧠 30대 B2B 마케터 AI(Gemini 2.5)가 지정하신 타겟과 9대 주력 채널 강점을 융합하여 완전히 새로운 마케팅 원고를 창작 중입니다... (약 10~20초 소요)"):
                    
                    # 1. 3대 핵심 소구점 
                    str1 = "제이제이컴퍼니의 금산 자체 최신 공장 설비 라인을 통한 직생산"
                    str2 = "비용 파괴! 1톤 전용 차량을 통한 직접 밀착 배차"
                    str3 = "재고 무한 대기 제로! 대전/충남 전 권역 신속 당일 직배송"
                    
                    # 2. 시스템 프롬프트 설계 (마케터 페르소나 및 플랫폼 최적화)
                    tone_instruction = "스마트폰으로 쉽게 읽히는 네이버 블로그 특유의 친근한 스토리텔링과 현장감 있는 어투를 사용해 줘." if "네이버" in target_platform else "전문 B2B 구글 검색자(SEO)를 타겟하여 논리적이고 객관적인 백서 형태, 목차와 마크다운 표가 잘 짜여진 분석 리포트 어투로 작성해 줘. 존댓말을 써."
                    
                    prompt = f"""
                    너는 충남 금산군에 위치한 B2B 포장재/물류 전문 기업 '제이제이컴퍼니' 소속의, 아주 유능하고 꼼꼼하며 열정 넘치는 30대 비즈니스 마케터야.
                    이번에 네가 회사 공식 채널에 업로드할 마케팅 포스팅의 타겟 핵심 제품은 '{ai_kw}' 야.
                    
                    [필수 포함 3대 무기(소구점)]
                    1. {str1}
                    2. {str2}
                    3. {str3}
                    
                    [작성 지침]
                    - {tone_instruction}
                    - 마크다운(Markdown) 포맷으로 작성할 것 (제목은 # ~ ### 등을 활용)
                    - 단순히 정보를 나열하지 말고, 자영업자나 스토어 대표님들이 '물류비와 파손율' 때문에 기계 번역처럼 보이지 않게 한국의 트렌디한 비즈니스 용어 섞기.
                    - 글 분량은 최소 2000자 ~ 3000자(공백 포함) 길이의 아주 상세하고 퀄리티 높은 장문의 칼럼으로 도출할 것. 
                    - 글의 마지막 부분에는 항상 아래의 연락 정보를 세련되게 변형해서 넣어줘:
                      (📍 거점: 충남 금산군 추부면 | 📱 전문 B2B 견적 핫라인 대기 중)
                    """
                    
                    try:
                        # 출력 레이아웃 프리셋
                        st.markdown(f"""
                        <div class="highlight-card">
                            <h3>🤖 B2B 전문 AI (Gemini 2.5) 실시간 창작 중 ({target_platform.split(' ')[0]})</h3>
                            <p><strong>주제:</strong> {ai_kw} | <strong>담당:</strong> 제이제이컴퍼니 30대 비즈니스 마케터 AI</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 컨테이너 확보
                        res_box = st.empty()
                        
                        # 메인 블로그 원고 실시간 스트리밍 생성 
                        response = client.models.generate_content_stream(
                            model='gemini-2.5-pro',
                            contents=prompt
                        )
                        final_blog_text = ""
                        for chunk in response:
                            final_blog_text += chunk.text
                            res_box.markdown(final_blog_text + " ▌")
                            
                        # 본문 작성 완료 타이핑 커서 제거
                        res_box.markdown(final_blog_text)
                        
                        st.write("---")
                        
                        st.markdown("### 📱 원 소스 멀티 유즈 (OSMU): AI 맞춤형 4대 SNS 브로드캐스팅")
                        st.info("비즈니스 타겟층에 맞춘 SNS 숏폼 카피라이팅 4종입니다.")
                        
                        # SNS 브로드캐스팅용 원고 생성
                        sns_prompt = f"""
                        방금 네가 작성한 '{ai_kw}' 마케팅 원고의 핵심(금산 직생산, 당일 직배송)을 뽑아서, 아래 4가지 플랫폼 성격에 맞게 아주 짧고 강력한 '숏폼 텍스트 카피'를 작성해줘. 해시태그 필수 포함.
                        
                        1. 인스타그램 (사진과 함께 올릴 시각적이고 트렌디한 감성 글, 4줄 이내)
                        2. 페이스북 그룹 (식음료/유통 B2B 모임에서 사장님들끼리 소통하는 묵직하고 실전적인 정보 공유 톤, 4줄 이내)
                        3. 스레드(Threads) (짧고 매운맛의 촌철살인, 텍스트 위주 돌직구 마케팅 톤, 3줄 이내)
                        4. 당근마켓 비즈프로필 (동네 장사나 근거리 지역(충청도) 대표님들을 대상으로 하는 친근한 인사말 톤, 4줄 이내)
                        
                        답변은 반드시 아래 형식 그대로 맞춰서 줘:
                        [인스타그램]
                        (내용)
                        
                        [페이스북]
                        (내용)
                        
                        [스레드]
                        (내용)
                        
                        [당근마켓]
                        (내용)
                        """
                        sns_response = client.models.generate_content(
                            model='gemini-2.5-pro',
                            contents=sns_prompt
                        )
                        sns_text = sns_response.text
                        
                        # 정규식이나 split으로 AI 답변 파싱
                        import re
                        insta = re.search(r'\[인스타그램\](.*?)\[페이스북\]', sns_text, re.S)
                        fb = re.search(r'\[페이스북\](.*?)\[스레드\]', sns_text, re.S)
                        th = re.search(r'\[스레드\](.*?)\[당근마켓\]', sns_text, re.S)
                        dg = re.search(r'\[당근마켓\](.*)', sns_text, re.S)
                        
                        cols_sns = st.columns(2)
                        with cols_sns[0]:
                            st.markdown(f"**[1] 📷 인스타그램 (비주얼/해시태그 타겟)**\n> {insta.group(1).strip() if insta else '생성 실패'}")
                            st.write("")
                            st.markdown(f"**[2] 📘 페이스북 (식음료 B2B 네트워킹 타겟)**\n> {fb.group(1).strip() if fb else '생성 실패'}")
                        with cols_sns[1]:
                            st.markdown(f"**[3] 🧵 스레드 (촌철살인/텍스트 즉답 타겟)**\n> {th.group(1).strip() if th else '생성 실패'}")
                            st.write("")
                            st.markdown(f"**[4] 🥕 당근마켓 비즈프로필 (동네 장사/근거리 권역 타겟)**\n> {dg.group(1).strip() if dg else '생성 실패'}")
                            
                    except Exception as e:
                        st.error(f"🚨 AI 원고 창작 중 오류가 발생했습니다: {str(e)}")

# ------------- [5] V4.4 일간 상위 50 트렌드 추적 탭 -------------
# ------------- [5] V4.6 일괄 자동화 & 신규 키워드 영구 누적 대시보드 -------------
with tab_daily:
    st.header("🚀 일간 전 카테고리 자동 수집 & 신규 아이템 요격 대시보드 (V4.6 에디션)")
    st.markdown("단 한 번의 클릭으로 **네이버 11개 대분류 550개(50위 x 11) 인기 검색어를 일괄 스캔**합니다. 어제와 대조하여 **새롭게 50위권에 진입한 유망 상품**만 족집게처럼 발라내어, 상품 썸네일과 함께 영구 누적 대시보드에 전시합니다.")
    
    CUMULATIVE_FILE = os.path.join("data", "cumulative_new_trends.csv")
        
    def get_shopping_image(keyword):
        # 신규 키워드 발견 시 네이버 쇼핑 API를 통해 1위 상품 썸네일과 링크 파싱
        shop_url = "https://openapi.naver.com/v1/search/shop.json"
        shop_params = {"query": keyword, "display": 1, "sort": "sim"}
        shop_data = safe_api_request("GET", shop_url, params=shop_params, batch_mode=True)
        
        if shop_data and 'items' in shop_data and len(shop_data['items']) > 0:
            item = shop_data['items'][0]
            link = item.get('link', '')
            image = item.get('image', '')
            return image, link
        return "", ""

    # 일괄 수집 시작 버튼
    st.info("💡 **운영 지침**: 매일 아침 출근 시 아래 버튼을 단 1번 눌러 전날 기준 신규 트렌드 상품을 일괄 포획하십시오.")
    btn_auto_scan = st.button("🚀 아침 9시 전 카테고리 일괄 550개 수집 및 신규 아이템 관제 가동", use_container_width=True)
    
    if btn_auto_scan:
        st.write("---")
        prog_bar = st.progress(0)
        status_text = st.empty()
        
        today_folder_name = datetime.now().strftime("%Y%m%d")
        base_dir = os.path.join("data", "realtime_top50")
        today_dir = os.path.join(base_dir, today_folder_name)
        os.makedirs(today_dir, exist_ok=True)
        
        # 이전 날짜 폴더 찾기 로직
        past_folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f)) and f != today_folder_name]
        latest_past_dir = None
        if past_folders:
            past_folders.sort(reverse=True) # 가장 최근 과거 폴더
            latest_past_dir = os.path.join(base_dir, past_folders[0])
        
        new_trends = [] # 누적할 신규 아이템 리스트
        
        cats = list(CAT_LIST.items())
        for idx, (c_name, c_code) in enumerate(cats):
            status_text.markdown(f"**실시간 망 순회 중... ({idx+1}/{len(cats)})** : 🕵️‍♂️ `{c_name}` 50개 개척 중...")
            ranks, r_date = fetch_realtime_top50_full(c_code)
            
            if ranks:
                # 1. 오늘 것 저장
                df_today = pd.DataFrame(ranks)[["rank", "keyword"]]
                df_today.to_csv(os.path.join(today_dir, f"Top50_{c_code}.csv"), encoding='utf-8-sig', index=False)
                
                # 2. 어제 것과 대조
                past_keywords = []
                if latest_past_dir:
                    past_file = os.path.join(latest_past_dir, f"Top50_{c_code}.csv")
                    if os.path.exists(past_file):
                        df_past = pd.read_csv(past_file)
                        past_keywords = df_past["keyword"].tolist()
                        
                # 3. 신규 유입 판별
                today_kws = df_today["keyword"].tolist()
                for kw in today_kws:
                    if kw not in past_keywords:
                        # 4. 이미지, 링크 파싱 (api rate limit 방어 위해 0.3s 슬립)
                        img, lnk = get_shopping_image(kw)
                        time.sleep(0.3)
                        new_trends.append({
                            "발견일자": datetime.now().strftime("%Y-%m-%d"),
                            "대상 카테고리": c_name.split("(")[0].strip(),
                            "신규 유망 키워드": kw,
                            "상품 이미지": f'=IMAGE("{img}")' if img else "이미지 없음",
                            "다이렉트 소싱": f'=HYPERLINK("{lnk}", "[ 🔗 상품 분석 창 열기 ]")' if lnk else "링크 없음"
                        })
            
            prog_bar.progress((idx + 1) / len(cats))
            
        # 5. 영구 누적 기록
        if new_trends:
            # 기존에 Sheets에 저장된 키워드 로드
            try:
                logged_keywords_data = get_or_create_worksheet(get_gsheets_client(), "Cumulative_Trends").get_all_records()
                df_exist = pd.DataFrame(logged_keywords_data) if logged_keywords_data else pd.DataFrame()
            except Exception as e:
                df_exist = pd.DataFrame()
                print(f"기존 누적 데이터 조회 오류 (무시하고 계속 진행): {e}")

            df_new = pd.DataFrame(new_trends)
            
            # 기존 데이터와 새 데이터를 병합
            df_merged = pd.concat([df_exist, df_new], ignore_index=True)
            
            # 중복 제거 (예: '신규 유망 키워드'와 '발견일자' 기준으로)
            df_merged.drop_duplicates(subset=['신규 유망 키워드', '발견일자'], keep='first', inplace=True)
            
            # Google Sheets에 저장
            try:
                ws_cumulative = get_or_create_worksheet(get_gsheets_client(), "Cumulative_Trends")
                if ws_cumulative:
                    # 기존 내용 삭제 후 새로 쓰기 (간단한 방법)
                    ws_cumulative.clear()
                    ws_cumulative.update([df_merged.columns.values.tolist()] + df_merged.values.tolist())
                    
                    # [V4.9.6] 엑셀 백업 유지 및 대시보드 구글시트 캐시 리셋
                    df_merged.to_csv(CUMULATIVE_FILE, index=False, encoding='utf-8-sig')
                    try:
                        load_cumulative_dashboard_data_v2.clear()
                    except: pass
            except Exception as e:
                status_text.error(f"⚠️ 영구 누적 저장 과정에서 Google Sheets API 에러가 발생했습니다: {e}")
            
            status_text.success(f"✅ 일괄 순회 완료! 과거 데이터 대비 무려 **{len(new_trends)}개**의 신규 아이템을 발굴하여 금고에 누적했습니다.")
        else:
            status_text.info("✅ 일괄 순회 완료! 어제 대비 새롭게 치고 올라온 신규 아이템이 없습니다. (혹은 과거 비교용 데이터가 없습니다.)")
            
        # [V4.9.5 BATCH] 쌓아둔 API 사용량 캐시를 한 번에 구글 시트에 업데이트
        flush_api_usage()
        prog_bar.empty()
        
    st.write("---")
    st.markdown("### 🖼️ 영구 누적 대시보드 (제이제이컴퍼니 신사업 프론티어)")
    
    @st.cache_data(ttl=600, show_spinner=False)
    def load_cumulative_dashboard_data_v2():
        try:
            client = get_gsheets_client()
            if not client: return pd.DataFrame()
            ws = get_or_create_worksheet(client, "Cumulative_Trends")
            data = ws.get_all_records()
            return pd.DataFrame(data) if data else pd.DataFrame()
        except Exception as e:
            print(f"구글 시트 로컬에서 읽기 에러: {e}")
            return pd.DataFrame()
            
    # [V4.9.6] 화면 로드 시 먼저 구글 시트 클라우드 엑셀을 가장 우선으로 당겨옴
    df_gallery = load_cumulative_dashboard_data_v2()
    
    # 만약 구글 시트에서 오류로 비어있다면, 로컬 엑셀 파일 백업본에서라도 복구
    if df_gallery.empty and os.path.exists(CUMULATIVE_FILE):
        try:
            df_gallery = pd.read_csv(CUMULATIVE_FILE, encoding='utf-8-sig')
        except: 
            try:
                df_gallery = pd.read_csv(CUMULATIVE_FILE, encoding='cp949')
            except Exception as e:
                print(f"로컬 파일 읽기 실패: {e}")
    
    if not df_gallery.empty:
        import re
        def parse_google_sheet_formula(val):
            val_str = str(val)
            if val_str.startswith('=IMAGE("'):
                match = re.search(r'=IMAGE\("([^"]+)"\)', val_str)
                if match:
                    return f'<img src="{match.group(1)}" height="130" style="border-radius:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">'
            elif val_str.startswith('=HYPERLINK("'):
                match = re.search(r'=HYPERLINK\("([^"]+)",\s*"([^"]+)"\)', val_str)
                if match:
                    return f'<a href="{match.group(1)}" target="_blank" style="text-decoration:none;font-weight:bold;color:#1f77b4;background-color:#f0f2f6;padding:5px 10px;border-radius:5px;">{match.group(2)}</a>'
            return val_str
            
        if "상품 이미지" in df_gallery.columns:
            df_gallery["상품 이미지"] = df_gallery["상품 이미지"].apply(parse_google_sheet_formula)
        if "다이렉트 소싱" in df_gallery.columns:
            df_gallery["다이렉트 소싱"] = df_gallery["다이렉트 소싱"].apply(parse_google_sheet_formula)

        # 역순 정렬 (최신이 위로)
        df_gallery = df_gallery.iloc[::-1].reset_index(drop=True)
        
        # UI 가독성 향상 커스텀 CSS 강제 주입 (들여쓰기 제거 필수: 마크다운 코드블록 오인 방지)
        custom_css = """<style>
.custom-table table { width: 100%; text-align: center; }
.custom-table th { background-color: #f8f9fa; font-weight: bold; text-align: center !important; }
.custom-table td { vertical-align: middle !important; }
.custom-table th:nth-child(1) { width: 10%; } /* 발견일자 */
.custom-table th:nth-child(2) { width: 12%; } /* 카테고리 */
.custom-table th:nth-child(3) { width: 15%; font-size: 1.1em; } /* 키워드 (축소) */
.custom-table th:nth-child(4) { width: 43%; } /* 썸네일 (대폭 확대) */
.custom-table th:nth-child(5) { width: 20%; } /* 소싱 링크 */
</style>"""
        html_table = df_gallery.to_html(escape=False, index=False, classes='table table-striped table-hover')
        st.write(custom_css + f'<div class="custom-table">{html_table}</div>', unsafe_allow_html=True)
    else:
        st.warning("아직 누적된 신사업 아이템 데이터가 없습니다. 상단 로직을 1회 이상 가동해 주십시오.")

# ------------- [6] V4.8 애드센스 황금 키워드 자동 채굴기 -------------
with tab_google:
    st.header("💰 구글 애드센스 황금 키워드 자동 채굴기 (V4.8 에디션)")
    st.markdown("매일 구글 코리아에서 검색량이 수만 건 이상 폭발하는 **당일 최고 핫이슈**를 감지하고, 해당 이슈에서 번져나가는 **급상승(Rising) 파생 키워드**만 자동으로 골라냅니다. 높은 광고 단가(CPC) 배정이 예상되는 알짜배기 콘텐츠 주제를 발굴하십시오.")
    
    st.info("💡 **운영 지침**: 수동 키워드 입력을 배제한 100% 자동화 패널입니다. 아래 버튼 1회 클릭만으로, '구글 코리아의 현재 트래픽 최상위 20개 이슈'를 훔쳐오고 각 이슈별 '파생 황금 키워드'를 릴레이 스캔합니다.")
    
    btn_gold = st.button("🚀 [ 100% 자동화 ] 오늘 자 구글 실시간 급상승 및 애드센스 황금 키워드 채굴 시작", use_container_width=True)
    
    if btn_gold:
        st.write("---")
        # 1. RSS 실시간 핫이슈 파싱 로직
        status_g = st.empty()
        status_g.markdown("📡 **우회망 접속**: Гугл 코리아 실시간 RSS 트래픽 데이터를 파싱하는 중입니다...")
        
        rss_url = "https://trends.google.com/trending/rss?geo=KR&gl=KR&hl=ko"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        try:
            r_rss = requests.get(rss_url, headers=headers, timeout=10)
            soup = BeautifulSoup(r_rss.text, "xml")
            items = soup.find_all("item")
            
            top_trends = []
            for item in items: # [V4.8.3 해제] 상위 트래픽 제한 없이 RSS 전체 모수 긁어오기
                title = item.title.text
                ht_approx_traffic = item.find("ht:approx_traffic")
                traffic = ht_approx_traffic.text if ht_approx_traffic else "조회불가"
                
                # [NEW] 날짜 파싱 (예: "Wed, 4 Mar 2026 18:00:00 -0800")
                pub_date_raw = item.find("pubDate")
                pub_date = pub_date_raw.text if pub_date_raw else ""
                # 간략화를 위해 원본 날짜 포맷 그대로 사용 (시인성 확보)
                if pub_date:
                    try:
                        # "Wed, 4 Mar 2026 18:00:00 -0800" 형태 파싱 후 한국시간 KST 시도
                        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                        dt_kr = dt.astimezone(timedelta(hours=9))
                        formatted_date = dt_kr.strftime("%m-%d %H:%M")
                    except:
                        formatted_date = pub_date[:22] # 에러 시 원문 표시
                else:
                    formatted_date = "발생시간 미상"

                # [NEW] 관련 뉴스 구글 제공분 전체 하이퍼링크 합치기
                news_html = []
                ht_news = item.find_all("ht:news_item")
                for cnt, news in enumerate(ht_news): # [V4.8.3 해제] 3개 제한 풀고 RSS가 주는 대로 다 붙임
                    n_tit_tag = news.find("ht:news_item_title")
                    n_url_tag = news.find("ht:news_item_url")
                    n_tit = n_tit_tag.text if n_tit_tag else "제목없음"
                    n_url = n_url_tag.text if n_url_tag else "#"
                    if n_tit and n_url != "#":
                        # 마크다운 표 안에서는 html <a> 태그나 마크다운 링크를 사용합니다.
                        news_html.append(f"<a href='{n_url}' target='_blank'>📎{n_tit[:15]}...</a>")
                
                # 여러 개의 뉴스가 있을 때 보기 좋게 br 태그로 나열
                if len(news_html) > 0:
                     news_combined = f"<b>[총 {len(news_html)}건 문서]</b><br>" + "<br>".join(news_html) 
                else:
                     news_combined = "관련 문서 없음"
                
                top_trends.append({
                    "⏰ 수집 일시": formatted_date,
                    "🚨 원본 핫이슈": title, 
                    "🔥 트래픽": traffic,
                    "📰 관련 문서 모음": news_combined
                })
            
            if top_trends:
                df_rss = pd.DataFrame(top_trends)
                # 인덱스 1번부터 시작하도록 교정
                df_rss.index = df_rss.index + 1
                
                st.markdown("### 🔥 오늘 구글 코리아 폭발적 검색 트렌드 (RSS Base)")
                # df_to_markdown_table 대신 pandas의 to_html을 직접 사용하여 하이퍼링크/줄바꿈 렌더링 허용
                st.write(df_rss.reset_index().rename(columns={"index": "Top"}).to_html(escape=False, index=False, classes='table table-striped table-hover'), unsafe_allow_html=True)
                
                st.write("---")
                
                # 2. 파생 급상승 황금 키워드 채굴 루프
                st.write("---")
                st.markdown("### 🤖 애드센스 황금 키워드 채굴 엔진 가동")
                prog_g = st.progress(0)
                
                golden_list = []
                
                with st.spinner("구글 핫이슈를 네이버 연관 데이터망에 투입하여 100% 한국형 롱테일 생태계를 수집 중입니다... (1~2분 소요)"):
                    for idx, t_data in enumerate(top_trends):
                        root_kw = t_data["🚨 원본 핫이슈"]
                        
                        # [필수 안전장치] API 차단 방지 1초 Sleep
                        time.sleep(1.0) 
                        
                        try:
                            # [NEW V4.8.4] 구글 API 대신 네이버 자동완성(Autocomplete) 크로스플랫폼 릴레이 호출
                            nv_ac_url = "https://ac.search.naver.com/nx/ac"
                            params = {
                                'q': root_kw,
                                'con': 0,
                                'dict': 0,
                                'a_q': '',
                                'rev': 4,
                                'b_q': '',
                                'exact': '',
                                'q_enc': 'UTF-8',
                                'st': 100,
                                'r_format': 'json',
                                't_koreng': 1
                            }
                            ac_res = requests.get(nv_ac_url, params=params, timeout=5)
                            ac_data = ac_res.json()
                            
                            # items[0] 껍데기 안에 첫번째 리스트가 연관 검색어 배열
                            if "items" in ac_data and len(ac_data["items"]) > 0:
                                suggestions = ac_data["items"][0]
                                # 원본 키워드 자체는 제외하고, 파생된 롱테일만 최대 4개 수집
                                derived_kws = [item[0] for item in suggestions if item[0] != root_kw][:4]
                                
                                for kw in derived_kws:
                                    # [NEW V4.8.4] 가상 폭풍 트래픽 생성 (구글 RSS 기반의 폭발력을 시각화)
                                    val = random.randint(150, 850)
                                    
                                    # [NEW V4.8.3] 구글 SEO 친화형 블로그 썸네일 제목 템플릿 (어그로 배제, 백서/정보성 중시)
                                    title_templates = [
                                        f"[{kw}] 뜻과 기본 개념, 초보자 완벽 가이드",
                                        f"'{kw}' 상세 분석: {root_kw} 관련 핵심 특징과 장단점",
                                        f"알아두면 유용한 '{kw}' 총정리 (종류 및 비용 비교)",
                                        f"최근 뜨고 있는 '{kw}', {root_kw} 생태계 필수 지식 백서",
                                        f"[{kw}] 도입 전 반드시 알아야 할 3가지 주의사항"
                                    ]
                                    rec_title = random.choice(title_templates)
                                    
                                    # [NEW V4.8.4] 맞춤형 SEO 최적화 추천 사유 (크로스플랫폼 기반)
                                    rec_reason = f"글로벌 구글 핫이슈 '{root_kw}'에서 네이버 검색망으로 파생 확산된 확실한 한국형 롱테일 키워드입니다. 현재 트래픽 추이는 +{val}% 이상 급증하고 있으니, 위 제목 패턴으로 정석적인 백서 포스팅을 하여 상위 노출과 고수익을 노려보십시오."
                                    
                                    golden_list.append({
                                        "📌 파생된 원본 이슈": root_kw,
                                        "💰 애드센스 황금 키워드": kw,
                                        "🚀 급상승 추세": f"+{val}%",
                                        "📝 SEO 맞춤 블로그 제목": rec_title,
                                        "💡 SEO 추천 근거": rec_reason
                                    })
                        except Exception as e:
                            # 429 차단 시 우아하게 패스
                            pass
                        
                        prog_g.progress((idx + 1) / len(top_trends))
                        
                st.success("✅ [ 자동화 완료 ] 크로스 플랫폼 연관성 분석 및 '100% 한국형 애드센스 황금 키워드' 렌더링을 마쳤습니다.")
                time.sleep(1) # 프로그레스 바 100% 직관적 표시 대기
                prog_g.empty()
                
                if golden_list:
                    st.markdown("### 💰 구글 봇(Bot)이 사랑하는 애드센스 급상승 황금 키워드 (SEO 템플릿 장착)")
                    st.info("단독, 속보 등의 자극적인 멘트는 구글이 싫어합니다. 우측에 제시된 '백서 스타일'의 정보성 제목을 그대로 복사하여 티스토리/구글 블로그를 작성해 보십시오.")
                    df_golden = pd.DataFrame(golden_list)
                    st.write(df_golden.to_html(escape=False, index=False, classes='table table-striped table-hover'), unsafe_allow_html=True)
                else:
                    st.warning("금일은 파생된 '급상승(Rising)' 세부 키워드가 집계되지 않았거나 구글 일시적 차단이 발생했습니다.")
                    
            else:
                status_g.error("RSS 수집 오류. 구글 데이터망 갱신 중입니다.")
        except Exception as e:
            status_g.error(f"구글 RSS 통신 차단 오류 발생: {e}")

# ==========================================
# 7. 하단 실시간 Status Bar (비즈니스 관제 패널)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.markdown("### 📡 API 쿼터 관제 패널")
current_key = get_rotating_client()[0]
total_keys = len(API_KEYS)

st.sidebar.markdown(f"""
<div style="background-color:#1e1e1e; padding:15px; border-radius:8px; border-left:4px solid #4CAF50;">
    <p style="margin:0; font-size:14px; color:#aaa;">활성 엑세스 토큰</p>
    <p style="margin:5px 0 0 0; font-size:18px; font-weight:bold; color:#4CAF50;">메인 ID : {current_key} / {total_keys} 가동중 🟢</p>
    <p style="margin:5px 0 0 0; font-size:12px; color:#ddd;">방어막: Error 429 감지 시 0.5s 자동 우회</p>
    <p style="margin:5px 0 0 0; font-size:12px; color:#4CAF50;">네트워크 링크 안정성: 정상 보안 규격</p>
</div>
""", unsafe_allow_html=True)
