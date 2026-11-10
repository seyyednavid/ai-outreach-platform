
import asyncio
import json

from agents import Runner
from dotenv import load_dotenv

from app.agents.improver_agent import improver_agent


async def main():
    load_dotenv()

    original_email = {
        "subject": "Enhancing Customer Flow at Waitrose Stores",
        "body": (
            "Hi,\n\n"
            "I understand that delivering a seamless customer experience "
            "in busy retail environments like Waitrose stores is a key "
            "priority. Given that Waitrose is part of the John Lewis "
            "Partnership, efficient customer flow can further enhance "
            "this experience.\n\n"
            "Our queue management solutions help reduce waiting times.\n\n"
            "Would you be open to a brief conversation?\n\n"
            "Best regards,"
        ),
        "call_to_action": "Would you be open to a brief conversation?",
    }

    review = {
        "overall_score": 7.5,
        "approved": False,
        "improvement_suggestions": [
            "Use a more specific greeting.",
            "Explain the customer flow benefit more clearly.",
            "Improve the CTA.",
        ],
    }

    research = {
        "company_name": "Waitrose",
        "verified_findings": [
            "Waitrose is part of the John Lewis Partnership."
        ],
        "potential_pain_points": [
            "Managing customer flow in busy retail environments"
        ],
    }

    sender_offering = (
        "We provide queue management and customer flow solutions "
        "for retail environments."
    )

    prompt = (
        "Improve this email using the feedback and context.\n\n"
        f"ORIGINAL EMAIL:\n{json.dumps(original_email, indent=2)}\n\n"
        f"REVIEW:\n{json.dumps(review, indent=2)}\n\n"
        f"RESEARCH:\n{json.dumps(research, indent=2)}\n\n"
        f"SENDER OFFERING:\n{sender_offering}"
    )

    result = await Runner.run(improver_agent, prompt)

    print(result.final_output.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
