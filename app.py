import streamlit as st
import json
import re
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Auto-install node_modules on Streamlit Cloud
from setup import ensure_node_modules
ensure_node_modules()

from youtube_search import fetch_transcripts_from_urls, fetch_transcripts_from_search
from ai_generator import generate_slides
from image_fetcher import get_slide_image
from pptx_builder import build_pptx

NODE_MODULES = os.path.join(os.path.dirname(__file__), "node_modules")

# ── Load secrets (Streamlit Cloud) ───────────────────────────────────────────
def get_secret(key: str, fallback_env: str = "") -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(fallback_env or key, "")

GROQ_KEY     = get_secret("GROQ_API_KEY")
YT_KEY       = get_secret("YOUTUBE_API_KEY")
PEXELS_KEY   = get_secret("PEXELS_API_KEY")
PIXABAY_KEY  = get_secret("PIXABAY_API_KEY", "PIXABAY_API_KEY")
SUPADATA_KEY = get_secret("SUPADATA_API_KEY")
GROQ_MODEL   = get_secret("GROQ_MODEL") or "llama-3.3-70b-versatile"

KEYS_OK = bool(GROQ_KEY)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="YT → Slides",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
*, html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #0a0f1e 0%, #0f172a 45%, #1a1040 100%) !important;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] label { color: #94a3b8 !important; font-size: 0.8rem !important; font-weight: 500 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #0f172a !important; border-color: #334155 !important; border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-baseweb="slider"] { accent-color: #6366f1; }

/* ── Main ── */
.main .block-container { padding-top: 1.4rem; max-width: 1180px; }

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 45%, #db2777 100%);
    border-radius: 20px; padding: 2.4rem 2.8rem; margin-bottom: 2rem;
    color: white; position: relative; overflow: hidden;
    box-shadow: 0 20px 60px rgba(79,70,229,0.4);
}
.hero::before {
    content:''; position:absolute; top:-40%; right:-8%; width:420px; height:420px;
    background:rgba(255,255,255,0.06); border-radius:50%;
}
.hero::after {
    content:''; position:absolute; bottom:-55%; left:-4%; width:320px; height:320px;
    background:rgba(255,255,255,0.04); border-radius:50%;
}
.hero h1 { font-size:2.1rem; font-weight:800; margin:0; letter-spacing:-0.5px; position:relative; }
.hero p  { font-size:1rem; opacity:0.88; margin:0.4rem 0 0; position:relative; }
.hero-pills { display:flex; gap:0.5rem; margin-top:1.1rem; flex-wrap:wrap; position:relative; }
.hero-pill {
    background:rgba(255,255,255,0.15); border:1px solid rgba(255,255,255,0.22);
    border-radius:20px; padding:3px 14px; font-size:0.75rem; font-weight:500;
}

/* ── Mode selector ── */
.mode-row { display:flex; gap:0.8rem; margin-bottom:1.4rem; }
.mode-btn {
    flex:1; border:2px solid #e2e8f0; border-radius:12px; padding:0.9rem 1rem;
    background:white; cursor:pointer; transition:all 0.18s; text-align:center;
}
.mode-btn.active { border-color:#6366f1; background:#eef2ff; }
.mode-btn:hover  { border-color:#a5b4fc; }
.mode-btn-icon   { font-size:1.5rem; display:block; margin-bottom:0.3rem; }
.mode-btn-label  { font-size:0.8rem; font-weight:600; color:#374151; }
.mode-btn-desc   { font-size:0.7rem; color:#6b7280; margin-top:2px; }

/* ── Input cards ── */
.input-card {
    background:white; border:1.5px solid #e2e8f0; border-radius:14px;
    padding:1.3rem 1.4rem; margin-bottom:1rem;
    box-shadow:0 2px 10px rgba(0,0,0,0.04);
}
.input-label {
    display:flex; align-items:center; gap:0.5rem;
    font-weight:600; color:#1e293b; font-size:0.9rem; margin-bottom:0.7rem;
}
.num-badge {
    display:inline-flex; align-items:center; justify-content:center;
    width:22px; height:22px; background:#4f46e5; color:white;
    border-radius:50%; font-size:0.7rem; font-weight:700; flex-shrink:0;
}
.stTextArea textarea {
    border-radius:10px !important; border:1.5px solid #e2e8f0 !important;
    font-size:0.88rem !important;
}
.stTextArea textarea:focus {
    border-color:#6366f1 !important;
    box-shadow:0 0 0 3px rgba(99,102,241,0.1) !important;
}

/* ── Generate button ── */
.stButton > button {
    background:linear-gradient(135deg,#4f46e5,#7c3aed) !important;
    color:white !important; border:none !important; border-radius:12px !important;
    padding:0.75rem 1.5rem !important; font-weight:700 !important;
    font-size:1rem !important; width:100% !important;
    box-shadow:0 4px 20px rgba(79,70,229,0.38) !important;
    transition:all 0.2s !important;
}
.stButton > button:hover {
    transform:translateY(-2px) !important;
    box-shadow:0 8px 28px rgba(79,70,229,0.52) !important;
}

/* ── Progress ── */
.stProgress > div > div {
    background:linear-gradient(90deg,#6366f1,#ec4899) !important;
    border-radius:4px !important;
}

/* ── Log messages ── */
.log-ok   { background:#f0fdf4; border:1px solid #86efac; border-left:4px solid #22c55e; border-radius:8px; padding:0.55rem 0.9rem; color:#166534; font-size:0.8rem; margin:0.25rem 0; }
.log-err  { background:#fff1f2; border:1px solid #fda4af; border-left:4px solid #f43f5e; border-radius:8px; padding:0.55rem 0.9rem; color:#9f1239; font-size:0.8rem; margin:0.25rem 0; }
.log-info { background:#eff6ff; border:1px solid #bfdbfe; border-left:4px solid #3b82f6; border-radius:8px; padding:0.55rem 0.9rem; color:#1e40af; font-size:0.8rem; margin:0.25rem 0; }

/* ── Video found cards ── */
.vid-card {
    background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px;
    padding:0.7rem 0.9rem; margin-bottom:0.45rem;
    display:flex; align-items:flex-start; gap:0.75rem;
}
.vid-thumb { width:80px; border-radius:6px; flex-shrink:0; object-fit:cover; }
.vid-info h4 { margin:0 0 0.18rem; font-size:0.82rem; font-weight:600; color:#1e293b; line-height:1.35; }
.vid-info p  { margin:0; font-size:0.73rem; color:#64748b; }

/* ── Result / preview ── */
.result-banner {
    background:linear-gradient(135deg,#059669,#0ea5e9);
    border-radius:14px; padding:1.3rem 1.6rem; color:white; margin-bottom:1rem;
    box-shadow:0 8px 24px rgba(5,150,105,0.3);
}
.result-banner h3 { margin:0 0 0.25rem; font-size:1.1rem; font-weight:700; }
.result-banner p  { margin:0; opacity:0.88; font-size:0.85rem; }

.slide-card {
    background:white; border:1px solid #e2e8f0; border-radius:10px;
    padding:0.8rem 1rem; margin-bottom:0.5rem; border-left:4px solid #6366f1;
    box-shadow:0 1px 4px rgba(0,0,0,0.04);
}
.slide-card h4 { margin:0 0 0.2rem; font-size:0.87rem; font-weight:600; color:#1e293b; }
.slide-card p  { margin:0; font-size:0.76rem; color:#64748b; line-height:1.5; }

.chip { display:inline-block; border-radius:20px; padding:2px 10px; font-size:0.7rem; font-weight:600; margin:2px; }
.chip-purple { background:#ede9fe; color:#5b21b6; }
.chip-green  { background:#dcfce7; color:#166534; }
.chip-blue   { background:#dbeafe; color:#1e40af; }
.chip-amber  { background:#fef3c7; color:#92400e; }
.chip-pink   { background:#fce7f3; color:#9d174d; }
.chip-white  { background:rgba(255,255,255,0.2); color:white; }

/* ── Sidebar labels ── */
.sb-head { font-size:0.68rem; text-transform:uppercase; letter-spacing:0.09em; color:#6366f1 !important; font-weight:700; margin:0.9rem 0 0.35rem; display:block; }
.sb-info { background:rgba(99,102,241,0.1); border:1px solid rgba(99,102,241,0.2); border-radius:8px; padding:0.6rem 0.8rem; font-size:0.73rem; color:#a5b4fc !important; line-height:1.65; margin-bottom:0.4rem; }

/* ── Empty state ── */
.empty-state {
    background:#f8fafc; border:2px dashed #cbd5e1; border-radius:16px;
    padding:3.5rem 2rem; text-align:center;
}
.empty-icon  { font-size:3rem; margin-bottom:0.7rem; }
.empty-title { font-weight:600; color:#475569; font-size:1rem; margin-bottom:0.3rem; }
.empty-sub   { font-size:0.82rem; color:#94a3b8; }

/* ── Warning banner ── */
.warn-banner {
    background:#fff7ed; border:1px solid #fed7aa; border-radius:12px;
    padding:1rem 1.2rem; color:#92400e; margin-bottom:1.5rem;
    font-size:0.85rem; line-height:1.6;
}

#MainMenu, footer, header { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
GROQ_MODELS = {
    "llama-3.3-70b (Best)": "llama-3.3-70b-versatile",
    "mixtral-8x7b (Balanced)": "mixtral-8x7b-32768",
    "llama-3.1-8b (Fastest)": "llama-3.1-8b-instant",
}
THEMES = ["Auto (AI chooses)", "tech", "business", "education", "creative", "science", "health"]
TYPE_META = {
    "title":       ("🏠", "chip-purple"),
    "section":     ("📌", "chip-blue"),
    "content":     ("📝", "chip-purple"),
    "two_col":     ("⚖️", "chip-blue"),
    "stats":       ("📊", "chip-amber"),
    "quote":       ("💬", "chip-pink"),
    "image_focus": ("🖼️", "chip-green"),
    "closing":     ("🏁", "chip-purple"),
}

# ── Session state ─────────────────────────────────────────────────────────────
for key, val in [("deck", None), ("pptx_bytes", None), ("found_videos", []), ("mode", "search")]:
    if key not in st.session_state:
        st.session_state[key] = val

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div style="font-size:1.15rem;font-weight:800;color:#a5b4fc;padding:0.5rem 0 0.1rem">🎬 YT → Slides</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.73rem;color:#475569;margin-bottom:0.5rem">AI-powered presentation generator</div>', unsafe_allow_html=True)

    if KEYS_OK:
        st.markdown('<div class="sb-info">✅ All API keys loaded — users need no setup</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.25);border-radius:8px;padding:0.6rem 0.8rem;font-size:0.73rem;color:#fca5a5;margin-bottom:0.4rem">⚠️ API keys not configured — add to Streamlit secrets</div>', unsafe_allow_html=True)

    st.markdown('<span class="sb-head">🎛️ Presentation Settings</span>', unsafe_allow_html=True)
    num_slides   = st.slider("Number of slides", 6, 22, 12)
    theme_choice = st.selectbox("Theme", THEMES)
    max_videos   = st.slider("Max videos to use", 2, 8, 4)

    if not KEYS_OK:
        st.markdown('<span class="sb-head">⚙️ Developer Override</span>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:0.72rem;color:#64748b;margin-bottom:0.4rem">For local testing only</div>', unsafe_allow_html=True)
        dev_groq    = st.text_input("Groq Key",    type="password", placeholder="gsk_...")
        dev_yt      = st.text_input("YouTube Key", type="password", placeholder="AIza...")
        dev_pexels  = st.text_input("Pexels Key",  type="password", placeholder="...")
        if dev_groq:    GROQ_KEY   = dev_groq
        if dev_yt:      YT_KEY     = dev_yt
        if dev_pexels:  PEXELS_KEY = dev_pexels
        dev_supadata = st.text_input("Supadata Key", type="password", placeholder="...")
        if dev_supadata: SUPADATA_KEY = dev_supadata

    st.markdown("---")
    st.markdown("""<div style='font-size:0.72rem;color:#475569;line-height:1.75'>
<b style='color:#818cf8'>3 modes:</b><br>
🔍 <b>Search</b> — AI finds best videos<br>
🔗 <b>URLs</b> — use your own videos<br>
⚡ <b>Hybrid</b> — combine both<br><br>
<b style='color:#818cf8'>Powered by:</b><br>
• Groq LLaMA-3.3-70b<br>
• YouTube Data API v3<br>
• youtube-transcript-api<br>
• Pexels Photos<br>
• Supadata Transcripts<br>
• pptxgenjs
</div>""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>🎬 YouTube → Slides</h1>
  <p>Type a topic or paste YouTube URLs — AI reads the videos and builds your presentation</p>
  <div class="hero-pills">
    <span class="hero-pill">🔍 Smart Video Search</span>
    <span class="hero-pill">🤖 Groq AI</span>
    <span class="hero-pill">🖼️ Real Photos</span>
    <span class="hero-pill">📊 Pro Slide Layouts</span>
    <span class="hero-pill">⚡ Free to Use</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Keys missing warning ───────────────────────────────────────────────────────
if not KEYS_OK:
    st.markdown("""<div class="warn-banner">
    ⚠️ <b>API keys not configured.</b> If you're the developer, add keys to <code>.streamlit/secrets.toml</code>
    or use the Developer Override in the sidebar for local testing.
    </div>""", unsafe_allow_html=True)

# ── Mode selector ─────────────────────────────────────────────────────────────
st.markdown("#### Choose your mode")
m1, m2, m3 = st.columns(3)

with m1:
    if st.button("🔍  Search Mode\nAI finds best videos", use_container_width=True):
        st.session_state.mode = "search"
with m2:
    if st.button("🔗  URL Mode\nUse your own videos", use_container_width=True):
        st.session_state.mode = "urls"
with m3:
    if st.button("⚡  Hybrid Mode\nCombine both sources", use_container_width=True):
        st.session_state.mode = "hybrid"

mode = st.session_state.mode

# Active mode indicator
mode_labels = {"search": "🔍 Search Mode", "urls": "🔗 URL Mode", "hybrid": "⚡ Hybrid Mode"}
mode_descs  = {
    "search":  "Enter a topic → AI searches YouTube → finds best videos with captions → generates PPT",
    "urls":    "Paste YouTube URLs → AI reads those specific videos → generates PPT",
    "hybrid":  "Paste URLs + enter a topic → AI uses your videos AND searches for more → richer PPT",
}
st.markdown(f"""<div style='background:#eef2ff;border:2px solid #6366f1;border-radius:12px;
padding:0.8rem 1.1rem;margin:0.8rem 0 1.4rem;'>
<span style='font-weight:700;color:#4338ca'>{mode_labels[mode]}</span>
<span style='color:#64748b;font-size:0.83rem;margin-left:0.5rem'>{mode_descs[mode]}</span>
</div>""", unsafe_allow_html=True)

# ── Input columns ─────────────────────────────────────────────────────────────
col_in, col_out = st.columns([1.05, 1], gap="large")

with col_in:

    # Search query — shown in search + hybrid
    search_query = ""
    if mode in ("search", "hybrid"):
        st.markdown('<div class="input-label"><span class="num-badge">1</span> What topic do you want a presentation on?</div>', unsafe_allow_html=True)
        search_query = st.text_area("query", label_visibility="collapsed",
            placeholder='e.g. "machine learning for beginners"\n     "startup fundraising strategies"\n     "climate change solutions 2025"',
            height=90)

    # URLs — shown in urls + hybrid
    urls_input = ""
    step = "1" if mode == "urls" else "2"
    if mode in ("urls", "hybrid"):
        st.markdown(f'<div class="input-label"><span class="num-badge">{step}</span> Paste YouTube URLs <span style="font-weight:400;color:#94a3b8;font-size:0.8rem">(one per line)</span></div>', unsafe_allow_html=True)
        urls_input = st.text_area("urls", label_visibility="collapsed",
            placeholder="https://www.youtube.com/watch?v=...\nhttps://youtu.be/...",
            height=100)

    # Presentation prompt — always shown
    last_step = {"search": "2", "urls": "2", "hybrid": "3"}[mode]
    st.markdown(f'<div class="input-label"><span class="num-badge">{last_step}</span> What kind of presentation do you want?</div>', unsafe_allow_html=True)
    user_prompt = st.text_area("prompt", label_visibility="collapsed",
        placeholder='e.g. "Executive summary for a board meeting — focus on ROI and risks"\n     "Beginner-friendly tutorial with clear examples and takeaways"\n     "Compare different approaches and give a recommendation"',
        height=110)

    st.markdown("<br>", unsafe_allow_html=True)
    generate_btn = st.button("✨  Generate My Presentation", use_container_width=True)

with col_out:
    st.markdown('<div style="font-weight:600;color:#1e293b;font-size:0.9rem;margin-bottom:0.7rem">📥 Preview & Download</div>', unsafe_allow_html=True)
    preview_ph  = st.empty()
    download_ph = st.empty()

    if st.session_state.deck is None:
        preview_ph.markdown("""<div class="empty-state">
          <div class="empty-icon">🎞️</div>
          <div class="empty-title">Your presentation appears here</div>
          <div class="empty-sub">Fill in the fields on the left and click Generate</div>
        </div>""", unsafe_allow_html=True)

# ── Previously found videos expander ─────────────────────────────────────────
if st.session_state.found_videos:
    with st.expander(f"📹 Videos used in last generation ({len(st.session_state.found_videos)})", expanded=False):
        for v in st.session_state.found_videos:
            thumb = v.get("thumbnail", "")
            img_tag = f'<img class="vid-thumb" src="{thumb}">' if thumb else ""
            title   = v.get("title", v.get("vid_id", ""))
            channel = v.get("channel", "")
            url     = v.get("url", "")
            words   = len(v.get("text", "").split())
            st.markdown(f"""<div class="vid-card">
              {img_tag}
              <div class="vid-info">
                <h4>{title[:70]}</h4>
                <p>📺 {channel} &nbsp;·&nbsp; {words:,} words &nbsp;·&nbsp;
                <a href="{url}" target="_blank" style="color:#6366f1">Watch ↗</a></p>
              </div>
            </div>""", unsafe_allow_html=True)

# ── Generation ────────────────────────────────────────────────────────────────
if generate_btn:

    # ── Validate inputs ───────────────────────────────────────────────────────
    errs = []
    if not GROQ_KEY:
        errs.append("Groq API key not configured — add to Streamlit secrets or sidebar override")
    if mode in ("search", "hybrid") and not search_query.strip():
        errs.append("Please enter a search topic")
    if mode in ("urls", "hybrid") and not urls_input.strip():
        errs.append("Please paste at least one YouTube URL")
    if mode == "search" and not YT_KEY:
        errs.append("YouTube API key not configured — needed for search mode")
    if not user_prompt.strip():
        errs.append("Please describe what kind of presentation you want")
    if errs:
        for e in errs:
            st.markdown(f'<div class="log-err">⚠️ {e}</div>', unsafe_allow_html=True)
        st.stop()

    prog   = st.progress(0)
    status = st.empty()
    logs   = st.container()

    def ok(msg):   logs.markdown(f'<div class="log-ok">✅ {msg}</div>',   unsafe_allow_html=True)
    def err(msg):  logs.markdown(f'<div class="log-err">⚠️ {msg}</div>',  unsafe_allow_html=True)
    def info(msg): logs.markdown(f'<div class="log-info">ℹ️ {msg}</div>', unsafe_allow_html=True)

    # ── Step 1: Gather transcripts ────────────────────────────────────────────
    status.markdown("🔍 **Step 1 / 4** — Gathering video content…")
    all_transcripts = []
    found_vids      = []
    urls = [u.strip() for u in urls_input.strip().splitlines() if u.strip()]

    # Manual URLs
    if urls:
        manual, errs_list = fetch_transcripts_from_urls(urls, SUPADATA_KEY)
        for e in errs_list: err(e)
        for t in manual:
            ok(f"Transcript from URL — <b>{t['vid_id']}</b> ({len(t['text'].split()):,} words)")
        all_transcripts.extend(manual)
        found_vids.extend(manual)

    # Keyword search
    if search_query.strip() and YT_KEY:
        need = max(1, max_videos - len(all_transcripts))
        info(f"Searching YouTube for: <b>{search_query.strip()}</b>…")
        searched, errs_list, raw_vids = fetch_transcripts_from_search(
            search_query.strip(), YT_KEY, SUPADATA_KEY, max_videos=need
        )
        for e in errs_list: err(e)
        for t in searched:
            ok(f"Found — <b>{t['title'][:55]}</b> ({len(t['text'].split()):,} words)")
        all_transcripts.extend(searched)
        found_vids.extend(raw_vids[:need])

    if not all_transcripts:
        st.error("❌ Could not fetch any transcripts. Make sure videos have English captions enabled.")
        st.stop()

    st.session_state.found_videos = [
        {**v, "text": v.get("text", "")} for v in found_vids
    ]
    prog.progress(25)

    # ── Step 2: Generate slides with AI ──────────────────────────────────────
    status.markdown("🤖 **Step 2 / 4** — AI designing your slides…")

    transcripts_block = ""
    for t in all_transcripts:
        transcripts_block += f"\n\n=== VIDEO: {t.get('title', t['vid_id'])} ===\n{t['text']}"

    prompt_final = user_prompt.strip()
    if theme_choice != "Auto (AI chooses)":
        prompt_final += f"\n\nUse theme: {theme_choice}"

    try:
        deck = generate_slides(
            transcripts_block, prompt_final, num_slides,
            GROQ_KEY, "Groq (Free)", GROQ_MODEL
        )
        ok(f"AI generated <b>{len(deck['slides'])} slides</b> — theme: <b>{deck.get('theme','')}</b>")
        st.session_state.deck = deck
    except json.JSONDecodeError as e:
        st.error(f"❌ AI returned invalid JSON. Try again. ({e})")
        st.stop()
    except Exception as e:
        st.error(f"❌ AI error: {e}")
        st.stop()

    prog.progress(52)

    # ── Step 3: Fetch slide images ────────────────────────────────────────────
    status.markdown("🖼️ **Step 3 / 4** — Fetching slide photos from Pexels…")
    images = {}
    slides = deck["slides"]

    if PEXELS_KEY or PIXABAY_KEY:
        for i, sl in enumerate(slides):
            kw = sl.get("image_keyword", "")
            if kw:
                path = get_slide_image(kw, PEXELS_KEY, PIXABAY_KEY)
                if path:
                    images[i] = path
        ok(f"Photos fetched for <b>{len(images)}</b> / {len(slides)} slides")
    else:
        info("No image API keys — slides use themed gradient designs")

    prog.progress(74)

    # ── Step 4: Build PPTX ────────────────────────────────────────────────────
    status.markdown("🛠️ **Step 4 / 4** — Building your PowerPoint file…")
    try:
        pptx_bytes = build_pptx(deck, images, NODE_MODULES)
        st.session_state.pptx_bytes = pptx_bytes
        ok(f"PPTX built — <b>{len(pptx_bytes)//1024} KB</b>")
    except Exception as e:
        st.error(f"❌ PPTX build error: {e}")
        st.stop()

    prog.progress(100)
    status.markdown("✅ **Done!** Your presentation is ready to download.")

# ── Show preview + download ───────────────────────────────────────────────────
if st.session_state.deck and st.session_state.pptx_bytes:
    deck  = st.session_state.deck
    slides = deck.get("slides", [])

    with preview_ph.container():
        st.markdown(f"""<div class="result-banner">
          <h3>🎉 {deck.get('title','')}</h3>
          <p>{deck.get('subtitle','')}</p>
          <div style='margin-top:0.6rem'>
            <span class='chip chip-white'>{len(slides)} slides</span>
            <span class='chip chip-white'>{len(st.session_state.found_videos)} video(s)</span>
            <span class='chip chip-white'>🎨 {deck.get('theme','')}</span>
          </div>
        </div>""", unsafe_allow_html=True)

        for i, sl in enumerate(slides[:9], 1):
            stype       = sl.get("type", "content")
            emoji, chip = TYPE_META.get(stype, ("📝", "chip-purple"))

            preview = ""
            if sl.get("body"):
                preview = "  ·  ".join(str(b)[:50] for b in sl["body"][:2])
            elif sl.get("quote"):
                preview = f'"{str(sl["quote"])[:80]}"'
            elif sl.get("stats"):
                preview = "  |  ".join(f'{s["value"]} {s["label"]}' for s in sl["stats"][:3])
            elif sl.get("left_title"):
                preview = f'{sl["left_title"]}  vs  {sl.get("right_title","")}'

            st.markdown(f"""<div class="slide-card">
              <h4>{emoji} {i}. {sl.get('title','')}</h4>
              <span class="chip {chip}">{stype}</span>
              {'<p style="margin-top:0.3rem">'+preview+'</p>' if preview else ''}
            </div>""", unsafe_allow_html=True)

        if len(slides) > 9:
            st.markdown(f'<div style="text-align:center;color:#94a3b8;font-size:0.78rem;padding:0.4rem">…and {len(slides)-9} more slides in the file</div>', unsafe_allow_html=True)

    safe_title = re.sub(r'[^\w\s-]', '', deck.get("title", "Presentation")).strip().replace(" ", "_")[:50]
    download_ph.download_button(
        label="⬇️  Download PPTX",
        data=st.session_state.pptx_bytes,
        file_name=f"{safe_title}.pptx",
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
    )
