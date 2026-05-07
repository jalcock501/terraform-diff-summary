from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


@pytest.fixture
def resource_change(
):
    def build(
        address: str,
        resource_type: str,
        actions: list[str],
        before: Any,
        after: Any,
    ) -> dict[str, Any]:
        return {
            "address": address,
            "type": resource_type,
            "change": {
                "actions": actions,
                "before": before,
                "after": after,
            },
        }

    return build
