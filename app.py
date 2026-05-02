"""
app.py — Galaxy VOC Collector
Gemma 3n E2B-it 기반 VOC 수집 및 요구사항명세서 생성
streamlit run app.py
"""

import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ── 경로 설정 ─────────────────────────────────────────────────
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from utils.voc_collector import (
    collect_all, build_stats, get_demo_voc, VOCItem
)

# ── 페이지 설정 ───────────────────────────────────────────────
st.set_page_config(
    page_title="Galaxy VOC Collector",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --samsung: #1428A0;
    --accent:  #00D4C8;
    --neg:     #FF4560;
    --pos:     #00D48A;
    --neu:     #FFB800;
}

html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif !important; }

/* 헤더 배너 */
.hero {
    background: linear-gradient(135deg, #0a0c1a 0%, #1428A0 50%, #0a1a40 100%);
    border-radius: 16px; padding: 28px 32px; margin-bottom: 24px;
    display: flex; align-items: center; justify-content: space-between;
    border: 1px solid rgba(255,255,255,0.1);
}
.hero-title { font-size: 28px; font-weight: 900; color: white; margin: 0; }
.hero-title em { color: #00D4C8; font-style: normal; }
.hero-sub { font-size: 13px; color: rgba(255,255,255,0.6); margin-top: 4px; }
.hero-badge {
    background: rgba(0,212,200,0.15); border: 1px solid rgba(0,212,200,0.4);
    color: #00D4C8; padding: 6px 14px; border-radius: 20px; font-size: 11px;
    font-family: 'JetBrains Mono', monospace;
}

/* 메트릭 카드 */
.metric-row { display: flex; gap: 12px; margin-bottom: 20px; }
.metric-card {
    flex: 1; background: #10121e; border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px; padding: 16px; text-align: center;
}
.metric-val { font-size: 32px; font-weight: 900; font-family: 'JetBrains Mono', monospace; }
.metric-lbl { font-size: 11px; color: #7c85b8; text-transform: uppercase; letter-spacing: .5px; margin-top: 4px; }

/* VOC 아이템 */
.voc-item {
    background: #10121e; border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px; padding: 12px 14px; margin-bottom: 6px;
    display: flex; align-items: flex-start; gap: 12px;
}
.voc-title { font-size: 13px; flex: 1; line-height: 1.5; }
.voc-tags { display: flex; gap: 4px; flex-wrap: wrap; justify-content: flex-end; min-width: 160px; }
.tag {
    padding: 2px 8px; border-radius: 8px; font-size: 10px; font-weight: 600;
}
.t-src  { background: rgba(20,40,160,.3); color: #7090ff; }
.t-cat  { background: rgba(0,212,200,.15); color: #00D4C8; }
.t-neg  { background: rgba(255,69,96,.15); color: #ff7090; }
.t-pos  { background: rgba(0,212,138,.15); color: #00D48A; }
.t-neu  { background: rgba(255,184,0,.15); color: #FFB800; }

/* 이슈 카드 */
.issue-card {
    background: #10121e; border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
    border-left: 4px solid #1428A0;
}
.issue-card.hi  { border-left-color: #FF4560; }
.issue-card.mid { border-left-color: #FFB800; }
.issue-card.lo  { border-left-color: #00D48A; }
.issue-title { font-size: 14px; font-weight: 700; margin-bottom: 5px; }
.issue-desc  { font-size: 12px; color: #7c85b8; line-height: 1.5; margin-bottom: 8px; }

/* 요구사항 */
.req-card {
    background: #10121e; border: 1px solid rgba(255,255,255,.07);
    border-radius: 10px; padding: 13px; margin-bottom: 8px;
}
.req-id    { font-family: monospace; font-size: 10px; color: #7c85b8; background: #181b2e; padding: 2px 7px; border-radius: 5px; }
.req-title { font-weight: 700; font-size: 13px; }

/* SRS 박스 */
.srs-box {
    background: #0d0f1a; border: 1px solid rgba(255,255,255,.07);
    border-radius: 12px; padding: 20px; font-family: 'JetBrains Mono', monospace;
    font-size: 12px; line-height: 1.8; white-space: pre-wrap;
    max-height: 600px; overflow-y: auto;
}

/* 바 차트 */
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.bar-name { font-size: 11px; color: #7c85b8; width: 110px; flex-shrink: 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-track { flex: 1; height: 5px; background: #181b2e; border-radius: 3px; overflow: hidden; }
.bar-fill  { height: 100%; background: linear-gradient(90deg, #1428A0, #00D4C8); border-radius: 3px; }
.bar-val   { font-size: 10px; color: #3d4270; font-family: monospace; width: 24px; text-align: right; }

/* 스텝 배지 */
.step-badge {
    display: inline-flex; align-items: center; gap: 8px;
    background: #1428A0; color: white; border-radius: 20px;
    padding: 4px 12px; font-size: 11px; font-weight: 700;
    margin-bottom: 10px;
}

/* 구분선 */
.divider { border: none; border-top: 1px solid rgba(255,255,255,.07); margin: 20px 0; }

/* Streamlit 기본 UI 커스터마이징 */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-family: 'Noto Sans KR', sans-serif !important;
}
.stProgress > div > div { background: linear-gradient(90deg, #1428A0, #00D4C8) !important; }
div[data-testid="stSidebar"] { background: #0d0f1a !important; }
</style>
""", unsafe_allow_html=True)

# ── 세션 상태 초기화 ──────────────────────────────────────────
for key, default in [
    ("voc_list",   []),
    ("stats",      None),
    ("analysis",   None),
    ("srs_text",   ""),
    ("model_loaded", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── 헬퍼 ─────────────────────────────────────────────────────

def snt_label(s): return {"negative": "불만", "positive": "긍정", "neutral": "중립"}.get(s, s)
def snt_cls(s):   return {"negative": "t-neg", "positive": "t-pos", "neutral": "t-neu"}.get(s, "t-neu")
def src_short(s):
    m = {"삼성 Members 커뮤니티": "Samsung", "네이버 지식인": "N.지식인",
         "네이버 카페": "N.카페", "클리앙": "Clien",
         "DC인사이드 갤럭시S24": "DC.S24", "DC인사이드 삼성갤럭시": "DC.Galaxy"}
    return m.get(s, s[:10])

def impact_cls(v): return {"높음": "hi", "중간": "mid", "낮음": "lo"}.get(v, "")
def priority_color(p):
    return {"필수": "#FF4560", "권장": "#FFB800", "선택": "#00D48A"}.get(p, "#7c85b8")

def render_voc_list(items):
    if not items:
        st.info("수집된 VOC가 없습니다.")
        return
    html = ""
    for v in items[:100]:
        cat  = v.category  if hasattr(v, "category")  else v.get("category", "")
        snt  = v.sentiment if hasattr(v, "sentiment") else v.get("sentiment", "neutral")
        src  = v.source    if hasattr(v, "source")    else v.get("source", "")
        ttl  = v.title     if hasattr(v, "title")     else v.get("title", "")
        html += f"""<div class="voc-item">
            <div class="voc-title">{ttl}</div>
            <div class="voc-tags">
                <span class="tag t-src">{src_short(src)}</span>
                <span class="tag t-cat">{cat}</span>
                <span class="tag {snt_cls(snt)}">{snt_label(snt)}</span>
            </div>
        </div>"""
    st.markdown(html, unsafe_allow_html=True)

def render_stats(stats):
    if not stats:
        return
    total = stats["total"]
    neg   = stats["by_sentiment"].get("negative", 0)
    pos   = stats["by_sentiment"].get("positive", 0)

    st.markdown(f"""
    <div class="metric-row">
        <div class="metric-card">
            <div class="metric-val" style="color:white">{total}</div>
            <div class="metric-lbl">총 수집 VOC</div>
        </div>
        <div class="metric-card">
            <div class="metric-val" style="color:#FF4560">{round(neg/total*100)}%</div>
            <div class="metric-lbl">부정 의견</div>
        </div>
        <div class="metric-card">
            <div class="metric-val" style="color:#00D48A">{round(pos/total*100)}%</div>
            <div class="metric-lbl">긍정 의견</div>
        </div>
        <div class="metric-card">
            <div class="metric-val" style="color:#00D4C8">{len(stats['by_source'])}</div>
            <div class="metric-lbl">수집 채널</div>
        </div>
    </div>""", unsafe_allow_html=True)

    cat_data = stats["by_category"]
    if cat_data:
        max_v = max(cat_data.values(), default=1)
        rows  = "".join(
            f'<div class="bar-row">'
            f'<span class="bar-name" title="{k}">{k}</span>'
            f'<div class="bar-track"><div class="bar-fill" style="width:{round(v/max_v*100)}%"></div></div>'
            f'<span class="bar-val">{v}</span></div>'
            for k, v in cat_data.items()
        )
        st.markdown(f"**카테고리별 분포**")
        st.markdown(rows, unsafe_allow_html=True)


# ── 사이드바 ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📱 Galaxy VOC")
    st.markdown("---")

    # ── STEP 1: 모델 설정 ─────────────────────────────────────
    st.markdown('<div class="step-badge">STEP 1 — 모델 설정</div>', unsafe_allow_html=True)

    hf_token = st.text_input(
        "HuggingFace 토큰",
        value=os.getenv("HF_TOKEN", ""),
        type="password",
        help="https://huggingface.co/settings/tokens",
        placeholder="hf_...",
    )

    use_4bit = st.checkbox("4bit 양자화 (VRAM 절약)", value=True,
                           help="T4 GPU(무료 Colab)에서 동작하려면 체크")
    use_gpu  = st.checkbox("GPU 사용", value=True,
                           help="체크 해제 시 CPU 모드 (매우 느림)")

    if st.button("🤖 Gemma 3n 모델 로드", use_container_width=True, type="primary"):
        if not hf_token:
            st.error("HuggingFace 토큰을 입력하세요.")
        else:
            with st.spinner("모델 로딩 중… (최초 실행 시 ~6GB 다운로드)"):
                try:
                    from models.gemma_engine import engine
                    progress_log = st.empty()
                    def cb(msg): progress_log.info(msg)
                    engine.load(hf_token=hf_token, use_4bit=use_4bit, use_gpu=use_gpu, progress_cb=cb)
                    st.session_state["model_loaded"] = True
                    st.success("✅ 모델 로드 완료!")
                except Exception as e:
                    st.error(f"모델 로드 실패: {e}")

    if st.session_state["model_loaded"]:
        st.success("✅ Gemma 3n E2B-it 로드됨")
    else:
        st.warning("⚠️ 모델 미로드")

    st.markdown("---")

    # ── STEP 2: VOC 수집 ──────────────────────────────────────
    st.markdown('<div class="step-badge">STEP 2 — VOC 수집</div>', unsafe_allow_html=True)

    keyword = st.text_input("검색 키워드", value="갤럭시", placeholder="예: 갤럭시, S25, 폴드")

    sources = st.multiselect(
        "수집 채널",
        options=["samsung", "naver_kin", "naver_cafe", "dcinside", "clien"],
        default=["samsung", "naver_kin", "naver_cafe", "dcinside", "clien"],
        format_func=lambda x: {
            "samsung":    "삼성 Members",
            "naver_kin":  "네이버 지식인",
            "naver_cafe": "네이버 카페",
            "dcinside":   "DC인사이드",
            "clien":      "클리앙",
        }.get(x, x),
    )

    max_per = st.slider("소스당 최대 건수", 10, 50, 25)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗂 데모", use_container_width=True):
            st.session_state["voc_list"] = get_demo_voc()
            st.session_state["stats"]    = build_stats(st.session_state["voc_list"])
            st.session_state["analysis"] = None
            st.session_state["srs_text"] = ""
            st.success(f"데모 {len(st.session_state['voc_list'])}건 로드")
            st.rerun()

    with col2:
        collect_btn = st.button("🔍 수집", use_container_width=True, type="primary")

    if collect_btn:
        if not sources:
            st.error("채널을 선택하세요.")
        else:
            prog_bar = st.progress(0, text="수집 준비 중…")
            log_area = st.empty()

            def on_progress(step, total, name, status):
                prog_bar.progress(step / total, text=f"[{step}/{total}] {name}: {status}")
                log_area.info(f"🔄 {name} — {status}")

            with st.spinner("VOC 수집 중…"):
                result = collect_all(keyword, sources, max_per, on_progress)

            st.session_state["voc_list"] = result
            st.session_state["stats"]    = build_stats(result)
            st.session_state["analysis"] = None
            st.session_state["srs_text"] = ""
            prog_bar.progress(1.0, text=f"✅ 수집 완료: {len(result)}건")
            st.rerun()

    st.markdown("---")

    # ── STEP 3: AI 분석 ───────────────────────────────────────
    st.markdown('<div class="step-badge">STEP 3 — AI 분석</div>', unsafe_allow_html=True)

    model_info = st.text_input("대상 제품", value="갤럭시 S25 시리즈")

    analyze_btn = st.button(
        "🤖 Gemma AI 분석",
        use_container_width=True,
        type="primary",
        disabled=not (st.session_state["voc_list"] and st.session_state["model_loaded"]),
    )

    if analyze_btn:
        with st.spinner("Gemma 3n이 VOC를 분석 중… (1-3분)"):
            try:
                from models.gemma_engine import analyze_voc
                result = analyze_voc(st.session_state["voc_list"], model_info)
                st.session_state["analysis"] = result
                st.success("✅ 분석 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"분석 오류: {e}")

    if not st.session_state["model_loaded"] and st.session_state["voc_list"]:
        st.caption("⚠️ 모델을 먼저 로드하세요.")

    st.markdown("---")

    # ── STEP 4: 명세서 ────────────────────────────────────────
    st.markdown('<div class="step-badge">STEP 4 — 명세서 생성</div>', unsafe_allow_html=True)

    product_name = st.text_input("제품명",   value="삼성 갤럭시")
    doc_version  = st.text_input("버전",     value="1.0")
    doc_author   = st.text_input("작성자",   value="제품기획팀")

    srs_btn = st.button(
        "📝 SRS 명세서 생성",
        use_container_width=True,
        type="primary",
        disabled=not (st.session_state["voc_list"] and
                      st.session_state["analysis"] and
                      st.session_state["model_loaded"]),
    )

    if srs_btn:
        from models.gemma_engine import engine, build_srs_prompt
        prompt = build_srs_prompt(
            st.session_state["voc_list"],
            st.session_state["analysis"],
            product_name, doc_version, doc_author,
        )
        srs_placeholder = st.empty()
        full_text = ""
        with st.spinner("SRS 명세서 생성 중… (3-5분)"):
            try:
                for chunk in engine.generate_stream(prompt, max_new_tokens=4000):
                    full_text += chunk
                    srs_placeholder.text(full_text[-500:] + "▌")
                st.session_state["srs_text"] = full_text
                srs_placeholder.empty()
                st.success("✅ 명세서 생성 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"생성 오류: {e}")

    st.markdown("---")

    # ── 내보내기 ──────────────────────────────────────────────
    st.markdown("**📥 내보내기**")

    if st.session_state["voc_list"]:
        # DOCX
        if st.button("📄 DOCX 다운로드", use_container_width=True,
                     disabled=not st.session_state["voc_list"]):
            try:
                from utils.doc_generator import generate_docx
                filepath = generate_docx(
                    st.session_state["voc_list"],
                    st.session_state["analysis"] or {},
                    st.session_state["srs_text"],
                    product_name, doc_version, doc_author,
                    output_dir="./output",
                )
                with open(filepath, "rb") as f:
                    st.download_button(
                        "⬇️ 파일 받기", f.read(),
                        file_name=Path(filepath).name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
            except Exception as e:
                st.error(f"DOCX 오류: {e}")

        # JSON
        json_data = json.dumps(
            {
                "metadata": {"product": product_name, "version": doc_version, "author": doc_author,
                             "model": "google/gemma-3n-E2B-it", "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                             "total_voc": len(st.session_state["voc_list"])},
                "voc_list":  [v.to_dict() if hasattr(v, "to_dict") else v for v in st.session_state["voc_list"]],
                "analysis":  st.session_state["analysis"],
            },
            ensure_ascii=False, indent=2,
        )
        st.download_button(
            "💾 JSON 다운로드",
            json_data.encode("utf-8"),
            file_name=f"galaxy_voc_{time.strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True,
        )


# ── 메인 영역 ─────────────────────────────────────────────────

# 히어로 배너
st.markdown("""
<div class="hero">
    <div>
        <div class="hero-title">GALAXY <em>VOC</em> COLLECTOR</div>
        <div class="hero-sub">Gemma 3n E2B-it · 완전 로컬 동작 · VOC 수집 → AI 분석 → SRS 자동 생성</div>
    </div>
    <div class="hero-badge">google/gemma-3n-E2B-it</div>
</div>
""", unsafe_allow_html=True)

# 탭
tab1, tab2, tab3, tab4 = st.tabs(["📥 수집 현황", "📊 통계 분석", "🤖 AI 분석 결과", "📋 요구사항명세서"])

# ── 탭 1: 수집 ────────────────────────────────────────────────
with tab1:
    voc_list = st.session_state["voc_list"]
    st.markdown(f"#### 수집된 VOC **{len(voc_list)}건**")

    if st.session_state["stats"]:
        render_stats(st.session_state["stats"])
        st.markdown('<hr class="divider">', unsafe_allow_html=True)

    render_voc_list(voc_list)

    if len(voc_list) > 100:
        st.caption(f"처음 100건만 표시 (전체 {len(voc_list)}건)")

# ── 탭 2: 통계 ────────────────────────────────────────────────
with tab2:
    stats = st.session_state["stats"]
    if not stats:
        st.info("VOC를 수집하면 통계가 표시됩니다.")
    else:
        render_stats(stats)

        st.markdown("---")
        st.markdown("**채널별 수집 현황**")
        src_data = stats["by_source"]
        if src_data:
            max_v = max(src_data.values(), default=1)
            rows  = "".join(
                f'<div class="bar-row">'
                f'<span class="bar-name" title="{k}">{k}</span>'
                f'<div class="bar-track"><div class="bar-fill" style="width:{round(v/max_v*100)}%"></div></div>'
                f'<span class="bar-val">{v}</span></div>'
                for k, v in src_data.items()
            )
            st.markdown(rows, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**감성 분석**")
        snt = stats["by_sentiment"]
        total = stats["total"]
        st.markdown(f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-val" style="color:#FF4560">{snt.get('negative',0)}</div>
                <div class="metric-lbl">부정 ({round(snt.get('negative',0)/total*100)}%)</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#00D48A">{snt.get('positive',0)}</div>
                <div class="metric-lbl">긍정 ({round(snt.get('positive',0)/total*100)}%)</div>
            </div>
            <div class="metric-card">
                <div class="metric-val" style="color:#FFB800">{snt.get('neutral',0)}</div>
                <div class="metric-lbl">중립 ({round(snt.get('neutral',0)/total*100)}%)</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── 탭 3: AI 분석 결과 ────────────────────────────────────────
with tab3:
    analysis = st.session_state["analysis"]
    if not analysis:
        st.info("좌측 사이드바에서 Gemma AI 분석을 실행하세요.")
    else:
        # 요약
        if analysis.get("executive_summary"):
            st.markdown("#### 📋 종합 요약")
            st.info(analysis["executive_summary"])

        # 인사이트
        if analysis.get("key_insights"):
            st.markdown("#### 💡 핵심 인사이트")
            for i, ins in enumerate(analysis["key_insights"], 1):
                st.markdown(f"**{i}.** {ins}")

        st.markdown("---")

        # 핵심 이슈
        if analysis.get("critical_issues"):
            st.markdown(f"#### 🚨 핵심 이슈 ({len(analysis['critical_issues'])}개)")
            for iss in analysis["critical_issues"]:
                cls = impact_cls(iss.get("impact", ""))
                st.markdown(f"""
                <div class="issue-card {cls}">
                    <div class="issue-title">{iss.get('title','')}</div>
                    <div class="issue-desc">{iss.get('description','')}</div>
                    <span class="tag t-cat">{iss.get('category','')}</span>&nbsp;
                    <span class="tag t-{'neg' if iss.get('impact')=='높음' else 'neu' if iss.get('impact')=='중간' else 'pos'}">
                        영향: {iss.get('impact','')}
                    </span>&nbsp;
                    <span class="tag t-{'neg' if iss.get('frequency')=='높음' else 'neu'}">
                        빈도: {iss.get('frequency','')}
                    </span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # 요구사항
        if analysis.get("requirements"):
            st.markdown(f"#### 📌 도출된 요구사항 ({len(analysis['requirements'])}개)")
            for req in analysis["requirements"]:
                pri   = req.get("priority", "?")
                color = priority_color(pri)
                with st.expander(f"[{req.get('id','?')}] {req.get('title','?')}  ·  {pri}", expanded=False):
                    st.markdown(f"**설명:** {req.get('description','')}")
                    st.markdown(f"*{req.get('user_story','')}*")
                    if req.get("acceptance_criteria"):
                        st.markdown("**검증 기준:**")
                        for c in req["acceptance_criteria"]:
                            st.markdown(f"• {c}")

        st.markdown("---")

        # 로드맵
        if analysis.get("roadmap"):
            st.markdown("#### 🗺️ 개선 로드맵")
            cols = st.columns(len(analysis["roadmap"]))
            for col, phase in zip(cols, analysis["roadmap"]):
                with col:
                    st.markdown(f"**{phase.get('phase','')}**")
                    for item in phase.get("items", []):
                        st.markdown(f"• {item}")

# ── 탭 4: SRS ─────────────────────────────────────────────────
with tab4:
    srs = st.session_state["srs_text"]
    if not srs:
        st.info("좌측 사이드바에서 SRS 명세서 생성을 실행하세요.")
    else:
        col_a, col_b = st.columns([6, 1])
        with col_a:
            st.markdown(f"#### 📋 요구사항명세서 ({len(srs):,}자)")
        with col_b:
            st.download_button(
                "📋 MD",
                srs.encode("utf-8"),
                file_name=f"srs_{time.strftime('%Y%m%d')}.md",
                mime="text/markdown",
            )
        st.markdown(f'<div class="srs-box">{srs}</div>', unsafe_allow_html=True)
