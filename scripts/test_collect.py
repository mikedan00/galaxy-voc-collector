"""
scripts/test_collect.py
VOC 수집 모듈 단독 테스트 (모델 없이 실행 가능)
python scripts/test_collect.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.voc_collector import (
    collect_all, get_demo_voc, build_stats,
    collect_naver_kin, collect_naver_cafe,
    collect_dcinside, collect_clien,
)

def print_section(title: str) -> None:
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)

def test_demo():
    print_section("데모 데이터 테스트")
    items = get_demo_voc()
    stats = build_stats(items)
    print(f"총 {len(items)}건 로드")
    print(f"카테고리 수: {len(stats['by_category'])}")
    print(f"부정 비율: {stats['neg_pct']}%")
    print("\n[카테고리별]")
    for cat, cnt in stats['by_category'].items():
        bar = '█' * int(cnt / max(stats['by_category'].values()) * 20)
        print(f"  {cat:<16} {bar:<20} {cnt:>3}건")
    return items

def test_live_collect(keyword: str = "갤럭시"):
    print_section(f"실제 크롤링 테스트: '{keyword}'")

    tasks = [
        ("네이버 지식인",  lambda: collect_naver_kin(f"갤럭시 {keyword} 불편", 5)),
        ("네이버 카페",    lambda: collect_naver_cafe(f"갤럭시 {keyword} 문제", 5)),
        ("DC인사이드",     lambda: collect_dcinside("galaxys24", "갤럭시S24", 5)),
        ("클리앙",         lambda: collect_clien(keyword, 5)),
    ]

    all_items = []
    for name, fn in tasks:
        print(f"\n  📡 {name} 수집 중…", end="", flush=True)
        try:
            items = fn()
            all_items.extend(items)
            print(f" → {len(items)}건")
            for it in items[:3]:
                print(f"     · {it.title[:55]}")
        except Exception as e:
            print(f" ✗ 오류: {e}")

    print(f"\n총 수집: {len(all_items)}건")
    return all_items

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="실제 크롤링 실행")
    parser.add_argument("--keyword", default="갤럭시", help="검색 키워드")
    args = parser.parse_args()

    # 항상 데모 테스트
    demo_items = test_demo()

    if args.live:
        live_items = test_live_collect(args.keyword)
    else:
        print("\n💡 실제 크롤링: python scripts/test_collect.py --live")

    print("\n✅ 테스트 완료!")
