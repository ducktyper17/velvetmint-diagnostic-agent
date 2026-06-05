"""Idempotent Phoenix seed script.

Pushes:
  1. Six judge prompts (one per scoring dimension) into Phoenix as versioned
     prompt objects (each becomes a new version on every run if the template
     changed; same content = no-op).
  2. The 30 seed scenarios into a Phoenix dataset.
  3. The initial (deliberately-flawed) VelvetMint SUT system prompt as
     ``sut-velvetmint-support`` prompt v1.

The QA agent reads everything back through Phoenix MCP at runtime, so this
script is the only place Phoenix is mutated outside the agent's loop.

Run:
    cd 02-arize-mystery-shopper/agent
    uv run python ../scripts/seed_phoenix.py
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from pathlib import Path

AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

from dotenv import load_dotenv

load_dotenv(AGENT_DIR / ".env")

from judge_prompts import ALL_JUDGE_PROMPTS  # noqa: E402
from scenarios import DEFAULT_SCENARIO_SET  # noqa: E402
from sut.prompt import VELVETMINT_SUT_INSTRUCTION  # noqa: E402


def _phoenix_client():
    """Lazy-import phoenix to keep the file importable without it.

    Phoenix v16 split the REST client out into ``phoenix.client.Client``.
    We pass the endpoint + api key explicitly so the script works without
    relying on Phoenix's own env-var resolution.
    """

    try:
        from phoenix.client import Client
    except ImportError as exc:  # pragma: no cover
        sys.exit(
            "phoenix.client not installed. Run `make setup` in the agent dir first.\n"
            f"(import error: {exc})"
        )
    base_url = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").strip()
    api_key = (os.environ.get("PHOENIX_API_KEY") or "").strip()
    return Client(base_url=base_url, api_key=api_key)


def _upload_judge_prompts(client) -> None:
    """Upsert each judge prompt as a Phoenix prompt object.

    Phoenix v16 API: PromptVersion(messages, *, model_name, model_provider,
    template_format). We use F_STRING because the templates use ``{conversation}``
    style placeholders; literal braces in the prompts already use ``{{...}}``.
    """

    from phoenix.client.types import PromptVersion

    print(f"\n[1/3] Upserting {len(ALL_JUDGE_PROMPTS)} judge prompts...")
    for jp in ALL_JUDGE_PROMPTS:
        try:
            version = PromptVersion(
                [{"role": "user", "content": jp.template}],
                model_name=os.environ.get("JUDGE_MODEL", "gemini-2.5-flash"),
                model_provider="GOOGLE",
                description=jp.description,
                template_format="F_STRING",
            )
            client.prompts.create(
                name=jp.name,
                version=version,
                prompt_description=jp.description,
            )
            print(f"    upsert ok: {jp.name}")
        except Exception as exc:  # noqa: BLE001
            print(f"    upsert WARN ({jp.name}): {exc!r}")


def _upload_scenarios_dataset(client, dataset_name: str) -> None:
    """Push the scenarios as a Phoenix dataset.

    Each scenario becomes one dataset row. The fields land on the row's
    ``input`` and ``metadata`` so the QA agent can resolve them via
    ``get-dataset-examples`` and feed them to ``run_scenario``.
    """

    print(f"\n[2/3] Pushing {len(DEFAULT_SCENARIO_SET)} scenarios → dataset '{dataset_name}'...")
    inputs: list[dict] = []
    metadata: list[dict] = []
    for s in DEFAULT_SCENARIO_SET:
        scen = asdict(s)
        inputs.append(
            {
                "scenario_id": scen["id"],
                "opening_message": scen["opening_message"],
            }
        )
        metadata.append(
            {
                "title": scen["title"],
                "persona": scen["persona"],
                "must_say": scen["must_say"],
                "must_not_say": scen["must_not_say"],
                "stop_when": scen["stop_when"],
                "primary_dimensions": scen["primary_dimensions"],
                "tags": scen["tags"],
            }
        )

    try:
        client.datasets.create_dataset(
            name=dataset_name,
            inputs=inputs,
            metadata=metadata,
            dataset_description="VelvetMint customer-support scenarios for the QA agent.",
        )
        print(f"    dataset upload ok: {dataset_name}")
    except Exception as exc:  # noqa: BLE001
        print(f"    dataset upload WARN: {exc!r}")


def _upload_sut_prompt(client, prompt_name: str) -> None:
    """Upsert the seed SUT system prompt as ``sut-velvetmint-support`` v1."""

    from phoenix.client.types import PromptVersion

    print(f"\n[3/3] Upserting SUT system prompt as '{prompt_name}'...")
    try:
        version = PromptVersion(
            [{"role": "system", "content": VELVETMINT_SUT_INSTRUCTION}],
            model_name=os.environ.get("SUT_MODEL", "gemini-2.5-flash"),
            model_provider="GOOGLE",
            description="Seed VelvetMint SUT system prompt (intentionally flawed).",
            template_format="NONE",
        )
        client.prompts.create(
            name=prompt_name,
            version=version,
            prompt_description="VelvetMint customer-support SUT system prompt.",
        )
        print(f"    upsert ok: {prompt_name}")
    except Exception as exc:  # noqa: BLE001
        print(f"    upsert WARN ({prompt_name}): {exc!r}")


def main() -> None:
    api_key = (os.environ.get("PHOENIX_API_KEY") or "").strip()
    if not api_key:
        sys.exit(
            "PHOENIX_API_KEY is not set; copy .env.example to .env and fill in "
            "your Phoenix Cloud key (px_live_...)."
        )

    endpoint = (os.environ.get("PHOENIX_COLLECTOR_ENDPOINT") or "").strip()
    if not endpoint:
        sys.exit("PHOENIX_COLLECTOR_ENDPOINT is unset. Must include /s/<your-space>.")

    dataset_name = os.environ.get("PHOENIX_SCENARIO_DATASET_NAME", "velvetmint-support.scenarios")
    sut_prompt_name = os.environ.get("PHOENIX_SUT_PROMPT_NAME", "sut-velvetmint-support")

    print("=" * 60)
    print("Phoenix seed script (idempotent)")
    print("=" * 60)
    print(f"  endpoint      : {endpoint}")
    print(f"  dataset       : {dataset_name}")
    print(f"  sut prompt    : {sut_prompt_name}")
    print(f"  judge prompts : {len(ALL_JUDGE_PROMPTS)}")
    print(f"  scenarios     : {len(DEFAULT_SCENARIO_SET)}")

    client = _phoenix_client()
    _upload_judge_prompts(client)
    _upload_scenarios_dataset(client, dataset_name)
    _upload_sut_prompt(client, sut_prompt_name)

    print("\nDone. Visit your Phoenix workspace to confirm objects exist.")


if __name__ == "__main__":
    main()
