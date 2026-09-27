"""IBM watsonx.ai client — System 2 remediation brain for GhostBuster.

Uses the official ``ibm-watsonx-ai`` SDK when installed, otherwise the
plain HTTPS REST API (only ``requests`` is required). When no credentials
are configured, ``available`` is False and callers fall back to built-in
rule templates — so ``--demo`` and offline runs never break.

Env vars (see .env.example):
    WATSONX_API_KEY    IBM Cloud IAM API key            (required for live)
    WATSONX_PROJECT_ID watsonx.ai project ID            (required for live)
    WATSONX_URL        region endpoint (default: us-south)
    WATSONX_MODEL_ID   foundation model (default: ibm/granite-3-8b-instruct)

Live usage needs:  pip install ibm-watsonx-ai   (optional — REST works anyway)
Docs: https://ibm.github.io/watsonx-ai-python-sdk/
"""

import os

import requests

DEFAULT_URL = "https://us-south.ml.cloud.ibm.com"
DEFAULT_MODEL = "ibm/granite-3-8b-instruct"
_API_VERSION = "2023-05-29"


class WatsonxClient:
    """Thin wrapper over watsonx.ai foundation-model inference."""

    def __init__(self, api_key: str = "", project_id: str = "",
                 url: str = "", model_id: str = ""):
        self.api_key = api_key or os.environ.get("WATSONX_API_KEY", "")
        self.project_id = project_id or os.environ.get("WATSONX_PROJECT_ID", "")
        self.url = (url or os.environ.get("WATSONX_URL", "") or DEFAULT_URL).rstrip("/")
        self.model_id = model_id or os.environ.get("WATSONX_MODEL_ID", "") or DEFAULT_MODEL
        if self.available:
            print(f"[WatsonxClient] Live mode — model {self.model_id}")
        else:
            print("[WatsonxClient] No credentials — rule-template fallback "
                  "(set WATSONX_API_KEY + WATSONX_PROJECT_ID for live Granite)")

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.project_id)

    # ── public API ───────────────────────────────────────────────────

    def suggest_fix(self, finding: dict) -> str:
        """Return a 2–4 line remediation for one SlopWatch finding.

        Raises RuntimeError when live inference fails so callers can
        fall back to rule templates.
        """
        prompt = (
            "You are a senior code reviewer in a CI merge gate. "
            "Given one static-analysis finding, reply with 2-4 lines: "
            "what is wrong and the minimal code fix. No preamble.\n\n"
            f"Scanner: {finding.get('scanner')}\n"
            f"Rule: {finding.get('rule', finding.get('verdict', ''))}\n"
            f"Location: {finding.get('file')}:{finding.get('line')}\n"
            f"Finding: {finding.get('message')}\n"
            f"Offending code: {finding.get('code', '')}\n"
        )
        try:
            return self._generate_sdk(prompt)
        except ImportError:
            return self._generate_rest(prompt)

    # ── backends ─────────────────────────────────────────────────────

    def _generate_sdk(self, prompt: str) -> str:
        from ibm_watsonx_ai import Credentials  # type: ignore
        from ibm_watsonx_ai.foundation_models import ModelInference  # type: ignore

        model = ModelInference(
            model_id=self.model_id,
            credentials=Credentials(api_key=self.api_key, url=self.url),
            project_id=self.project_id,
        )
        return str(model.generate_text(prompt=prompt)).strip()

    def _generate_rest(self, prompt: str) -> str:
        token = self._iam_token()
        r = requests.post(
            f"{self.url}/ml/v1/text/generation?version={_API_VERSION}",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "model_id": self.model_id,
                "input": prompt,
                "parameters": {"decoding_method": "greedy", "max_new_tokens": 300},
                "project_id": self.project_id,
            },
            timeout=60,
        )
        r.raise_for_status()
        return str(r.json()["results"][0]["generated_text"]).strip()

    def _iam_token(self) -> str:
        r = requests.post(
            "https://iam.cloud.ibm.com/identity/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                  "apikey": self.api_key},
            timeout=30,
        )
        r.raise_for_status()
        return str(r.json()["access_token"])
