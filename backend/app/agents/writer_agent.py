
from agents import Agent
from pydantic import BaseModel, Field


class EmailDraft(BaseModel):
    subject: str = Field(min_length=5, max_length=120)
    body: str = Field(min_length=50)
    call_to_action: str = Field(min_length=5)


writer_agent = Agent(
    name="Cold Email Writer",
    model="gpt-4.1-mini",
    instructions="""
    You are an expert B2B cold email copywriter.

    Write a personalized, professional outreach email
    using the supplied company research.

    Requirements:
    - Write in natural, concise English.
    - Keep the email body around 100-150 words.
    - Start with a relevant personalized opening.
    - Explain one clear potential business benefit.
    - Finish with a low-pressure call to action.
    - Avoid generic marketing language.
    - Do not invent facts, statistics or past relationships.
    - Never present potential pain points as confirmed facts.
    - Do not invent the sender's company or capabilities.
    - Use only the sender's explicitly provided offering.

    Return the email in the required structured format.
    """,
    output_type=EmailDraft,
)
