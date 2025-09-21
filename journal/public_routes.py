# journal/public_routes.py
from flask import (
    Blueprint, render_template, request, current_app,
    send_from_directory, abort, Response, url_for
)
from sqlalchemy import or_, func
from datetime import datetime
import os

from . import db
from .models import Submission, SubmissionStatus, Issue

public_bp = Blueprint(
    'public',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/static'
)

def _pdf_filename(submission_id: int) -> str:
    return f"submission_{submission_id}.pdf"


@public_bp.route('/')
def landing():
    # Latest accepted articles (for landing page cards)
    latest = (Submission.query
              .filter_by(status=SubmissionStatus.ACCEPTED)
              .order_by(Submission.id.desc())
              .limit(6)
              .all())

    # Safe, SQLAlchemy-2.0 compatible stats (no raw SQL strings)
    stats = {
        "submissions": db.session.query(Submission).count(),
        "accepted": db.session.query(Submission).filter_by(status=SubmissionStatus.ACCEPTED).count(),
        "reviewers": db.session.query(func.count(func.distinct(Submission.assigned_reviewer_id))).scalar() or 0,
    }
    return render_template('landing.html', latest=latest, stats=stats)


# --- static content pages ---
@public_bp.route('/aims')
def aims():
    return render_template('public_aims.html')

@public_bp.route('/guidelines')
def guidelines():
    return render_template('public_guidelines.html')

@public_bp.route('/board')
def board():
    return render_template('public_board.html')

@public_bp.route('/policies')
def policies():
    return render_template('public_policies.html')

@public_bp.route('/contact')
def contact():
    return render_template('public_contact.html')


# --- browse issues / articles ---
@public_bp.route('/issues')
def issues():
    issues = (Issue.query
              .order_by(Issue.year.desc(), Issue.volume.desc(), Issue.number.desc())
              .all())
    ahead = (Submission.query
             .filter_by(status=SubmissionStatus.ACCEPTED, issue_id=None)
             .order_by(Submission.created_at.desc())
             .all())
    return render_template('public_issues.html', issues=issues, ahead=ahead)

@public_bp.route('/issues/<int:year>/v<int:volume>/n<int:number>')
def issue_detail(year, volume, number):
    issue = Issue.query.filter_by(year=year, volume=volume, number=number).first_or_404()
    return render_template('public_issue_detail.html', issue=issue)

@public_bp.route('/article/<int:submission_id>')
def article(submission_id):
    art = Submission.query.get_or_404(submission_id)
    if art.status != SubmissionStatus.ACCEPTED:
        abort(404)
    return render_template('public_article.html', art=art)


# --- public PDF for ACCEPTED only ---
@public_bp.route('/article/<int:submission_id>/pdf')
def public_pdf(submission_id):
    art = Submission.query.get_or_404(submission_id)
    if art.status != SubmissionStatus.ACCEPTED:
        abort(403)
    filename = _pdf_filename(art.id)
    path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(path):
        abort(404)
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=False)


# --- search ---
@public_bp.route('/search')
def search():
    q = (request.args.get('q') or "").strip()
    results = []
    if q:
        results = (Submission.query
                   .filter(Submission.status == SubmissionStatus.ACCEPTED)
                   .filter(or_(
                       Submission.title.ilike(f"%{q}%"),
                       Submission.abstract.ilike(f"%{q}%"),
                       Submission.keywords.ilike(f"%{q}%")
                   ))
                   .order_by(Submission.created_at.desc())
                   .all())
    return render_template('public_search.html', q=q, results=results)


# --- sitemap & robots ---
@public_bp.route('/sitemap.xml')
def sitemap():
    urls = [
        url_for('public.landing', _external=True),
        url_for('public.aims', _external=True),
        url_for('public.guidelines', _external=True),
        url_for('public.board', _external=True),
        url_for('public.policies', _external=True),
        url_for('public.contact', _external=True),
        url_for('public.issues', _external=True),
    ]
    # add issue/article urls
    for i in Issue.query.all():
        urls.append(url_for('public.issue_detail', year=i.year, volume=i.volume, number=i.number, _external=True))
    for a in Submission.query.filter_by(status=SubmissionStatus.ACCEPTED).all():
        urls.append(url_for('public.article', submission_id=a.id, _external=True))

    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    now = datetime.utcnow().strftime("%Y-%m-%d")
    for u in urls:
        xml.append(f"<url><loc>{u}</loc><lastmod>{now}</lastmod><changefreq>weekly</changefreq></url>")
    xml.append('</urlset>')
    return Response("\n".join(xml), mimetype="application/xml")

@public_bp.route('/robots.txt')
def robots():
    return Response("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", mimetype="text/plain")
