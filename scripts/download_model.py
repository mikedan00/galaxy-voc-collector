"""
scripts/download_model.py
Gemma 3n E2B-it 모델을 미리 다운로드합니다.
(Streamlit 앱 실행 전에 먼저 실행하면 빠릅니다)

python scripts/download_model.py
"""

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

MODEL_ID = "google/gemma-3n-E2B-it"

def main():
    hf_token = os.getenv("HF_TOKEN")
    if not hf_token:
        print("❌ .env 파일에 HF_TOKEN을 설정하세요.")
        print("   발급: https://huggingface.co/settings/tokens")
        sys.exit(1)

    print("="*55)
    print(f"  Gemma 3n E2B-it 모델 다운로드")
    print(f"  모델 ID : {MODEL_ID}")
    print(f"  저장 위치: {os.getenv('HF_HOME', '~/.cache/huggingface')}")
    print("="*55)
    print("⚠️  최초 다운로드 약 6GB, 인터넷 속도에 따라 5-20분 소요\n")

    from huggingface_hub import snapshot_download
    from tqdm import tqdm

    try:
        print("📥 다운로드 시작…")
        snapshot_download(
            repo_id=MODEL_ID,
            token=hf_token,
            ignore_patterns=["*.msgpack", "flax_model*", "tf_model*"],
        )
        print("\n✅ 다운로드 완료!")
        print("   이제 'streamlit run app.py' 로 앱을 실행하세요.")
    except Exception as e:
        print(f"❌ 다운로드 실패: {e}")
        print("\n가능한 원인:")
        print("  1. HF_TOKEN 오류 → https://huggingface.co/settings/tokens 에서 재발급")
        print("  2. Gemma 라이선스 미동의 → https://huggingface.co/google/gemma-3n-E2B-it 에서 동의")
        print("  3. 네트워크 오류 → VPN 해제 후 재시도")
        sys.exit(1)

if __name__ == "__main__":
    main()
