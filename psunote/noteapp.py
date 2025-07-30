import flask

import models
import forms


app = flask.Flask(__name__)
app.config["SECRET_KEY"] = "This is secret key"
app.config[
    "SQLALCHEMY_DATABASE_URI"
] = "postgresql://coe:CoEpasswd@localhost:5432/coedb"
# app.config[
#     "SQLALCHEMY_DATABASE_URI"
# ] = "sqlite:///notes.db"
models.init_app(app)


@app.route("/")
def index():
    db = models.db
    notes = db.session.execute(
        db.select(models.Note).order_by(models.Note.title)
    ).scalars()
    return flask.render_template(
        "index.html",
        notes=notes,
    )


@app.route("/notes/create", methods=["GET", "POST"])
def notes_create():
    form = forms.NoteForm()
    if not form.validate_on_submit():
        print("error", form.errors)
        return flask.render_template(
            "notes-create.html",
            form=form,
        )
    note = models.Note()
    form.populate_obj(note)
    note.tags = []

    db = models.db
    for tag_name in form.tags.data:
        tag = (
            db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name))
            .scalars()
            .first()
        )

        if not tag:
            tag = models.Tag(name=tag_name)
            db.session.add(tag)

        note.tags.append(tag)

    db.session.add(note)
    db.session.commit()

    return flask.redirect(flask.url_for("index"))


@app.route("/tags/<tag_name>")
def tags_view(tag_name):
    db = models.db
    tag = (
        db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name))
        .scalars()
        .first()
    )
    notes = db.session.execute(
        db.select(models.Note).where(models.Note.tags.any(id=tag.id))
    ).scalars()

    return flask.render_template(
        "tags-view.html",
        tag_name=tag_name,
        notes=notes,
    )


# Edit Note
@app.route("/notes/<int:note_id>/edit", methods=["GET", "POST"])
def notes_edit(note_id):
    db = models.db
    note = db.session.get(models.Note, note_id)
    # Convert Tag objects to tag names for the form
    note_data = note.__dict__.copy()
    note_data['tags'] = [t.name for t in note.tags]
    form = forms.NoteForm(data=note_data)
    if not form.validate_on_submit():
        return flask.render_template("notes-create.html", form=form, edit=True)
    # Populate all fields except tags
    form_data = form.data.copy()
    form_data.pop('tags', None)
    for key, value in form_data.items():
        setattr(note, key, value)
    # Now set tags as Tag objects
    note.tags = []
    for tag_name in form.tags.data:
        tag = db.session.execute(db.select(models.Tag).where(models.Tag.name == tag_name)).scalars().first()
        if not tag:
            tag = models.Tag(name=tag_name)
            db.session.add(tag)
        note.tags.append(tag)
    db.session.commit()
    return flask.redirect(flask.url_for("index"))

# Delete Note
@app.route("/notes/<int:note_id>/delete", methods=["POST"])
def notes_delete(note_id):
    db = models.db
    note = db.session.get(models.Note, note_id)
    db.session.delete(note)
    db.session.commit()
    return flask.redirect(flask.url_for("index"))

# Edit Tag
@app.route("/tags/<int:tag_id>/edit", methods=["GET", "POST"])
def tags_edit(tag_id):
    db = models.db
    tag = db.session.get(models.Tag, tag_id)
    if flask.request.method == "POST":
        new_name = flask.request.form.get("name")
        if new_name:
            tag.name = new_name
            db.session.commit()
            return flask.redirect(flask.url_for("tags_view", tag_name=tag.name))
    return flask.render_template("tags-edit.html", tag=tag)

# Delete Tag
@app.route("/tags/<int:tag_id>/delete", methods=["POST"])
def tags_delete(tag_id):
    db = models.db
    tag = db.session.get(models.Tag, tag_id)
    # Remove tag from all notes before deleting
    notes_with_tag = db.session.execute(db.select(models.Note).where(models.Note.tags.any(id=tag_id))).scalars().all()
    for note in notes_with_tag:
        note.tags = [t for t in note.tags if t.id != tag_id]
    db.session.commit()
    db.session.delete(tag)
    db.session.commit()
    return flask.redirect(flask.url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
