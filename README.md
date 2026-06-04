# 🎬 YouTube → Slides (Production)

AI-powered presentation generator. Users open the link, type a topic, download their PPT. No API keys needed from users.

## ✨ What users see
- Clean UI — just type a topic or paste URLs
- 3 modes: Search / URLs / Hybrid
- Download professional PPTX in ~60 seconds
- No signup, no API keys, no friction

## 🚀 Deploy to Streamlit Cloud (5 minutes)

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "initial commit"
# create repo on github.com then:
git remote add origin https://github.com/YOUR_USERNAME/yt2ppt.git
git push -u origin main
```

### Step 2 — Deploy on Streamlit Cloud
1. Go to **share.streamlit.io**
2. Sign in with GitHub
3. Click **New app**
4. Select your repo → Branch: `main` → Main file: `app.py`
5. Click **Advanced settings** → **Secrets**
6. Paste your secrets (see below)
7. Click **Deploy**

### Step 3 — Add secrets in Streamlit Cloud
In the Secrets box paste:
```toml
GROQ_API_KEY     = "gsk_xxxxxxxxxxxxxxxxxxxx"
YOUTUBE_API_KEY  = "AIzaxxxxxxxxxxxxxxxxxxxxxxxxx"
PEXELS_API_KEY   = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
GROQ_MODEL       = "llama-3.3-70b-versatile"
```

### Step 4 — Share your link
```
https://your-app-name.streamlit.app
```
Anyone can use it — no setup needed on their end.

## 🗂 Project Structure
```
yt2ppt_final/
├── app.py                  ← Main Streamlit app (production)
├── youtube_search.py       ← YouTube search + transcripts
├── ai_generator.py         ← Groq / Anthropic AI generation
├── image_fetcher.py        ← Pexels + Pixabay photos
├── pptx_builder.py         ← pptxgenjs PPTX renderer
├── requirements.txt        ← Python dependencies
├── package.json            ← Node.js dependencies
├── .gitignore              ← Keeps secrets safe
└── .streamlit/
    ├── secrets.toml        ← Your API keys (never commit!)
    └── config.toml         ← App theme settings
```

## 🔑 API Keys Needed (you add these, users don't)

| Key | Free | Get it at |
|-----|------|-----------|
| Groq | ✅ Free | console.groq.com |
| YouTube Data v3 | ✅ Free | console.cloud.google.com |
| Pexels | ✅ Free | pexels.com/api |
| Pixabay | ✅ Free (optional) | pixabay.com/api/docs |

## 🖥 Run locally
```bash
pip install -r requirements.txt
npm install
# Fill .streamlit/secrets.toml with your keys
streamlit run app.py
```

## 3 Usage Modes
| Mode | How | Best for |
|------|-----|---------|
| 🔍 Search | Type a topic → AI finds videos | Exploring a subject |
| 🔗 URLs | Paste specific YouTube links | Using trusted sources |
| ⚡ Hybrid | Topic + URLs combined | Richest content |
