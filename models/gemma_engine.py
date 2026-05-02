"""
gemma_engine.py
Gemma 3n E2B-it 모델 로딩 및 추론 엔진
- HuggingFace에서 자동 다운로드 (최초 1회, ~6GB)
- 4bit 양자화로 VRAM ~4GB에서 동작
- CPU fallback 지원 (느리지만 GPU 없어도 동작)
"""

from __future__ import annotations

import json
import os
import re
import time
import gc
from pathlib import Path
from typing import Iterator, Optional

import torch

MODEL_ID = "google/gemma-3n-E2B-it"
SYSTEM_PROMPT = (
    "당신은 삼성전자 갤럭시 스마트폰 시니어 제품 기획 전문가입니다. "
    "항상 한국어로 답변하세요. 분석은 구체적이고 실용적으로 작성하세요."
)


class GemmaEngine:
    """Gemma 3n E2B-it 추론 엔진 (싱글톤)"""

    _instance: Optional["GemmaEngine"] = None
    _model    = None
    _processor= None
    _loaded   = False

    def __new__(cls) -> "GemmaEngine":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── 로딩 ──────────────────────────────────────────────────
    def load(
        self,
        hf_token:  Optional[str] = None,
        use_4bit:  bool = True,
        use_gpu:   bool = True,
        progress_cb: Optional[callable] = None,
    ) -> None:
        """모델 로드 (이미 로드된 경우 스킵)"""
        if self._loaded:
            return

        from transformers import (
            AutoProcessor,
            Gemma3nForConditionalGeneration,
            BitsAndBytesConfig,
        )

        token = hf_token or os.getenv("HF_TOKEN")
        if not token:
            raise ValueError(
                "HF_TOKEN이 필요합니다.\n"
                "발급: https://huggingface.co/settings/tokens\n"
                ".env 파일에 HF_TOKEN=hf_... 형태로 입력하세요."
            )

        if progress_cb:
            progress_cb("프로세서 로딩 중…")

        self._processor = AutoProcessor.from_pretrained(
            MODEL_ID, token=token, trust_remote_code=True
        )

        if progress_cb:
            progress_cb("모델 가중치 로딩 중… (최초 실행 시 ~6GB 다운로드)")

        device_map = "auto" if (use_gpu and torch.cuda.is_available()) else "cpu"

        load_kwargs: dict = {
            "token": token,
            "trust_remote_code": True,
        }

        if use_4bit and torch.cuda.is_available():
            load_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            load_kwargs["device_map"] = device_map
        elif torch.cuda.is_available():
            load_kwargs["torch_dtype"] = torch.bfloat16
            load_kwargs["device_map"] = device_map
        else:
            load_kwargs["torch_dtype"] = torch.float32
            load_kwargs["device_map"] = "cpu"

        self._model = Gemma3nForConditionalGeneration.from_pretrained(
            MODEL_ID, **load_kwargs
        ).eval()

        self._loaded = True

        if progress_cb:
            if torch.cuda.is_available():
                used  = torch.cuda.memory_allocated() / 1024**3
                total = torch.cuda.get_device_properties(0).total_memory / 1024**3
                progress_cb(f"모델 로드 완료 ✅  VRAM {used:.1f}/{total:.1f}GB")
            else:
                progress_cb("모델 로드 완료 ✅  (CPU 모드)")

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # ── 추론 ──────────────────────────────────────────────────
    def generate(
        self,
        prompt:         str,
        system:         str  = SYSTEM_PROMPT,
        max_new_tokens: int  = 2048,
        temperature:    float = 0.3,
        do_sample:      bool  = True,
    ) -> str:
        if not self._loaded:
            raise RuntimeError("모델이 로드되지 않았습니다. load()를 먼저 호출하세요.")

        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": f"{system}\n\n{prompt}"}],
        }]

        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )

        device = next(self._model.parameters()).device
        inputs = {
            k: v.to(device)
            for k, v in inputs.items()
            if isinstance(v, torch.Tensor)
        }
        input_len = inputs["input_ids"].shape[-1]

        gen_kwargs: dict = dict(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            pad_token_id=self._processor.tokenizer.eos_token_id,
        )
        if do_sample:
            gen_kwargs.update(temperature=temperature, top_p=0.9)

        with torch.inference_mode():
            output = self._model.generate(**gen_kwargs)

        new_tokens = output[0][input_len:]
        return self._processor.decode(new_tokens, skip_special_tokens=True)

    def generate_stream(
        self,
        prompt:         str,
        system:         str  = SYSTEM_PROMPT,
        max_new_tokens: int  = 3000,
        temperature:    float = 0.25,
        chunk_size:     int   = 8,
    ) -> Iterator[str]:
        """토큰 단위 스트리밍 제너레이터 (streamlit st.write_stream 호환)"""
        if not self._loaded:
            raise RuntimeError("모델이 로드되지 않았습니다.")

        from transformers import TextIteratorStreamer
        import threading

        messages = [{
            "role": "user",
            "content": [{"type": "text", "text": f"{system}\n\n{prompt}"}],
        }]

        inputs = self._processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )
        device = next(self._model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}

        streamer = TextIteratorStreamer(
            self._processor.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )

        gen_kwargs = dict(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            pad_token_id=self._processor.tokenizer.eos_token_id,
            streamer=streamer,
        )

        thread = threading.Thread(target=self._model.generate, kwargs=gen_kwargs)
        thread.start()

        for text in streamer:
            yield text

        thread.join()

    def unload(self) -> None:
        """메모리 해제"""
        if self._model is not None:
            del self._model
            self._model = None
        if self._processor is not None:
            del self._processor
            self._processor = None
        self._loaded = False
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ── 전역 싱글톤 ──────────────────────────────────────────────
engine = GemmaEngine()


# ── 분석 함수 ─────────────────────────────────────────────────

def analyze_voc(voc_list: list, model_info: str = "갤럭시 스마트폰") -> dict:
    """VOC 리스트를 분석하여 JSON 구조 반환"""
    from collections import Counter

    grouped = {}
    for v in voc_list:
        cat = v.category if hasattr(v, "category") else v.get("category", "기타")
        ttl = v.title    if hasattr(v, "title")    else v.get("title", "")
        grouped.setdefault(cat, []).append(ttl)

    voc_summary = "\n\n".join(
        f"[{cat}] ({len(titles)}건)\n" + "\n".join(f"  • {t}" for t in titles[:8])
        for cat, titles in sorted(grouped.items(), key=lambda x: -len(x[1]))
    )

    prompt = f"""아래는 {model_info} 관련 실제 사용자 VOC 데이터입니다.
수집 건수: {len(voc_list)}건

=== VOC 데이터 (카테고리별) ===
{voc_summary}

위 VOC를 분석하여 아래 JSON 형식으로만 응답하세요. JSON 외 텍스트 없이 순수 JSON만:

{{
  "executive_summary": "전체 현황 핵심 요약 (3-4문장, 수치 포함)",
  "critical_issues": [
    {{
      "title": "이슈명",
      "description": "구체적 설명 (2문장)",
      "frequency": "높음/중간/낮음",
      "impact": "높음/중간/낮음",
      "category": "카테고리명"
    }}
  ],
  "requirements": [
    {{
      "id": "REQ-001",
      "category": "카테고리",
      "priority": "필수/권장/선택",
      "title": "요구사항 제목",
      "description": "상세 설명",
      "user_story": "사용자로서 나는 [무엇을] [왜] 하고 싶다",
      "acceptance_criteria": ["기준1", "기준2"]
    }}
  ],
  "roadmap": [
    {{"phase": "즉시(1개월)", "items": ["항목1", "항목2"]}},
    {{"phase": "단기(1-3개월)", "items": ["항목1", "항목2"]}},
    {{"phase": "중기(3-6개월)", "items": ["항목1", "항목2"]}},
    {{"phase": "장기(6개월+)", "items": ["항목1", "항목2"]}}
  ],
  "key_insights": ["인사이트1", "인사이트2", "인사이트3", "인사이트4"]
}}"""

    raw = engine.generate(prompt, max_new_tokens=3500, temperature=0.2)

    # JSON 파싱
    try:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            return json.loads(m.group())
    except json.JSONDecodeError:
        pass

    # 파싱 실패 시 기본값 반환
    return {
        "executive_summary": raw[:400] if raw else "분석 결과를 파싱하지 못했습니다.",
        "critical_issues": [], "requirements": [],
        "roadmap": [], "key_insights": [],
    }


def build_srs_prompt(voc_list: list, analysis: dict, product_name: str, version: str, author: str) -> str:
    """SRS 생성 프롬프트 구성"""
    from collections import Counter

    if not voc_list:
        return ""

    cat_lines = "\n".join(
        f"  {cat}: {cnt}건"
        for cat, cnt in Counter(
            (v.category if hasattr(v, "category") else v.get("category", "기타"))
            for v in voc_list
        ).most_common()
    )
    req_lines = "\n".join(
        f"  - {r.get('id')}: {r.get('title')} [{r.get('priority')}]"
        for r in analysis.get("requirements", [])[:15]
    )
    iss_lines = "\n".join(
        f"  - [{i.get('impact','?')} 영향] {i.get('title')}: {i.get('description','')[:60]}"
        for i in analysis.get("critical_issues", [])[:8]
    )
    snt_neg = sum(1 for v in voc_list if (v.sentiment if hasattr(v, "sentiment") else v.get("sentiment")) == "negative")

    return f"""삼성전자 갤럭시 시니어 제품 기획자로서 다음 정보를 바탕으로 체계적인 소프트웨어 요구사항명세서(SRS)를 작성하세요.

제품명: {product_name} | 버전: v{version} | 작성자: {author}
작성일: {time.strftime('%Y년 %m월 %d일')}
AI 분석 엔진: Gemma 3n E2B-it (google/gemma-3n-E2B-it)
총 VOC: {len(voc_list)}건 | 부정 의견: {snt_neg}건 ({round(snt_neg/len(voc_list)*100)}%)

핵심 이슈:
{iss_lines}

도출된 요구사항:
{req_lines}

카테고리별 분포:
{cat_lines}

종합 분석: {analysis.get('executive_summary', '')}

다음 구조로 완전한 SRS를 한국어로 작성하세요 (각 섹션 충분히 상세하게):

# {product_name} VOC 기반 소프트웨어 요구사항명세서 v{version}

## 1. 문서 개요
### 1.1 목적 및 배경
### 1.2 적용 범위
### 1.3 용어 정의

## 2. 제품 및 사용자 분석
### 2.1 제품 개요
### 2.2 사용자 세그먼트

## 3. VOC 분석 결과
### 3.1 수집 현황
### 3.2 카테고리별 분석
### 3.3 핵심 불편사항

## 4. 기능 요구사항
(카테고리별 상세 요구사항, 우선순위 명시)

## 5. 비기능 요구사항
### 5.1 성능 (수치 포함)
### 5.2 보안
### 5.3 사용성
### 5.4 신뢰성

## 6. 제약사항 및 가정

## 7. 개선 로드맵

## 8. 검토 및 승인"""
