"""
voc_collector.py
삼성 멤버스·네이버·DC인사이드·클리앙에서 갤럭시 VOC를 수집합니다.
"""

import time
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable
from collections import Counter

import requests
from bs4 import BeautifulSoup

# ── 공통 설정 ────────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
DELAY_SEC   = 1.2
TIMEOUT_SEC = 10

# ── 카테고리 분류 ─────────────────────────────────────────────
CATEGORY_KW: dict[str, list[str]] = {
    "배터리/전원":     ["배터리","방전","충전","전원","전력","충전기"],
    "카메라":          ["카메라","사진","촬영","렌즈","야간","줌","셀카","화질","동영상"],
    "성능/속도":       ["렉","버벅","느림","속도","성능","발열","과열","프리징","강제종료"],
    "디스플레이":      ["화면","디스플레이","잔상","번인","밝기","색상","터치","액정"],
    "통신/네트워크":   ["와이파이","wifi","블루투스","5g","lte","통화","데이터","신호","gps"],
    "UI/소프트웨어":   ["원ui","oneui","업데이트","앱","설정","버그","오류","팝업","광고","알림","빅스비"],
    "디자인/하드웨어": ["디자인","무게","두께","그립","케이스","버튼","외관"],
    "음향":            ["스피커","마이크","음질","이어폰","볼륨","소리"],
    "보안/생체인식":   ["지문","얼굴인식","생체","비밀번호","보안","잠금","인식"],
    "AS/품질":         ["as","수리","불량","파손","방수","품질","내구성","고장"],
}

NEG_W = ["불편","문제","오류","버그","느림","렉","버벅","안됨","이상","고장",
         "실망","불만","최악","짜증","끊김","느려","불량","파손"]
POS_W = ["좋음","만족","개선","좋아","빠름","완벽","최고","추천","편리","깔끔"]


@dataclass
class VOCItem:
    source:       str
    title:        str
    content:      str
    url:          str          = ""
    category:     str          = "기타"
    sentiment:    str          = "neutral"
    collected_at: str          = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "source": self.source, "title": self.title,
            "content": self.content, "url": self.url,
            "category": self.category, "sentiment": self.sentiment,
            "collected_at": self.collected_at,
        }


def classify_category(text: str) -> str:
    t = text.lower()
    for cat, kws in CATEGORY_KW.items():
        if any(k in t for k in kws):
            return cat
    return "기타"


def classify_sentiment(text: str) -> str:
    t = text.lower()
    neg = sum(1 for w in NEG_W if w in t)
    pos = sum(1 for w in POS_W if w in t)
    return "negative" if neg > pos else ("positive" if pos > neg else "neutral")


def safe_get(url: str, extra: dict = None) -> Optional[BeautifulSoup]:
    try:
        r = requests.get(url, headers={**HEADERS, **(extra or {})}, timeout=TIMEOUT_SEC)
        if r.status_code == 200:
            r.encoding = r.apparent_encoding or "utf-8"
            return BeautifulSoup(r.text, "lxml")
    except Exception:
        pass
    return None


def _make(source: str, title: str, content: str, url: str) -> VOCItem:
    merged = f"{title} {content}"
    return VOCItem(
        source=source, title=title.strip(),
        content=(content or title).strip()[:300], url=url,
        category=classify_category(merged),
        sentiment=classify_sentiment(merged),
    )


# ── 수집 함수 ─────────────────────────────────────────────────

def collect_naver_kin(keyword: str, max_items: int = 25) -> List[VOCItem]:
    results: List[VOCItem] = []
    url = f"https://kin.naver.com/search/list.naver?query={requests.utils.quote(keyword)}"
    soup = safe_get(url, {"Referer": "https://kin.naver.com"})
    if not soup:
        return results
    for li in soup.select("ul.basic1 li")[:max_items]:
        a     = li.select_one("dt a, .title a")
        if not a:
            continue
        title = a.get_text(strip=True)
        desc  = (li.select_one("dd") or li).get_text(" ", strip=True)
        href  = a.get("href", "")
        if len(title) < 6:
            continue
        link = href if href.startswith("http") else f"https://kin.naver.com{href}"
        results.append(_make("네이버 지식인", title, desc[:200], link))
    return results


def collect_naver_cafe(keyword: str, max_items: int = 25) -> List[VOCItem]:
    results: List[VOCItem] = []
    url = (f"https://search.naver.com/search.naver?where=article"
           f"&query={requests.utils.quote(keyword)}&nso=so%3Ar%2Cp%3A1w")
    soup = safe_get(url)
    if not soup:
        return results
    for item in soup.select(".cafe_item, li.bx, .api_ani_send")[:max_items]:
        a     = item.select_one("a.title, .api_txt_lines, strong a")
        if not a:
            continue
        title = a.get_text(strip=True)
        desc  = (item.select_one(".dsc_txt, .desc") or item).get_text(" ", strip=True)
        href  = a.get("href", "")
        if len(title) < 6:
            continue
        results.append(_make("네이버 카페", title, desc[:200], href))
    return results


def collect_dcinside(gallery_id: str, gallery_name: str, max_items: int = 20) -> List[VOCItem]:
    results: List[VOCItem] = []
    url  = f"https://gall.dcinside.com/board/lists/?id={gallery_id}&page=1"
    soup = safe_get(url)
    if not soup:
        return results
    for tr in soup.select("tr.ub-content")[:max_items]:
        a     = tr.select_one(".gall_tit a")
        if not a:
            continue
        title = a.get_text(strip=True)
        href  = a.get("href", "")
        if len(title) < 4 or "[공지]" in title:
            continue
        link = href if href.startswith("http") else f"https://gall.dcinside.com{href}"
        results.append(_make(f"DC인사이드 {gallery_name}", title, title, link))
    return results


def collect_clien(keyword: str, max_items: int = 20) -> List[VOCItem]:
    results: List[VOCItem] = []
    url  = f"https://www.clien.net/service/search?q={requests.utils.quote(keyword)}&sort=recency&page=0"
    soup = safe_get(url)
    if not soup:
        return results
    for item in soup.select(".list_item, .symph-row")[:max_items]:
        a     = item.select_one(".list_subject, a.list_subject")
        if not a:
            continue
        title = a.get_text(strip=True)
        href  = a.get("href", "")
        if len(title) < 6:
            continue
        link = href if href.startswith("http") else f"https://www.clien.net{href}"
        results.append(_make("클리앙", title, title, link))
    return results


def collect_samsung_members(keyword: str, max_items: int = 25) -> List[VOCItem]:
    results: List[VOCItem] = []
    url  = (f"https://r1.community.samsung.com/t5/forums/searchpage/tab/message"
            f"?q={requests.utils.quote(keyword)}&include_archived=false")
    soup = safe_get(url)
    if not soup:
        return results
    for el in soup.select(".lia-message-subject a, .MessageSubject a, h3 a")[:max_items]:
        title = el.get_text(strip=True)
        href  = el.get("href", "")
        if len(title) < 6:
            continue
        link = href if href.startswith("http") else f"https://r1.community.samsung.com{href}"
        results.append(_make("삼성 Members 커뮤니티", title, title, link))
    return results


# ── 통합 수집 ─────────────────────────────────────────────────

def collect_all(
    keyword:        str,
    sources:        List[str],
    max_per_source: int = 25,
    on_progress:    Optional[Callable] = None,
) -> List[VOCItem]:
    """모든 선택된 소스에서 VOC 수집"""

    tasks = []
    if "samsung"    in sources: tasks.append(("삼성 Members 커뮤니티",  lambda: collect_samsung_members(keyword, max_per_source)))
    if "naver_kin"  in sources: tasks.append(("네이버 지식인",           lambda: collect_naver_kin(f"갤럭시 {keyword} 불편", max_per_source)))
    if "naver_cafe" in sources: tasks.append(("네이버 카페",             lambda: collect_naver_cafe(f"갤럭시 {keyword} 문제", max_per_source)))
    if "dcinside"   in sources:
        tasks.append(("DC인사이드 갤럭시S24",    lambda: collect_dcinside("galaxys24",      "갤럭시S24",    max_per_source)))
        tasks.append(("DC인사이드 삼성갤럭시",   lambda: collect_dcinside("samsunggalaxy",  "삼성갤럭시",   max_per_source)))
    if "clien"      in sources: tasks.append(("클리앙",                  lambda: collect_clien(keyword, max_per_source)))

    all_items: List[VOCItem] = []
    for i, (name, fn) in enumerate(tasks):
        if on_progress:
            on_progress(i + 1, len(tasks), name, "수집 중")
        try:
            items = fn()
            all_items.extend(items)
            if on_progress:
                on_progress(i + 1, len(tasks), name, f"완료 ({len(items)}건)")
        except Exception as e:
            if on_progress:
                on_progress(i + 1, len(tasks), name, f"오류: {e}")
        if i < len(tasks) - 1:
            time.sleep(DELAY_SEC)

    return deduplicate(all_items)


def deduplicate(items: List[VOCItem]) -> List[VOCItem]:
    seen, out = set(), []
    for it in items:
        key = re.sub(r"\s+", "", it.title[:20].lower())
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def build_stats(items: List[VOCItem]) -> dict:
    by_cat = Counter(v.category  for v in items)
    by_src = Counter(v.source    for v in items)
    by_snt = Counter(v.sentiment for v in items)
    return {
        "total":      len(items),
        "by_category": dict(by_cat.most_common()),
        "by_source":   dict(by_src.most_common()),
        "by_sentiment": dict(by_snt),
        "neg_pct":    round(by_snt["negative"] / len(items) * 100) if items else 0,
        "pos_pct":    round(by_snt["positive"] / len(items) * 100) if items else 0,
    }


# ── 데모 데이터 ───────────────────────────────────────────────
DEMO_RAW = [
    ("삼성 Members 커뮤니티", "배터리/전원",    "갤럭시 S25 배터리 소모가 너무 심합니다"),
    ("네이버 지식인",          "배터리/전원",    "충전 속도가 이전 모델보다 많이 느려졌어요"),
    ("네이버 카페",            "배터리/전원",    "게임할 때 배터리 소모가 너무 빨라요"),
    ("DC인사이드 갤럭시S24",   "배터리/전원",    "원UI 업데이트 후 배터리가 더 빨리 닳는 현상"),
    ("클리앙",                 "배터리/전원",    "보조배터리 없으면 하루 못버팀"),
    ("삼성 Members 커뮤니티", "카메라",         "야간 카메라 사진이 흐릿하게 나옵니다"),
    ("네이버 지식인",          "카메라",         "줌 배율이 올라갈수록 화질이 너무 떨어져요"),
    ("네이버 카페",            "카메라",         "셀피 찍을 때 피부 보정이 너무 과해요"),
    ("DC인사이드 갤럭시S24",   "카메라",         "카메라 업데이트 후 색감이 이상해짐"),
    ("클리앙",                 "카메라",         "카메라 앱 실행 속도가 느립니다"),
    ("삼성 Members 커뮤니티", "성능/속도",      "멀티태스킹 중 앱이 자꾸 종료됩니다"),
    ("네이버 지식인",          "성능/속도",      "게임하면 발열이 너무 심해요"),
    ("네이버 카페",            "성능/속도",      "고사양 게임할 때 프레임 드랍이 심함"),
    ("DC인사이드 갤럭시S24",   "성능/속도",      "업데이트 후 앱 실행 속도가 느려진 것 같아요"),
    ("삼성 Members 커뮤니티", "디스플레이",     "화면 잔상이 오래 남습니다"),
    ("네이버 지식인",          "디스플레이",     "화면 밝기가 자동으로 너무 어두워져요"),
    ("네이버 카페",            "디스플레이",     "야외에서 화면이 잘 안보임"),
    ("클리앙",                 "디스플레이",     "화면 색상이 이전 기기보다 누런 것 같아요"),
    ("삼성 Members 커뮤니티", "통신/네트워크",  "와이파이 연결이 자꾸 끊깁니다"),
    ("네이버 지식인",          "통신/네트워크",  "5G 잡았다가 LTE로 자꾸 내려가는 현상"),
    ("DC인사이드 갤럭시S24",   "통신/네트워크",  "블루투스 이어폰이 자꾸 끊겨요"),
    ("클리앙",                 "통신/네트워크",  "GPS 실내에서 너무 부정확해요"),
    ("삼성 Members 커뮤니티", "UI/소프트웨어",  "원UI 업데이트 후 자꾸 팝업 광고가 떠요"),
    ("네이버 지식인",          "UI/소프트웨어",  "빅스비가 실수로 자꾸 켜집니다"),
    ("네이버 카페",            "UI/소프트웨어",  "기본 앱 삭제가 안됩니다"),
    ("DC인사이드 갤럭시S24",   "UI/소프트웨어",  "앱 알림이 제대로 안 오는 현상"),
    ("삼성 Members 커뮤니티", "보안/생체인식",  "지문인식 인식률이 확실히 떨어졌어요"),
    ("네이버 지식인",          "보안/생체인식",  "얼굴인식이 어두운 곳에서 작동을 안 해요"),
    ("클리앙",                 "보안/생체인식",  "지문인식 인식이 너무 느림"),
    ("삼성 Members 커뮤니티", "디자인/하드웨어","폰이 너무 무거워서 손목이 아파요"),
    ("네이버 카페",            "디자인/하드웨어","케이스 끼면 너무 두꺼워짐"),
    ("클리앙",                 "음향",           "스피커 볼륨이 이전 기기보다 작아요"),
    ("삼성 Members 커뮤니티", "AS/품질",        "AS 비용이 너무 비쌉니다"),
    ("네이버 지식인",          "AS/품질",        "방수 성능이 광고보다 낮은 것 같아요"),
    ("클리앙",                 "카메라",         "사진 AI 지우개 기능이 정말 편리해요"),
    ("삼성 Members 커뮤니티", "배터리/전원",    "배터리 최적화 업데이트 후 확실히 좋아짐"),
    ("네이버 카페",            "성능/속도",      "원UI 7 업데이트 후 확실히 빨라진 것 같아요"),
    ("DC인사이드 갤럭시S24",   "카메라",         "야간 촬영 AI 개선이 정말 마음에 들어요"),
]


def get_demo_voc() -> List[VOCItem]:
    return [
        VOCItem(
            source=src, title=title, content=title, url="#",
            category=cat, sentiment=classify_sentiment(title),
        )
        for src, cat, title in DEMO_RAW
    ]
