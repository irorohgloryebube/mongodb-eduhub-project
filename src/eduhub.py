

from pymongo.collection import ReturnDocument  
import time, functools
import re 
import pymongo
from pymongo import MongoClient
from datetime import datetime , timedelta
from bson.objectid import ObjectId
from faker import Faker 
import random
from pprint import pprint
from random import choice
import bson
import uuid
from pymongo.errors import (
     WriteError,DuplicateKeyError
)

# %%
def get_db(uri="mongodb://localhost:27017/", db_name="eduhub_db"):
    """Return a MongoDB database handle."""
    return MongoClient(uri)[db_name]

db = get_db()



# %%
fake = Faker()
client = MongoClient('mongodb://localhost:27017')

# %%
db = client['eduhub_db']
db

# %%
# Create collections
users_collection = db["users"]
courses_collection = db["courses"]
enrollments_collection = db["enrollments"]
lessons_collection = db["lessons"]
assignments_collection = db["assignments"]
submissions_collection = db["submissions"]


# USER VALIDATOR COLLECTION AND SCHEMA
user_validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["userId", "email", "firstName", "lastName", "role", "dateJoined", "profile", "isActive"],
        "properties": {
            "userId": {"bsonType": "string"},
            "email": {"bsonType": "string", "pattern": "^.+@.+$"},
            "firstName": {"bsonType": "string"},
            "lastName": {"bsonType": "string"},
            "role": {"enum": ["student", "instructor"]},
            "dateJoined": {"bsonType": "date"},
            "profile": {
                "bsonType": "object",
                "required": ["bio", "avatar", "skills"],
                "properties": {
                    "bio": {"bsonType": "string"},
                    "avatar": {"bsonType": "string"},
                    "skills": {
                        "bsonType": "array",
                        "items": {"bsonType": "string"}
                    }
                }
            },
            "isActive": {"bsonType": "bool"}
        }
    }
}

# Recreate users collection with the validator
db.create_collection("users", validator=user_validator)


# %%
#  Avatar pools
student_avatars = [
    "https://i.pravatar.cc/128?img=15",
    "https://i.pravatar.cc/128?img=22",
    "https://i.pravatar.cc/128?img=34",
    "https://i.pravatar.cc/128?img=47",
]

instructor_avatars = [
    "https://i.pravatar.cc/128?img=53",
    "https://i.pravatar.cc/128?img=68",
    "https://i.pravatar.cc/128?img=72",
    "https://i.pravatar.cc/128?img=91",
]

#  Bios & skills
bio = [
  "Just a chill person who loves good food, long walks, and binge‑watching documentaries on weekends. Always down for spontaneous adventures.",
  "Coffee lover , bookworm , and part‑time plant parent. Life’s messy but I’m vibing through it.",
  "Trying to figure out adulthood one day at a time. I cook, I nap, and I listen to way too many true crime podcasts.",
  "I like rainy days, loud music, and people who laugh at their own jokes. Currently learning how to not kill my houseplants.",
  "Small‑town soul with big‑city dreams. I believe in kindness, good playlists, and late‑night deep talks.",
  "Dog lover , taco enthusiast , and someone who presses 'snooze' way too often. Living life soft and slow."
]

skills = ["python", "java", "power bi", "mongodb", "cloud computing", "docker"]

# 15 students + 5 instructors
roles = ["student"] * 15 + ["instructor"] * 5
random.shuffle(roles)        # randomize the order a bit

users = []
student_idx = instructor_idx = 0

for role in roles:
    avatar_url = (
        student_avatars[student_idx % len(student_avatars)]
        if role == "student"
        else instructor_avatars[instructor_idx % len(instructor_avatars)]
    )

    # Increment whichever pointer we used
    if role == "student":
        student_idx += 1
    else:
        instructor_idx += 1

    users.append({
        "_id": ObjectId(), 
        "userId": str(uuid.uuid4()),
        "email": fake.unique.email(),
        "firstName": fake.first_name(),
        "lastName": fake.last_name(),
        "role": role,
        "dateJoined": fake.date_time_between(start_date="-1y", end_date="now"),
        "profile": {
            "bio": random.choice(bio),
            "avatar": avatar_url,
            "skills": random.sample(skills, k=random.randint(1, 3))
        },
        "isActive": True
    })

#  Insert into MongoDB
insert_result = db.users.insert_many(users)
print(f" Inserted {len(insert_result.inserted_ids)} users → "
      f"{roles.count('student')} students & {roles.count('instructor')} instructors.")


## COURSE VALIDATOR COLLECTION AND SCHEMA

# Drop old collection if it exists
db.drop_collection("courses")

# Validation schema
course_validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["courseId", "title", "instructorId", "level", "category", "createdAt", "isPublished"],
        "properties": {
            "courseId": {"bsonType": "string"},
            "title": {"bsonType": "string"},
            "description": {"bsonType": "string"},
            "instructorId": {"bsonType": "string"},
            "category": {"bsonType": "string"},
            "level": {"enum": ["beginner", "intermediate", "advanced"]},
            "duration": {"bsonType": "double"},
            "price": {"bsonType": "double"},
            "tags": {
                "bsonType": "array",
                "items": {"bsonType": "string"}
            },
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"},
            "isPublished": {"bsonType": "bool"}
        }
    }
}

# Create collection with validator
db.create_collection("courses", validator=course_validator)


# %%
course_categories = ["data engineering", "data science", "artificial intelligence", "data analysis", "cybersecurity"]
levels = ["beginner", "intermediate", "advanced"]
tags = ["project based", "career ready", "mentor supported", "interactive", "quiz-included"]
titles = [
    "Mastering Python for Data Science",
    "Fullstack Data Engineering Bootcamp",
    "AI Foundations with TensorFlow",
    "Power BI Essentials",
    "Cloud Computing Basics",
    "Cybersecurity for Beginners",
    "Docker Mastery",
    "Intro to MongoDB"
]

descriptions = [
    "An immersive course covering everything you need to start your journey.",
    "Learn by building real-world projects in this hands-on course.",
    "Get mentorship and interactive lessons tailored to your learning pace.",
    "Your pathway to becoming career-ready in under 10 weeks!",
    "Explore the tools and workflows used by professionals.",
    "Quiz-based learning for deep skill retention and feedback.",
    "Build, ship, and run apps using Docker like a pro!",
    "Hands-on guide to managing and querying NoSQL databases."
]

instructors = list(db.users.find({"role": "instructor"}))
if not instructors:
    raise ValueError("No instructors found – seed users first!")

courses = []
for i in range(8):
    inst = random.choice(instructors)
    courses.append({
        "_id": ObjectId(),
        "courseId": str(uuid.uuid4()),
        "title": titles[i],
        "description": descriptions[i],
        "instructorId": inst["userId"],
        "category": random.choice(course_categories),
        "level": random.choice(levels),
        "duration": round(random.uniform(5, 20), 2),
        "price": round(random.uniform(49.99, 299.99), 2),
        "tags": random.sample(tags, k=random.randint(2, 4)),
        "createdAt": datetime.utcnow(),    
        "updatedAt": datetime.utcnow(),      
        "isPublished": random.choice([True, False])
    })

db.courses.insert_many(courses)
print(" 8 courses inserted with proper timestamps!")


# %% [markdown]
# ENROLLMENT VALIDATOR COLLECTION AND SCHEMA

# %%
db.create_collection("enrollments", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["enrollmentId", "studentId", "courseId", "enrolledAt", "progress", "isActive"],
        "properties": {
            "enrollmentId": {"bsonType": "string"},
            "studentId": {"bsonType": "string"},
            "courseId": {"bsonType": "string"},
            "enrolledAt": {"bsonType": "date"},
            "progress": {"bsonType": "double"},
            "isActive": {"bsonType": "bool"}
        }
    }
})


# %%
students = list(db.users.find({"role": "student"}))
courses = list(db.courses.find({}))

enrollments = []

for _ in range(15):
    student = random.choice(students)
    course = random.choice(courses)
    
    enrollments.append({
        "_id": ObjectId(),
        "enrollmentId": str(uuid.uuid4()),
        "studentId": student["userId"],
        "courseId": course["courseId"],
        "enrolledAt": datetime.utcnow(),
        "progress": round(random.uniform(0.0, 1.0), 2),
        "isActive": random.choice([True, False])
    })

db.enrollments.insert_many(enrollments)
print(" Inserted  15 enrollments.")


# %% [markdown]
# lessons

# %%
#LESSONS VALIDATOR COLLECTION AND SCHEMA

db.create_collection("lessons", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["lessonId", "courseId", "title", "content", "videoUrl", "duration", "order", "createdAt"],
        "properties": {
            "lessonId": {"bsonType": "string"},
            "courseId": {"bsonType": "string"},
            "title": {"bsonType": "string"},
            "content": {"bsonType": "string"},
            "videoUrl": {"bsonType": "string"},
            "duration": {"bsonType": "double"},
            "order": {"bsonType": "int"},
            "createdAt": {"bsonType": "date"}
        }
    }
})


# %%

#  lesson titles and their matching content
lesson_titles_contents = [
    ("Introduction to Data Engineering", "Learn what data engineering is, its key concepts, and real-world applications."),
    ("Setting Up Your Dev Environment", "Walkthrough for installing Python, VS Code, Git, and MongoDB."),
    ("Understanding Databases", "Dive into relational vs NoSQL databases with real-world examples."),
    ("ETL Pipelines Explained", "Break down the Extract, Transform, Load process with hands-on demos."),
    ("Working with SQL", "Write basic to advanced SQL queries for data analysis."),
    ("NoSQL with MongoDB", "Understand document-based data modeling with MongoDB."),
    ("Data Warehousing Basics", "Explore star and snowflake schemas, OLAP cubes, and use cases."),
    ("Building Data Pipelines", "Use Python to create automated and reusable data pipelines."),
    ("Data Visualization Tools", "Learn to use Power BI and Tableau to build stunning dashboards."),
    ("Cloud Storage & BigQuery", "Introduction to Google Cloud's BigQuery and cloud storage services."),
    ("Scheduling with Airflow", "Use Apache Airflow to schedule and monitor data workflows."),
    ("Docker for Data Engineering", "Containerize your apps using Docker for reproducibility."),
    ("Monitoring & Logging", "Implement logging and alerting for production data pipelines."),
    ("Version Control with Git", "Track your changes and collaborate efficiently using Git and GitHub."),
    ("Data Quality Checks", "Ensure your data is accurate and clean using validation techniques."),
    ("Building APIs for Data Access", "Create RESTful APIs to share and consume data."),
    ("Batch vs Stream Processing", "Compare batch vs real-time pipelines with examples."),
    ("Using Pandas Like a Pro", "Advanced data manipulation and wrangling with Pandas."),
    ("Intro to Spark", "Use PySpark for distributed data processing."),
    ("Capstone Project Kickoff", "Plan your final project and define deliverables."),
    ("Writing Clean Code", "Learn how to write modular, reusable, and readable code."),
    ("Error Handling & Debugging", "Debugging strategies and best practices in Python."),
    ("Deploying to the Cloud", "Deploy your pipelines and dashboards to GCP/AWS."),
    ("Review & Optimization", "Refactor pipelines for better performance and scalability."),
    ("Final Presentation Tips", "How to present your project clearly and professionally.")
]

# Pull courses from database
courses = list(db.courses.find({}))

lessons = []
order_counter = 1
for i in range(25):
    course = random.choice(courses)
    title, content = lesson_titles_contents[i]  # structured title & content
    lesson = {
        "_id": ObjectId(),
        "lessonId": str(uuid.uuid4()),
        "courseId": course["courseId"],
        "title": title,
        "content": content,
        "videoUrl": f"https://educontent.fakevideos.com/vid-{uuid.uuid4()}",
        "duration": round(random.uniform(5.0, 25.0), 2),
        "order": order_counter,
        "createdAt": datetime.utcnow()
    }
    order_counter += 1
    lessons.append(lesson)

# Insert into MongoDB
db.lessons.insert_many(lessons)




# %%
#  ASSIGNMENTS VALIDATOR COLLECTION AND SCHEMA

db.create_collection("assignments", validator={
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "assignmentId", "courseId", "title", "description",
            "dueDate", "maxScore", "createdAt", "updatedAt", "isActive"
        ],
        "properties": {
            "assignmentId": {"bsonType": "string"},
            "courseId": {"bsonType": "string"},
            "title": {"bsonType": "string"},
            "description": {"bsonType": "string"},
            "dueDate": {"bsonType": "date"},
            "maxScore": {"bsonType": "int"},
            "createdAt": {"bsonType": "date"},
            "updatedAt": {"bsonType": "date"},
            "isActive": {"bsonType": "bool"}
        }
    }
})

#  Sample titles & descriptions
assignment_titles = [
    "Data Cleaning Challenge",
    "Build a REST API with Flask",
    "Exploratory Data Analysis (EDA)",
    "TensorFlow Model Training",
    "Power BI Dashboard Project",
    "Cloud Deployment Exercise",
    "Security Risk Assessment",
    "Containerization with Docker",
    "MongoDB Aggregation Pipeline",
    "Capstone Project Proposal"
]

assignment_descriptions = [
    "Clean and preprocess a raw dataset using Python and Pandas.",
    "Develop a basic REST API that performs CRUD operations.",
    "Perform EDA on a dataset and generate visualizations.",
    "Train and evaluate a neural network using TensorFlow.",
    "Create an interactive dashboard showing business metrics.",
    "Deploy a simple web app using a cloud platform of your choice.",
    "Identify and assess common cybersecurity vulnerabilities.",
    "Package and run a Python app using Docker containers.",
    "Use MongoDB's aggregation framework to summarize data.",
    "Write a proposal for your final course project."
]

#  Get courses
courses = list(db.courses.find({}))

#  Generate assignment docs
assignments = []

for i in range(10):
    course = random.choice(courses)
    assignment = {
        "_id": ObjectId(),
        "assignmentId": str(uuid.uuid4()),
        "courseId": course["courseId"],
        "title": assignment_titles[i],
        "description": assignment_descriptions[i],
        "dueDate": datetime.now() + timedelta(days=random.randint(7, 21)),
        "maxScore": random.choice([50, 75, 100]),
        "createdAt": datetime.now(),
        "updatedAt": datetime.now(),
        "isActive": random.choice([True, False])
    }
    assignments.append(assignment)

# 💾 Insert into collection
db.assignments.insert_many(assignments)



# %%

#ASSIGNMENT VALIDATOR COLLECTION AND SCHEMA

# JSON Schema validator
submission_validator = {
    "$jsonSchema": {
        "bsonType":  "object",
        "required": [
            "submissionId", "assignmentId", "studentId",
            "submittedAt", "contentUrl", "grade", "feedback",
            "isLate", "createdAt", "updatedAt"
        ],
        "properties": {
            "submissionId": {"bsonType": "string"},
            "assignmentId": {"bsonType": "string"},
            "studentId":   {"bsonType": "string"},
            "submittedAt": {"bsonType": "date"},
            "contentUrl":  {"bsonType": "string"},
            "grade":       {"bsonType": ["int", "null"]},
            "feedback":    {"bsonType": ["string", "null"]},
            "isLate":      {"bsonType": "bool"},
            "createdAt":   {"bsonType": "date"},
            "updatedAt":   {"bsonType": "date"}
        }
    }
}

db.create_collection("submissions", validator=submission_validator)


# %%
#  grab 10 assignments & students
assignments = list(db.assignments.find({}))
students    = list(db.users.find({"role": "student"}))

submissions = []

for _ in range(12):
    assign   = random.choice(assignments)
    student  = random.choice(students)

    # Simulate a submit time: some on‑time, some late
    submit_time = assign["dueDate"] - timedelta(days=random.randint(-2, 4))
    is_late     = submit_time > assign["dueDate"]

    submissions.append({
        "_id": ObjectId(),
        "submissionId": str(uuid.uuid4()),
        "assignmentId": assign["assignmentId"],
        "studentId":    student["userId"],
        "submittedAt":  submit_time,
        "contentUrl":   f"https://eduhub.submissions/{uuid.uuid4()}.ipynb",
        "grade":        random.choice([None, random.randint(60, 100)]),  # graded or awaiting
        "feedback":     None,
        "isLate":       is_late,
        "createdAt":    datetime.utcnow(),
        "updatedAt":    datetime.utcnow()
    })

#  shove into Mongo
db.submissions.insert_many(submissions)
print(" Inserted exactly 12 assignment submissions!")




# CRUDE OPERATION 

# -------------------------------------------------------------------------
# 3.1  CREATE OPERATIONS
# -------------------------------------------------------------------------

def add_student_user(email, first_name, last_name,   #ADD NEW STUDENT
                     bio="", avatar="", skills=None):
    """Insert and return _id of a new student user."""
    skills = skills or []
    doc = {
        "_id": ObjectId(),
        "userId": str(uuid.uuid4()),
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "role": "student",
        "dateJoined": datetime.utcnow(),
        "profile": {"bio": bio, "avatar": avatar, "skills": skills},
        "isActive": True
    }
    return db.users.insert_one(doc).inserted_id


def create_course(title, instructor_id, category,   # CREATE COURSE
                  level="beginner", description="",
                  duration=10, price=0.0, tags=None):
    """Insert and return _id of a new course."""
    tags = tags or []
    doc = {
        "_id": ObjectId(),
        "courseId": str(uuid.uuid4()),
        "title": title,
        "description": description,
        "instructorId": instructor_id,
        "category": category,
        "level": level,
        "duration": duration,
        "price": price,
        "tags": tags,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
        "isPublished": False
    }
    return db.courses.insert_one(doc).inserted_id


def enroll_student_in_course(student_id, course_id):  #enroll_student_in_course
    """Insert enrollment; return _id."""
    doc = {
        "_id": ObjectId(),
        "enrollmentId": str(uuid.uuid4()),
        "studentId": student_id,
        "courseId": course_id,
        "enrolledAt": datetime.utcnow(),
        "progress": 0.0,
        "isActive": True
    }
    return db.enrollments.insert_one(doc).inserted_id


def add_lesson(course_id, title, content,          #ADD LESSON
               video_url="", duration=10.0, order=1):
    """Insert lesson; return _id."""
    doc = {
        "_id": ObjectId(),
        "lessonId": str(uuid.uuid4()),
        "courseId": course_id,
        "title": title,
        "content": content,
        "videoUrl": video_url,
        "duration": duration,
        "order": order,
        "createdAt": datetime.utcnow()
    }
    return db.lessons.insert_one(doc).inserted_id



#  I EXECUTED THE FUNCTIONS ABOVE IN 3.1

# add new student 
new_student = add_student_user(
    email="hinata@vb.com",
    first_name="Shoyo",
    last_name="Hinata",
    bio="pace setter",
    skills=["python"]
)

print("New student _id:", new_student)


# %%
# create course 
#  one instructor & one student to work with
instructor = db.users.find_one({"role": "instructor"})
if not instructor:
    raise ValueError("No instructor found  seed instructors first!")
student = db.users.find_one({"role": "student", "isActive": True})
if not student:
    raise ValueError("No active student found – seed students first!")

instructor_id = instructor["userId"]
student_id    = student["userId"]

print("Instructor  →", instructor["firstName"], instructor_id)
print("Student     →", student["firstName"],    student_id)

course_id = create_course(
    title="Async Programming in Python",
    instructor_id=instructor_id,
    category="data engineering",
    level="intermediate",
    description="Master async/await, asyncio, and concurrent Python patterns.",
    duration=12.0,           # ← float, not int
    price=49.0,              # already float, but keep one decimal place
    tags=["interactive", "project based"]
)
print(" course _id:", course_id)


# %%


# %%
# -------------------------------------------------------------
#  enroll_student_in_course  +  add_lesson
# -------------------------------------------------------------


# fetch fresh course doc so we have the string field
course_doc   = db.courses.find_one({"_id": course_id})   # course_id is ObjectId
courseId_str = course_doc["courseId"]                    # ← this is the string UUID
enrollment_id = enroll_student_in_course(
    student_id=student_id,       # string
    course_id=courseId_str       # string, matches validator
)
print(" Enrollment _id:", enrollment_id)




# %%
# -------------------------------------------------------------
# Add a lesson 
# -------------------------------------------------------------


# Get the course's string ID, not the ObjectId
course_doc   = db.courses.find_one({"_id": course_id})
courseId_str = course_doc["courseId"]

try:
    lesson_id = add_lesson(
        course_id=courseId_str,                      #  string ID
        title="Intro to Async/Await",
        content="Learn the basics of asynchronous programming in Python using async and await.",
        video_url="https://example.com/videos/async-await.mp4",
        duration=8.5,
        order=1
    )
    print(" Lesson _id:", lesson_id)

    # Pretty‑print the stored lesson
    pprint(db.lessons.find_one(
        {"_id": lesson_id},
        {"_id": 0, "lessonId": 1, "title": 1, "courseId": 1, "order": 1}
    ))

except WriteError as err:
    print(" Lesson insert failed:", err.details['errmsg'])


# %%
# -------------------------------------------------------------------------
# 3.2  READ OPERATIONS
# -------------------------------------------------------------------------

def find_active_students():
    return list(db.users.find({"role": "student", "isActive": True})) # FINDING ACTIVE STUDENTS


def get_course_with_instructor(course_id):    #GET COURSE WITH INSTRUCTOR
    """Return merged course+instructor doc, or None if not found."""
    pipeline = [
        {"$match": {"courseId": course_id}},
        {"$lookup": {
            "from": "users",
            "localField": "instructorId",
            "foreignField": "userId",
            "as": "instructor"}},
        {"$unwind": "$instructor"}
    ]
    docs = list(db.courses.aggregate(pipeline))
    return docs[0] if docs else None       



def get_courses_by_category(category):  # GET COURSE BY CATEGORY
    return list(db.courses.find({"category": category}))


def get_students_enrolled(course_id):           #GET STUDENTS ENROLLED
    pipeline = [
        {"$match": {"courseId": course_id}},
        {"$lookup": {
            "from": "users",
            "localField": "studentId",
            "foreignField": "userId",
            "as": "student"}},
        {"$unwind": "$student"},
        {"$replaceRoot": {"newRoot": "$student"}}
    ]
    return list(db.enrollments.aggregate(pipeline))


def search_courses_by_title(keyword):      #SEARCH COURSES BY TITLE
    regex = re.compile(keyword, re.IGNORECASE)
    return list(db.courses.find({"title": regex}))





# #  I EXECUTED THE FUNCTIONS ABOVE IN 3.2
# -------------------------------------------------------------
#  Task 3.2 – READ operations
# -------------------------------------------------------------
#  3.2.1 find_active_students
students = find_active_students()
print("\n1) Active students count:", len(students))
if students:
    pprint(students[0])   



# %%
cid_async = "b1aaa889-1fe5-4437-98a3-b1607f901ac9" 

course_with_teacher = get_course_with_instructor(cid_async)

if course_with_teacher:
    from pprint import pprint
    pprint(course_with_teacher)
else:
    print(" No match found – double‑check the courseId string.")





# %%
category = "data engineering"   

print("\n3) All courses in category:", category)
for c in get_courses_by_category(category):
    print(" •", c["title"])


# %%
# active student
student_doc = db.users.find_one({"role": "student", "isActive": True})
if not student_doc:
    raise ValueError("No active student found!")

student_id_str = student_doc["userId"]

# 3.2.2 find course
course_doc = db.courses.find_one({})
if not course_doc:
    raise ValueError("No course found!")

courseId_str = course_doc["courseId"]

print("Chosen student →", student_doc["firstName"], student_id_str)
print("Chosen course  →", course_doc["title"],  courseId_str)



# %%
# 3.2.3 search_courses_by_title
keyword = "python"   
print(f"\n5) Courses whose title contains '{keyword}':")
for c in search_courses_by_title(keyword):
    print("  •", c["title"])

# %%
# -------------------------------------------------------------------------
# 3.3  UPDATE OPERATIONS
# -------------------------------------------------------------------------

def update_user_profile(user_id, bio=None, skills=None, avatar=None): #UPDATE USER PROFILE
    updates = {}
    if bio is not None:    updates["profile.bio"] = bio
    if skills is not None: updates["profile.skills"] = skills
    if avatar is not None: updates["profile.avatar"] = avatar
    if not updates:
        return None
    return db.users.find_one_and_update(
        {"userId": user_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER
    )


def publish_course(course_id, publish=True):   # PUBLISH COURSE
    return db.courses.find_one_and_update(
        {"courseId": course_id},
        {"$set": {"isPublished": publish,
                  "updatedAt": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER
    )


def update_submission_grade(submission_id, grade, feedback=None): #UPDATE GRADE
    updates = {"grade": grade, "updatedAt": datetime.utcnow()}
    if feedback is not None:
        updates["feedback"] = feedback
    return db.submissions.find_one_and_update(
        {"submissionId": submission_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER
    )


def add_tags_to_course(course_id, tags):        # ADD TAG TO COURSE
    return db.courses.find_one_and_update(
        {"courseId": course_id},
        {"$addToSet": {"tags": {"$each": tags}},
         "$set": {"updatedAt": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER
    )





##  I EXECUTED THE FUNCTIONS ABOVE IN 3.3

# Pick a user (student or instructor)
uid = "0737f249-4d29-43aa-a604-c10e7c407b68"

updated_user = update_user_profile(
    user_id=uid,
    bio="I love learning data engineering!",
    skills=["MongoDB", "Python", "Docker"],
    avatar="https://example.com/avatars/leslie.png"
)


pprint(updated_user)


# %%

# -------------------------------------------------------------
# 2) Pick or create a course to publish
# -------------------------------------------------------------
course_doc = db.courses.find_one({"isPublished": False})   # any unpublished course
if not course_doc:
    course_doc = db.courses.find_one()                     
    if not course_doc:
        raise ValueError(" No courses exist—seed courses first!")

courseId_str = course_doc["courseId"]
print("Target courseId:", courseId_str, "| title:", course_doc["title"])

# Publish the course
updated_course = publish_course(courseId_str, publish=True)
print("\n2 Course published? →", updated_course["isPublished"])
pprint({"title": updated_course["title"], "updatedAt": updated_course["updatedAt"]})



# %%

# -------------------------------------------------------------
# 3) Pick or insert a submission to update
# -------------------------------------------------------------
submission_doc = db.submissions.find_one({"grade": None})   # ungraded submission
if not submission_doc:
    # Create a dummy submission for demo
    student = db.users.find_one({"role": "student", "isActive": True})
    assignment = db.assignments.find_one()
    submission_doc = {
        "_id": ObjectId(),
        "submissionId": str(uuid.uuid4()),
        "assignmentId": assignment["assignmentId"],
        "studentId": student["userId"],
        "submittedAt": datetime.utcnow(),
        "contentUrl": "https://example.com/dummy.ipynb",
        "grade": None,
        "feedback": None,
        "isLate": False,
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    db.submissions.insert_one(submission_doc)
    print("\n3  Inserted demo submission for grading.")

submission_id_str = submission_doc["submissionId"]

# Grade it
graded_sub = update_submission_grade(
    submission_id=submission_id_str,
    grade=93,
    feedback="Excellent work—clean async code!"
)

print("\n Submission graded:")
pprint({"submissionId": graded_sub["submissionId"],
        "grade": graded_sub["grade"],
        "feedback": graded_sub["feedback"]})



# %%

# -------------------------------------------------------------
# 4) Add tags to the same course
# -------------------------------------------------------------
new_tags = ["mentor supported", "career ready"]

updated_course = add_tags_to_course(courseId_str, new_tags)

print("\n4 Updated tags:")
pprint({"courseId": updated_course["courseId"], "tags": updated_course["tags"]})


# %%

# -------------------------------------------------------------------------
# 3.4  DELETE OPERATIONS
# -------------------------------------------------------------------------

def soft_delete_user(user_id):  #SOFT DELETE
    return db.users.find_one_and_update(
        {"userId": user_id},
        {"$set": {"isActive": False}},
        return_document=ReturnDocument.AFTER
    )


def delete_enrollment(enrollment_id):     #DELETE ENROLLMENT
    return db.enrollments.delete_one({"enrollmentId": enrollment_id}).deleted_count


def delete_lesson(lesson_id): #DELETE LESSON
    return db.lessons.delete_one({"lessonId": lesson_id}).deleted_count



# #  I EXECUTED THE FUNCTIONS ABOVE IN 3.4
# -------------------------------------------------------------
#  Task 3.4 – DELETE operations
# ---------------------------------------------------------

# a) User to soft‑delete
user_doc = db.users.find_one({"role": "student", "isActive": True}) 
if not user_doc:
    # Insert a demo student
    user_id_str = str(uuid.uuid4())
    db.users.insert_one({
        "_id": ObjectId(),
        "userId": user_id_str,
        "email": "temp@student.com",
        "firstName": "Temp",
        "lastName": "User",
        "role": "student",
        "dateJoined": datetime.utcnow(),
        "profile": {"bio": "Temp user", "avatar": "", "skills": []},
        "isActive": True
    })
    user_doc = db.users.find_one({"userId": user_id_str})
print("User for delete:", user_doc["userId"])

# b) Enrollment to delete
enrollment_doc = db.enrollments.find_one()
if not enrollment_doc:
    # Need a course + student
    student = db.users.find_one({"role": "student"})
    course  = db.courses.find_one()
    enroll_student_in_course(student["userId"], course["courseId"])
    enrollment_doc = db.enrollments.find_one()
print("Enrollment for delete:", enrollment_doc["enrollmentId"])

# c) Lesson to delete
lesson_doc = db.lessons.find_one()
if not lesson_doc:
    course = db.courses.find_one()
    add_lesson(
        course["courseId"],
        "Temp Lesson",
        "To be deleted.",
        duration=1.0,
        order=99
    )
    lesson_doc = db.lessons.find_one()
print("Lesson for delete:", lesson_doc["lessonId"])

# ---------------------------------------------------------
# 1) SOFT‑DELETE the user
# ---------------------------------------------------------
#  the helper
deleted_user = soft_delete_user(user_doc["userId"])   # <- note the parentheses!

#  Check what we got back
print("deleted_user value:", deleted_user)

#  Safely print fields if the user was found
if deleted_user:
    from pprint import pprint
    pprint({
        "userId":   deleted_user["userId"],
        "isActive": deleted_user["isActive"]
    })
else:
    print(" No user matched that userId, nothing to soft‑delete.")



# %%

# ---------------------------------------------------------
# 2) HARD‑DELETE the enrollment
# ---------------------------------------------------------
print("\n🔸 Deleting enrollment …")
deleted_count = delete_enrollment(enrollment_doc["enrollmentId"])
print("Deleted count:", deleted_count)

# Verify it’s gone
exists = db.enrollments.find_one({"enrollmentId": enrollment_doc["enrollmentId"]})
print("Enrollment exists after delete?", bool(exists))



# %%

# ---------------------------------------------------------
# 3) HARD‑DELETE the lesson
# ---------------------------------------------------------
print("\n Deleting lesson …")
deleted_count = delete_lesson(lesson_doc["lessonId"])
print("Deleted count:", deleted_count)

exists = db.lessons.find_one({"lessonId": lesson_doc["lessonId"]})
print("Lesson exists after delete?", bool(exists))

# %% #Part 4: Advanced Queries and Aggregation 
#  Task 4.1: Complex Queries


# %%  #Find courses with price between $50 and $200 
# 	
courses = db.courses.find({         
    "price": {"$gte": 50, "$lte": 200}
})
print("\nCourses priced between $50 and $200:")
for c in courses:
    print(" •", c["title"], "-", c["price"])


# %%#2	Get users who joined in the last 6 months  

six_months_ago = datetime.utcnow() - timedelta(days=180) 
users = db.users.find({
    "dateJoined": {"$gte": six_months_ago}
})
print("\nUsers who joined in the last 6 months:")
for u in users:
    print(" •", u["firstName"], u["email"])


# %%  #3 Find courses that have specific tags using $in operator

desired_tags = [ 'interactive', 'mentor supported', 'project based']  	
tagged_courses = db.courses.find({
    "tags": {"$in": desired_tags}
})
print("\nCourses with desired tags:")
for c in tagged_courses:
    print(" •", c["title"], "-", c.get("tags", []))


# %% 4	Retrieve assignments with due dates 

now = datetime.utcnow()
next_week = now + timedelta(days=7)
upcoming_assignments = db.assignments.find({
    "dueDate": {"$gte": now, "$lte": next_week}
})
print("\nAssignments due in the next week:")
for a in upcoming_assignments:
    print(" •", a["title"], "Due:", a["dueDate"].strftime("%Y-%m-%d"))


# %%  Task 4.2: Aggregation Pipeline Create aggregation pipelines using PyMongo 
# ---------------------------------------------
# 0) ONE‑TIME PATCH  → add grades if missing
# ---------------------------------------------
patched = db.submissions.update_many(
    {"grade": {"$exists": False}},
    {"$set": {"grade": {"$add": [60, {"$multiply": [random.random(), 40]}]}}}
).modified_count
print(f" Patched {patched} submissions with dummy grades.\n")


# build a list of real courseId strings
valid_course_ids = list(db.courses.distinct("courseId"))

# find graded submissions whose courseId is NOT in that list
broken_submissions = list(db.submissions.find({
    "grade": {"$ne": None},
    "courseId": {"$nin": valid_course_ids}
}))

print(" Broken graded submissions:", len(broken_submissions))

for sub in broken_submissions:
    new_cid = choice(valid_course_ids)
    db.submissions.update_one(
        {"_id": sub["_id"]},
        {"$set": {"courseId": new_cid}}
    )

print(" Re‑linked every graded submission to a real course.")
# =============================================================
# 4.2.1  COURSE ENROLLMENT STATS
# =============================================================


#  Step 1: get all valid courseIds from the courses collection
valid_course_ids = list(db.courses.distinct("courseId"))

#  Step 2: find enrollments that have invalid (broken) courseIds
broken_enrollments = list(db.enrollments.find({
    "courseId": {"$nin": valid_course_ids}
}))

print("Found broken enrollments:", len(broken_enrollments))

#  Step 3: assign each broken enrollment to a random valid courseId
for e in broken_enrollments:
    new_course_id = choice(valid_course_ids)
    db.enrollments.update_one(
        {"_id": e["_id"]},
        {"$set": {"courseId": new_course_id}}
    )

print(" All fixed. Broken enrollments now point to real courses.")



# Total enrollments per course  (handles ObjectId/string)

pipeline = [
    {"$group": {"_id": "$courseId", "total": {"$sum": 1}}},
    {"$lookup": {
        "from": "courses",
        "localField": "_id",
        "foreignField": "courseId",
        "as": "course"
    }},
    {"$unwind": "$course"},
    {"$project": {
        "_id": 0,
        "course": "$course.title",
        "total": 1
    }},
    {"$sort": {"total": -1}}
]
print(" Total enrollments per course:")
pprint(list(db.enrollments.aggregate(pipeline)))


# Avg grade per course

pipeline = [
    {"$match": {"grade": {"$ne": None}}},
    {"$group": {"_id": "$courseId", "avgGrade": {"$avg": "$grade"}}},
    {"$lookup": {
        "from": "courses",
        "localField": "_id",
        "foreignField": "courseId",
        "as": "course"}},
    {"$unwind": "$course"},
    {"$project": {"_id": 0,
                  "course": "$course.title",
                  "avgGrade": {"$round": ["$avgGrade", 1]}}},
    {"$sort": {"avgGrade": -1}}
]

print("\n Average grade per course:")
pprint(list(db.submissions.aggregate(pipeline)))


# Courses by category
pipeline = [
    {"$group": {"_id": "$category", "numCourses": {"$sum": 1}}},
    {"$sort": {"numCourses": -1}}
]
print("\n Courses grouped by category:")
pprint(list(db.courses.aggregate(pipeline)))


# %%

# =============================================================
# 4.2.2  STUDENT PERFORMANCE
# ============================================================

# Grab valid userIds for students
valid_student_ids = list(db.users.distinct("userId", {"role": "student"}))

broken_subs = list(db.submissions.find({
    "grade": {"$ne": None},
    "studentId": {"$nin": valid_student_ids}
}))

print("Broken graded submissions (bad studentId):", len(broken_subs))

for sub in broken_subs:
    db.submissions.update_one(
        {"_id": sub["_id"]},
        {"$set": {"studentId": choice(valid_student_ids)}}
    )

print(" Re‑linked all graded submissions to real students.")

# Pick 5 random enrollments and mark them completed
completed_ids = [e["_id"] for e in db.enrollments.aggregate([{"$sample": {"size": 5}}])]
db.enrollments.update_many({"_id": {"$in": completed_ids}},
                           {"$set": {"progress": 1.0}})
print(" Set 5 enrollments to progress = 1.0")

# Set first 3 graded submissions to a high score
high_subs = list(db.submissions.find({"grade": {"$exists": True}}).limit(3))
for s in high_subs:
    db.submissions.update_one({"_id": s["_id"]}, {"$set": {"grade": 95}})
print(" Updated 3 submissions to grade = 95")



# Avg grade per student
pipeline = [
    {"$group": {"_id": "$studentId", "avgGrade": {"$avg": "$grade"}}},
    {"$lookup": {"from": "users", "localField": "_id",
                 "foreignField": "userId", "as": "student"}},
    {"$unwind": "$student"},
    {"$project": {"_id": 0,
                  "student": {"$concat": ["$student.firstName", " ", "$student.lastName"]},
                  "avgGrade": {"$round": ["$avgGrade", 1]}}},
    {"$sort": {"avgGrade": -1}}
]
print("\n🎓 Average grade per student:")
pprint(list(db.submissions.aggregate(pipeline)))

# Completion rate by course (progress==1)
pipeline = [
    {"$group": {
        "_id": "$courseId",
        "completed": {"$sum": {"$cond": [{"$gte": ["$progress", 1]}, 1, 0]}},
        "total": {"$sum": 1}
    }},
    {"$addFields": {"completionRate": {"$divide": ["$completed", "$total"]}}},
    {"$lookup": {"from": "courses", "localField": "_id",
                 "foreignField": "courseId", "as": "course"}},
    {"$unwind": "$course"},
    {"$project": {"_id": 0, "course": "$course.title",
                  "completionRate": {"$round": ["$completionRate", 2]}}},
    {"$sort": {"completionRate": -1}}
]
print("\n Completion rate by course:")
pprint(list(db.enrollments.aggregate(pipeline)))

# Top-performing students (avgGrade ≥ 90)

pipeline = [
    {"$group": {"_id": "$studentId", "avgGrade": {"$avg": "$grade"}}},
    {"$match": {"avgGrade": {"$gte": 90}}},
    {"$lookup": {"from": "users", "localField": "_id",
                 "foreignField": "userId", "as": "student"}},
    {"$unwind": "$student"},
    {"$project": {"_id": 0,
                  "student": {"$concat": ["$student.firstName", " ", "$student.lastName"]},
                  "avgGrade": {"$round": ["$avgGrade", 1]}}},
    {"$sort": {"avgGrade": -1}}
]
print("\n Top‑performing students (avg ≥ 90):")
pprint(list(db.submissions.aggregate(pipeline)))


# %%

# =============================================================
# 4.2.3  INSTRUCTOR ANALYTICS
# =============================================================

# Total unique students taught per instructor
pipeline = [
    {"$group": {
        "_id": "$courseId",
        "students": {"$addToSet": "$studentId"}
    }},
    {"$lookup": {"from": "courses", "localField": "_id",
                 "foreignField": "courseId", "as": "course"}},
    {"$unwind": "$course"},
    {"$group": {
        "_id": "$course.instructorId",
        "totalStudents": {"$sum": {"$size": "$students"}}
    }},
    {"$lookup": {"from": "users", "localField": "_id",
                 "foreignField": "userId", "as": "instructor"}},
    {"$unwind": "$instructor"},
    {"$project": {"_id": 0,
                  "instructor": {"$concat": ["$instructor.firstName", " ", "$instructor.lastName"]},
                  "totalStudents": 1}},
    {"$sort": {"totalStudents": -1}}
]
print("\n Total students taught per instructor:")
pprint(list(db.enrollments.aggregate(pipeline)))

# Avg grade per instructor
pipeline = [
    {"$group": {"_id": "$courseId", "avgGrade": {"$avg": "$grade"}}},
    {"$lookup": {"from": "courses", "localField": "_id",
                 "foreignField": "courseId", "as": "course"}},
    {"$unwind": "$course"},
    {"$group": {"_id": "$course.instructorId", "avgGrade": {"$avg": "$avgGrade"}}},
    {"$lookup": {"from": "users", "localField": "_id",
                 "foreignField": "userId", "as": "instructor"}},
    {"$unwind": "$instructor"},
    {"$project": {"_id": 0,
                  "instructor": {"$concat": ["$instructor.firstName", " ", "$instructor.lastName"]},
                  "avgGrade": {"$round": ["$avgGrade", 1]}}},
    {"$sort": {"avgGrade": -1}}
]
print("\n Avg course grade per instructor:")
pprint(list(db.submissions.aggregate(pipeline)))

# Revenue per instructor
pipeline = [
    {"$lookup": {"from": "courses", "localField": "courseId",
                 "foreignField": "courseId", "as": "course"}},
    {"$unwind": "$course"},
    {"$group": {"_id": "$course.instructorId", "revenue": {"$sum": "$course.price"}}},
    {"$lookup": {"from": "users", "localField": "_id",
                 "foreignField": "userId", "as": "instructor"}},
    {"$unwind": "$instructor"},
    {"$project": {"_id": 0,
                  "instructor": {"$concat": ["$instructor.firstName", " ", "$instructor.lastName"]},
                  "revenue": {"$round": ["$revenue", 2]}}},
    {"$sort": {"revenue": -1}}
]
print("\n Revenue per instructor:")
pprint(list(db.enrollments.aggregate(pipeline)))


# %%

# =============================================================
# 4.2.4  ADVANCED ANALYTICS
# =============================================================

# Monthly enrollment trends
pipeline = [
    {"$addFields": {"month": {"$dateToString": {"format": "%Y-%m", "date": "$enrolledAt"}}}},
    {"$group": {"_id": "$month", "numEnrollments": {"$sum": 1}}},
    {"$sort": {"_id": 1}}
]
print("\n Monthly enrollment trends:")
pprint(list(db.enrollments.aggregate(pipeline)))

# Most popular categories (by enrollments)
pipeline = [
    {"$lookup": {"from": "courses", "localField": "courseId",
                 "foreignField": "courseId", "as": "course"}},
    {"$unwind": "$course"},
    {"$group": {"_id": "$course.category", "enrollments": {"$sum": 1}}},
    {"$sort": {"enrollments": -1}}
]
print("\n Most popular course categories:")
pprint(list(db.enrollments.aggregate(pipeline)))

# Student engagement (avg progress per course)
pipeline = [
    {"$group": {"_id": "$courseId", "avgProgress": {"$avg": "$progress"}}},
    {"$lookup": {"from": "courses", "localField": "_id",
                 "foreignField": "courseId", "as": "course"}},
    {"$unwind": "$course"},
    {"$project": {"_id": 0,
                  "course": "$course.title",
                  "avgProgress": {"$round": ["$avgProgress", 2]}}},
    {"$sort": {"avgProgress": -1}}
]
print("\n Student engagement (avg progress per course):")
pprint(list(db.enrollments.aggregate(pipeline)))


# %% [markdown]
# PART 5 INDEXING AND PERFORMANCE 

# %%

# --------------------------------------------------
# 1. Create  all indexes
# --------------------------------------------------
print("Creating indexes …")

ix_email   = db.users.create_index(
    [("email", 1)], name="idx_user_email", unique=True
)
ix_course  = db.courses.create_index(
    [("title", "text"), ("category", "text")],
    name="idx_course_title_category"
)
ix_assign  = db.assignments.create_index(
    [("dueDate", -1)], name="idx_assignment_dueDate"
)
ix_enroll  = db.enrollments.create_index(
    [("studentId", 1), ("courseId", 1)],
    name="idx_enrollment_student_course"
)

print("\n Returned index names:")
print(ix_email, ix_course, ix_assign, ix_enroll)

# --------------------------------------------------
# 2. Show every index on each collection
# --------------------------------------------------
def show_indexes(col_name):
    print(f"\n  {col_name} indexes:")
    for name, info in db[col_name].index_information().items():
        print(" •", name, "→", info["key"])

show_indexes("users")
show_indexes("courses")
show_indexes("assignments")
show_indexes("enrollments")

# --------------------------------------------------
# 3. raw server docs 
# --------------------------------------------------
print("\n  Full detail for courses:")
for ix in db.courses.list_indexes():
    pprint(ix)


# %% [markdown]
# QUERY OPTIMIZATION 5.2

# %%


def timed(label):
    """Decorator to time a function"""
    def wrap(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            start = time.perf_counter()
            result = func(*args, **kwargs)
            dur = (time.perf_counter() - start) * 1000  # ms
            print(f"{label}: {dur:.2f} ms")
            return result
        return inner
    return wrap




@timed("  Search courses WITHOUT text index") # slow query 1
def slow_course_search_no_index():
    return list(db.courses.find(
        {"title": {"$regex": "python", "$options": "i"}}
    ))

slow_course_search_no_index()

print("\nExplain plan:")
pprint(db.courses.find({"title": {"$regex": "python", "$options": "i"}}).explain()["queryPlanner"])


@timed(" Assignment lookup w/o index") #slow query 2
def slow_assignment_lookup():
    now = datetime.utcnow()
    return list(db.assignments.find({"dueDate": {"$gte": now}}))

slow_assignment_lookup()

@timed(" Assignment lookup WITH idx_assignment_dueDate")
def fast_assignment_lookup():
    now = datetime.utcnow()
    return list(db.assignments.find(
        {"dueDate": {"$gte": now}}
    ).hint("idx_assignment_dueDate"))

fast_assignment_lookup()





sample_enrollment = db.enrollments.find_one()  #slow query 3
student_id = sample_enrollment["studentId"]
course_id  = sample_enrollment["courseId"]

@timed("⏱  Enrollment lookup w/o hint")
def slow_enroll_lookup():
    return list(db.enrollments.find({
        "studentId": student_id,
        "courseId":  course_id
    }))

@timed(" Enrollment lookup WITH compound index")
def fast_enroll_lookup():
    return list(db.enrollments.find({
        "studentId": student_id,
        "courseId":  course_id
    }).hint("idx_enrollment_student_course"))

slow_enroll_lookup()
fast_enroll_lookup()


# %% [markdown]
# Part 6 – Data Validation & Error Handling

# %%
# 6  Schema Validation Recap i already added JSON schema validators (users, courses, etc.).


#  Missing required field:  'title'
bad_course = {
    "courseId": "BAD‑123",
    "category": "data science",
    "level": "beginner",
    "price": 75,
    "createdAt": datetime.utcnow(),
    "isPublished": False
}

try:
    db.courses.insert_one(bad_course)
except WriteError as e:
    print(" Validation error caught!")
    pprint(e.details["errmsg"])



 # error handling

def safe_add_user(user_doc):
    try:
        db.users.insert_one(user_doc)
        print("User inserted.")
    except DuplicateKeyError:
        print(" Email already exists.")
    except WriteError as e:
        print(" Validation error:", e.details["errmsg"])

def safe_update_progress(enrollment_id, new_progress):
    try:
        result = db.enrollments.update_one(
            {"enrollmentId": enrollment_id},
            {"$set": {"progress": float(new_progress)}}
        )
        if result.matched_count == 0:
            print("No enrollment found.")
    except Exception as e:
        print("Unexpected error:", e)



