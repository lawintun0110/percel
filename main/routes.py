# tumedx_platform/app/main/routes.py

from flask import render_template
from app.main import main_bp # Import the blueprint instance
from flask import send_from_directory

@main_bp.route("/sitemap.xml")
def sitemap_xml():
    return send_from_directory("static", "sitemap.xml")

@main_bp.route("/robots.txt")
def robots_txt():
    return send_from_directory("static", "robots.txt")


@main_bp.route('/')
def guest_page():
    return render_template('guest_page.html')


# @main_bp.route('/about')
# def about():
#     return render_template('about.html')
