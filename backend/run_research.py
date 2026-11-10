
import asyncio

from agents import Runner
from dotenv import load_dotenv

from app.agents.research_agent import research_agent


async def main():
    load_dotenv()

    company_info = """
    Company: Waitrose
    Website: https://www.waitrose.com
    Industry: UK Supermarket Retail
    Target Role: Operations Manager

    Research the company using public web sources.
    Identify verified information and potential
    outreach opportunities.
    """

    result = await Runner.run(
        research_agent,
        company_info,
    )


    # Inspect web search tool calls
    web_search_calls = [
        item
        for item in result.new_items
        if item.type == "tool_call_item"
        and getattr(item.raw_item, "type", None) == "web_search_call"
    ]

    print("\n--- TOOL USAGE ---")
    print(f"Web Search Calls: {len(web_search_calls)}")

    if not web_search_calls:
        raise RuntimeError(
            "Research Agent did not execute Web Search."
        )

    print("\n--- RESEARCH REPORT ---")
    print(result.final_output.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
