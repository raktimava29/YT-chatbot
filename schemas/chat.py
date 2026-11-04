from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    video_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    
    @field_validator("video_id", "question")
    @classmethod
    def reject_whitespace(cls, value: str):
        value = value.strip()
        
        if not value:
            raise ValueError("Field cannot be empty")
            
        return value