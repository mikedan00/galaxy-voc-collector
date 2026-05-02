"""
scripts/test_model.py
Gemma 3n E2B-it 모델 단독 테스트
python scripts/test_model.py
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

def test_model_load():
    print("="*55)
    print("  Gemma 3n E2B-it 모델 테스트")
    print("="*55)

    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ HF_TOKEN이 없습니다.")
        print("   .env 파일에 HF_TOKEN=hf_... 를 설정하세요.")
        sys.exit(1)

    print(f"✅ HF_TOKEN 확인: {hf_token[:8]}…")

    # GPU 확인
    try:
        import torch
        print(f"✅ PyTorch: {torch.__version__}")
        if torch.cuda.is_available():
            gpu = torch.cuda.get_device_name(0)
            vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"✅ GPU: {gpu} ({vram:.1f}GB)")
        else:
            print("⚠️  GPU 없음 (CPU 모드로 실행, 매우 느릴 수 있음)")
    except ImportError:
        print("❌ PyTorch가 설치되지 않았습니다.")
        sys.exit(1)

    # transformers 버전 확인
    try:
        import transformers
        from packaging import version
        tv = version.parse(transformers.__version__)
        if tv >= version.parse("4.53.0"):
            print(f"✅ transformers: {transformers.__version__} (Gemma 3n 지원)")
        else:
            print(f"⚠️  transformers {transformers.__version__} → 4.53.0 이상 필요")
            print("   pip install -U transformers")
    except ImportError:
        print("❌ transformers 미설치")
        sys.exit(1)

    # 모델 로드
    print("\n📥 모델 로딩 중… (최초 실행 시 ~6GB 다운로드)")
    from models.gemma_engine import engine

    def progress(msg):
        print(f"  {msg}")

    try:
        use_4bit = os.getenv("USE_4BIT", "true").lower() == "true"
        use_gpu  = os.getenv("USE_GPU",  "true").lower() == "true"
        engine.load(hf_token=hf_token, use_4bit=use_4bit, use_gpu=use_gpu, progress_cb=progress)
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        sys.exit(1)

    # 추론 테스트
    print("\n🧪 추론 테스트…")
    test_cases = [
        ("기본 한국어", "갤럭시 스마트폰의 배터리 문제 해결 방법을 간단히 3가지만 알려주세요.", 200),
        ("VOC 분류",   "다음 VOC를 카테고리로 분류하세요: '야간 카메라 사진이 흐릿합니다'", 100),
    ]

    for name, prompt, max_tok in test_cases:
        print(f"\n  [{name}]")
        print(f"  입력: {prompt[:60]}…")
        try:
            start = __import__("time").time()
            result = engine.generate(prompt, max_new_tokens=max_tok, do_sample=False)
            elapsed = __import__("time").time() - start
            print(f"  출력: {result[:120]}…" if len(result) > 120 else f"  출력: {result}")
            print(f"  시간: {elapsed:.1f}초")
        except Exception as e:
            print(f"  ❌ 오류: {e}")

    print("\n✅ 모든 테스트 완료!")

if __name__ == "__main__":
    test_model_load()
