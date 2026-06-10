from pydantic import BaseModel, Field


class AnswerItem(BaseModel):
    box_id: int
    student_answer: str


class AnswerSet(BaseModel):
    answers: list[AnswerItem]


class Prediction(BaseModel):
    trial: int
    raw_output: str
    score: int = Field(ge=0, le=1)


class HumanNotes(BaseModel):
    debug_status: str = ""
    root_cause: str = ""


class DebugCase(BaseModel):
    case_id: str
    image_uri: str
    prompt: str
    golden_answer: AnswerSet
    scoring_standard: str
    predictions: list[Prediction]
    avg_score: float = Field(ge=0.0, le=1.0)
    human_notes: HumanNotes = Field(default_factory=HumanNotes)
