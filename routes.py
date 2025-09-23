# tumedx_platform/app/student/routes.py
from flask import render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.student import student_bp # Import the blueprint instance
from flask import render_template, url_for, flash, redirect, abort, request, jsonify, session, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import selectinload
from sqlalchemy import desc, asc
from app import db 
from . import student_bp
from flask_wtf.csrf import generate_csrf 
from flask_login import login_required, current_user
from app.teacher import teacher_bp
from app.models import db, User, Course, Chapter, Session, Material, Quiz , Enroll, Progress , LearningCurve 
import json
import os
from urllib.parse import urlparse, parse_qs
import requests
from flask import jsonify
import re  
from flask import render_template_string
from flask import current_app 
from datetime import datetime, timedelta
import string 

 
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime

from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

 
 

JSON_FILE = os.path.join("app", "student", "enrollment.json")

PISTON_API_URL = "https://emkc.org/api/v2/piston/execute"

LANG_MAP = {
    'python': 'python',
    'clike': 'c++',  # Piston uses 'c++' for C++
    'javascript': 'javascript',
    'php': 'php',
    'java': 'java',
}

LETTER_TO_INDEX = {
    'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5
}


#this is I usage
def models_helper(student_id):
    print("student id = " ,student_id)
    enrollment = Enroll.query.filter_by(student_id = student_id).all()
    #print("enrollment  ===== " ,enrollment)
    course_id_list = []
    for e in enrollment:
        course_id_list.append(e.course_id)
    #print("course_temp ", course_id_list)
    
    course_chapter_id_dict = {}
    course_chapter_name_dict = {}
    chapter_obj_list = []
    for c in course_id_list:
        chapter = Chapter.query.filter_by(course_id=c).all()
        chapter_obj_list.append(chapter)
        course_chapter_id_dict[c] = []
        for ch in chapter:
            course_chapter_id_dict[c].append(ch.id)

    #print("course_id : [ chapter_id ]  ", course_chapter_id_dict)
    #print("chapter obj list ", chapter_obj_list)
    course_chapter_session_dict = {}
    for co,ch_obj_list in zip(course_chapter_id_dict,chapter_obj_list):
        course_chapter_session_dict[co] = {}
        for ch in ch_obj_list:
            course_chapter_session_dict[co][ch.id] = []
        for ch in ch_obj_list:
            session = Session.query.filter_by(chapter_id=ch.id).all()
            for s in session:
                course_chapter_session_dict[co][ch.id].append(s.id)

    return course_chapter_session_dict

def chapter_progress_session(chapter_id,student_id): #chapter view usage 
    print("this is chapter_progress_session, chapter id = ", chapter_id)

def course_progress_chapter(course_id,student_id): #learning room usage 
    print("this is course_progress_chapter , course id = " ,course_id)



@student_bp.route('/dashboard')
@login_required # Requires user to be logged in
def student_dashboard():
    """Renders the student dashboard."""
    # Ensure only student users can access this page
    if current_user.role != 'student':
        flash('You do not have permission to access the student dashboard.', 'danger')
        # Redirect to their respective dashboard or guest page
        if current_user.role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif current_user.role == 'teacher':
            return redirect(url_for('teacher.teacher_dashboard'))
        else:
            return redirect(url_for('main.guest_page')) # Fallback for unknown roles or logged out
    student = User.query.get(current_user.id)
    name = student.username
    courses = Course.query.all()
    enroll = Enroll.query.all()

    enrolled_courses = (
        Course.query
        .join(Enroll)
        .filter(Enroll.student_id == current_user.id)
        .all()
    )
    enrollment_course_list = [course.id for course in enrolled_courses]
    num_enrollment_courses = len(enrollment_course_list)
    models_helper(current_user.id)



    course_description = [(c.title, c.description) for c in courses]

    return render_template('student_dashboard.html' , 
        num_enrollment_courses=num_enrollment_courses, 
        name=name , 
        enrollment_course_list=enrollment_course_list, 
        course=courses)



@student_bp.route("/enroll_course/<int:course_id>", methods=["POST"])
@login_required
def enroll_course(course_id):
    # Only students can enroll
    if current_user.role != 'student':
        return "Unauthorized", 403

    course = Course.query.get(course_id)
    if not course:
        return "Course not found", 404
    print("Enrollment is successful  ======================= ")
    enroll_course = Enroll(
        student_id=current_user.id,
        course_id=course_id,
        grade="O",
        status="Active"
        )
    db.session.add(enroll_course)
    db.session.commit()

    return render_template("partials/enrolled_message.html", course=course)




@student_bp.route("/my_course", methods=["GET"])
@login_required
def my_course():
    # Get the courses the student is enrolled in
    enrolled_courses = (
        Course.query
        .join(Enroll)
        .filter(Enroll.student_id == current_user.id)
        .all()
    )

    # Build a list of course IDs for template logic (if needed)
    enrollment_course_list = [c.id for c in enrolled_courses]
    certification = 0

    return render_template(
        "partials/my_course.html",
        courses=enrolled_courses,
        enrollment_course_list=enrollment_course_list,
        certification = certification
    )


#==================== quick ========================


@student_bp.route("/course/<int:course_id>/<int:certification>/learning-room", methods = ['GET',"POST"])
@login_required
def learning_room(course_id,certification):
    course = Course.query.get_or_404(course_id)
    chapters = Chapter.query.filter_by(course_id=course_id).order_by(Chapter.order).all()
    chapter_id_dict = models_helper(current_user.id)[course_id]
    print("This is chapter_id_dict = ", chapter_id_dict )
    enrollment_list = Enroll.query.filter_by(student_id=current_user.id,course_id=course_id).all()
    enrollment_id = enrollment_list[0].id

    #Grading work or finish controls logic
    student_id = current_user.id  
    file_name = f"score{student_id}.json"
    certificate_file_name = f"certificate{student_id}.json" 
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_path, file_name)
    certificate_json_path = os.path.join(base_path,certificate_file_name)

    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            score_data = json.load(f)
    else:
        score_data = None

    if  os.path.exists(certificate_json_path):
        with open(json_path, "r") as f :
            certificate_data = json.load(f)
    else:
        certificate_data = None

    course_id = course_id
    for ch in chapter_id_dict:
        if score_data and score_data[str(student_id)] :
            if str(ch) in score_data[str(student_id)]:
                original_score = score_data[str(student_id)][str(ch)]
                print("original_score ====== ", original_score)
                if original_score < 1:
                    score_data[str(student_id)][str(ch)] = 0 
                    with open(json_path, "w") as f:
                        json.dump(score_data, f, indent=4)
                else:
                    score_data[str(student_id)][str(ch)] = 1
                    with open(certificate_json_path, "w") as f:
                        json.dump(score_data, f, indent=4)
                    if score_data[str(student_id)][str(ch)] != 1:
                        score_data[str(student_id)][str(ch)] = 0
                        with open(json_path, "w") as f:
                            json.dump(score_data, f, indent=4)





    #Grading works or finish controls logic

    #first

    chapter_id_list = list(chapter_id_dict.keys())
    print("chapter id list ",chapter_id_list)

    for chapter_id in chapter_id_list:
        progress_ = Progress.query.filter_by(course_id=course_id,chapter_id=chapter_id,enrollment_id=enrollment_id).all()
        if len(progress_) == 0:
            print("len(progress) == ", 0)
            print("chapter_id == ", chapter_id )
            for c_id , s_id_list in chapter_id_dict.items():
                if c_id == chapter_id:
                    for s_id in s_id_list:
                        progress = Progress(enrollment_id=enrollment_id,course_id=course_id,chapter_id=c_id,session_id=s_id)
                        db.session.add(progress)
                        db.session.commit()
                        #print("s_id = ", s_id)
        else:
            detect_pg_uncomplete = []
            print("len(progress) != ", 0) 



    lock_chapter_list = []        
    check = Progress.query.filter_by(course_id=course_id,enrollment_id=enrollment_id).all()
    for c in check:
        if c.completed is False:
            lock_chapter_list.append(c.chapter_id)
    lock_chapter_list = list(set(lock_chapter_list))
    
    #test_temp = []
    #print(test_temp[1:])

    if len(chapter_id_list) != 0 and len(lock_chapter_list) != 0 :
        inter_set = set(lock_chapter_list) & set(lock_chapter_list)
        inter_list = sorted(list(inter_set))
        lock_chapter_id_list = inter_list[1:]
        print("intersection of chapter id list - lock chapter id list ", lock_chapter_id_list)
    elif len(chapter_id_list) != 0 and len(lock_chapter_list) == 0:
        lock_chapter_id_list = []
        chapter_id_list = chapter_id_list  
    elif len(chapter_id_list) == 0 and len(lock_chapter_list) != 0:
        lock_chapter_id_list = []
        chapter_id_list = []
    else:
        print("lock chapter id list ", lock_chapter_list)
        print("chapter id list ", chapter_id_list)

    progress = Progress.query.filter_by(enrollment_id=enrollment_id).all()
    detect_completed = []
    if progress:
        for p in progress:
            if p.completed == 1:
                detect_completed.append(1)
            else:
                detect_completed.append(0)
        if detect_completed.count(0) >= 1:
            pass 
        else: 
            certification = 1


    return render_template(
        "partials/learning_room.html",
        course=course,
        chapters=chapters,
        lock_chapter_id_list=lock_chapter_id_list,
        chapter_id_list=chapter_id_list,
        enrollment_id=enrollment_id,
        certification=certification
    )
    

#reset starting

@student_bp.route("/reset/<int:chapter_id>/<int:course_id>/<int:enrollment_id>")
@login_required
def reset(chapter_id,course_id,enrollment_id):
    try:
        db.session.query(LearningCurve).filter_by(enrollment_id=enrollment_id,chapter_id=chapter_id).delete(synchronize_session='fetch')
        print("this is ok in delete in reset practice ")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("this is failure in delete in reset practice") 
    certification = 0 
    progress = Progress.query.filter_by(enrollment_id=enrollment_id).all()
    detect_completed = []
    if progress:
        for p in progress:
            if p.completed == 1:
                detect_completed.append(1)
            else:
                detect_completed.append(0)
        if detect_completed.count(0) >= 1:
            pass 
        else: 
            certification = 1
    return redirect(url_for("student.learning_room", chapter_id=chapter_id, course_id=course_id, certification=certification))

#reset ending

@student_bp.route("/chapter/<int:chapter_id>/<int:enrollment_id>")
@login_required
def chapter_view(chapter_id,enrollment_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    # get sessions ordered by "order"
    sessions = Session.query.filter_by(chapter_id=chapter_id).order_by(Session.order).all()
    
    #start to restrict over 5 attempts 

    LC = LearningCurve.query.filter_by(enrollment_id=enrollment_id).order_by(LearningCurve.attempt_number.desc()).first()
    #LC = LearningCurve.query.filter_by(enrollment_id=enrollment_id).all()
    results = LearningCurve.query.filter_by(enrollment_id=enrollment_id,chapter_id=chapter_id).all()
    results_data = {}
    detect_exceed = []
    if results:
        for r in results:
            results_data[r.attempt_number] = r.error_count
            if r.attempt_number >= 5:
                detect_exceed.append(r.course_id)

    certification = 0
    detect_completed = []            
    progress__ = Progress.query.filter_by(enrollment_id=enrollment_id).all()
    for p in progress__:
        if p.completed == 0 :
            detect_completed.append(0)
    if len(detect_completed) != 0:
        certification = 1

    if LC and len(detect_exceed) != 0:
        print("You exceed 5 times")
        return render_template(
        'partials/attempt_time_exceed.html',
        chapter_id=chapter_id,
        course_id=LC.course_id,
        results_data=results_data,
        enrollment_id=enrollment_id,
        certification=certification
    )

    #end to restrict over 5 attempts 

    if not sessions:
        flash("This chapter has no sessions yet.", "warning")
        return redirect(url_for("student.learning_room", course_id=chapter.course_id))



    detect_completed = []
    detect_existing = []
    quiz_session_count = []

    for session in sessions:
        progress = Progress.query.filter_by(
        enrollment_id=enrollment_id,
        course_id=chapter.course_id,
        chapter_id=chapter_id,
        session_id=session.id).all()
        if len(progress) != 0:
            if progress[0].completed == 1:
                detect_completed.append(1)
            detect_existing.append(1)
        if session.session_type == "quiz_session":
            quiz_session_count.append(1)

    if len(detect_completed) == 0 and len(detect_existing) != 0:
        print("detect completed first debug", len(detect_completed), " vs ", len(detect_existing))
        
        learning_curve = LearningCurve.query.filter_by(
            enrollment_id=enrollment_id,
            course_id=chapter.course_id,
            chapter_id=chapter_id).first()

        if learning_curve == None :
            #error setting 
            error_count = 0
            curve_set = LearningCurve(
                enrollment_id=enrollment_id,
                course_id=chapter.course_id,
                chapter_id=chapter_id,
                attempt_number = 1,
                error_count = error_count)
            db.session.add(curve_set)
            db.session.commit()
            print("Before condition, attempt_number = ", curve_set.attempt_number)
        else:
            temp_attempt = []
            temp_error_count = []
            learning_curve = LearningCurve.query.filter_by(
                enrollment_id=enrollment_id,
                course_id=chapter.course_id).all()
            for lc in learning_curve:
                temp_attempt.append(lc.attempt_number)
                temp_error_count.append(lc.error_count)
            print("/ntemp_attempt == ", temp_attempt)
            print("/ntemp_error_count == ", temp_error_count) ######## 


    elif len(detect_completed) != 0 and len(detect_existing) != 0:
        print("detect completed second debug", len(detect_completed), " vs ", len(detect_existing))
        if len(detect_completed) == len(detect_existing):
            learning_curve = LearningCurve.query.filter_by(
            enrollment_id=enrollment_id,
            course_id=chapter.course_id,
            chapter_id=chapter_id).order_by(LearningCurve.chapter_id.desc()).first()
            temp_attempt = []
            temp_error_count = []
            learning_curve_check = LearningCurve.query.filter_by(
                enrollment_id=enrollment_id,
                course_id=chapter.course_id).all()
            for lc in learning_curve_check:
                temp_attempt.append(lc.attempt_number)
                temp_error_count.append(lc.error_count)
            print("/ntemp_attempt == ", temp_attempt)
            print("/ntemp_error_count == ", temp_error_count)
            if learning_curve != None: #existing row in LC and error is not zero , not any quiz
                latest_progress = Progress.query.filter_by(
                    enrollment_id=enrollment_id,
                    course_id=chapter.course_id,
                    chapter_id=chapter_id
                    ).order_by(Progress.id.desc()).first()
                print("latest progress extrace ", latest_progress)
                if latest_progress and latest_progress.completed == 1:
                    # get the latest LC row
                    learning_curve = LearningCurve.query.filter_by(
                    enrollment_id=enrollment_id,
                    course_id=chapter.course_id,
                    chapter_id=chapter_id).order_by(LearningCurve.id.desc()).first()
                    if learning_curve:
                        # create a NEW row with +1 attempt
                        new_lc = LearningCurve(
            enrollment_id=learning_curve.enrollment_id,
            course_id=learning_curve.course_id,
            chapter_id=learning_curve.chapter_id,
            attempt_number=learning_curve.attempt_number + 1,
            error_count=0  # reset or carry over? depends on your logic
        )
                        db.session.add(new_lc)
                        db.session.commit()
                        print("✅ New attempt created:", new_lc.attempt_number)




    #start certification 
    certification = 0
    certified_progress = Progress.query.filter_by(
                    enrollment_id=enrollment_id,
                    course_id=chapter.course_id,
                    chapter_id=chapter_id
                    ).all()
    detect_completed = []
    if certified_progress:
        for cp in certified_progress:
            if cp.completed == 1:
                detect_completed.append(1)
            else:
                detect_completed.append(0)
        if detect_completed.count(0) >= 1 :
            certification = 0
        else:
            certification = 1 
    #end certification
    # start with the first session
    first_session = sessions[0]
    return redirect(url_for("student.session_view", session_id=first_session.id, enrollment_id=enrollment_id,certification=certification))


#progress definition 
@student_bp.route("/session/<int:session_id>/<int:enrollment_id>/<int:certification>")
@login_required
def session_view(session_id, enrollment_id,certification):
    session = Session.query.get_or_404(session_id)
    enroll = Enroll.query.get_or_404(enrollment_id)
    course_id = enroll.course_id
    chapter_id = session.chapter_id
    progress = None

    #progress definition for learning session
    if session.session_type == "learning_session":
        progress = Progress.query.filter_by(
        enrollment_id=enrollment_id,
        course_id=course_id,
        chapter_id=chapter_id,
        session_id=session.id
    ).first()
        if progress:
            # Example: mark as completed
            progress.completed = True
            # or if you need to increment something numeric (not completed because it's bool):
            # progress.percentage = progress.percentage + 10  # for example
        else:
            # If not exist → create new
            progress = Progress(
            enrollment_id=enrollment_id,
            course_id=course_id,
            chapter_id=chapter_id,
            session_id=session.id,
            completed=True
        )
            db.session.add(progress)

        db.session.commit()

    # ✅ Find the next session
    next_session = (
        Session.query.filter(
            Session.chapter_id == session.chapter_id,
            Session.order > session.order
        )
        .order_by(Session.order)
        .first()
    )



    #progress definition for quiz 

    if session.session_type == "quiz_session":
        progress = Progress.query.filter_by(
        enrollment_id=enrollment_id,
        course_id=course_id,
        chapter_id=chapter_id,
        session_id=session_id
    ).first()

        if progress:
            progress.completed = True
            print("progress is existing ", progress)
            progress.percentage = None
        else:
            progress = Progress(
            enrollment_id=enrollment_id,
            course_id=course_id,
            chapter_id=chapter_id,
            session_id=session_id,
            completed=True,
            percentage=None
        )
        db.session.add(progress)
    db.session.commit()
    pg = Progress.query.filter_by(
        enrollment_id=enrollment_id,
        course_id=chapter_id,
        chapter_id=chapter_id,
        session_id=session_id,
        completed=True).first()
   




    alphabet = list(string.ascii_uppercase)  # ['A','B','C','D', ...]

    return render_template(
        "partials/session_view.html",
        session=session,
        materials=session.materials,
        quizzes=session.quizzes,
        next_session=next_session,
        enrollment_id=enrollment_id,
        alphabet=alphabet,  # ✅ pass alphabet into template
        certification=certification
    )


@student_bp.route("/submit_quiz/<int:quiz_id>", methods=["POST"])
@login_required
def submit_quiz(quiz_id):
    data = request.get_json()
    enrollment_id = data.get("enrollment_id")
    answers = data.get("answers", {})
    print("Enrollment id ", enrollment_id)
    print("📩 Received answers:", answers)

    # Example: calculate error_count
    quiz = Quiz.query.get_or_404(quiz_id)
    error_count = 0
    index = {"A" : 0 , "B": 1 , "C" : 2 , "D" : 3, "True": 0, "False": 1}

    #user_answer to index
    print("==================== quiz.option ================= ", quiz.option)
    index_list = []

    if quiz.type == "MCQ" or quiz.type == "TF": 
        for key,val in quiz.key.items():
            if isinstance(val, list):
                for v in val:
                    print("key ",index[v])
                    index_list.append(index[v])
            else:
                print("key ", index[val])
                index_list.append(index[val])

        print("index_list ", index_list)
    
        for val,l,a in zip(quiz.option.values(),index_list,answers.values()):
            if val[l] != a:
                error_count += 1
    else:
        for a,key in zip(answers.values(),quiz.key.values()):
            if a != key:
                error_count += 1

    #quiz number 
    given_score = len(quiz.key.values())

    

    print("error count ===== ....... ", error_count)

    session = Session.query.get_or_404(quiz.session_id)
    chapter = Chapter.query.get_or_404(session.chapter_id)
    course = Course.query.get_or_404(chapter.course_id)
    learning_curve = LearningCurve.query.filter_by(
        enrollment_id=enrollment_id,
        course_id=course.id,
        chapter_id=chapter.id).order_by(LearningCurve.attempt_number.desc()).first()

    if learning_curve:
        learning_curve.error_count += error_count
        attempt_number = learning_curve.attempt_number
        db.session.commit()
    else:
        curve_set = LearningCurve(
                enrollment_id=enrollment_id,
                course_id=chapter.course_id,
                chapter_id=chapter.id,
                attempt_number = 1,
                error_count = error_count)
        db.session.add(curve_set)
        db.session.commit()

    #valid attributes for belows code
    learning_curve = LearningCurve.query.filter_by(
        enrollment_id=enrollment_id,
        course_id=course.id,
        chapter_id=chapter.id).order_by(LearningCurve.attempt_number.desc()).first()

    if learning_curve:
        attempt_number = learning_curve.attempt_number
     
    

    progress = Progress.query.filter_by(
        enrollment_id=enrollment_id,
        course_id=course.id).all()
    
    completed_detect = []
    for pg in progress:
        if pg.completed == False:
            completed_detect.append(1)
        print("This is pg === ", pg)

    if len(completed_detect) == 0:
        learning_curve_updated = LearningCurve(
        enrollment_id=enrollment_id,
        course_id=course.id,
        chapter_id=chapter.id,
        attempt_number= attempt_number+1,
        error_count=0)





    #base_path = os.path.dirname(os.path.abspath(__file__))  # folder of routes.py
    student_id = current_user.id 
    chapter_id = chapter.id
    course_id = course.id  
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_name = f"score{student_id}.json"
    json_path = os.path.join(base_path, file_name)
    score = 0
    score_data = {}
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            score_data = json.load(f)
    else:
        score_data = {

        str(student_id) : {
        str(chapter_id) : score 
        } 

        }
    # to test keys exist before accessing
    if str(student_id) not in score_data:
        score_data[str(student_id)] = {}
    if str(chapter_id) not in score_data[str(student_id)]:
        score_data[str(student_id)][str(chapter_id)] = score
    
    #how many quiz session
    counter = 0 
    session = Session.query.filter_by(chapter_id=chapter_id).all()
    for s in session:
        if s.session_type == "quiz_session":
            counter += 1

    original_score = score_data[str(student_id)][str(chapter_id)] 
    updated_score =  original_score + (((given_score - error_count) /given_score) / counter) #updating score
    print("counter quiz :::::: ", counter )
    if updated_score > 1:
        updated_score -= original_score
    updated_score = round(updated_score, 2) #normalize 0.99 to 1.0 or 0.49 to 0.5
    score_data[str(student_id)][str(chapter_id)] = updated_score

    with open(json_path, "w") as f:
        json.dump(score_data, f, indent=4)

    print("score_data ::::::: ", score_data ) 
    print("given score :::::: ", given_score)


    return jsonify({"status": "ok", "error_count": error_count , "score" : updated_score , "given_score" : given_score})



#=========================== end quiz ================================

#============ certification ====

@student_bp.route("certification/<int:enrollment_id>", methods=["POST"])
@login_required
def certification(enrollment_id):
    results_data = {}
    learning_curve = LearningCurve.query.filter_by(enrollment_id=enrollment_id).all()
    if learning_curve:
        for lc in learning_curve:
            results_data[lc.attempt_number] = 0
        for lc in learning_curve:
            if lc.attempt_number in results_data.keys():
                temp = results_data[lc.attempt_number] + lc.error_count
                results_data[lc.attempt_number] = temp


    is_eligible = all(item < 50 for item in results_data.values())


    student_id = current_user.id  
    file_name = f"score{student_id}.json"
    certificate_file_name = f"certificate{student_id}.json" 
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    certificate_json_path = os.path.join(base_path,certificate_file_name)
    chapter_name_dict = {}
    if  os.path.exists(certificate_json_path):
        with open(certificate_json_path, "r") as f :
            certificate_data = json.load(f)
            certificated_data = certificate_data[str(student_id)]
            if learning_curve:
                learning_curve = LearningCurve.query.filter_by(enrollment_id=enrollment_id).first()
                course_id = learning_curve.course_id
                chapter_list = models_helper(student_id)[course_id].keys()
                print("chapter list === ", chapter_list)
                chapter = Chapter.query.filter_by(course_id=course_id).all()
                for ch in chapter:
                      if ch.id in chapter_list:
                        print("ch.id === chapter_list ", ch.id)
                        if certificated_data[str(ch.id)]:
                            if certificated_data[str(ch.id)] == 1:
                                chapter_name_dict[ch.title] = "Pass"
                            else:
                                chapter_name_dict[ch.title] = "Failure"
                        else:
                            chapter_name_dict[ch.title] = "Fail"
                print("chapter_name_dict ", chapter_name_dict)
    else:
        certificated_data = None
        chapter_name_dict = None 
    course = Course.query.filter_by(id=course_id).first()
    course_name = course.title

    return render_template("partials/certification.html", enrollment_id=enrollment_id, course_id=course.id, certification=1, course_name=course_name, chapter_name_dict=chapter_name_dict)


@student_bp.route("/certificate/<int:enrollment_id>", methods=["GET", "POST"])
@login_required
def certificate_application(enrollment_id):
    enroll= Enroll.query.filter_by(id=enrollment_id).first()
    course_id=enroll.course_id 

    course = Course.query.filter_by(id=course_id).first()
    course_title = course.title 
    # Assumes current_user has these attributes
    return render_template(
        "partials/certificate_application.html",
        enrollment_id=enrollment_id,
        user=current_user,
        course_name=course_title
            )



#============ certification ====


#==================== endquick ==================

@student_bp.route("/editor")
@login_required
def editor():
    return render_template('partials/editor.html')

@student_bp.route("/run", methods=["POST"])
@login_required
def run_code():
    data = request.json
    code = data.get('code')
    lang = data.get('lang')
    
    # Check if the requested language is supported
    if lang not in LANG_MAP:
        return jsonify({'output': f"Unsupported language: {lang}"}), 400

    piston_payload = {
        "language": LANG_MAP[lang],
        "version": "*",
        "files": [{"content": code}]
    }

    try:
        response = requests.post(PISTON_API_URL, json=piston_payload, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract output and error from Piston's response format
        output = result.get('run', {}).get('stdout', '')
    
        error = result.get('run', {}).get('stderr', '')
        
        return jsonify({'output': output + error})
        
    except requests.exceptions.Timeout:
        return jsonify({'output': 'Execution request timed out.'}), 408
    except requests.exceptions.RequestException as e:
    
        return jsonify({'output': f"Error connecting to code execution service: {str(e)}"}), 502
    except Exception as e:
        return jsonify({'output': f"An unexpected error occurred: {str(e)}"}), 500

#pdf file starts

'''def generate_certificate(full_name, email, course_name, combine_phone_number, user_id):
    import os
    from datetime import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, Frame
    from reportlab.lib.enums import TA_CENTER

    # --- Paths ---
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_path, "static", "img", "tumedx_logo.png")
    output_path = os.path.join(base_path, "static", "img", f"certification{user_id}.pdf")

    width, height = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    # --- Logo ---
    c.drawImage(logo_path, width/2 - 3*cm, height - 3*cm, 6*cm, 2*cm, mask="auto")

    # --- Title ---
    c.setFont("Times-BoldItalic", 18)
    c.drawCentredString(width/2, height - 4*cm, "CERTIFICATE of")
    c.setFont("Times-Bold", 22)
    c.drawCentredString(width/2, height - 5*cm, "COURSE COMPLETION")

    # --- Styles ---
    styles = getSampleStyleSheet()
    centered_style = ParagraphStyle(
        'centered_paragraph',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        leading=18,
        alignment=TA_CENTER
    )

    # --- Student details ---
    paragraph_text = f'This is to certify that <b>{full_name}</b>, {email}, {combine_phone_number} ' \
                     f'has successfully completed the course "{course_name}" on the TUMEDX platform.'
    para = Paragraph(paragraph_text, centered_style)

    frame_width = width - 6*cm
    frame_height = 3*cm
    student_frame_y = height - 10*cm
    frame = Frame(3*cm, student_frame_y, frame_width, frame_height, showBoundary=0)
    frame.addFromList([para], c)

    # --- Recognition paragraph ---
    recognition_text = f"""
    In recognition of <b>{full_name}</b>'s dedication and achievement, 
    the institution proudly awards this certificate of completion, 
    acknowledging outstanding commitment to learning.
    """
    recognition_para = Paragraph(recognition_text.strip(), centered_style)

    recognition_frame_height = 4*cm
    recognition_y = student_frame_y - recognition_frame_height - 0.5*cm
    recognition_frame = Frame(3*cm, recognition_y, frame_width, recognition_frame_height, showBoundary=0)
    recognition_frame.addFromList([recognition_para], c)

    # --- Date section ---
    date_y = recognition_y - 2*cm
    today = datetime.today()
    formatted_date = today.strftime("%B %d, %Y")

    c.setFont("Times-Roman", 12)
    c.drawString(3*cm, date_y, "Certificate issued on")
    c.setFont("Times-Bold", 12)
    c.drawString(3*cm, date_y - 0.6*cm, formatted_date)

    # --- Website at the bottom ---
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, 2*cm, "www.tumedx.com")

    c.showPage()
    c.save()'''


'''def generate_certificate(full_name, email, course_name, combine_phone_number, user_id):
    # --- Paths ---
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base_path, "static", "img", "tumedx_logo.png")
    signature_path = os.path.join(base_path, "static", "img", "signature.jpg")
    output_path = os.path.join(base_path, "static", "img", f"certification{user_id}.pdf")

    width, height = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    # --- Logo ---
    c.drawImage(logo_path, width/2 - 3*cm, height - 3*cm, 6*cm, 2*cm, mask="auto")

    # --- Title ---
    c.setFont("Times-BoldItalic", 18)
    c.drawCentredString(width/2, height - 4*cm, "CERTIFICATE of")
    c.setFont("Times-Bold", 22)
    c.drawCentredString(width/2, height - 5*cm, "COURSE COMPLETION")

    # --- Styles ---
    styles = getSampleStyleSheet()
    centered_style = ParagraphStyle(
        'centered_paragraph',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        leading=18,
        alignment=TA_CENTER
    )

    # --- Student details ---
    paragraph_text = f'This is to certify that <b>{full_name}</b>, {email}, {combine_phone_number} ' \
                     f'has successfully completed the course "{course_name}" on the TUMEDX platform.'
    para = Paragraph(paragraph_text, centered_style)

    frame_width = width - 6*cm
    frame_height = 3*cm
    student_frame_y = height - 10*cm
    frame = Frame(3*cm, student_frame_y, frame_width, frame_height, showBoundary=0)
    frame.addFromList([para], c)

    # --- Recognition paragraph (just below student details) ---
    recognition_text = f"""
    In recognition of <b>{full_name}</b>'s dedication and achievement, 
    the institution proudly awards this certificate of completion, 
    acknowledging outstanding commitment to learning.
    """
    recognition_para = Paragraph(recognition_text.strip(), centered_style)

    # Reserve a generous height (e.g., 4 cm block) so text always fits
    recognition_frame_height = 4*cm  
    recognition_y = student_frame_y - recognition_frame_height - 0.5*cm

    recognition_frame = Frame(
    3*cm, recognition_y, frame_width, recognition_frame_height, showBoundary=0
    )
    recognition_frame.addFromList([recognition_para], c)


    # --- Date section (below recognition paragraph) ---
    date_y = recognition_y - 2*cm
    today = datetime.today()
    formatted_date = today.strftime("%B %d, %Y")
    valid_through = (today + timedelta(days=365)).strftime("%B %d, %Y")

    left_x = 3*cm
    right_x = width - 3*cm
    line_x = width/2

    c.setFont("Times-Roman", 12)
    c.drawString(left_x, date_y, "Certificate issued on")
    c.setFont("Times-Bold", 12)
    c.drawString(left_x, date_y - 0.6*cm, formatted_date)

    c.setFont("Times-Roman", 12)
    c.drawRightString(right_x, date_y, "Certificate valid through")
    c.setFont("Times-Bold", 12)
    c.drawRightString(right_x, date_y - 0.6*cm, valid_through)

    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.line(line_x, date_y - 1.8*cm, line_x, date_y + 0.2*cm)

    # --- Signature section ---
    signature_y = date_y - 6*cm  # leave good space below date
    if signature_y < 4*cm:
        signature_y = 4*cm  # prevent it from going too low

    c.drawImage(signature_path, width/2 - 1.5*cm, signature_y, 3*cm, 3*cm, mask="auto")

    line_y = signature_y - 0.8*cm
    c.setStrokeColor(colors.black)
    c.line(width/2 - 5*cm, line_y, width/2 + 5*cm, line_y)

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.black)
    c.drawCentredString(width/2, line_y - 1*cm, "Daw Myat Thinzar Soe Oo (BE IT)")
    c.drawCentredString(width/2, line_y - 1.7*cm, "Founder of the Institution")
    c.setFont("Helvetica-Oblique", 11)
    c.setFillColor(colors.HexColor("#2563eb"))
    c.drawCentredString(width/2, line_y - 2.5*cm, "www.tumedx.online")

    c.showPage()
    c.save()
    return output_path'''

'''def generate_certificate(full_name, email, course_name, combine_phone_number, user_id):
    # --- Base paths ---
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_path, "static", "img")
    os.makedirs(static_dir, exist_ok=True)  # Ensure folder exists

    # --- File paths ---
    logo_path = os.path.join(static_dir, "tumedx_logo.png")
    user_id_str = str(user_id) if user_id is not None else "unknown"
    output_path = os.path.join(static_dir, f"certification{user_id_str}.pdf")

    # --- Create PDF canvas ---
    width, height = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    # --- Logo ---
    if os.path.exists(logo_path):
        c.drawImage(logo_path, width/2 - 3*cm, height - 3*cm, 6*cm, 2*cm, mask="auto")

    # --- Title ---
    c.setFont("Times-BoldItalic", 18)
    c.drawCentredString(width/2, height - 4*cm, "CERTIFICATE of")
    c.setFont("Times-Bold", 22)
    c.drawCentredString(width/2, height - 5*cm, "COURSE COMPLETION")

    # --- Styles ---
    styles = getSampleStyleSheet()
    centered_style = ParagraphStyle(
        'centered_paragraph',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        leading=18,
        alignment=TA_CENTER
    )

    # --- Student details ---
    paragraph_text = (
        f'This is to certify that <b>{full_name}</b>, {email}, {combine_phone_number} '
        f'has successfully completed the course "{course_name}" on the TUMEDX platform.'
    )
    para = Paragraph(paragraph_text, centered_style)
    frame_width = width - 6*cm
    frame_height = 3*cm
    student_frame_y = height - 10*cm
    frame = Frame(3*cm, student_frame_y, frame_width, frame_height, showBoundary=0)
    frame.addFromList([para], c)

    # --- Recognition paragraph ---
    recognition_text = (
        f'In recognition of <b>{full_name}</b>\'s dedication and achievement, '
        f'the institution proudly awards this certificate of completion, '
        f'acknowledging outstanding commitment to learning.'
    )
    recognition_para = Paragraph(recognition_text, centered_style)
    recognition_frame_height = 4*cm
    recognition_y = student_frame_y - recognition_frame_height - 0.5*cm
    recognition_frame = Frame(3*cm, recognition_y, frame_width, recognition_frame_height, showBoundary=0)
    recognition_frame.addFromList([recognition_para], c)

    # --- Date section ---
    date_y = recognition_y - 2*cm
    today = datetime.today()
    formatted_date = today.strftime("%B %d, %Y")

    c.setFont("Times-Roman", 12)
    c.drawString(width/2 - 2*cm, date_y, "Certificate issued on")
    c.setFont("Times-Bold", 12)
    c.drawString(width/2 - 2*cm , date_y - 0.6*cm, formatted_date)

    # --- Website at the bottom ---
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width/2, 2*cm, "www.tumedx.com")

    c.showPage()
    c.save()

    return output_path  # <-- Always return the valid file path'''


def generate_certificate(full_name, email, course_name, combine_phone_number, user_id):
    # --- Base paths ---
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_path, "static", "img")
    os.makedirs(static_dir, exist_ok=True)

    # --- File paths ---
    logo_path = os.path.join(static_dir, "tumedx_logo.png")
    user_id_str = str(user_id) if user_id is not None else "unknown"
    output_path = os.path.join(static_dir, f"certification{user_id_str}.pdf")

    # --- PDF canvas ---
    width, height = A4
    c = canvas.Canvas(output_path, pagesize=A4)

    # --- Logo at top center (1 cm margin) ---
    if os.path.exists(logo_path):
        logo_width, logo_height = 6*cm, 2*cm
        c.drawImage(
            logo_path,
            (width - logo_width) / 2,
            height - 1*cm - logo_height,
            logo_width,
            logo_height,
            mask="auto"
        )

    # --- Title ---
    c.setFont("Times-Italic", 24)
    c.drawCentredString(width/2, height - 5*cm, "Course Completion Certificate")

    # --- Subtitle ---
    c.setFont("Times-Roman", 12)
    c.drawCentredString(width/2, height - 6*cm, "This qualification is awarded to")

    # --- User name ---
    c.setFont("Times-Bold",62)
    c.drawCentredString(width/2, height - 10*cm, full_name)

    # --- Paragraph text ---
    styles = getSampleStyleSheet()
    centered_style = ParagraphStyle(
        'centered_paragraph',
        parent=styles['Normal'],
        fontName='Times-Roman',
        fontSize=12,
        leading=18,
        alignment=TA_CENTER
    )
    paragraph_text = (
        f'This is to certify that <b>{full_name}</b>, {email}, {combine_phone_number} '
        f'has successfully completed the course "{course_name}" on the TUMEDX platform.'
    )
    para = Paragraph(paragraph_text, centered_style)

    frame_width = width - 6*cm
    frame_height = 4*cm
    frame_y = height - 16*cm
    frame = Frame(3*cm, frame_y, frame_width, frame_height, showBoundary=0)
    frame.addFromList([para], c)

    # --- Date section ---
    today = datetime.today()
    formatted_date = today.strftime("%B %d, %Y")

    date_y = frame_y - 2*cm
    c.setFont("Times-Roman", 12)
    c.drawCentredString(width/2, date_y, "Certificate issued on")
    c.setFont("Times-Bold", 12)
    c.drawCentredString(width/2, date_y - 0.6*cm, formatted_date)

    # --- Website at bottom ---
    c.setFont("Times-Bold", 12)
    c.setFillColor(colors.HexColor("#2563eb"))
    c.drawCentredString(width/2, 2*cm, "www.tumedx.com")

    # --- Save ---
    c.showPage()
    c.save()

    return output_path




#pdf file ends 
 

@student_bp.route("/preview", methods=["GET","POST"])
@login_required
def  form_certificate():
    full_name = request.form.get("full_name")
    email = request.form.get("email")
    country_code = request.form.get("country_code")
    phone_number = request.form.get("phone_number")
    combine_phone_number = f"{country_code}{phone_number}"
    course_name = request.form.get("course_name")
    user_id = current_user.id
    certification_path =  generate_certificate(full_name, email, course_name, combine_phone_number, user_id)
    return send_file(
        certification_path,
        as_attachment=True,
        download_name=f"certificate_of_{full_name}.pdf",
        mimetype="application/pdf"
    )
 