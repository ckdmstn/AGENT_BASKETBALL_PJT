import json
from urllib.parse import urlsplit

import requests
from pydantic import ValidationError

from backend.agent.prompts import COMMON, PROMPTS
from backend.config import Settings


class LLMError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__('LLM 요청 또는 구조화 응답을 확인할 수 없습니다.')


class JsonLLM:
    """OpenAI-compatible JSON mode with local Pydantic validation; no retries hidden from events."""
    def __init__(self, settings: Settings):
        self.settings = settings

    def complete(self, stage, payload, output_model):
        s = self.settings
        if not s.llm_key or not s.llm_model:
            raise LLMError('MISSING_LLM_CONFIG')
        url = urlsplit(s.llm_base_url)
        if url.scheme != 'https' or url.username or url.password or url.query or url.fragment:
            raise LLMError('INVALID_LLM_CONFIG')
        messages = [
            {'role': 'system', 'content': COMMON + '\n' + PROMPTS[stage] + '\nJSON schema:\n' + json.dumps(output_model.model_json_schema(), ensure_ascii=False)},
            {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False, default=str)},
        ]
        try:
            r = requests.post(s.llm_base_url + '/chat/completions', headers={'Authorization': 'Bearer ' + s.llm_key},
                              json={'model': s.llm_model, 'messages': messages, 'response_format': {'type': 'json_object'},
                                    'max_completion_tokens': 1800}, timeout=(5, 45))
            if r.status_code != 200:
                raise LLMError('LLM_UPSTREAM_ERROR')
            content = r.json()['choices'][0]['message']['content']
            return output_model.model_validate_json(content)
        except requests.Timeout:
            raise LLMError('LLM_TIMEOUT') from None
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError, ValidationError):
            raise LLMError('LLM_INVALID_RESPONSE') from None
