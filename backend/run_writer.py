
import asyncio

from agents import Runner
from dotenv import load_dotenv

from app.agents.writer_agent import writer_agent


async def main():
    load_dotenv()

    research = {
        "company_name": "Waitrose",
        "industry": "UK Supermarket Retail",
        "verified_findings": [
            {
                "claim": "Waitrose is part of the John Lewis Partnership.",
                "source_url": "https://www.johnlewispartnership.co.uk",
            }
        ],
        "potential_pain_points": [
            "Maintaining operational efficiency across stores"
        ],
        "suggested_solution": "Improve customer flow and queue management",
        "personalization_angle": (
            "Focus on customer experience in busy retail environments"
        ),
    }

    sender_offering = """
    We provide queue management and customer flow solutions
    for retail environments.
    """

    prompt = f"""
    COMPANY RESEARCH:
    {research}

    OUR OFFERING:
    {sender_offering}

    Write a B2B outreach email for an Operations Manager.
    """

    result = await Runner.run(writer_agent, prompt)

    print(result.final_output.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
