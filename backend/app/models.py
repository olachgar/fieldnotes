from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoteInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=20_000)

    @field_validator("name", "subject")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("This field cannot be blank")
        return value


class NoteCreate(NoteInput):
    pass


class NoteUpdate(NoteInput):
    pass


class Note(BaseModel):
    id: str
    name: str
    date: datetime
    subject: str
