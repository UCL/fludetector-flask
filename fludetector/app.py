import csv
import os
from functools import wraps
from collections import defaultdict
from datetime import timedelta
from StringIO import StringIO

import sh
from flask import Flask, request, jsonify, render_template, make_response, Response, abort, redirect, url_for, flash
from flask_dotenv import DotEnv

from fludetector import models, scripts, forms
from fludetector.errors import FluDetectorError
from fludetector.models import db, get_region, REGIONS, Model, ModelScore, GoogleScore

app = Flask(__name__)
env = DotEnv(app)

os.environ['GOOGLE_API_KEY'] = app.config['GOOGLE_API_KEY']

models.init_app(app)
scripts.init_app(app)


@app.errorhandler(FluDetectorError)
def handle_bad_request(e):
    return jsonify({'error': e.message})


def check_auth(username, password):
    """This function is called to check if a username password combination is valid."""
    return username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def calculate_averages(scores):
    averages = defaultdict(lambda: defaultdict(list))
    for (s, smoothed) in scores:
        averages[s.model][s.region].append(smoothed)
    for model, regions in averages.iteritems():
        for region, scores in regions.iteritems():
            yield (model, get_region(region), sum(scores) / len(scores))


def calculate_raw_scores(scores):
    raw_scores = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for s, smoothed in scores:
        raw_scores[s.day][s.model][s.region] = smoothed
    return raw_scores


def get_scores_form(public=True):
    all_models = Model.query
    if public:
        all_models = all_models.filter_by(public=public)
    all_models = all_models.all()
    score = None
    for m in all_models:
        score = m.last_score
        if score is not None:
            break
    form = forms.GetScoresWebForm(request.args, model_regions=[(score.model, score.region)])
    return all_models, form


@app.route('/')
def home():
    all_models, form = get_scores_form()
    scores = form.scores()

    return render_template(
        'home.html',
        models=all_models,
        form=form,
        regions=REGIONS,
        averages=calculate_averages(scores),
        raw_scores=calculate_raw_scores(scores))


@app.route('/export/')
def export():
    all_models, form = get_scores_form()

    raw_scores = calculate_raw_scores(form.scores())

    fd = StringIO()
    csv_fd = csv.writer(fd)

    headers = [
        [''] + [m.name for m, r in form.model_regions.data],
        ['Date'] + [REGIONS[r] for m, r in form.model_regions.data]
    ]
    for r in headers:
        csv_fd.writerow(r)

    for day, models_ in sorted(raw_scores.iteritems()):
        row = [[day.strftime('%Y-%m-%d')]]
        row.append([models_[m][r] for m, r in form.model_regions.data])
        csv_fd.writerow(row)

    resp = make_response(fd.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=fluedetector-export.csv"
    resp.headers["Content-type"] = "text/csv"
    return resp


@app.route('/about/')
def about():
    return render_template('about.html')


@app.route('/docs/')
def docs():
    model = Model.query.filter_by(public=True).first()
    score = model.scores.first()
    example = {
        'model': model.id,
        'region': score.region,
        'resolution': 'day',
        'smoothing': 3,
        'start': score.day - timedelta(days=7),
        'end': score.day + timedelta(days=7)
    }
    return render_template('docs.html', example=example, model=model)


@app.route('/api/scores/')
def api_scores():
    form = forms.GetScoresApiForm(request.args)

    if not form.validate():
        return jsonify({'errors': form.errors}), 400

    model = form.model.data

    return jsonify({
        'model': {'id': model.id, 'name': model.name},
        'region': form.region.data,
        'start': form.start.data.strftime('%Y-%m-%d'),
        'end': form.end.data.strftime('%Y-%m-%d'),
        'resolution': form.resolution.data,
        'smoothing': form.smoothing.data,
        'scores': form.scores()})


@app.route('/api/models/')
def api_models():
    models = Model.query.filter_by(public=True).all()
    return jsonify([
        {'id': m.id, 'name': m.name}
        for m in models])


@app.route('/admin/')
@requires_auth
def admin_home():
    all_models, form = get_scores_form(public=False)
    scores = form.scores()

    return render_template(
        'admin/home.html',
        models=all_models,
        form=form,
        regions=REGIONS,
        all_model_regions=[(m, r) for m in all_models for r in m.regions],
        averages=calculate_averages(scores),
        raw_scores=calculate_raw_scores(scores))


@app.route('/admin/models/')
@requires_auth
def admin_list_models():
    return render_template(
        'admin/model_list.html',
        models=Model.query.all(),
        region_codes=list(REGIONS.keys()))


@app.route('/admin/models/<int:id>/')
@requires_auth
def admin_retrieve_model(id):
    model = Model.query.get(id)
    if not model:
        abort(404)
    return render_template('admin/model_retrieve.html', model=model, REGIONS=REGIONS)


@app.route('/admin/models/<int:id>/delete/', methods=['GET', 'POST'])
@requires_auth
def admin_delete_model(id):
    model = Model.query.get(id)
    if not model:
        abort(404)
    form = forms.DeleteModelForm(model)
    if form.validate_on_submit():
        for term in model.google_terms:
            # Delete any orphaned GoogleTerms
            # There should be a way to cascade these deletes automatically?
            # I couldn't work it out :(
            if len(term.models) == 1:
                db.session.delete(term)
        db.session.delete(model)
        db.session.commit()
        flash('Model deleted!', 'success')
        return redirect(url_for('admin_list_models'))
    return render_template('admin/model_delete.html', form=form, model=model)


@app.route('/admin/models/create/', methods=['GET', 'POST'])
@requires_auth
def admin_create_model():
    form = forms.CreateModelForm.factory(request.args.get('type', 'csv'))
    if form.validate_on_submit():
        model = Model()
        form.populate_obj(model)
        db.session.add(model)
        db.session.commit()
        return redirect(url_for('admin_retrieve_model', id=model.id))
    return render_template('admin/model_create.html', form=form)


@app.route('/admin/models/<int:id>/update/', methods=['GET', 'POST'])
@requires_auth
def admin_update_model(id):
    model = Model.query.get(id)
    if not model:
        abort(404)
    form = forms.CreateModelForm.factory(model.type, model=model)
    if form.validate_on_submit():
        form.populate_obj(model)
        db.session.add(model)
        db.session.commit()
        return redirect(url_for('admin_retrieve_model', id=model.id))
    return render_template('admin/model_create.html', form=form, model=model)


@app.route('/admin/models/<int:id>/run/', methods=['GET', 'POST'])
@requires_auth
def admin_run_model(id):
    model = Model.query.get(id)
    if not model:
        abort(404)
    form = forms.RunModelForm.factory(model)
    if form.validate_on_submit():
        run = sh.Command('./scripts/run.sh')
        run(str(id), _bg=True, **form.to_dict())
        flash('Model running in background, check logs for details', 'info')
        return redirect(url_for('admin_list_models'))
    return render_template('admin/model_run.html', form=form, model=model)


@app.route('/admin/logs/')
@requires_auth
def admin_list_logs():
    logs = os.listdir('logs')
    return render_template('admin/log_list.html', logs=logs)


@app.route('/admin/logs/<filename>')
@requires_auth
def admin_retrieve_log(filename):
    """This feels dangerous. However, filename cannot contain slashes so we
    should be confined to direct children of the logs directory. Also, only
    admins can access this file so hopefully exposure is minimal.

    Famous last words :)
    """
    with open(os.path.join('logs', filename), 'rb') as fd:
        return fd.read(), {'Content-Type': 'text/plain'}


def admin_export_google(model, start, end, writer):
    writer.writerow(['Term', 'Day', 'Value'])
    for term in model.google_terms:
        scores = term.scores.filter(GoogleScore.day >= start, GoogleScore.day < end)
        for score in scores:
            writer.writerow([term.term, score.day.strftime('%Y-%m-%d'), score.value])


def admin_export_csv(model, start, end, writer):
    scores = model.scores.filter(ModelScore.day >= start, ModelScore.day < end)
    by_date = defaultdict(lambda: defaultdict(int))
    regions = set()
    for s in scores:
        regions.add(s.region)
        by_date[s.day][s.region] = s.value
    regions = list(regions)
    writer.writerow(['Date'] + [REGIONS[code] for code in regions])
    for day, by_region in sorted(by_date.iteritems()):
        writer.writerow([day.strftime('%Y-%m-%d')] + [by_region.get(code) for code in regions])


@app.route('/admin/models/<int:id>/export/', methods=['GET', 'POST'])
@requires_auth
def admin_export_model(id):
    model = Model.query.get(id)
    if not model:
        abort(404)
    form = forms.ExportModelForm()

    if form.validate_on_submit():
        fd = StringIO()
        csv_fd = csv.writer(fd)

        {
            'google': admin_export_google,
            'csv': admin_export_csv
        }.get(model.type)(model, form.start.data, form.end.data, csv_fd)

        resp = make_response(fd.getvalue())
        resp.headers["Content-Disposition"] = "attachment; filename=fluedetector-export.csv"
        resp.headers["Content-type"] = "text/csv"
        return resp

    return render_template('admin/model_export.html', form=form, model=model)
