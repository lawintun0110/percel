from dotenv import load_dotenv
from flask import render_template, url_for, flash, redirect, abort, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload
from app import db 
from . import teacher_bp # Assuming your blueprint is named teacher_bp
from flask_wtf.csrf import generate_csrf 
from flask_login import login_required, current_user
from app.teacher import teacher_bp
from app.models import db, User, Course, Chapter, Session, Material, Quiz, Enroll , LearningCurve
import json
import os
from urllib.parse import urlparse, parse_qs
import requests
from flask import jsonify
import re  
from flask import render_template_string
from flask import current_app 
from sqlalchemy.orm import joinedload
from flask import render_template
from sqlalchemy import func
import json
from huggingface_hub import InferenceClient

load_dotenv()

HF_TOKEN =  os.getenv("HF_TOKEN")
client = InferenceClient(token=HF_TOKEN)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
API_URL = os.getenv("OPENROUTER_API_URL")
MODEL = os.getenv("OPENROUTER_MODEL")
'''HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json"
}'''

'''HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "HTTP-Referer": os.getenv("OPENROUTER_REFERER", "http://localhost"),
    "X-Title": "Quiz Question Generator"  # optional but recommended
}'''

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
    "Referer": "http://localhost"  # or your local Flask URL
}


print("DEBUG: OPENROUTER_API_KEY", OPENROUTER_API_KEY[:10] + "..." if OPENROUTER_API_KEY else None)
print("DEBUG: API_URL", API_URL)
print("DEBUG: MODEL", MODEL)


# ... any other imports or routes you have ...
path = os.getcwd()
question = os.path.join(path,"app","teacher")
qdata = os.path.join(question,"question.json")
print("=================== this is my path ========= ", qdata) #testing


# --- NEW: Teacher Dashboard Route ---
@teacher_bp.route('/dashboard') # This route defines the /teacher/dashboard URL
@login_required
def teacher_dashboard():
    # Ensure only teachers can access this page
    if current_user.role != 'teacher':
        flash('You do not have permission to access the teacher dashboard.', 'danger')
        # Redirect to appropriate dashboard based on user's actual role
        print("=================== this is my path ========= ", path) #testing
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.student_dashboard'))
        else:
            return redirect(url_for('main.guest_page'))

    # You can fetch teacher-specific data here, e.g., courses taught by the current user
    # Assuming 'current_user' (a User model instance) has a relationship like 'teaching_courses'
    # Or, if Course has a teacher_id, you can query for it:
    courses = Course.query.filter_by(teacher_id=current_user.id).all()

    # For now, let's just pass a simple message or an empty list if no courses
    teacher_courses = current_user.teaching_courses.all() if hasattr(current_user, 'teaching_courses') else []

    return render_template('teacher_dashboard.html', title='Teacher Dashboard', courses=courses)

#create_cover ==========================
@teacher_bp.route("/create_cover", methods=["POST"])
@login_required
def create_cover():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    course_id = request.form.get("course_id")

    if not title:
        # Only return message snippet
        return f'''  <p class="text-red-500 mt-2">Title is required!</p> '''

    if course_id:
        course = Course.query.get(course_id)
        course.title = title
        course.description = description
        db.session.commit()
        new_course_created = False
        new_course_id = course.id
        message = "Course updated!"
    else:
        course = Course(title=title, description=description, teacher_id=current_user.id)
        db.session.add(course)
        db.session.commit()
        new_course_created = True
        new_course_id = course.id
        message = "Course created!"
        return  render_template(
    "_create_cover_content.html",
    course=course,
    new_course_id=new_course_id,
    message=message
) #create_cover create_cover

#end create cover ==========================

#create_course templates returning 
@teacher_bp.route('/create_course', methods=['GET'])
@login_required
def create_course():
    new_create_course = None
    if current_user.role != 'teacher':
        flash('You do not have permission to create courses.', 'danger')        
        return redirect(url_for('teacher.teacher_dashboard'))
    else: 
        return render_template('create_course.html', csrf_token=generate_csrf()) #create_course, create_course
#end create_course



@teacher_bp.route("/edit_cover", methods=["POST"])
@login_required
def edit_cover():
    course_id = request.form.get("course_id")
    if not course_id:
        return '<p class="text-red-500 mt-2">Course ID is missing!</p>'
    else:
        course = Course.query.get(course_id)
        course_title = course.title
        course_description = course.description 
        return render_template('_edit_cover.html', course_id=course_id, course_title=course_title, course_description=course_description )

@teacher_bp.route("/save_cover", methods=["POST"])
@login_required
def save_cover():
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    course_id = request.form.get("course_id")
    if course_id:
        course = Course.query.get(course_id)
        course.title = title
        course.description = description
        db.session.commit()
        new_course_created = False
        new_course_id = course.id
        message = "Course updated!"
        return render_template("_create_cover_content.html",
    course=course,
    new_course_id=new_course_id,
    message=message
) #create_cover create_cover

    else:
        return f''' invalid id '''

#=======================chapter=========================
@teacher_bp.route("/add_chapter", methods=["POST"])
@login_required
def add_chapter():
    course_id = request.form.get("course_id")

    if not course_id:
        return '<p class="text-red-500">Course ID is missing!</p>'

    course = Course.query.get(course_id)
    if not course:
        return '<p class="text-red-500">Course not found!</p>'

    # Find the next chapter order
    max_order = db.session.query(db.func.max(Chapter.order)).filter_by(course_id=course.id).scalar()
    next_order = (max_order or 0) + 1

    # Create new chapter with placeholder title
    new_chapter = Chapter(
        title=f"New Chapter {next_order}",
        course_id=course.id,
        order=next_order
    )

    db.session.add(new_chapter)
    db.session.commit()

    # After saving, return an updated snippet
    # Refresh course with new chapter included
    course = Course.query.get(course.id)

    # Render updated chapter list
    return render_template("_chapters_item.html", course=course, chapter=new_chapter)

@teacher_bp.route("/edit_chapter", methods=["POST"])
@login_required
def edit_chapter():
    chapter_id = request.form.get("chapter_id")
    if not chapter_id:
        return '<p class="text-red-500">Chapter ID is missing!</p>'

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return '<p class="text-red-500">Invalid Chapter!</p>'

    # Render a small inline edit form for this chapter
    return render_template("_chapter_edit_form.html", chapter=chapter)

@teacher_bp.route("/cancel_edit_chapter", methods=["POST"])
@login_required
def cancel_edit_chapter():
    chapter_id = request.form.get("chapter_id")
    if not chapter_id:
        return '<p class="text-red-500">Chapter ID is missing!</p>'

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return '<p class="text-red-500">Invalid Chapter!</p>'
    message = "Retrun to base"
    course = chapter.course

    # Render a small inline edit form for this chapter
    return render_template("_create_cover_content.html", 
    course=course,
    new_course_id=chapter.course.id,
    message=message)


@teacher_bp.route("/save_chapter", methods=["POST"])
@login_required
def save_chapter():
    chapter_id = request.form.get("chapter_id")
    title = request.form.get("title")

    message = "Welcome Back"

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return '<p class="text-red-500">Invalid Chapter!</p>'

    chapter.title = title
    db.session.commit()

    # Re-render the updated chapter card
    return render_template("_create_cover_content.html", 
        new_course_id=chapter.course.id, 
        course=chapter.course,
        message=message)

@teacher_bp.route("/delete_chapter_standalone", methods=["POST"])
@login_required
def delete_chapter_standalone():
    chapter_id = request.form.get("chapter_id")
    if not chapter_id:
        return "Invalid chapter", 400

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return "Chapter not found", 404

    course = chapter.course

    db.session.delete(chapter)
    db.session.commit()

    # Refresh the full chapter list after deletion
    return render_template("_chapters_list.html", course=course)


#==============session logic ======================================================


@teacher_bp.route("/add_session", methods=["POST"])
@login_required
def add_session():
    chapter_id = request.form.get("chapter_id")
    session_type = request.form.get("session_type", "learning_session")

    if not chapter_id:
        return '<p class="text-red-500">Chapter ID is missing!</p>', 400

    chapter = Chapter.query.get(chapter_id)
    if not chapter:
        return '<p class="text-red-500">Chapter not found!</p>', 404

    # Determine next order
    max_order = db.session.query(db.func.max(Session.order)).filter_by(chapter_id=chapter.id).scalar()
    next_order = (max_order or 0) + 1

    # Create session
    new_session = Session(
        title=f"New Session {next_order}",
        session_type=session_type,
        chapter_id=chapter.id,
        order=next_order
    )

    db.session.add(new_session)
    db.session.commit()

    # Refresh chapter to include the new session
    chapter = Chapter.query.get(chapter.id)

    # Return updated sessions list (not just one item!)
    return render_template("_sessions_item.html", session=new_session)





@teacher_bp.route("/edit_session", methods=["POST"])
@login_required
def edit_session():
    session_id = request.form.get("session_id")
    if not session_id:
        return '<p class="text-red-500">Session ID is missing!</p>', 400

    session = Session.query.get(session_id)
    if not session:
        return '<p class="text-red-500">Session not found!</p>', 404

    if session.session_type == "quiz_session":
        quiz = Quiz.query.filter_by(session_id=session.id).first()
        return render_template("_session_edit_form_for_quiz.html", session=session, quiz=quiz)

    # learning_session path stays as-is
    return render_template("_session_edit_form.html", session=session, course=session.chapter.course)






@teacher_bp.route("/update_session", methods=["POST"])
@login_required
def update_session():
    session_id = request.form.get("session_id")#
    title = request.form.get("title")#
    #session_type = request.form.get("session_type")

    session = Session.query.get(session_id)#
    if not session:
        return '<p class="text-red-500">Session not found!</p>', 404

    session.title = title
    #session.session_type = session_type
    db.session.commit()

    # Get the parent chapter
    chapter = session.chapter
    course =  session.chapter.course

    # Return the full chapter edit form
    return render_template("_chapter_edit_form.html", chapter=chapter , course=course)


@teacher_bp.route("/cancel_edit_session", methods=["POST"])
@login_required
def cancel_edit_session():
    session_id = request.form.get("session_id")
    if not session_id:
        return "Invalid session", 400

    session = Session.query.get(session_id)
    if not session:
        return "Session not found", 404

    session = Session.query.get(session_id)
    chapter = session.chapter 


    return render_template("_chapter_edit_form.html", chapter=chapter)




@teacher_bp.route("/delete_session_standalone", methods=["POST"])
@login_required
def delete_session_standalone():
    session_id = request.form.get("session_id")
    if not session_id:
        return "Invalid session", 400

    session = Session.query.get(session_id)
    if not session:
        return "Session not found", 404

    chapter = session.chapter

    db.session.delete(session)
    db.session.commit()

    # Return the updated sessions list for this chapter
    return render_template("_sessions_list.html", chapter=chapter)

#============================end session============================================


# ================== Materials ===================

@teacher_bp.route("/add_material", methods=["POST"])
@login_required
def add_material():
    session_id = request.form.get("session_id")
    session = Session.query.get(session_id)
    if not session:
        return '<p class="text-red-500">Invalid session!</p>', 404

    new_material = Material(name="New Material", type="text", content="", session_id=session.id)
    db.session.add(new_material)
    db.session.commit()

    return render_template("_material_edit_form.html", material=new_material)


@teacher_bp.route("/edit_material", methods=["POST"])
@login_required
def edit_material():
    # Prefer material_id since that's what your button is sending
    material_id = request.form.get("material_id")
    if not material_id:
        return '<p class="text-red-500">Material ID is missing!</p>', 400

    material = Material.query.get(material_id)
    if not material:
        return '<p class="text-red-500">Material not found!</p>', 404

    # Resolve session from material if relationship exists
    session = material.session if hasattr(material, "session") else None
    if not session:
        return '<p class="text-red-500">This material is not linked to any session!</p>', 404

    # Now you have both material and session
    return render_template("_material_edit_form.html", material=material, session=session)


def get_youtube_id(url):
    """Extract YouTube video ID from a URL, return None if not valid."""
    parsed = urlparse(url)
    # Shortened youtu.be link
    if parsed.netloc in ["youtu.be"]:
        return parsed.path[1:]  # remove leading /
    # Full youtube.com/watch link
    if parsed.netloc in ["www.youtube.com", "youtube.com"]:
        qs = parse_qs(parsed.query)
        return qs.get("v", [None])[0]
    return None

@teacher_bp.route("/update_material", methods=["POST"])
@login_required
def update_material():
    material_id = request.form.get("material_id")
    session_id = request.form.get("session_id")
    name = request.form.get("name")
    mtype = request.form.get("type")
    content = request.form.get("content") or ""

    if not material_id or not session_id:
        return '<p class="text-red-500">Material or Session ID missing!</p>', 400

    material = Material.query.get(material_id)
    if not material:
        return '<p class="text-red-500">Material not found!</p>', 404

    # Update fields
    material.name = name
    material.type = mtype
    material.content = content
    db.session.commit()

    # Return to the parent session edit form
    session = Session.query.get(session_id)
    return render_template("_session_edit_form.html", session=session)



@teacher_bp.route("/delete_material_standalone", methods=["POST"])
@login_required
def delete_material_standalone():
    material_id = request.form.get("material_id")
    material = Material.query.get(material_id)
    if not material:
        return "Material not found", 404

    session = material.session
    db.session.delete(material)
    db.session.commit()

    return render_template("_materials_list.html", session=session)


@teacher_bp.route("/cancel_edit_material", methods=["POST"])
@login_required
def cancel_edit_material():
    session_id = request.form.get("session_id")
    session = Session.query.get(session_id)
    if not session:
        return '<p class="text-red-500">Invalid session!</p>', 404

    course = session.chapter.course
    return render_template("_session_edit_form.html", session=session, course=course)
#==========================end materials=====================================

#+++++ +++++++++++++++++++++++++++++ quiz +++++++++++++++++++++++

# --- QUIZ: create one quiz per session, swap only the local block ---

@teacher_bp.route("/create_quiz", methods=["POST"])
@login_required
def create_quiz():
    session_id = request.form.get("session_id")
    if not session_id:
        return '<p class="text-red-500">Session ID is missing!</p>', 400

    session = Session.query.get(session_id)
    if not session or session.session_type != "quiz_session":
        return '<p class="text-red-500">Invalid quiz session!</p>', 400

    # If a quiz already exists, just render the item (no duplicates)
    existing = Quiz.query.filter_by(session_id=session.id).first()
    if existing:
        return render_template("_quiz_item.html", session=session, quiz=existing)

    quiz = Quiz(
    name="New Quiz",
    type="mcq",
    question={},  # empty dict
    option={},   # empty dict
    key={},       # empty dict
    session_id=session.id
)
    db.session.add(quiz)
    db.session.commit()

    # Return only the quiz item block so htmx swaps the local container
    return render_template("_quiz_item.html", session=session, quiz=quiz)


@teacher_bp.route("/delete_quiz", methods=["POST"])
@login_required
def delete_quiz():
    quiz_id = request.form.get("quiz_id")
    if not quiz_id:
        return '<p class="text-red-500">Quiz ID is missing!</p>', 400

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return '<p class="text-red-500">Quiz not found!</p>', 404

    session = quiz.session
    db.session.delete(quiz)
    db.session.commit()

    # After delete, show the "Create Quiz" button again (only that block)
    return render_template("_quiz_create_button.html", session=session)


@teacher_bp.route("/edit_quiz", methods=["POST"])
@login_required
def edit_quiz():
    quiz_id = request.form.get("quiz_id")
    if not quiz_id:
        return '<p class="text-red-500">Quiz ID is missing!</p>', 400

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return '<p class="text-red-500">Quiz not found!</p>', 404

    # Standalone quiz editing page (replace #content-wrapper)
    return render_template("_quiz_edit_form.html", quiz=quiz, session=quiz.session)

@teacher_bp.route("/update_quiz", methods=["POST"])
@login_required
def update_quiz():
    return f''' update quiz '''

#================== generate quiz =======================


#================ Gen quiz ============================


@teacher_bp.route("/generate_quiz_questions", methods=["POST"])
@login_required
def generate_quiz_questions():
    session_id = request.form.get("session_id")
    quiz_id = request.form.get("quiz_id")   
    content = request.form.get("content")
    question_type = request.form.get("question_type")
    question_count = request.form.get("question_count")
    difficulty = request.form.get("difficulty")
    blooms_level = request.form.get("bloom_level")

    question = f""" You are special quiz generating teacher . 
The following content would be used for generating questions : 

Respond ONLY in this JSON array format (do NOT include any extra text): 

============= Specific info ===================
Question count : {question_count}
Question type : {question_type}
Difficulty: {difficulty}
Bloom's level: {blooms_level}
=============================================

Before generating , please read it .

Notic : You don't need all type of questions to be generated , this is sample for future and current question type pattern that are important so that to remember it, I will provide you this pattern format in every conversation.   
for MCQ 
[  id , question , option , key , difficulty , blooms_level, type ] (answer key A,B,C,D , option must be list, type is question  type {question_type} )
for True/False
[ id , question , option, key , difficulty , blooms_level , type ] (answer key True,False , option must be list , type is question type {question_type})
for Blank 
[ id ,question, option, key , difficulty , blooms_level , type ] (answer key text , option must be default empty list , type is question type like this {question_type})

Respond ONLY in this JSON array format (do NOT include any extra text).

===========content============
Use this content : {content} 

========== Please Check the questions are JSON format valid ============== 

""" 

    completion = client.chat.completions.create(
        model="deepseek-ai/DeepSeek-V3-0324",
        messages=[{"role": "user", "content": question}],
    )
    text = completion.choices[0].message.content

    # Remove ```json ... ``` wrappers if present
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())

    default_question_set = [
    {
        "id": 1,
        "question": "Do you think addition 2 + 5 ?",
        "option": ["A", "B", "C", "D"],
        "key": "A",
        "question_type": "MCQ",
        "difficulty": "easy",
        "blooms_level": "understand"
    },
    {
        "id": 2,
        "question": "Do you think multiply 4 * 4 ?",
        "option": ["A", "B", "C", "D"],
        "key": "B",
        "question_type": "MCQ",
        "difficulty": "easy",
        "blooms_level": "understand"
    }   ]

    # match = re.search(r'\[\s*{.*?}\s*]', content_text, re.DOTALL)
    # Remove ```json ... ``` wrappers if present
    match = re.sub(r"^```json\s*|\s*```$", "", text.strip())

    if match:
        try:
            parsed_questions = json.loads(match)
        except Exception as e:
            print("JSON parsing failed, using default:", e)
            parsed_questions = default_question_set
    else:
        parsed_questions = default_question_set
        # Save to file
    teacher_id = current_user.id
    file_name = f"question{teacher_id}.json"
    file_path = os.path.join(current_app.root_path, "teacher", file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(parsed_questions, f, ensure_ascii=False, indent=4)
    print(f"Questions saved to {file_path}")

    return jsonify({
    "status": "success",
    "message": f"Questions saved to {file_path}",
    "questions": parsed_questions
})

    
#================ Gen Quiz ========================

@teacher_bp.route('/cancel_edit_quiz', methods=["POST"])
@login_required
def cancel_edit_quiz():
    session_id = request.form.get("session_id")
    session = Session.query.get(session_id)
    if not session:
        return f''' Not Session id '''
    course = session.chapter.course
    quiz = Quiz.query.filter_by(session_id=session.id).first()
    return render_template("_session_edit_form_for_quiz.html", session=session, course=course, quiz=quiz)


#=============== save =====================

@teacher_bp.route("/save_quiz", methods=["POST"])
@login_required
def save_quiz():
    try:
        print("=== save_quiz called ===")
        data = request.form.to_dict()
        print("Incoming data:", data)

        quiz_id = data.get("quiz_id")
        session_id = data.get("session_id")
        name = data.get("name")
        session = Session.query.get(session_id)
        quiz = Quiz.query.get(quiz_id)

        if not quiz_id:
            return "<p class='text-red-500'>quiz_id is required</p>", 400

        # Build teacher-specific file path
        file_name = f"question{current_user.id}.json"
        file_path = os.path.join(current_app.root_path, "teacher", file_name)
        print("File path:", file_path)

        if not os.path.exists(file_path):
            return f"<p class='text-red-500'>No quiz file found for teacher {current_user.id}</p>", 404

        # Load questions JSON file
        with open(file_path, "r", encoding="utf-8") as f:
            questions = json.load(f)

        print("Questions loaded, sample:", questions[0])

        # Fetch quiz
        quiz = Quiz.query.get(quiz_id)
        if not quiz:
            return f"<p class='text-red-500'>Quiz {quiz_id} not found</p>", 404

        # Break down into dictionaries
        questions_dict = {}
        options_dict = {}
        keys_dict = {}
        difficulty_dict = {}
        blooms_dict = {}

        for q in questions:
            qid = str(q.get("id"))  # string key for JSON
            questions_dict[qid] = q.get("question", "")
            options_dict[qid] = q.get("option", [])
            keys_dict[qid] = q.get("key", "")
            difficulty_dict[qid] = q.get("difficulty", "")
            blooms_dict[qid] = q.get("blooms_level", "")
        type_val = questions[0].get("type")


            

        # Update quiz fields
        quiz.question = questions_dict
        quiz.option = options_dict
        quiz.key = keys_dict
        quiz.difficulty = difficulty_dict
        quiz.blooms_level = blooms_dict
        quiz.session_id = session_id
        quiz.type = type_val
        quiz.name = name 

        print("Before commit quiz:", quiz.id)
        db.session.commit()
        print("After commit quiz:", quiz.id)

        return render_template("_session_edit_form_for_quiz.html", session=session, quiz=quiz)

    except Exception as e:
        db.session.rollback()
        print("Error in save_quiz:", str(e))
        return f"<p class='text-red-500'>Exception: {str(e)}</p>", 500


@teacher_bp.route("/save_quiz_json", methods=["POST"])
@login_required
def save_quiz_json():
    try:
        data = request.get_json()  # Still expects JSON from JS
        print("Received data for JSON file:", data)

        quiz_id = data.get("quiz_id")
        questions = data.get("questions", [])

        if not quiz_id:
            return jsonify({"status": "error", "message": "Quiz ID missing"}), 400

        filename = os.path.join(app.root_path, f"quiz_{quiz_id}.json")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=4)

        return jsonify({"status": "success", "message": f"Quiz saved to {filename}"})
    
    except Exception as e:
        print("Error saving quiz to JSON:", e)
        return jsonify({"status": "error", "message": str(e)}), 500



#++++++++++++++++++++++++++++++++++++++++ end quiz +++++++++++++++


@teacher_bp.route('/course/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)

    if course.teacher_id != current_user.id:
        flash('You are not authorized to delete this course.', 'danger')
        abort(403)
    
    try:
        # Get all session IDs related to the course's chapters
        sessions_to_delete = db.session.execute(
            db.select(Session.id)
            .join(Chapter)
            .filter(Chapter.course_id == course.id)
        ).scalars().all()

        if sessions_to_delete:
            # 1. Delete all materials associated with these sessions
            db.session.execute(db.delete(Material).filter(Material.session_id.in_(sessions_to_delete)))
            
            # 2. DELETE ALL QUIZZES associated with these sessions
            # This is the new, crucial step to satisfy the foreign key constraint
            db.session.execute(db.delete(Quiz).filter(Quiz.session_id.in_(sessions_to_delete)))

            # 3. Delete all sessions themselves
            db.session.execute(db.delete(Session).filter(Session.id.in_(sessions_to_delete)))

        # 4. Delete all chapters associated with the course
        db.session.execute(db.delete(Chapter).filter(Chapter.course_id == course.id))

        # 5. Delete the course itself
        db.session.delete(course)
        db.session.commit()
        flash('Course and all associated data successfully deleted!', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'danger')
    
    return redirect(url_for('teacher.teacher_dashboard'))


@teacher_bp.route('/course/<int:course_id>/course_options')
def view_course_options(course_id):
    """
    Renders the SoloLearn-style overview of course chapters for teacher preview.
    All chapters appear unlocked for the teacher.
    """
    course = Course.query.get_or_404(course_id)
    chapters = Chapter.query.filter_by(course_id=course.id).order_by(Chapter.order).all()
    
    # Fetch all chapters for this course, ordered by their sequence
    #chapters = Chapter.query.filter_by(course_id=course.id).order_by(Chapter.order_number).all()

    return render_template(
        'view_course_options.html',
        course=course,
        chapters=chapters
    )


@teacher_bp.route('/course/<int:course_id>/detailed_view')
def course_detailed_view(course_id):
    """
    Renders the SoloLearn-style overview of course chapters for teacher preview.
    All chapters appear unlocked for the teacher.
    """
    course = Course.query.get_or_404(course_id)
    chapters = Chapter.query.filter_by(course_id=course.id).order_by(Chapter.order).all()
    
    # Fetch all chapters for this course, ordered by their sequence
    #chapters = Chapter.query.filter_by(course_id=course.id).order_by(Chapter.order_number).all()

    return render_template(
        'course_detailed_view.html',
        course=course,
        chapters=chapters
    )



@teacher_bp.route('/course/<int:course_id>/preview_student_flow')
@login_required
def preview_course(course_id):
    """
    Displays a comprehensive, detailed view of a specific course for the teacher,
    including its chapters, sessions, and materials.
    """
    # Fetch the course by ID. If not found, Flask's abort(404) will be triggered.
    course = Course.query.get_or_404(course_id)
    
    # Eager-load chapters, sessions, and materials to avoid N+1 queries
    # and ensure all data needed by the template is available.
    # Assuming 'chapters' is a relationship on Course, 'sessions' on Chapter,
    # and 'materials' on Session.
    chapters = Chapter.query.filter_by(course_id=course.id).order_by(Chapter.order).all()
    
    # Manually attach sessions and materials to avoid complex joinedload
    # if relationships aren't directly nested for eager loading in one query
    for chapter in chapters:
        chapter.sessions = Session.query.filter_by(chapter_id=chapter.id).order_by(Session.order).all()
        for session in chapter.sessions:
            session.materials = Material.query.filter_by(session_id=session.id).order_by(Material.id).all() # Assuming Material has an 'id' or 'order'
            
    # Attach the fetched chapters (which now have their sessions and materials)
    # to the course object for easy access in the template.
    course.chapters = chapters

    return render_template(
        'preview_student_course_flow.html',
        course=course
    )

@teacher_bp.route('/course/<int:course_id>/session/<int:session_id>/preview')
@login_required
def preview_course_session(course_id, session_id):
    """
    Renders the content of a specific session for teacher preview,
    including placeholders for progression and coins.
    """

    course = Course.query.get_or_404(course_id)
    session = Session.query.get_or_404(session_id)
    quizzes = Quiz.query.filter_by(session_id=session.id).all()
    structured_quiz_data = []
    # Assuming 'quizzes' contains the list of Quiz objects for a session
    if quizzes:
        quiz_object = quizzes[0]
        question_keys = quiz_object.question.keys()
        for key in question_keys:
            try:
                question_data = {
                "id": int(key),
                "question": quiz_object.question[key],
                "option": quiz_object.option[key],
                "key": quiz_object.key[key],
                "difficulty": quiz_object.difficulty[key],
                "blooms_level": quiz_object.blooms_level[key],
                "type": quiz_object.type }
                structured_quiz_data.append(question_data)
            except KeyError as e:
                print(f"Skipping question {key} due to missing data: {e}")
    print("structured_quiz_data  : ", structured_quiz_data )
    quiz_data = [
    {
        "id": 1,
        "question": "What does returning a function without parentheses (e.g., return first_child) indicate in Python?",
        "option": [
            "It executes the function immediately",
            "It returns a reference to the function",
            "It returns the function's output value",
            "It creates a new instance of the function"
        ],
        "key": "B",
        "difficulty": "medium",
        "blooms_level": "Understand",
        "type": "MCQ"
    },
    {
        "id": 2,
        "question": "In the parent() function example, what will first() return when called after first = parent(1)?",
        "option": [
            "'Hi, I'm Elias'",
            "'Call me Ester'",
            "A reference to first_child function",
            "An error because first is not callable"
        ],
        "key": "A",
        "difficulty": "medium",
        "blooms_level": "Understand",
        "type": "MCQ"
    },
    {
        "id": 3,
        "question": "What is the main difference between returning first_child and first_child() from a function?",
        "option": [
            "first_child returns a string, first_child() returns a function",
            "first_child returns a function reference, first_child() executes the function",
            "first_child is invalid syntax, first_child() is correct",
            "There is no difference between them"
        ],
        "key": "B",
        "difficulty": "medium",
        "blooms_level": "Understand",
        "type": "MCQ"
    },
    {
        "id": 4,
        "question": "What does the output '<function parent.<locals>.first_child at 0x7f599f1e2e18>' indicate?",
        "option": [
            "The memory address where the function result is stored",
            "A reference to the local first_child function inside parent()",
            "An error message from Python",
            "The documentation string of the function"
        ],
        "key": "B",
        "difficulty": "medium",
        "blooms_level": "Understand",
        "type": "MCQ"
    },
    {
        "id": 5,
        "question": "How does Python allow you to use the returned function references (first and second) from parent()?",
        "option": [
            "They can be called like regular functions",
            "They can only be used within the parent function",
            "They require special syntax to execute",
            "They are not usable outside the parent function"
        ],
        "key": "A",
        "difficulty": "medium",
        "blooms_level": "Understand",
        "type": "MCQ"
    }
]



    quiz_data = structured_quiz_data # Basic validation: ensure the session belongs to the course and chapter
    if session.chapter.course_id != course.id: # Assuming Session has a 'chapter' relationship
        abort(404)

    if course.teacher_id != current_user.id:
        flash('You do not have permission to preview this course session.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    # Retrieve all sessions in the current chapter to determine next/previous
    chapter_sessions = db.session.execute(
        db.select(Session)
        .filter_by(chapter_id=session.chapter_id)
        .order_by(Session.title) # Or Session.order if you add it
    ).scalars().all()

    current_session_index = chapter_sessions.index(session)
    previous_session = chapter_sessions[current_session_index - 1] if current_session_index > 0 else None
    next_session = chapter_sessions[current_session_index + 1] if current_session_index < len(chapter_sessions) - 1 else None

    # Dummy values for progression and coins for teacher preview
    total_sections = 5 # Example: assume each session has 5 conceptual sections
    current_section = 1 # Teacher starts at the beginning for preview

    return render_template(
        'course_session_view.html',
        course=course,
        session=session,
        previous_session=previous_session,
        next_session=next_session,
        total_sections=total_sections,
        current_section=current_section,
        quiz_data = quiz_data
    )



    
@teacher_bp.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)

    # Authorization check
    if course.teacher_id != current_user.id:
        flash('You are not authorized to edit this course.', 'danger')
        return redirect(url_for('teacher.teacher_dashboard'))

    # Handle the form submission (POST request)
    if request.method == 'POST':
        try:
            # Get the updated title and description from the form data
            course_title = request.form.get('title')
            course_description = request.form.get('description')

            # Update the course object with the new data
            course.title = course_title
            course.description = course_description

            # Commit the changes to the database
            db.session.commit()
            
            flash('Course details updated successfully!', 'success')
            return redirect(url_for('teacher.edit_course', course_id=course.id))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('teacher.edit_course', course_id=course.id))
    message = "Edit Your Course !"


    # Handle the page display (GET request)
    # This part remains the same, it just renders the template
    return render_template('_edit_cover_content.html',  course=course,
    new_course_id=course.id,
    message=message)
#=================================================================

@teacher_bp.route('/edit_course/<int:course_id>/update', methods=['POST' , "GET"])
@login_required
def update_course_content(course_id):
    """
    Handles a POST request to update course details and all nested content.
    This route uses a "delete and recreate" strategy for nested content to ensure consistency.
    """
    course = Course.query.get_or_404(course_id)
    if course.teacher_id != current_user.id:
        flash('You are not authorized to edit this course.', 'danger')
        abort(403)

    try:
        data = request.get_json()
        course_title = data.get('title')
        course_description = data.get('description')
        course_chapters_data = data.get('chapters')

        if not course_title:
            return jsonify({'success': False, 'message': 'Course title is required.'}), 400

        # Update the course's top-level details
        course.title = course_title
        course.description = course_description
        db.session.commit()

        # Delete all existing nested content (chapters, sessions, materials)
        # SQLAlchemy with cascade="all, delete-orphan" handles this for us
        db.session.execute(db.delete(Chapter).filter_by(course_id=course.id))
        db.session.commit()

        # Recreate the nested content from the new data
        if course_chapters_data:
            for chapter_order, chapter_data in enumerate(course_chapters_data):
                if not chapter_data.get('title'):
                    return jsonify({'success': False, 'message': f'Chapter at order {chapter_order + 1} is missing a title.'}), 400
                
                new_chapter = Chapter(
                    title=chapter_data['title'],
                    course_id=course.id,
                    order=chapter_order + 1
                )
                db.session.add(new_chapter)
                db.session.commit() # Commit to get new_chapter.id

                for session_order, session_data in enumerate(chapter_data.get('sessions', [])):
                    session_title = session_data.get('title') or session_data.get('quiz_name')
                    if not session_title:
                        return jsonify({'success': False, 'message': f'Session is missing a title in chapter "{new_chapter.title}".'}), 400
                    
                    new_session = Session(
                        title=session_title,
                        session_type=session_data['type'],
                        chapter_id=new_chapter.id,
                        order=session_order + 1
                    )
                    db.session.add(new_session)
                    db.session.commit() # Commit to get new_session.id
                    
                    if session_data['type'] == 'learning_session':
                        for material_data in session_data.get('materials', []):
                            if not material_data.get('name') or not material_data.get('content'):
                                return jsonify({'success': False, 'message': f'Material is missing a name or content in session "{new_session.title}".'}), 400
                            new_material = Material(
                                name=material_data['name'],
                                type=material_data['type'],
                                content=material_data['content'],
                                session_id=new_session.id
                            )
                            db.session.add(new_material)
                
        db.session.commit()
        return jsonify({'success': True, 'message': 'Course updated successfully!'}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Error updating course content: {e}")
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500


# --- Individual Deletion Routes ---

@teacher_bp.route('/chapter/<int:chapter_id>/delete', methods=['POST'])
@login_required
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    if chapter.course.teacher_id != current_user.id:
        flash('You are not authorized to delete this chapter.', 'danger')
        abort(403)
    try:
        db.session.delete(chapter)
        db.session.commit()
        flash('Chapter and all its content deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting chapter: {str(e)}', 'danger')
    return redirect(url_for('teacher.edit_course', course_id=chapter.course_id))


@teacher_bp.route('/session/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    session = Session.query.get_or_404(session_id)
    if session.chapter.course.teacher_id != current_user.id:
        flash('You are not authorized to delete this session.', 'danger')
        abort(403)
    try:
        db.session.delete(session)
        db.session.commit()
        flash('Session and all its materials deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting session: {str(e)}', 'danger')
    return redirect(url_for('teacher.edit_course', course_id=session.chapter.course_id))


@teacher_bp.route('/material/<int:material_id>/delete', methods=['POST'])
@login_required
def delete_material(material_id):
    material = Material.query.get_or_404(material_id)
    if material.session.chapter.course.teacher_id != current_user.id:
        flash('You are not authorized to delete this material.', 'danger')
        abort(403)
    try:
        db.session.delete(material)
        db.session.commit()
        flash('Material deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting material: {str(e)}', 'danger')
    return redirect(url_for('teacher.edit_course', course_id=material.session.chapter.course_id))

@teacher_bp.route('/material/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete_quiz_(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if quiz.session.chapter.course.teacher_id != current_user.id:
        flash('You are not authorized to delete this material.', 'danger')
        abort(403)
    try:
        db.session.delete(quiz_id)
        db.session.commit()
        flash('Material deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting material: {str(e)}', 'danger')
    return redirect(url_for('teacher.edit_course', course_id=quiz.session.chapter.course_id))


# --- Existing: Preview Student Course Flow Route ---


'''@teacher_bp.route('/course/<int:course_id>/progress')
def view_student_progress(course_id):
    enroll = Enroll.query.get_or_404(course_id).all()
    learning_curve = LearningCurve.query.get(enroll.id) #how to all data are extract 
    #in this case I want to extract the enrollments id 
    course = Course.query.get_or_404(course_id)
    students_data = {
        "students": [
            {"name": "Alpha", "data": [[1, 1], [2, 15], [4, 13], [8, 1], [16, 11]]},
            {"name": "Bravo", "data": [[1, 3], [13, 4.5], [5, 4], [10, 1.5], [20, 0.9]]},
            {"name": "Charlie", "data": [[1, 17], [2.5, 16], [5, 5], [10, 2], [15, 1.3]]},
            {"name": "Delta", "data": [[1, 15], [2, 4], [4, 5], [8, 1.5], [12, 1.1]]},
            {"name": "Echo", "data": [[1, 17], [2, 17], [3, 14], [6, 2], [11, 12]]}
        ]
    }

    return render_template(
        'view_student_progress.html', 
        course=course, 
        raw_data=json.dumps(students_data))'''

'''@teacher_bp.route('/course/<int:course_id>/progress')
def view_student_progress(course_id):
    # Get the course
    course = Course.query.get_or_404(course_id)

    # Get all enrollments for this course (with student + learning_curves eager-loaded)
    enrollments = (
        Enroll.query.options(
            joinedload(Enroll.student),          # load User
            joinedload(Enroll.learning_curves)   # load LearningCurve
        )
        .filter_by(course_id=course_id)
        .all()
    )

    students_data = {"students": []}

    for enrollment in enrollments:
        student_name = enrollment.student.username  # ✅ from User model

        # Get learning curve attempts sorted by attempt_number
        curves = sorted(enrollment.learning_curves, key=lambda lc: lc.attempt_number)

        # Transform into [[attempt_number, error_count], ...]
        dataset = [[lc.attempt_number, lc.error_count] for lc in curves]

        students_data["students"].append({
            "name": student_name,
            "data": dataset
        })
    print("students data : ==== ", students_data)

    return render_template(
        'view_student_progress.html',
        course=course,
        raw_data=json.dumps(students_data)
    )'''





@teacher_bp.route('/course/<int:course_id>/progress')
def view_student_progress(course_id):
    course = Course.query.get_or_404(course_id)

    enrollments = Enroll.query.filter_by(course_id=course_id).options(joinedload(Enroll.student)).all()

    students_data = {"students": []}
    
    # Get all chapters for this course, ordered by their order field
    chapters = Chapter.query.filter_by(course_id=course_id).order_by(Chapter.order).all()
    chapter_map = {chapter.id: chapter for chapter in chapters}

    for enrollment in enrollments:
        student_name = enrollment.student.username
        student_id = enrollment.student.id

        # Aggregate across chapters for this enrollment+course:
        rows = (
            db.session.query(
                LearningCurve.attempt_number,
                func.sum(LearningCurve.error_count).label("errors_sum")
            )
            .filter(
                LearningCurve.enrollment_id == enrollment.id,
                LearningCurve.course_id == course_id
            )
            .group_by(LearningCurve.attempt_number)
            .order_by(LearningCurve.attempt_number)
            .all()
        )

        # Convert SQL result into [[attempt, sum], ...]
        dataset = [[int(r.attempt_number), int(r.errors_sum)] for r in rows]

        # Get chapter progress from JSON certificate file
        chapter_progress = get_chapter_progress(student_id, chapters, chapter_map)

        students_data["students"].append({
            "name": student_name,
            "data": dataset,
            "chapter_progress": chapter_progress,
            "student_id": student_id
        })
    #print("chapter_progress === ", chapter_progress)
    #print("student data ==== ", students_data)
    #print("studentData ", students_data)
    return render_template(
        'view_student_progress.html',
        course=course,
        raw_data=json.dumps(students_data),
        chapters_data=json.dumps({
            "chapters": [
                {
                    "id": chapter.id,
                    "title": chapter.title,
                    "order": chapter.order
                }
                for chapter in chapters
            ]
        })
    )

def get_chapter_progress(student_id, chapters, chapter_map):
    """Read chapter progress from JSON certificate files"""
    chapter_progress = []
    #print("get_chapter_progress = " , chapter_map , "   chapter_map")
    # Path to certificate files - adjust based on your actual path structure
    score_path = os.path.join(current_app.root_path, f"score{student_id}.json")
    cert_path = os.path.join(current_app.root_path, f"certificate{student_id}.json") 
    #cert_path = f"temp/app/certificate{student_id}.json"
    
    # Default: all chapters not started
    default_progress = {chapter.id: "not_started" for chapter in chapters}
    
    try:
        if os.path.exists(cert_path):
            with open(cert_path, 'r') as f:
                cert_data = json.load(f)
                #print("cert_data = ", cert_data)
            
            # The JSON structure: {"student_id": {"chapter_id": 1_or_0, ...}}
            student_cert_data = cert_data.get(str(student_id), {})
            
            for chapter in chapters:
                chapter_id_str = str(chapter.id)
                if chapter_id_str in student_cert_data:
                    result = student_cert_data[chapter_id_str]
                    if result == 1:
                        default_progress[chapter.id] = "completed"
                    elif result == 0:
                        default_progress[chapter.id] = "failed"
                # If chapter not in cert data, it remains "not_started"
        else:
            print(f"Certificate file not found: {cert_path}")
            
    except Exception as e:
        print(f"Error reading certificate file for student {student_id}: {e}")
    
    # Convert to the format expected by the frontend
    for chapter in chapters:
        # Determine if this is the current chapter (first not_started chapter)
        status = default_progress[chapter.id]
        
        chapter_progress.append({
            "chapter": chapter.order,  # Use order for display
            "chapter_id": chapter.id,  # Keep ID for reference
            "status": status,
            "title": chapter.title
        })
    #print("chapter_progress = ", chapter_progress)
    # Mark the current chapter (first chapter that's not completed)
    #mark_current_chapter(chapter_progress,student_id)
    chapter_progress_sorted = sorted(chapter_progress, key=lambda x: x["chapter"])
    #print("chapter_progress_sorted   ", chapter_progress_sorted)
    return chapter_progress_sorted

'''def mark_current_chapter(chapter_progress,student_id):
    """Mark the first incomplete chapter as current"""
    chapter_progress_sorted = sorted(chapter_progress, key=lambda x: x["chapter"])
    score_path = os.path.join(current_app.root_path, f"score{student_id}.json")
    print("mark_current_chapter === ", chapter_progress)
    if os.path.exists(score_path):
        print("mark_current_chapter   ", score_path)
    else:
        print("mark_current_chapter    ", score_path)



    for progress in chapter_progress_sorted:
        if progress["status"] == "not_started":
            progress["status"] = "current"
            break  # Only mark the first one as current
    
    return chapter_progress_sorted'''