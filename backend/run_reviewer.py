
import asyncio
import json

from agents import Runner
from dotenv import load_dotenv

from app.agents.reviewer_agent import reviewer_agent


async def main():
    load_dotenv()

    email = {
        "subject": "Enhancing Customer Flow at Waitrose Stores",
        "body": (
            "Hi,\n\n"
            "I understand that delivering a seamless customer experience "
            "in busy retail environments like Waitrose stores is a key "
            "priority. Given that Waitrose is part of the John Lewis "
            "Partnership and has a strong reputation for quality service, "
            "efficient customer flow can further enhance this experience.\n\n"
            "Our queue management solutions help reduce waiting times.\n\n"
            "Would you be open to a brief conversation?\n\n"
            "Best regards,"
        ),
        "call_to_action": "Would you be open to a brief conversation?",
    }

    research = {
        "company_name": "Waitrose",
        "verified_findings": [
            "Waitrose is part of the John Lewis Partnership."
        ],
        "potential_pain_points": [
            "Maintaining operational efficiency across stores"
        ],
    }

    sender_offering = (
        "We provide queue management and customer flow solutions."
    )

    prompt = (
        "Review this email using the supporting context.\n\n"
        f"EMAIL:\n{json.dumps(email, indent=2)}\n\n"
        f"RESEARCH:\n{json.dumps(research, indent=2)}\n\n"
        f"SENDER OFFERING:\n{sender_offering}"
    )

    result = await Runner.run(reviewer_agent, prompt)

    print(result.final_output.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
