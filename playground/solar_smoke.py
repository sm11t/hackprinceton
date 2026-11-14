# /// script
# requires-python = ">=3.12"
# dependencies = ["langchain-upstage==0.7.7"]
# ///
"""Exercise Solar Mini 4 through ChatUpstage with synthetic evidence only."""
import json
import os

from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langchain_upstage import ChatUpstage
from pydantic import BaseModel, ConfigDict


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str
    household_count: int
    demand_verified: bool


@tool
def read_demo_area(area_id: str) -> str:
    """Read a synthetic area record by its identifier."""
    if area_id != "demo-area":
        raise ValueError("Unexpected synthetic area identifier")
    return json.dumps({"source_id": "fixture-1", "household_count": 1200,
                       "demand_verified": False})


def main():
    model = ChatUpstage(
        api_key=os.environ["UPSTAGE_API_KEY"],
        model="solar-mini4",
        reasoning_effort="none",
        timeout=20,
        max_retries=1,
    )
    prompt = HumanMessage(content=(
        "Use read_demo_area once with area_id demo-area. "
        "Report its source identifier, household count and demand_verified value."
    ))
    response = model.bind_tools([read_demo_area]).invoke([prompt])
    calls = response.tool_calls
    if len(calls) != 1 or calls[0]["name"] != read_demo_area.name or not calls[0]["id"]:
        raise AssertionError("Expected one supported tool call with an ID")
    evidence = read_demo_area.invoke(calls[0]["args"])
    result = model.with_structured_output(Finding, method="json_schema", strict=True).invoke([
        prompt, response, ToolMessage(content=evidence, tool_call_id=calls[0]["id"])
    ])
    if result.model_dump() != json.loads(evidence):
        raise AssertionError("Structured output did not match the synthetic evidence")
    print("PASS: solar-mini4 tool selection, tool response replay and strict structured output")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # Keep provider request details and credentials out of terminal output.
        print(f"FAIL: {type(error).__name__}, HTTP status {getattr(error, 'status_code', None)}")
        raise SystemExit(1) from None
