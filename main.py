from fastapi import FastAPI, HTTPException, Request, Response, Body, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorCollection
from datetime import datetime, timedelta
import random
import os

from models import StudentBase, StudentCreate, AssessmentSubmission, AssessmentResult, Answer, Question, AdminLogin
from database import students_collection, questions_collection, results_collection, otp_collection, admins_collection, get_db
from utils import generate_otp, calculate_scholarship, send_sms_otp, hash_password, verify_password, create_access_token
from bson import ObjectId

app = FastAPI(title="Skill Assessment Academy API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for demo purposes
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_db_client():
    # Seed Admin if none exist
    admin_count = await admins_collection.count_documents({})
    if admin_count == 0:
        default_admin = {
            "email": "admin@gradex.com",
            "password": hash_password("admin123")
        }
        await admins_collection.insert_one(default_admin)
        print("Seeded default admin account: admin@gradex.com / admin123")

    # Seed initial questions if none exist
    count = await questions_collection.count_documents({})
    if count == 0:
        sample_questions = [
            {"text": "What does HVAC stand for?", "options": ["High Volume Air Cooling", "Heating, Ventilation, and Air Conditioning", "Home Vitality and Care", "None"], "correct_option": 1, "language": "English"},
            {"text": "Which tag is used to create a hyperlink in HTML?", "options": ["<link>", "<a>", "<div>", "<img>"], "correct_option": 1, "language": "English"},
            {"text": "What is 15% of 200?", "options": ["20", "30", "40", "50"], "correct_option": 1, "language": "English"},
            # Tamil Samples
            {"text": "HTML-ல் ஒரு ஹைப்பர்லிங்கை உருவாக்க எந்த டேக் பயன்படுத்தப்படுகிறது?", "options": ["<link>", "<a>", "<div>", "<img>"], "correct_option": 1, "language": "Tamil"},
            {"text": "கணினியின் மூளை என்று அழைக்கப்படுவது எது?", "options": ["RAM", "CPU", "GPU", "Hard Disk"], "correct_option": 1, "language": "Tamil"},
            {"text": "200-ல் 15% எவ்வளவு?", "options": ["20", "30", "40", "50"], "correct_option": 1, "language": "Tamil"}
        ]
        await questions_collection.insert_many(sample_questions)
        print("Seeded sample questions.")

@app.post("/api/admin/login")
async def admin_login(login: AdminLogin):
    admin = await admins_collection.find_one({"email": login.email})
    if not admin or not verify_password(login.password, admin["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_access_token({"sub": login.email})
    return {"token": token, "email": login.email}

@app.post("/api/register")
async def register_student(student: StudentCreate):
    existing = await students_collection.find_one({"phone": student.phone})
    if existing:
        await students_collection.update_one(
            {"phone": student.phone},
            {"$set": student.dict()}
        )
        return {"message": "Info updated. Please verify OTP."}
    
    student_dict = student.dict()
    student_dict["is_verified"] = False
    student_dict["created_at"] = datetime.utcnow()
    await students_collection.insert_one(student_dict)
    return {"message": "Registration successful. Please verify OTP."}

@app.post("/api/send-otp")
async def request_otp(phone: str = Body(..., embed=True)):
    otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    await otp_collection.update_one(
        {"phone": phone},
        {"$set": {"otp": otp, "expires_at": expires_at}},
        upsert=True
    )
    await send_sms_otp(phone, otp)
    return {"message": "OTP sent."}

@app.post("/api/verify-otp")
async def verify_otp(phone: str = Body(...), otp: str = Body(...)):
    stored_otp = await otp_collection.find_one({"phone": phone})
    if not stored_otp or stored_otp["otp"] != otp:
        raise HTTPException(status_code=400, detail="Invalid OTP.")
    
    if datetime.utcnow() > stored_otp["expires_at"]:
        raise HTTPException(status_code=400, detail="OTP expired.")
    
    await students_collection.update_one(
        {"phone": phone},
        {"$set": {"is_verified": True}}
    )
    await otp_collection.delete_one({"phone": phone})
    return {"message": "Verification successful."}

# Question Management CRUD
@app.get("/api/admin/questions")
async def get_all_questions():
    cursor = questions_collection.find()
    questions = []
    async for q in cursor:
        q["_id"] = str(q["_id"])
        questions.append(q)
    return questions

@app.post("/api/admin/questions")
async def add_question(question: Question):
    q_dict = question.dict(exclude={"id"})
    result = await questions_collection.insert_one(q_dict)
    return {"id": str(result.inserted_id)}

@app.put("/api/admin/questions/{q_id}")
async def update_question(q_id: str, question: Question):
    q_dict = question.dict(exclude={"id"})
    await questions_collection.update_one({"_id": ObjectId(q_id)}, {"$set": q_dict})
    return {"message": "Question updated"}

@app.delete("/api/admin/questions/{q_id}")
async def delete_question(q_id: str):
    await questions_collection.delete_one({"_id": ObjectId(q_id)})
    return {"message": "Question deleted"}

@app.post("/api/admin/questions/bulk")
async def bulk_add_questions(questions: list[Question]):
    docs = [q.dict(exclude={"id"}) for q in questions]
    if docs:
        await questions_collection.insert_many(docs)
    return {"message": f"Successfully added {len(docs)} questions"}

@app.get("/api/questions")
async def get_questions_by_lang(phone: str, language: str = "English"):
    student = await students_collection.find_one({"phone": phone})
    category = student.get("category", "School") if student else "School"
    
    cursor = questions_collection.aggregate([
        {"$match": {"language": language, "category": {"$in": [category, "Both"]}}},
        {"$sample": {"size": 20}}
    ])
    questions = []
    async for q in cursor:
        q["_id"] = str(q["_id"])
        questions.append(q)
    return questions

@app.post("/api/submit-assessment")
async def submit_assessment(submission: AssessmentSubmission):
    student = await students_collection.find_one({"phone": submission.phone, "is_verified": True})
    if not student:
        raise HTTPException(status_code=403, detail="Student not verified.")

    correct_count = 0
    for answer in submission.answers:
        question = await questions_collection.find_one({"_id": ObjectId(answer.question_id)})
        if question and question["correct_option"] == answer.selected_option:
            correct_count += 1
            
    total_questions = len(submission.answers)
    score_percentage = (correct_count / total_questions * 100) if total_questions > 0 else 0
    scholarship_percentage = calculate_scholarship(score_percentage)
    
    result = {
        "student_phone": submission.phone,
        "score_percentage": score_percentage,
        "scholarship_percentage": scholarship_percentage,
        "language": student.get("language", "English"),
        "timestamp": datetime.utcnow()
    }
    await results_collection.insert_one(result)
    return {"score": score_percentage, "scholarship": scholarship_percentage}

@app.get("/api/admin/results")
async def get_all_results():
    all_students = []
    cursor = students_collection.find().sort("created_at", -1)
    async for student in cursor:
        student["_id"] = str(student["_id"])
        result = await results_collection.find_one({"student_phone": student["phone"]})
        entry = {
            "_id": student["_id"],
            "student_name": student["name"],
            "student_email": student["email"],
            "student_phone": student["phone"],
            "student_category": student.get("category", "N/A"),
            "language": student.get("language", "English"),
            "score_percentage": result.get("score_percentage", 0) if result else 0,
            "scholarship_percentage": result.get("scholarship_percentage", 0) if result else 0,
            "timestamp": result.get("timestamp", student["created_at"]) if result else student["created_at"],
            "status": "Completed" if result else "Not Started"
        }
        all_students.append(entry)
    return all_students

@app.delete("/api/admin/students/{s_id}")
async def delete_student(s_id: str):
    student = await students_collection.find_one({"_id": ObjectId(s_id)})
    if student:
        # Delete related results too
        await results_collection.delete_many({"student_phone": student["phone"]})
        await students_collection.delete_one({"_id": ObjectId(s_id)})
    return {"message": "Student record deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
