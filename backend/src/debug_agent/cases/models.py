from pydantic import BaseModel, Field


class AnswerItem(BaseModel):
    box_id: int
    student_answer: str


class AnswerSet(BaseModel):
    answers: list[AnswerItem]


class ClassificationOutput(BaseModel):
    label: str
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class Prediction(BaseModel):
    trial: int
    raw_output: str
    score: int = Field(ge=0, le=1)


class HumanNotes(BaseModel):
    debug_status: str = ""
    root_cause: str = ""


class BoxRegion(BaseModel):
    box_id: int
    x: int
    y: int
    width: int
    height: int
    unit: str = "pixel"
    label: str = ""


class DebugCase(BaseModel):
    case_id: str
    task_type: str = "handwriting_ocr"
    image_uri: str
    prompt: str
    golden_answer: AnswerSet
    expected_output: dict[str, object] = Field(default_factory=dict)
    output_schema: dict[str, object] = Field(default_factory=dict)
    scoring_standard: str
    predictions: list[Prediction]
    avg_score: float = Field(ge=0.0, le=1.0)
    human_notes: HumanNotes = Field(default_factory=HumanNotes)
    box_regions: list[BoxRegion] = Field(default_factory=list)


DetectionOutput = AnswerSet
DetectionPrediction = Prediction
DetectionRegion = BoxRegion
DetectionCase = DebugCase
