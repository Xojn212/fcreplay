from flask import Flask, request, render_template, g, session, send_from_directory, redirect, url_for
from flask import Blueprint
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm

from wtforms import Form, StringField, BooleanField, SubmitField, SelectField

import os
import json
import logging
import pkg_resources

try:
    import googleclouddebugger
    googleclouddebugger.enable(
        breakpoint_enable_canary=True
    )
except ImportError:
    pass

with open("config.json", 'r') as json_data_file:
    config = json.load(json_data_file)

with open(pkg_resources.resource_filename('fcreplay', 'data/character_detect.json')) as json_data_file:
    character_dict = json.load(json_data_file)

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = config['sql_baseurl']
app.config['SECRET_KEY'] = config['secret_key']

Bootstrap(app)
db = SQLAlchemy(app)

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


class AdvancedSearchForm(FlaskForm):
    characters = [
        ('Any', 'Any'),
        ('alex', 'alex'),
        ('akuma', 'akuma'),
        ('chunli', 'chunli'),
        ('dudley', 'dudley'),
        ('elena', 'elena'),
        ('hugo', 'hugo'),
        ('ibuki', 'ibuki'),
        ('ken', 'ken'),
        ('makoto', 'makoto'),
        ('necro', 'necro'),
        ('oro', 'oro'),
        ('q', 'q'),
        ('remy', 'remy'),
        ('ryu', 'ryu'),
        ('sean', 'sean'),
        ('twelve', 'twelve'),
        ('urien', 'urien'),
        ('yang', 'yang'),
        ('yun', 'yun')]

    orderby_list = [
        ('date_replay', 'Replay Date'),
        ('date_added', 'Date Added')
    ]

    # Generate supported games
    game_list = []
    game_list.append(
        ('Any', 'Any')
    )

    for game in sorted(config['supported_games']):
        game_list.append(
            (game, config['supported_games'][game]['game_name'])
        )

    search = StringField()
    game = SelectField('Game', choices=game_list,
                       render_kw={'class': 'fixed', 'onChange': 'gameSelect(this)', 'id': 'game'})
    char1 = SelectField('Character1', choices=characters,
                        render_kw={'class': 'fixed'})
    char2 = SelectField('Character2', choices=characters,
                        render_kw={'class': 'fixed'})
    player_requested = BooleanField('Player Submitted')
    order_by = SelectField('Order by', choices=orderby_list,
                           render_kw={'class': 'fixed'})
    submit = SubmitField('Search')


class SearchForm(FlaskForm):
    orderby_list = [
        ('date_replay', 'Replay Date'),
        ('date_added', 'Date Added')
    ]

    # Generate supported games
    game_list = []
    game_list.append(
        ('Any', 'Any')
    )
    for game in sorted(config['supported_games']):
        game_list.append(
            (game, config['supported_games'][game]['game_name'])
        )

    search = StringField()
    game = SelectField('Game', choices=game_list,
                       render_kw={'class': 'fixed'})
    order_by = SelectField('Order by', choices=orderby_list,
                           render_kw={'class': 'fixed'})
    submit = SubmitField('Search')


class SubmitForm(FlaskForm):
    player_id = StringField()
    challenge_url = StringField()
    submit = SubmitField()


class Replays(db.Model):
    id = db.Column(db.Text, primary_key=True)
    p1_loc = db.Column(db.String)
    p2_loc = db.Column(db.String)
    p1 = db.Column(db.String)
    p2 = db.Column(db.String)
    date_replay = db.Column(db.DateTime)
    length = db.Column(db.Integer)
    created = db.Column(db.Boolean)
    failed = db.Column(db.Boolean)
    status = db.Column(db.String)
    date_added = db.Column(db.Integer)
    player_requested = db.Column(db.Boolean)
    game = db.Column(db.String)


class Descriptions(db.Model):
    id = db.Column(db.Text, primary_key=True)
    description = db.Column(db.Text)


class Character_detect(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Text, primary_key=True)
    p1_char = db.Column(db.String)
    p2_char = db.Column(db.String)
    vid_time = db.Column(db.String)


@app.route('/')
def index():
    searchForm = SearchForm()
    page = request.args.get('page', 1, type=int)
    pagination = Replays.query.filter(
        Replays.created == 'yes'
    ).filter(
        Replays.failed == 'no'
    ).order_by(Replays.date_added.desc()).paginate(page, per_page=9)
    replays = pagination.items

    return render_template('start.j2.html', pagination=pagination, replays=replays, form=searchForm, games=config['supported_games'])


@app.route('/submit')
def submit():
    searchForm = SearchForm()
    submitForm = SubmitForm()
    return render_template('submit.j2.html', form=searchForm, submitForm=submitForm, submit_active=True)


@app.route('/submitResult', methods=['POST', 'GET'])
def submitResult():
    logging.debug(f"Session: {session}")
    # I feel like there should be a better way to do this
    if request.method == 'POST':
        result = SubmitForm(request.form)

        player_id = result.player_id.data
        challenge_id = result.challenge_url.data
        session['player_id'] = result.player_id.data
        session['challenge_url'] = result.challenge_url.data

        from fcreplay.getreplay import get_replay
        replay_result = get_replay(
            player_id, challenge_id, player_requested=True)

        session['replay_result'] = replay_result

        # Add replay and get status here
        return redirect(url_for('submitResult'))
    else:
        searchForm = SearchForm()
        result = session['replay_result']
        return render_template('submitResult.j2.html', form=searchForm, result=result, submt_active=True)


@app.route('/assets/<path:path>')
def send_js(path):
    return send_from_directory('templates/assets', path)


@app.route('/about')
def about():
    searchForm = SearchForm()

    sortedGames = sorted(config['supported_games'])
    supportedGames = {}
    for game in sortedGames:
        supportedGames[game] = config['supported_games'][game]
        supportedGames[game]['count'] = db.session.execute(f"select count(id) from replays where created = true and game = '{game}'").first()[0]

    numberOfReplays = db.session.execute('select count(id) from replays where created = true').first()[0]

    toProcess = db.session.execute('select count(id) from replays where created = false and failed = false').first()[0]

    return render_template('about.j2.html', about_active=True, form=searchForm, supportedGames=supportedGames, numberOfReplays=numberOfReplays, toProcess=toProcess)


@app.route('/advancedSearch')
def advancedSearch():
    searchForm = SearchForm()
    advancedSearchForm = AdvancedSearchForm()
    return render_template('advancedSearch.j2.html', advancedsearch_active=True, form=searchForm, advancedSearchForm=advancedSearchForm)


@app.route('/advancedSearchResult', methods=['POST', 'GET'])
def advancedSearchResult():
    logging.debug(f"Session: {session}")
    # I feel like there should be a better way to do this
    if request.method == 'POST':
        result = AdvancedSearchForm(request.form)

        session['search'] = result.search.data
        session['char1'] = result.char1.data
        session['char2'] = result.char2.data
        session['player_requested'] = result.player_requested.data
        session['order_by'] = result.order_by.data
        session['game'] = result.game.data

        return redirect(url_for('advancedSearchResult'))
    else:
        search_query = session['search']
        char1 = session['char1']
        char2 = session['char2']
        player_requested = session['player_requested']
        order_by = session['order_by']
        game = session['game']

    searchForm = SearchForm()

    if player_requested:
        player_requested = True
    else:
        player_requested = False

    page = request.args.get('page', 1, type=int)

    if order_by == 'date_replay':
        order = Replays.date_replay.desc()
    elif order_by == 'date_added':
        order = Replays.date_added.desc()
    else:
        raise LookupError

    if char1 == 'Any':
        char1 = '%'
    if char2 == 'Any':
        char2 = '%'

    if game == 'Any':
        game = '%'

    replay_query = [
        Replays.created == True,
        Replays.failed == False,
        Replays.game.ilike(f'{game}'),
        Replays.player_requested == player_requested,
        Replays.id.in_(
            Descriptions.query.with_entities(Descriptions.id).filter(
                Descriptions.description.ilike(f'%{search_query}%')
            )
        )
    ]

    if game in character_dict:
        replay_query.append(
            Replays.id.in_(
                Character_detect.query.with_entities(Character_detect.challenge_id).filter(
                    Character_detect.p1_char.ilike(
                        f'{char1}') & Character_detect.p2_char.ilike(f'{char2}')
                ).union(
                    Character_detect.query.with_entities(Character_detect.challenge_id).filter(
                        Character_detect.p1_char.ilike(
                            f'{char2}') & Character_detect.p2_char.ilike(f'{char1}')
                    )
                )
            )
        )
    
    logging.debug(Replays.query.filter(*replay_query))
    pagination = Replays.query.filter(*replay_query).order_by(order).paginate(page, per_page=9)
    replays = pagination.items

    return render_template('start.j2.html', pagination=pagination, replays=replays, form=searchForm, games=config['supported_games'])


@app.route('/search', methods=['POST', 'GET'])
def search():
    logging.debug(f"Session: {session}")
    # I feel like there should be a better way to do this
    if request.method == 'POST':
        result = SearchForm(request.form)

        session['search'] = result.search.data
        session['order_by'] = result.order_by.data
        session['game'] = result.game.data

        return redirect(url_for('search'))
    else:
        search_query = session['search']
        order_by = session['order_by']
        game = session['game']

    searchForm = SearchForm(request.form,
                            search=search_query,
                            game=game)

    page = request.args.get('page', 1, type=int)

    if order_by == 'date_replay':
        order = Replays.date_replay.desc()
    elif order_by == 'date_added':
        order = Replays.date_added.desc()
    else:
        raise LookupError

    if game == 'Any':
        game = '%'

    replay_query = Replays.query.filter(
        Replays.created == True
    ).filter(
        Replays.failed == False
    ).filter(
        Replays.game.ilike(f'{game}')
    ).filter(
        Replays.id.in_(
            Descriptions.query.with_entities(Descriptions.id).filter(
                Descriptions.description.ilike(f'%{search_query}%')
            )
        )
    ).order_by(order)

    logging.debug(replay_query)
    pagination = replay_query.paginate(page, per_page=9)
    replays = pagination.items

    return render_template('start.j2.html', pagination=pagination, replays=replays, form=searchForm, games=config['supported_games'])


@app.route('/video/<challenge_id>',)
def videopage(challenge_id):
    searchForm = SearchForm()

    replay = Replays.query.filter(
        Replays.id == challenge_id
    ).first()
    char_detect = Character_detect.query.filter(
        Character_detect.challenge_id == challenge_id
    ).all()

    characters = []
    for c in char_detect:
        characters.append(
            {
                'p1_char': c.p1_char,
                'p2_char': c.p2_char,
                'vid_time': c.vid_time,
                'seek_time': sum(int(x) * 60 ** i for i, x in enumerate(reversed(c.vid_time.split(":"))))
            }
        )

    seek = request.args.get('seek', default=0, type=float)

    logging.debug(
        f"Video page, replay: {replay}, characters: {characters}, seek: {seek}")
    return render_template('video.j2.html', replay=replay, characters=characters, seek=seek, form=searchForm, games=config['supported_games'])


if __name__ == "__main__":
    app.run(debug=True)
