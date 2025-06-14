# 📚 EduHub MongoDB Project

> A data-driven MongoDB solution for managing EduHub, a modern e-learning platform.  
> Built with Python, PyMongo, Jupyter, and a performance-first mindset.

---

##  Folder Structure

```bash
mongodb-eduhub-project/
├── README.md                      # ← This file
├── notebooks/
│   └── eduhub_mongodb_project.ipynb  # Jupyter notebook (all code & results)
├── src/
│   └── eduhub_queries.py          # Reusable Python functions
├── data/
│   ├── sample_data.json           # Generated test dataset
│   └── schema_validation.json     # MongoDB collection validators
├── docs/
│   ├── performance_analysis.md    # Performance benchmarking & index summary
│   └── presentation.pptx          # Project design presentation (5–10 slides)
└── .gitignore                     # Ignore unnecessary files like __pycache__, .DS_Store


 Design Overview
🧾 Schemas & Collections
We modeled EduHub with the following collections:

users – Students & instructors with role-based fields

courses – Each with categories, tags, and instructor

lessons – Nested under courses, include video/text types

assignments – Linked to courses, have dueDates

submissions – Student responses to assignments

enrollments – Many-to-many mapping between users and courses



Indexing Decisions
| Collection    | Index Description                          |
| ------------- | ------------------------------------------ |
| `courses`     | Text index on title and category           |
| `assignments` | Index on `dueDate` (descending)            |
| `enrollments` | Compound index on `studentId` + `courseId` |

Validators ensure schema consistency at insert/update time for all collections.


 How to Run the Project
  Requirements
MongoDB 6.x+ installed locally

Python 3.11+

Install dependencies:

pip install pymongo faker


 Running the Scripts
Launch your MongoDB server (mongod)

Insert data and apply schema via:
python src/eduhub_queries.py

Explore and run queries in:
notebooks/eduhub_mongodb_project.ipynb

📈 Performance Summary
We tested and optimized 3 common queries:
| Query                     | Before | After | Speedup |
| ------------------------- | ------ | ----- | ------- |
| Course search (full-text) | 38 ms  | 6 ms  | \~84% ↓ |
| Assignments due in 7 days | 42 ms  | 8 ms  | \~81% ↓ |
| Student enrollment lookup | 29 ms  | 4 ms  | \~86% ↓ |
→ See docs/performance_analysis.md for full stats & explain plans.

🪪 License
This project is open-source under the MIT License.
Use, remix, or contribute freely 🫶

🧠 Author
Ebube Iroroh
📬 ebube.iroroh@gmail.com