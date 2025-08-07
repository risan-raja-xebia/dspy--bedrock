from pydantic import BaseModel, Field
from typing import Annotated


class BulletPoint(BaseModel):
    point: Annotated[
        str,
        Field(
            ...,
            description="A single concise statement detailing any functionality, scenario or information about a topic or use case",
        ),
    ]


class SystemPrompt(BaseModel):
    role: Annotated[
        list[BulletPoint],
        Field(..., description="Enhanced and verbose description of the role of the prompt."),
    ]
    objective: Annotated[
        list[BulletPoint],
        Field(
            ..., description="Enhanced and verbose description of the objective of the agent described in 4 to 5 sentences"
        ),
    ]
    model_instructions: Annotated[
        list[BulletPoint],
        Field(..., description="The model instructions limited to 5 points"),
    ]
    response_instructions: Annotated[
        list[BulletPoint],
        Field(..., description="The response instructions limited to 4 points"),
    ]


class PromptInput(BaseModel):
    body: Annotated[str, Field(..., description="The email body")]
    subject: Annotated[str, Field(..., description="The email subject")]


class DomainCategory(BaseModel):
    type: Annotated[
        str,
        Field(
            ...,
            description="Defines the specific business function or the primary nature of the risk associated with the email. It serves as the main classifier that refines the broader Domain, grouping communications by their core purpose.",
        ),
    ]
    info: Annotated[
        list[BulletPoint],
        Field(
            ...,
            description="Offers a concise definitions and concrete examples of the scenarios that fall under the specified Type",
        ),
    ]


class PositiveScenario(BaseModel):
    domain: Annotated[
        str,
        Field(
            ...,
            description="The Domain is the highest-level classifier, grouping emails by their fundamental purpose or strategic importance, such as commercial, business development, or information security risk.",
        ),
    ]
    categories: Annotated[
        list[DomainCategory],
        Field(
            ...,
            description="A list of categories that further specify the business function or risk type within the domain, each with definitions and examples.",
        ),
    ]


class ConfidenceScoreGuidelines(BaseModel):
    positve_classication_score_guidelines: Annotated[
        list[BulletPoint],
        Field(
            ...,
            description="The positive classification score guidelines used while assigning the confidence score in case of positive classification",
        ),
    ]
    negative_classication_score_guidelines: Annotated[
        list[BulletPoint],
        Field(
            ...,
            description="The negative classification score guidelines used while assigning the confidence score in case of negative classification",
        ),
    ]


class AnalysisInstructions(BaseModel):
    instructions: Annotated[
        list[BulletPoint],
        Field(
            ...,
            description="The instructions that needs to be followed for the analysis of the email",
        ),
    ]
    confidence_score_assignment: Annotated[
        ConfidenceScoreGuidelines,
        Field(..., description="The confidence score assignment from 0.0 to 1.0"),
    ]


class PromptOutput(BaseModel):
    confidence_score: Annotated[float, Field(..., description="The confidence score")]
    classification_label: Annotated[
        str, Field(..., description="The classification label")
    ]
    classification_rationale: Annotated[
        str, Field(..., description="The classification rationale")
    ]


class Sample(BaseModel):
    prompt_input: Annotated[
        PromptInput,
        Field(
            ...,
            description="The sample data that the prompt needs to process"
        ),
    ]
    prompt_output: Annotated[
        PromptOutput,
        Field(
            ...,
            description="The output of the prompt"
        ),
    ]


class UserPrompt(BaseModel):
    positive_scenarios: Annotated[
        list[PositiveScenario],
        Field(..., description="List of the Positive Scenarios Identified"),
    ]
    analysis_instructions: Annotated[
        AnalysisInstructions, Field(..., description="The analysis instructions")
    ]
    output_instructions: Annotated[
        list[BulletPoint],
        Field(
            ...,
            description="The output instructions that are needed to output the object as JSON object",
        ),
    ]
    examples: Annotated[list[Sample], Field(..., description="The examples")]


class Prompt(BaseModel):
    system_prompt: Annotated[SystemPrompt, Field(..., description="The system prompt")]
    user_prompt: Annotated[UserPrompt, Field(..., description="The user prompt")]
