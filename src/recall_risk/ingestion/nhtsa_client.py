from __future__ import annotations

from typing import Any

import httpx


class NHTSAClient:
    """Small client for NHTSA public APIs.

    This is intentionally thin for the MVP. We will harden retries, rate limiting,
    schema validation, and checkpointing after the first end-to-end cycle works.
    """

    def __init__(
        self,
        base_url: str = "https://api.nhtsa.gov",
        vpic_base_url: str = "https://vpic.nhtsa.dot.gov/api",
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.vpic_base_url = vpic_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def get_recalls_by_vehicle(
        self,
        make: str,
        model: str,
        model_year: int,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/recalls/recallsByVehicle"
        params = {"make": make, "model": model, "modelYear": model_year}
        return self._get_results(url, params=params)

    def get_complaints_by_vehicle(
        self,
        make: str,
        model: str,
        model_year: int,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/complaints/complaintsByVehicle"
        params = {"make": make, "model": model, "modelYear": model_year}
        return self._get_results(url, params=params)

    def get_models_for_make_year(self, make: str, model_year: int) -> list[dict[str, Any]]:
        url = f"{self.vpic_base_url}/vehicles/GetModelsForMakeYear/make/{make}/modelyear/{model_year}"
        params = {"format": "json"}
        return self._get_results(url, params=params)

    def _get_results(self, url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
        results = payload.get("results") or payload.get("Results") or []
        if not isinstance(results, list):
            raise ValueError(f"Unexpected NHTSA response shape: {payload.keys()}")
        return results

