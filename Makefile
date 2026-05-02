# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Galaxy VOC Collector — Makefile
# 사용: make <command>
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

.PHONY: help install setup download run dev test clean

help:
	@echo ""
	@echo "  📱  Galaxy VOC Collector — 명령어 목록"
	@echo "  ─────────────────────────────────────────"
	@echo "  make install      패키지 설치"
	@echo "  make setup        .env 파일 생성"
	@echo "  make download     Gemma 모델 다운로드 (~6GB)"
	@echo "  make run          Streamlit 앱 실행"
	@echo "  make dev          개발 모드 실행 (자동 재시작)"
	@echo "  make test-voc     VOC 수집 테스트"
	@echo "  make test-model   Gemma 모델 테스트"
	@echo "  make clean        캐시 정리"
	@echo ""

# 가상환경 + 패키지 설치
install:
	python -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@echo "✅ 설치 완료! 'make run' 으로 앱을 시작하세요."

# .env 파일 생성
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env 파일이 생성되었습니다."; \
		echo "   HF_TOKEN을 .env 파일에 입력하세요."; \
	else \
		echo "⚠️  .env 파일이 이미 존재합니다."; \
	fi

# 모델 미리 다운로드
download:
	python scripts/download_model.py

# Streamlit 실행
run:
	streamlit run app.py

# 개발 모드 (--server.runOnSave=true)
dev:
	streamlit run app.py --server.runOnSave=true --server.port=8501

# 테스트
test-voc:
	python scripts/test_collect.py

test-voc-live:
	python scripts/test_collect.py --live

test-model:
	python scripts/test_model.py

# 정리
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name ".DS_Store" -delete 2>/dev/null || true
	@echo "✅ 정리 완료"
