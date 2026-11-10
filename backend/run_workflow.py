import asyncio

from dotenv import load_dotenv

from app.workflows.outreach_workflow import run_outreach


async def main():
    load_dotenv()

    company_info = """
    Company: Waitrose
    Website: https://www.waitrose.com
    Industry: UK Supermarket Retail
    Target Role: Operations Manager

    Research the company using public web sources.
    """

    sender_offering = (
        "We provide queue management and customer flow "
        "solutions for retail environments."
    )

    result = await run_outreach(
        company_info=company_info,
        sender_offering=sender_offering,
    )

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
