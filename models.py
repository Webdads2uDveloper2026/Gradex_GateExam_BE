from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime

class StudentBase(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    category: str = Field(..., description="School or College")
    language: str = Field(default="English", description="English or Tamil")

class StudentCreate(StudentBase):
    pass

class Student(StudentBase):
    id: str = Field(alias="_id")
    is_verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Question(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    text: str
    options: List[str]
    correct_option: int # Index of the correct option
    language: str = Field(default="English")
    category: str = "Both" # School, College, or Both

class Answer(BaseModel):
    question_id: str
    selected_option: int

class AssessmentSubmission(BaseModel):
    phone: str
    answers: List[Answer]

class AssessmentResult(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    student_phone: str
    score_percentage: float
    scholarship_percentage: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AdminUser(BaseModel):
    email: EmailStr
    password: str

class AdminLogin(BaseModel):
    email: EmailStr
    password: str
