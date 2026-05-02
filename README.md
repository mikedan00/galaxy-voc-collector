# 📱 Galaxy VOC Collector
### Gemma 3n E2B-it 기반 · VS Code 로컬 + Streamlit 배포

> 삼성 갤럭시폰 VOC를 자동 수집하고, **Gemma 3n E2B-it (완전 로컬)** 으로 분석해  
> 요구사항명세서(SRS)를 자동 생성하는 Streamlit 애플리케이션

---

## ⚡ 빠른 시작

```bash
# 1. 클론 / 압축 해제
cd galaxy-voc-collector

# 2. 패키지 설치
make install
# 또는: pip install -r requirements.txt

# 3. 환경 설정
make setup          # .env 파일 생성
# → .env 열어서 HF_TOKEN 입력

# 4. (선택) 모델 미리 다운로드 ~6GB
make download

# 5. 앱 실행
make run
# → http://localhost:8501
```

---

## 🖥️ VS Code에서 실행

### 사전 요구사항
| 항목 | 버전 | 확인 |
|------|------|------|
| Python | 3.10 이상 | `python --version` |
| CUDA (선택) | 11.8 이상 | GPU 사용 시 필요 |
| VRAM | 4GB 이상 | 4bit 양자화 기준 |

### 단계별 설치

```bash
# ① 가상환경 생성 (권장)
python -m venv venv

# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# ② CUDA PyTorch 설치 (GPU 사용 시, CUDA 12.1 기준)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# ③ 나머지 패키지
pip install -r requirements.txt

# ④ .env 설정
cp .env.example .env
# .env 파일에 HF_TOKEN 입력

# ⑤ 실행
streamlit run app.py
```

### VS Code 디버깅
- `F5` 누르면 자동으로 Streamlit 앱 실행 (`.vscode/launch.json` 설정됨)
- `Run > Start Debugging` 메뉴 사용 가능

---

## 🌐 Streamlit Cloud 배포

### 1. GitHub에 업로드
```bash
git init
git add .
git commit -m "Galaxy VOC Collector"
git push origin main
```

### 2. Streamlit Cloud 연결
1. [share.streamlit.io](https://share.streamlit.io) 접속
2. **New app** 클릭
3. GitHub 저장소 선택, `app.py` 지정
4. **Advanced settings** → **Secrets** 탭에 입력:

```toml
HF_TOKEN = "hf_your_token_here"
USE_4BIT  = true
USE_GPU   = true
```

> ⚠️ Streamlit Cloud 무료 플랜은 CPU만 지원.  
> GPU가 필요하면 **Hugging Face Spaces** (A10G 무료) 또는 **Railway** 사용 권장.

### Hugging Face Spaces 배포 (GPU 무료)

`README.md` 상단에 아래 추가:
```yaml
---
title: Galaxy VOC Collector
emoji: 📱
colorFrom: blue
colorTo: cyan
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
hardware: a10g-small
---
```

---

## 📁 프로젝트 구조

```
galaxy-voc-collector/
├── app.py                      # 🎯 Streamlit 메인 앱
├── requirements.txt            # Python 의존성
├── Makefile                    # 편의 명령어
├── .env.example                # 환경변수 템플릿
│
├── models/
│   ├── __init__.py
│   └── gemma_engine.py         # Gemma 3n E2B-it 추론 엔진
│
├── utils/
│   ├── __init__.py
│   ├── voc_collector.py        # VOC 크롤링 (5개 채널)
│   └── doc_generator.py        # Word(.docx) 문서 생성
│
├── scripts/
│   ├── download_model.py       # 모델 미리 다운로드
│   ├── test_collect.py         # VOC 수집 테스트
│   └── test_model.py           # 모델 추론 테스트
│
├── .streamlit/
│   ├── config.toml             # Streamlit 테마 설정
│   └── secrets.toml.example    # 클라우드 시크릿 예시
│
├── .vscode/
│   ├── launch.json             # VS Code 디버그 설정
│   └── settings.json           # VS Code 설정
│
└── output/                     # 생성된 문서 저장
```

---

## 🤖 Gemma 3n E2B-it 모델 정보

| 항목 | 내용 |
|------|------|
| 모델 ID | `google/gemma-3n-E2B-it` |
| 실효 파라미터 | 2B (VRAM: ~4GB, 4bit 기준) |
| 실제 파라미터 | 5B (PLE 기술로 효율화) |
| 필요 transformers | 4.53.0 이상 |
| 라이선스 | [Gemma Terms of Service](https://ai.google.dev/gemma/terms) |

### VRAM 요구사항

| 실행 모드 | VRAM | 권장 GPU |
|-----------|------|----------|
| 4bit 양자화 | ~4 GB | RTX 3060, T4 |
| bfloat16 | ~12 GB | RTX 3080, A10G |
| CPU 전용 | RAM 16GB+ | 매우 느림 |

---

## 🔑 HuggingFace 토큰 발급

1. [huggingface.co](https://huggingface.co) 계정 생성
2. [Gemma 3n 라이선스 동의](https://huggingface.co/google/gemma-3n-E2B-it) 필수
3. [토큰 발급](https://huggingface.co/settings/tokens) → `Read` 권한

---

## 🔄 3단계 워크플로우

```
STEP 1 ─ VOC 수집          STEP 2 ─ AI 분석           STEP 3 ─ 명세서 생성
────────────────────        ─────────────────────        ────────────────────
키워드 + 채널 선택    →    Gemma 3n이 로컬에서    →    SRS 스트리밍 생성
5개 채널 자동 크롤링        핵심 이슈 / 요구사항         DOCX / JSON / MD
데모 데이터로 즉시 테스트    완전 오프라인 동작           output/ 폴더 저장
```

---

## ❓ 자주 묻는 질문

**Q. API 키 없이 테스트할 수 있나요?**  
A. 네. 사이드바의 `데모` 버튼으로 38건의 샘플 VOC를 즉시 로드할 수 있습니다.  
   단, AI 분석은 Gemma 모델 로드 후 가능합니다.

**Q. 인터넷 없이 동작하나요?**  
A. 모델 다운로드(최초 1회)만 인터넷이 필요합니다.  
   이후 AI 분석은 완전 오프라인으로 동작합니다.

**Q. GPU가 없어도 되나요?**  
A. CPU 모드로도 동작하지만 분석에 10-30분이 소요될 수 있습니다.

**Q. `transformers` 버전 오류가 발생합니다.**  
A. `pip install -U transformers` 로 4.53.0 이상으로 업그레이드하세요.

---

## 📦 기술 스택

| 분류 | 기술 |
|------|------|
| UI | Streamlit 1.35+ |
| AI 모델 | Gemma 3n E2B-it |
| 추론 | HuggingFace Transformers 4.53+ |
| 양자화 | bitsandbytes (4bit NF4) |
| 크롤링 | requests + BeautifulSoup4 |
| 문서 생성 | python-docx |
| 환경 관리 | python-dotenv |
