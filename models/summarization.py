from pydantic import BaseModel, Field
from typing import Optional
import pymysql
from pymysql.cursors import DictCursor


# this is what I return to the user
class Summarization(BaseModel):
    patient_id: Optional[int] = Field(default=None, description="ID of the patient associated with the text")
    summarization_id: Optional[int] = Field(default=None, description="Unique identifier for the summarization entry")
    status: int = Field(description="Numeric status code (e.g., 200 for OK)")
    status_message: str = Field(description="Human-readable status message")
    summary: Optional[str] = Field(default=None, description="The summarized version of the text")

item = Summarization(status=200,  status_message="OK",
                    summary="This is a summary of a long paragraph.",
                    patient_id=123,
                    summarization_id=456)

print(item.model_dump())
# this is used for requests
# creating a new summarization
class SummarizationCreate(BaseModel):
    patient_id: int = Field(..., description="ID of the patient associated with the text")
    text: str = Field(..., description="Text to be summarized")

# deleting a summarization
class SummarizationDelete(BaseModel):
    id: int = Field(..., description="Unique identifier for the summarization entry to delete")

# reading a summarization
class SummarizationRead(BaseModel):
    summarization_id: int = Field(..., description="Unique identifier for the summarization entry to read")
    summary: str = Field(..., description="The summarized text")
    
# updating a summarization
class SummarizationUpdate(BaseModel):
    id: int = Field(..., description="Unique identifier for the summarization entry to update")
    summary: str = Field(..., description="The updated summarized text")
    input_text: str = Field(..., description="input text")