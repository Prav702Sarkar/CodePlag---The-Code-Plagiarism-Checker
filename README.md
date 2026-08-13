<div align="center">

# 🔍 CodePlag — Advanced Code Plagiarism Checker

**Dual-source code plagiarism detection — GitHub API + Web intelligence**

A professional-grade plagiarism detection system that scans uploaded source code against **millions of GitHub repositories** and **web sources** (DuckDuckGo / Bing / Stack Overflow), using intelligent code extraction and structure-aware similarity matching.

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![Python 3.14](https://img.shields.io/badge/Python%203.14-Ready-3776AB)
![Flask](https://img.shields.io/badge/Flask-2.3-000000?logo=flask)
![Languages](https://img.shields.io/badge/21%20Languages-%E2%9C%93-00F5FF)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Production%20Ready-3DFF6A)

</div>

---

## ✨ Features

### 🧠 Intelligent Detection
- **Dual-source scanning** — GitHub REST API **and** web search (DuckDuckGo, Bing, Stack Overflow) run in parallel per file.
- **Smart code extraction** — AST parsing for Python, regex-based extraction for every other language. Removes comments, imports, docstrings and boilerplate to isolate the *algorithmic core* (≈61% noise reduction).
- **Structure-aware similarity** — 70% text matching + 30% structural pattern matching (functions, classes, loops, conditions). Every computed match ≥ 8% is shown with its real percentage.

### 🌍 Language Support — 21 languages, 32 file extensions
| Group | Extensions |
|---|---|
| Python | `.py`, `.pyw` |
| JavaScript / TypeScript | `.js`, `.jsx`, `.ts`, `.tsx` |
| Java | `.java` |
| C / C++ | `.c`, `.h`, `.cpp`, `.cc`, `.cxx`, `.hpp`, `.hh` |
| C# | `.cs` |
| Ruby / PHP / Perl | `.rb`, `.php`, `.pl`, `.pm` |
| Go / Rust / Swift / Kotlin / Scala | `.go`, `.rs`, `.swift`, `.kt`, `.scala` |
| Shell | `.sh`, `.bash` |
| R / Haskell / Lua | `.r`, `.hs`, `.lua` |
| Web | `.html`, `.htm`, `.css` |
| Archives | `.zip` (batch processing) |

### 🚀 Modern UX
- Drag & drop upload, multi-file selection, live file list with sizes.
- **Animated warning pop-ups** — files over **3 MB** trigger an attention-grabbing animated notification; scanning is **blocked** (button disabled) until oversized files are removed. Large files must be **split into parts (each under 3 MB) and uploaded as a ZIP**.
- Batch ZIP processing with per-file results.
- Neon cyberpunk UI — Bootstrap 5.1 + custom CSS, fully responsive.

### 🛡️ Security & Reliability
- **3 MB per-file limit enforced on both client and server** (`Config.MAX_UPLOAD_SIZE`) — oversized uploads never reach the analysis stage.
- Filename sanitization (path-traversal protection), content validation, binary detection.
- **Rate limiting** — 200 req/day & 50 req/hour default, 10 checks/minute on `/check`.
- GitHub API rate-limit awareness with graceful degradation.
- 1-hour result caching to avoid repeat API calls.
- **Fallback chain** — GitHub → Web → mock data, so the app never hard-fails.

> ℹ️ **Honesty note:** Professional plagiarism services (MOSS, JPlag, Codequiry…) are *simulated* for demonstration. The real detection engines are the **GitHub API** and **web scraping** — a `GITHUB_API_KEY` unlocks the GitHub half.

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [Detection Algorithm](#detection-algorithm)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Screenshots](#screenshots)
- [Performance](#performance)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [License](#license)

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** — tested on 3.12, compatible with **3.14**
- pip
- (Recommended) A [GitHub Personal Access Token](https://github.com/settings/tokens) with `public_repo` scope

### Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd "Plagiarism Checker main"

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env     # then edit .env

# 5. Run the application
python app.py
```

Open **http://localhost:5000** 🎉

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and set your values:

```env
# GitHub Personal Access Token (required for GitHub code search)
GITHUB_API_KEY=your_github_token_here

# Flask secret key for sessions (any random string; a dev default is used if omitted)
SECRET_KEY=your_secret_key_here
```

| Variable | Required | Description |
|---|---|---|
| `GITHUB_API_KEY` | ✅ for GitHub search | GitHub token with `public_repo` scope |
| `SECRET_KEY` | ❌ | Flask session secret; a dev default is used if omitted |

Without a token, the app still works — it falls back to web-only detection and returns clear, actionable messages.

---

## 🎯 Usage

1. **Upload code** — drag & drop files or click *Browse Files*. Multi-file and `.zip` uploads supported.
2. **Watch the size limit** — files over **3 MB** show an animated warning and **block scanning**. Split large files into parts (each under 3 MB) and upload them as a ZIP.
3. **Scan** — CodePlag extracts the core logic, then searches GitHub and the web in parallel.
4. **Review results** — per-file similarity scores (GitHub & Web), matched repositories/sources with links, and matched code blocks.

```
file.py        [GitHub: 79% | Web: 43%]
utils.py       [GitHub: 0%  | Web: 0%]
```

---

## 🔬 How It Works

```
Upload → Validate → Extract → Normalize → Search → Compare → Display
  │         │          │          │          │         │         │
  │    3MB limit,   AST/Regex   Remove     GitHub API  70% text  Results
  │    extension,   core-code   comments   Web search  30% structure  with %
  │    content      isolation   + noise                 matching
```

1. **Validation** — extension allow-list (32 types), 3 MB size enforcement, content sanity checks, filename sanitization.
2. **Intelligent extraction** — AST for Python; regex for all other languages. Keeps functions, classes and control flow; drops comments, imports, boilerplate.
3. **Normalization** — strips comments/whitespace, generates SHA-256 fingerprints.
4. **Dual-source search** — each core block generates search terms; GitHub code search + DuckDuckGo/Bing queries run with rate-limit awareness.
5. **Similarity scoring** — `SequenceMatcher` text similarity (70%) + structural pattern overlap (30%), deduplicated and sorted.

---

## 🧮 Detection Algorithm (Backend)

CodePlag's backend uses a **hybrid, multi-stage detection pipeline** that combines three complementary techniques:

### 1. Ratcliff–Obershelp Text Matching

Text similarity is computed with Python's `difflib.SequenceMatcher`, which implements the **Ratcliff–Obershelp (gestalt pattern-matching) algorithm**: it recursively finds the longest common substring between two normalized code blocks and scores them as `2 × matched characters / total characters`. It is language-agnostic, order-sensitive and robust to whitespace/comment edits.

### 2. Structure-Aware Pattern Matching

Raw text similarity alone can be fooled by renamed variables. The engine therefore also counts **structural patterns** — function/class definitions, `for`/`while` loops, `if` conditionals, `return` statements and assignments — and computes the overlap ratio between two blocks. This catches copies whose identifiers and formatting differ but whose *logic skeleton* is identical.

### 3. Weighted Hybrid Scoring

```
similarity = (text_similarity × 0.7) + (structure_similarity × 0.3)
```

The two scores are combined with a **70% text / 30% structure** weight. Every computed match above a **low reporting floor of 8%** (GitHub and web alike) is surfaced on the results page with its real percentage — nothing the engine computes is silently hidden. The **30% bar** is used only to label a match as *significant* for the recommendations panel, not to discard data.

### Supporting Techniques

- **Intelligent extraction** — AST parsing (Python) / regex parsing (all other languages) isolates functions, classes and control-flow blocks, dropping comments, imports, docstrings and boilerplate (~61% noise reduction). Each block becomes an independent comparison unit.
- **Normalization & fingerprinting** — comments/whitespace stripped; SHA-256 fingerprints generated for fast equality checks.
- **Dual-source search** — extracted blocks generate search terms; GitHub code search + DuckDuckGo/Bing queries run in parallel under per-request rate limiting.
- **Result caching** — MD5 query keys with a 1-hour TTL avoid duplicate API calls.
- **Fallback chain** — intelligent extraction → regex fallback → web-only → mock data, so analysis never hard-fails.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                       │
│      Flask Templates (Bootstrap 5) + vanilla JavaScript     │
└─────────────────────────────┬───────────────────────────────┘
                              ↕
┌─────────────────────────────▼───────────────────────────────┐
│                    APPLICATION LAYER (Flask)                │
│     Routing • Upload handling • Rate limiting • Results     │
└─────────────────────────────┬───────────────────────────────┘
                              ↕
┌─────────────────────────────▼───────────────────────────────┐
│                     BUSINESS LOGIC LAYER                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐     │
│  │File Processing│ │Plagiarism Check│ │Code Extraction │     │
│  └──────────────┘ └──────────────┘ └──────────────────┘     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐     │
│  │  Security    │ │  GitHub API  │ │  Web Scraping    │     │
│  └──────────────┘ └──────────────┘ └──────────────────┘     │
└─────────────────────────────┬───────────────────────────────┘
                              ↕
┌─────────────────────────────▼───────────────────────────────┐
│                   EXTERNAL SERVICES                         │
│   GitHub REST API • DuckDuckGo • Bing • Stack Overflow      │
└─────────────────────────────────────────────────────────────┘
```

### Project Structure

```
├── app.py                       # Flask application & routes
├── config.py                    # Central configuration (languages, limits)
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variable template
├── utils/
│   ├── file_processing.py       # Upload validation, language detection, ZIP extraction
│   ├── github_api.py            # GitHub search, rate limits, caching
│   ├── intelligent_extraction.py# AST/regex core-code extraction
│   ├── plagiarism_check.py      # Normalization, similarity, orchestration
│   ├── security.py              # Sanitization, content validation, rate limiting
│   └── web_check.py             # DuckDuckGo/Bing search + page scraping
├── templates/                   # base, index, results, error
├── static/
│   ├── css/style.css            # Cyberpunk theme
│   └── js/script.js             # Upload UX, animated notifications, validation
└── cache/                       # 1-hour result cache (auto-generated)
```

---

## 🔌 API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Upload page |
| `/check` | POST | Plagiarism check (multipart files) — rate limited: 10/min |
| `/health` | GET | Health check + supported languages |
| `/api-status` | GET | GitHub rate-limit status + detection methods |

---

## 🖼️ Screenshots

### Upload Interface
```
┌────────────────────────────────────────────┐
│  📁 Drag & Drop Your Code Files Here       │
│  Maximum file size: 3MB per file           │
│  Files over 3MB are blocked - split into   │
│  smaller parts and upload as a ZIP         │
└────────────────────────────────────────────┘
```

### Results Display
```
┌────────────────────────────────────────────┐
│  Overall: GitHub 79% | Web 43%             │
│  Files Checked:                            │
│  ├─ app.py      [GitHub: 79% | Web: 43%]   │
│  └─ utils.py    [GitHub: 0%  | Web: 0%]    │
│  GitHub Matches:                           │
│  • user/repo/file.py   (95.1% similar)     │
│  Web Matches:                              │
│  • stackoverflow.com/q/123456  (43.4%)     │
└────────────────────────────────────────────┘
```

---

## 📊 Performance

| Metric | Value |
|---|---|
| Supported languages | 21 (32 source extensions + ZIP) |
| Max file size | **3 MB** per file (client + server enforced) |
| Typical processing | 10–30 s per file (varies with API/network) |
| Code noise reduction | ~61% via intelligent extraction |
| Result caching | 1 hour (auto-purged) |
| Rate limits | 200/day & 50/hour default; 10/min on `/check` |
| Peak memory | tuned for **512 MB** (Render free plan) |

---

## ☁️ Deploy to Render (Free Plan)

The repo ships with a `render.yaml` tuned for Render's free tier (**512 MB RAM**, 512 MB disk):

- **Single worker, 2 threads** — each gunicorn worker duplicates the whole app in RAM, so the config keeps exactly one worker and serves concurrent requests with threads that *share* that memory.
- **Worker recycling** (`--max-requests`) — periodically restarts the worker to prevent slow memory leaks from accumulating.
- **300s request timeout** — scans take 10–30 s per file; the default 30 s timeout would kill them mid-request.
- **Bounded request memory** — ZIP extraction caps uncompressed size (30 MB total, 3 MB per file, 100 files) and GitHub match contents are truncated to 64 KB, so no single request can blow the 512 MB budget.
- **Slimmed dependencies** — unused heavy/native packages (`lxml`, `waitress`, `chardet`) were removed; BeautifulSoup uses the built-in `html.parser`.
- **Production logging** — DEBUG logging (which retains lots of strings) is only enabled when `DEBUG=true`.

> ⚠️ Free-tier instances **spin down after 15 minutes of inactivity** and take ~30–60 s to cold-start on the next request — the first request after idle will be slow. This is normal Render free behavior, not an app bug.

---

## 🐛 Troubleshooting

| Issue | Cause / Fix |
|---|---|
| *"exceeds the 3MB limit"* | File > 3 MB — split it into parts (each < 3 MB) and upload as a ZIP |
| *GitHub search error / rate limit* | Wait for the GitHub rate-limit reset, or set a valid `GITHUB_API_KEY` |
| *No web matches* | Search engines blocking requests / network issues / original code — retry later |
| *`ModuleNotFoundError`* | Run `pip install -r requirements.txt` |
| *File rejected on upload* | Unsupported extension, > 3 MB, or non-UTF-8 encoding |

---

## 🗺️ Roadmap

### Feature
- [ ] More search engines (Google, Startpage)
- [ ] GitHub GraphQL API for deeper searches
- [ ] PDF/CSV report generation
- [ ] Docker deployment
- [ ] Real test suite (pytest) for the full 32-extension matrix

### Performance & Algorithm Upgrades (faster, lower memory) {for Future upgrade}
- [ ] **Winnowing k-gram fingerprinting** (MOSS-style) — replace the O(n²) `SequenceMatcher` with fixed-size rolling hashes + window minima for near-linear detection
- [ ] **MinHash + LSH** — locality-sensitive hashing so candidate blocks are found in sub-linear time instead of comparing everything pairwise
- [ ] **Token-stream comparison** — compare tokenized code (not raw characters); faster and semantics-aware
- [ ] **AST-normalized fingerprints** (Deckard-style) — structure-aware clone detection immune to renamed variables
- [ ] **Inverted index / SQLite FTS** — replace flat JSON caching with an indexed, queryable result store
- [ ] **Async HTTP** (aiohttp/httpx) — replace sequential `requests` + `time.sleep(1)` with concurrent batched queries
- [ ] **Code embeddings** (UniXcoder / CodeBERT) + vector ANN (FAISS / HNSW) — semantic similarity for heavily rewritten code

---

## 📄 License

MIT — free to use and modify.

---

<div align="center">

**Built with ❤️ by [Praveen Kumar Sarkar](https://github.com/)** — for developers, educators, and organizations.

⭐ Star this repo if you find it useful!

</div>
