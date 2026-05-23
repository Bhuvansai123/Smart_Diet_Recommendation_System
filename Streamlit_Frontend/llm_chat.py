"""
Deployment-safe chat wrapper.

Default behavior on Streamlit Community Cloud:
- Uses the lightweight FAQ-based chatbot from llm_chat_lite.py
- Avoids installing/loading torch + transformers

Optional local behavior:
- Set environment variable USE_LOCAL_LLM=1 and install torch/transformers
  if you want to use the TinyLlama-based chatbot locally.
"""

from __future__ import annotations

import os

USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "0") == "1"

if USE_LOCAL_LLM:
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        import warnings

        warnings.filterwarnings("ignore")

        _model = None
        _tokenizer = None
        _device = None

        def load_model():
            global _model, _tokenizer, _device
            if _model is not None and _tokenizer is not None:
                return _model, _tokenizer, _device

            model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
            _device = "cuda" if torch.cuda.is_available() else "cpu"
            _tokenizer = AutoTokenizer.from_pretrained(model_name)
            if _tokenizer.pad_token is None:
                _tokenizer.pad_token = _tokenizer.eos_token

            _model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if _device == "cuda" else torch.float32,
                device_map="auto" if _device == "cuda" else None,
                low_cpu_mem_usage=True,
            )
            if _device == "cpu":
                _model = _model.to(_device)
            _model.eval()
            return _model, _tokenizer, _device

        def generate_chat_answer(context_text: str, history_text: str, user_message: str) -> str:
            try:
                model, tokenizer, device = load_model()
                system_prompt = (
                    "You are a helpful diet and nutrition assistant. "
                    "You answer questions about recommended recipes, ingredients, substitutions, "
                    "and simple modifications. Keep your answers concise and practical. "
                    "If a question is unrelated to food or nutrition, politely say you don't know."
                )
                prompt = f"<|system|>\n{system_prompt}\n\nCurrent Recommendations:\n{context_text}\n</s>\n"
                if history_text.strip():
                    history_lines = history_text.strip().split("\n")
                    recent_history = history_lines[-6:] if len(history_lines) > 6 else history_lines
                    for line in recent_history[:-1]:
                        if line.startswith("User:"):
                            prompt += f"<|user|>\n{line[5:].strip()}</s>\n"
                        elif line.startswith("Assistant:"):
                            prompt += f"<|assistant|>\n{line[10:].strip()}</s>\n"
                prompt += f"<|user|>\n{user_message}</s>\n<|assistant|>\n"
                inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1536)
                inputs = {k: v.to(device) for k, v in inputs.items()}
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=256,
                        temperature=0.7,
                        top_p=0.9,
                        do_sample=True,
                        pad_token_id=tokenizer.pad_token_id,
                        eos_token_id=tokenizer.eos_token_id,
                        repetition_penalty=1.1,
                    )
                generated_tokens = outputs[0][inputs["input_ids"].shape[1]:]
                response = tokenizer.decode(generated_tokens, skip_special_tokens=True).strip()
                if response.startswith(user_message):
                    response = response[len(user_message):].strip()
                return response or "I'm not sure how to answer that. Could you rephrase your question?"
            except Exception:
                from llm_chat_lite import generate_chat_answer as lite_generate_chat_answer
                return lite_generate_chat_answer(context_text, history_text, user_message)

        def clear_model_cache():
            global _model, _tokenizer, _device
            if _model is not None:
                del _model
                _model = None
            if _tokenizer is not None:
                del _tokenizer
                _tokenizer = None
            _device = None
            if 'torch' in globals() and torch.cuda.is_available():
                torch.cuda.empty_cache()

    except Exception:
        from llm_chat_lite import generate_chat_answer  # type: ignore

        def clear_model_cache():
            return None
else:
    from llm_chat_lite import generate_chat_answer  # type: ignore

    def clear_model_cache():
        return None
