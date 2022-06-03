#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
from email.policy import default
import sys
import dateutil.parser
import babel
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
from flask_migrate import Migrate
from sqlalchemy.orm import load_only
from sqlalchemy import distinct
import datetime
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# TODO: connect to a local postgresql database
# app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue_Genre(db.Model):
    __tablename__ = "venue_genres"
    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(
        db.Integer, db.ForeignKey("venues.id", ondelete="CASCADE"), nullable=False
    )
    genre = db.Column(db.String(50), nullable=False)
    owner = db.Column(db.String(50), default='Umar Abdullahi')


class Venue(db.Model):
    __tablename__ = "venues"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=True)
    owner = db.Column(db.String(50), default='Umar Abdullahi')
    genres = db.relationship(
        "Venue_Genre", passive_deletes=True, backref="venue", lazy=True,
    )
    seeking_talent = db.Column(db.Boolean, nullable=True, default=False)
    seeking_description = db.Column(db.String(120), nullable=True)
    image_link = db.Column(
        db.String(500),
        nullable=True,
        default="https://images.unsplash.com/photo-1600585154084-4e5fe7c39198?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=870&q=80",
    )
    facebook_link = db.Column(db.String(120), nullable=True, default="")
    website = db.Column(db.String(120), nullable=True)

    # TODO: implement any missing fields, as a database migration using Flask-Migrate


class Show(db.Model):
    __tablename__ = "shows"
    artist_id = db.Column(db.Integer, db.ForeignKey(
        "artists.id"), primary_key=True)
    venue_id = db.Column(
        db.Integer, db.ForeignKey("venues.id", ondelete="CASCADE"), primary_key=True
    )
    owner = db.Column(db.String(50), default='Umar Abdullahi')
    start_time = db.Column(db.DateTime, nullable=False)


class Artist_Genre(db.Model):
    __tablename__ = "artist_genres"
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.Integer, db.ForeignKey(
        "artists.id"), nullable=False)
    owner = db.Column(db.String(50), default='Umar Abdullahi')
    genre = db.Column(db.String(50), nullable=False)


class Artist(db.Model):
    __tablename__ = "artists"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120), nullable=False)
    genres = db.relationship("Artist_Genre", backref="artist", lazy=True)
    owner = db.Column(db.String(50), default='Umar Abdullahi')
    image_link = db.Column(
        db.String(500),
        nullable=True,
        default="https://assets.about.me/background/users/u/m/a/umarabdullahi_1634476090_225.jpg",
    )
    facebook_link = db.Column(db.String(120), nullable=True)
    venues = db.relationship(
        "Venue", secondary="shows", backref=db.backref("artists", lazy=True)
    )
    seeking_venue = db.Column(db.Boolean, nullable=True, default=False)
    seeking_description = db.Column(db.String(30), nullable=True, default="")
    # TODO: implement any missing fields, as a database migration using Flask-Migrate

# TODO Implement Show and Artist models, and complete all model relationships and properties, as a database migration.

# ----------------------------------------------------------------------------#
# Filters.
# ----------------------------------------------------------------------------#


def format_datetime(value, format="medium"):
    date = dateutil.parser.parse(value)
    if format == "full":
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == "medium":
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters["datetime"] = format_datetime

# ----------------------------------------------------------------------------#
# Controllers.
# ----------------------------------------------------------------------------#


@app.route("/")
def index():
    return render_template("pages/home.html")


#  Venues
#  ----------------------------------------------------------------

def venue_upcoming_show(venue_id):
    Show.query.filter_by(venue_id=venue_id).filter(
        Show.start_time > datetime.datetime.now()).all()


@app.route("/venues")
def venues():
    # TODO: replace with real venues data.
  #       num_upcoming_shows should be aggregated based on number of upcoming shows per venue.

    data = []

    try:
        locations = db.session.query(
            distinct(Venue.city), Venue.state).all()
        for location in locations:
            city = location[0]
            state = location[1]

            location_data = {"city": city, "state": state, "venues": []}

            for venue in (Venue.query.filter_by(
                    state=state, city=city).all()):
                name = venue.name
                id = venue.id

                upcoming_shows = (
                    Show.query.filter_by(venue_id=id)
                    .filter(Show.start_time > datetime.datetime.now())
                    .all()
                )

                venue_data = {
                    "id": id,
                    "name": name,
                    "num_upcoming_shows": len(upcoming_shows),
                }

                location_data["venues"].append(venue_data)

            data.append(location_data)

    except:
        flash("Cannot fetch, Try Again!!!")
        return render_template("pages/home.html")

    finally:
        return render_template("pages/venues.html", areas=data)


@app.route("/venues/search", methods=["POST"])
def search_venues():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    search = request.form.get("search_term", "")

    search_response = {"count": 0, "data": []}

    fields = ["id", "name"]

    search_response["count"] = len(db.session.query(Venue)
                                   .filter(Venue.name.ilike(f"%{search}%"))
                                   .options(load_only(*fields))
                                   .all())

    for result in (db.session.query(Venue)
                   .filter(Venue.name.ilike(f"%{search}%"))
                   .options(load_only(*fields))
                   .all()):
        item = {
            "id": result.id,
            "name": result.name,
        }
        search_response["data"].append(item)

    return render_template(
        "pages/search_venues.html",
        results=search_response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/venues/<int:venue_id>")
def show_venue(venue_id):
    # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
    data = {}

    try:
        if (Venue.query.get(venue_id)) is None:
            return render_template("errors/404.html"), 404

        genres = []
        for item in (Venue.query.get(venue_id)).genres:
            genres.append(item.genre)

        shows = Show.query.filter_by(venue_id=venue_id)
        past_shows = []
        for show in (shows.filter(Show.start_time < datetime.datetime.now()).all()):
            artist = Artist.query.get(show.artist_id)
            show_data = {
                "artist_id": artist.id,
                "artist_name": artist.name,
                "artist_image_link": artist.image_link,
                "start_time": str(show.start_time),
            }
            past_shows.append(show_data)

        shows = shows.filter(Show.start_time >= datetime.datetime.now()).all()
        upcoming_shows = []
        for show in shows:
            artist = Artist.query.get(show.artist_id)
            show_data = {
                "artist_id": artist.id,
                "artist_name": artist.name,
                "artist_image_link": artist.image_link,
                "start_time": str(show.start_time),
            }
            upcoming_shows.append(show_data)
        venue = Venue.query.get(venue_id)
        data = {
            "id": venue.id,
            "name": venue.name,
            "genres": genres,
            "address": venue.address,
            "city": venue.city,
            "state": venue.state,
            "phone": venue.phone,
            "website": venue.website,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "image_link": venue.image_link,
            "past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": len(past_shows),
            "upcoming_shows_count": len(upcoming_shows),
        }

    except:
        flash("Cannot fetch, Try Again!!!")

    return render_template("pages/show_venue.html", venue=data)


#  Create Venue
#  ----------------------------------------------------------------
@app.route("/venues/create", methods=["GET"])
def create_venue_form():

    form = VenueForm()
    return render_template("forms/new_venue.html", form=form)


@app.route("/venues/create", methods=["POST"])
def create_venue_submission():

    # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  # on successful db insert, flash success

    try:
        name = request.form.get("name")
        city = request.form.get("city")
        state = request.form.get("state")
        address = request.form.get("address")
        phone = request.form.get("phone")
        genres = request.form.getlist("genres")
        facebook_link = request.form.get("facebook_link")

        venue = Venue(
            name=name,
            city=city,
            state=state,
            address=address,
            phone=phone,
            facebook_link=facebook_link,
        )

        genres_for_this_venue = []
        for genre in genres:
            current_genre = Venue_Genre(genre=genre)
            current_genre.venue = venue
            genres_for_this_venue.append(current_genre)

        db.session.add(venue)
        db.session.commit()
        flash(f"{venue.name} was successfully added!")

    except:
        db.session.rollback()
        flash(
            "An error occurred. Venue "
            + request.form.get("name")
            + " could not be added"
        )

    finally:
        db.session.close()
        return render_template("pages/home.html")


@app.route("/venues/<venue_id>/delete", methods=["GET"])
def delete_venue(venue_id):
    # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
    try:
        venue_to_be_deleted = db.session.query(
            Venue).filter(Venue.id == venue_id)
        venue_to_be_deleted.delete()
        db.session.commit()
        name = Venue.query.get(venue_id).name
        flash(f"{name} was successfully deleted.")

    except:
        db.session.rollback()
        flash(f"{name} was not deleted.")

    finally:
        db.session.close()
        return redirect(url_for("index"))


#  Artists
#  ----------------------------------------------------------------
@app.route("/artists")
def artists():
    # TODO: replace with real data returned from querying the database
    fields = ["id", "name"]
    artists_data = db.session.query(Artist).options(load_only(*fields)).all()

    return render_template("pages/artists.html", artists=artists_data)


@app.route("/artists/search", methods=["POST"])
def search_artists():
    # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
    search = request.form.get("search_term", "")

    response = {"count": 0, "data": []}

    fields = ["id", "name"]
    results = (
        db.session.query(Artist)
        .filter(Artist.name.ilike(f"%{search}%"))
        .options(load_only(*fields))
        .all()
    )

    num_upcoming_shows = 0

    response["count"] = len(results)

    for result in results:
        item = {
            "id": result.id,
            "name": result.name,
            "num_upcoming_shows": num_upcoming_shows,
        }
        response["data"].append(item)

    return render_template(
        "pages/search_artists.html",
        results=response,
        search_term=request.form.get("search_term", ""),
    )


@app.route("/artists/<int:artist_id>")
def show_artist(artist_id):
    # shows the artist page with the given artist_id
  # TODO: replace with real artist data from the artist table, using artist_id
    data = {}

    try:
        artist = Artist.query.get(artist_id)

        if artist is None:
            return render_template("errors/404.html"), 404

        genres = []
        for item in artist.genres:
            genres.append(item.genre)

        shows = Show.query.filter_by(artist_id=artist_id)

        raw_past_shows = shows.filter(
            Show.start_time < datetime.datetime.now()).all()
        past_shows = []
        for show in raw_past_shows:
            venue = Venue.query.get(show.venue_id)
            show_data = {
                "venue_id": venue.id,
                "venue_name": venue.name,
                "venue_image_link": venue.image_link,
                "start_time": str(show.start_time),
            }
            past_shows.append(show_data)

        shows = shows.filter(
            Show.start_time >= datetime.datetime.now()).all()
        upcoming_shows = []
        for show in shows:
            venue = Venue.query.get(show.venue_id)
            show_data = {
                "venue_id": venue.id,
                "venue_name": venue.name,
                "venue_image_link": venue.image_link,
                "start_time": str(show.start_time),
            }
            upcoming_shows.append(show_data)

        data = {
            "id": artist.id,
            "name": artist.name,
            "genres": genres,
            "city": artist.city,
            "state": artist.state,
            "phone": artist.phone,
            "seeking_venue": False,
            "facebook_link": artist.facebook_link,
            "image_link": artist.image_link,
            "past_shows": past_shows,
            "upcoming_shows": upcoming_shows,
            "past_shows_count": len(past_shows),
            "upcoming_shows_count": len(upcoming_shows),
        }

    except:
        flash("Cannot Fetch. Please try again.")

    finally:
        db.session.close()

    return render_template("pages/show_artist.html", artist=data)


#  Update
#  ----------------------------------------------------------------
@app.route("/artists/<int:artist_id>/edit", methods=["GET"])
def edit_artist(artist_id):
    form = ArtistForm()

    data = {}

    try:
        artist = Artist.query.get(artist_id)
        if artist is None:
            return render_template("errors/404.html"), 404

        genres = []
        if len(artist.genres) > 0:
            for item in artist.genres:
                genres.append(item.genre)

        data = {
            "id": artist.id,
            "name": artist.name,
            "city": artist.city,
            "state": artist.state,
            "phone": artist.phone,
            "genres": genres,
            "facebook_link": artist.facebook_link,
            "seeking_venue": artist.seeking_venue,
            "seeking_description": artist.seeking_description,
            "image_link": artist.image_link,
        }

    except:
        flash("Cannot. Please try again.")
        return render_template("pages/home.html")

    finally:
        db.session.close()
        # TODO: populate form with fields from artist with ID <artist_id>

    return render_template("forms/edit_artist.html", form=form, artist=data)


@app.route("/artists/<int:artist_id>/edit", methods=["POST"])
def edit_artist_submission(artist_id):
    # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
    try:
        artist = Artist.query.get(artist_id)

        if artist is None:
            return render_template("errors/404.html"), 404

        name = request.form.get("name")
        city = request.form.get("city")
        state = request.form.get("state")
        phone = request.form.get("phone")
        genres = request.form.getlist("genres")
        facebook_link = request.form.get("facebook_link")

        artist = name
        artist.city = city
        artist.state = state
        artist.phone = phone
        artist.facebook_link = facebook_link
        artist.image_link = "https://images.unsplash.com/photo-1549213783-8284d0336c4f?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=300&q=80"

        genres = []
        for genre in genres:
            artistGenre = Artist_Genre(genre=genre)
            artistGenre.artist = artist
            genres.append(artistGenre)

        db.session.add(artist)
        db.session.commit()
        flash("This venue was successfully updated!")

    except:
        db.session.rollback()
        name = request.form.get("name")
        flash(f"{name} could not be updated.")

    finally:
        db.session.close()

    return redirect(url_for("show_artist", artist_id=artist_id))


@app.route("/venues/<int:venue_id>/edit", methods=["GET"])
def edit_venue(venue_id):
    # TODO: take values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes
    form = VenueForm()

    data = {}

    try:
        venue = Venue.query.get(venue_id)

        if venue is None:
            return render_template("errors/404.html"), 404

        genres = []
        if len(venue.genres) > 0:
            for item in venue.genres:
                genres.append(item.genre)

        data = {
            "id": venue.id,
            "name": venue.name,
            "city": venue.city,
            "state": venue.state,
            "address": venue.address,
            "phone": venue.phone,
            "genres": genres,
            "facebook_link": venue.facebook_link,
            "seeking_talent": venue.seeking_talent,
            "seeking_description": venue.seeking_description,
            "image_link": venue.image_link,
        }

    except:
        flash("Something went wrong. Please try again.")
        return render_template("pages/home.html")

    finally:
        db.session.close()

    return render_template("forms/edit_venue.html", form=form, venue=data)


@app.route("/venues/<int:venue_id>/edit", methods=["POST"])
def edit_venue_submission(venue_id):
    try:
        name = request.form.get("name")
        city = request.form.get("city")
        state = request.form.get("state")
        address = request.form.get("address")
        phone = request.form.get("phone")
        genres = request.form.getlist("genres")
        facebook_link = request.form.get("facebook_link")

        venue = Venue.query.get(venue_id)

        venue.name = name
        venue.city = city
        venue.state = state
        venue.address = address
        venue.phone = phone
        venue.facebook_link = facebook_link

        genres = []
        for genre in genres:
            venueGenre = Venue_Genre(genre=genre)
            venueGenre.venue = venue
            genres.append(venueGenre)

        db.session.add(venue)
        db.session.commit()
        flash("This venue was successfully updated!")

    except:
        name = request.form.get("name")
        flash("An error occurred. Venue {name} could not be updated.")

    finally:
        db.session.close()

    return redirect(url_for("show_venue", venue_id=venue_id))


#  Create Artist
#  ----------------------------------------------------------------
@app.route("/artists/create", methods=["GET"])
def create_artist_form():

    form = ArtistForm()
    return render_template("forms/new_artist.html", form=form)


@app.route("/artists/create", methods=["POST"])
def create_artist_submission():
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  # on successful db insert, flash success
    try:
        name = request.form.get("name")
        city = request.form.get("city")
        state = request.form.get("state")
        phone = request.form.get("phone")
        genres = request.form.getlist("genres")
        facebook_link = request.form.get("facebook_link")

        artist = Artist(
            name=name, city=city, state=state, phone=phone, facebook_link=facebook_link
        )

        genres = []
        for genre in genres:
            artistGenre = Artist_Genre(genre=genre)
            artistGenre.artist = artist
            genres.append(artistGenre)

        db.session.add(artist)
        db.session.commit()
        artistName = artist.name
        flash(f"{artistName} was successfully Added!")

    except:
        db.session.rollback()
        name = request.form.get("name")
        flash("An error occurred. Venue {name} could not be listed.")

    finally:
        db.session.close()
        return render_template("pages/home.html")


@app.route("/artists/<artist_id>/delete", methods=["GET"])
def delete_artist(artist_id):
    # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
    try:
        artist = db.session.query(
            Artist).filter(Artist.id == artist_id)
        artist.delete()
        db.session.commit()
        flash(f"{artist.name} was successfully deleted.")

    except:
        db.session.rollback()
        flash(f"{artist.name} was not deleted.")

    finally:
        db.session.close()
        return redirect(url_for("index"))


#  Shows
#  ----------------------------------------------------------------
@app.route("/shows")
def shows():
    # displays list of shows at /shows
    # TODO: replace with real venues data.
    data = []

    try:
        allShows = Show.query.all()
        for show in allShows:
            venue_id = show.venue_id
            artist_id = show.artist_id
            artist = Artist.query.get(artist_id)

            showInShows = {
                "venue_id": venue_id,
                "venue_name": Venue.query.get(venue_id).name,
                "artist_id": artist_id,
                "artist_name": artist.name,
                "artist_image_link": artist.image_link,
                "start_time": str(show.start_time),
            }

            data.append(showInShows)

    except:
        flash("Something went wrong, please try again.")

    finally:
        return render_template("pages/shows.html", shows=data)


@app.route("/shows/create")
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template("forms/new_show.html", form=form)


@app.route("/shows/create", methods=["POST"])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing form
    # TODO: insert form data as a new Show record in the db, instead

    # on successful db insert, flash success

    errors = {"notArtist": False, "notVenue": False}

    try:
        artist_id = request.form.get("artist_id")
        venue_id = request.form.get("venue_id")
        start_time = request.form.get("start_time")

        artist = Artist.query.get(artist_id)
        if artist is None:
            errors["notArtist"] = True

        venue = Venue.query.get(venue_id)
        if venue is None:
            errors["notVenue"] = True

        if venue is not None and artist is not None:
            show = Show(
                artist_id=artist.id,
                venue_id=venue.id,
                start_time=start_time,
            )
            db.session.add(show)
            db.session.commit()
            artistName = artist.name
            venueName = venue.name
            flash(
                f"The show by {artistName} has been successfully scheduled at the {venueName}")

    except:
        flash("Something went wrong and the show was not created. Please try again.")

    finally:
        db.session.close()

    if errors["notArtist"] is True:
        artistId = request.form.get("artist_id")
        flash(f"artist with id {artistId} does not exist")
    elif errors["notVenue"] is True:
        venueId = request.form.get("venue_id")
        flash(f"venue with id {venueId} does not exist")

    return render_template("pages/home.html")


@app.errorhandler(404)
def not_found_error(error):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def server_error(error):
    return render_template("errors/500.html"), 500


if not app.debug:
    file_handler = FileHandler("error.log")
    file_handler.setFormatter(
        Formatter(
            "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]")
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info("errors")

# ----------------------------------------------------------------------------#
# Launch.
# ----------------------------------------------------------------------------#

# Default port:
if __name__ == "__main__":
    app.run()

# Or specify port manually:
"""
if __name__ == '__main__':
		port = int(os.environ.get('PORT', 5000))
		app.run(host='0.0.0.0', port=port)
"""
