import os
import uuid
from datetime import datetime

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from auth import get_current_user, login_required
from db import get_db, init_db
from photos import save_uploaded_photo, delete_photo_file

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")


@app.context_processor
def cache_bust():
    """Add file mtime as cache buster for static assets."""
    def bust(filename):
        fpath = os.path.join(app.static_folder, filename)
        try:
            return f"/static/{filename}?v={int(os.path.getmtime(fpath))}"
        except OSError:
            return f"/static/{filename}"
    return {"static_bust": bust}


@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


UPLOAD_FOLDER = os.path.join(app.root_path, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "heic"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.before_request
def ensure_db():
    init_db()


def _user_id():
    return session["user_id"]


def _owns_item(db, item_id):
    """Return the item row if owned by current user, else None."""
    item = db.execute(
        "SELECT * FROM items WHERE id = ? AND user_id = ?", (item_id, _user_id())
    ).fetchone()
    return item


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if not email or not password:
            flash("Email and password are required.", "error")
            return render_template("register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        cursor = db.execute(
            "INSERT INTO users (email, password, name) VALUES (?, ?, ?)",
            (email, generate_password_hash(password), name or None),
        )
        db.commit()
        session["user_id"] = cursor.lastrowid
        flash("Account created!", "success")
        return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            flash(f"Welcome back{', ' + user['name'] if user['name'] else ''}!", "success")
            return redirect(url_for("index"))

        flash("Invalid email or password.", "error")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "success")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@app.route("/")
@login_required
def index():
    db = get_db()
    uid = _user_id()
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()

    query = "SELECT * FROM items WHERE user_id = ?"
    params = [uid]

    if search:
        query += " AND (name LIKE ? OR description LIKE ? OR brand LIKE ? OR notes LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like, like])
    if category:
        query += " AND category = ?"
        params.append(category)
    if location:
        query += " AND location = ?"
        params.append(location)

    query += " ORDER BY created_at DESC"
    items = db.execute(query, params).fetchall()

    # Fetch categories and locations for filter dropdowns
    categories = db.execute(
        "SELECT DISTINCT category FROM items WHERE user_id = ? AND category IS NOT NULL AND category != '' ORDER BY category",
        (uid,),
    ).fetchall()
    locations = db.execute(
        "SELECT DISTINCT location FROM items WHERE user_id = ? AND location IS NOT NULL AND location != '' ORDER BY location",
        (uid,),
    ).fetchall()

    # Attach first photo to each item for the listing
    items_with_photos = []
    for item in items:
        photo = db.execute(
            "SELECT filename FROM photos WHERE item_id = ? ORDER BY created_at ASC LIMIT 1",
            (item["id"],),
        ).fetchone()
        items_with_photos.append(
            {**dict(item), "thumbnail": photo["filename"] if photo else None}
        )

    return render_template(
        "index.html",
        items=items_with_photos,
        categories=[c["category"] for c in categories],
        locations=[c["location"] for c in locations],
        search=search,
        selected_category=category,
        selected_location=location,
    )


def _form_options():
    """Fetch distinct locations and categories for form datalists."""
    db = get_db()
    uid = _user_id()
    locations = db.execute(
        "SELECT DISTINCT location FROM items WHERE user_id = ? AND location IS NOT NULL AND location != '' ORDER BY location",
        (uid,),
    ).fetchall()
    categories = db.execute(
        "SELECT DISTINCT category FROM items WHERE user_id = ? AND category IS NOT NULL AND category != '' ORDER BY category",
        (uid,),
    ).fetchall()
    return {
        "locations": [r["location"] for r in locations],
        "categories": [r["category"] for r in categories],
    }


@app.route("/item/new")
@login_required
def new_item():
    return render_template("item_form.html", item=None, photos=[], **_form_options())


@app.route("/item/<int:item_id>")
@login_required
def view_item(item_id):
    db = get_db()
    item = _owns_item(db, item_id)
    if not item:
        flash("Item not found.", "error")
        return redirect(url_for("index"))
    photos = db.execute(
        "SELECT * FROM photos WHERE item_id = ? ORDER BY created_at ASC", (item_id,)
    ).fetchall()
    return render_template("item_view.html", item=item, photos=photos)


@app.route("/item/<int:item_id>/edit")
@login_required
def edit_item(item_id):
    db = get_db()
    item = _owns_item(db, item_id)
    if not item:
        flash("Item not found.", "error")
        return redirect(url_for("index"))
    photos = db.execute(
        "SELECT * FROM photos WHERE item_id = ? ORDER BY created_at ASC", (item_id,)
    ).fetchall()
    return render_template("item_form.html", item=item, photos=photos, **_form_options())


# ---------------------------------------------------------------------------
# API — Items
# ---------------------------------------------------------------------------


@app.route("/api/items", methods=["POST"])
@login_required
def create_item():
    data = request.form
    db = get_db()
    cursor = db.execute(
        """INSERT INTO items
           (user_id, name, description, category, brand, serial_number,
            purchase_date, purchase_location, purchase_price,
            warranty_info, warranty_expiry, location, condition, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            _user_id(),
            data.get("name"),
            data.get("description"),
            data.get("category"),
            data.get("brand"),
            data.get("serial_number"),
            data.get("purchase_date") or None,
            data.get("purchase_location"),
            data.get("purchase_price") or None,
            data.get("warranty_info"),
            data.get("warranty_expiry") or None,
            data.get("location"),
            data.get("condition"),
            data.get("notes"),
        ),
    )
    db.commit()
    item_id = cursor.lastrowid

    # Associate any staged photos (sent as comma-separated temp filenames)
    staged = data.get("staged_photos", "")
    if staged:
        for filename in staged.split(","):
            filename = filename.strip()
            if filename:
                db.execute(
                    "INSERT INTO photos (item_id, filename) VALUES (?, ?)",
                    (item_id, filename),
                )
        db.commit()

    flash("Item added!", "success")
    return redirect(url_for("view_item", item_id=item_id))


@app.route("/api/items/<int:item_id>", methods=["POST"])
@login_required
def update_item(item_id):
    db = get_db()
    if not _owns_item(db, item_id):
        flash("Item not found.", "error")
        return redirect(url_for("index"))

    data = request.form
    db.execute(
        """UPDATE items SET
           name=?, description=?, category=?, brand=?, serial_number=?,
           purchase_date=?, purchase_location=?, purchase_price=?,
           warranty_info=?, warranty_expiry=?, location=?, condition=?, notes=?,
           updated_at=CURRENT_TIMESTAMP
           WHERE id=? AND user_id=?""",
        (
            data.get("name"),
            data.get("description"),
            data.get("category"),
            data.get("brand"),
            data.get("serial_number"),
            data.get("purchase_date") or None,
            data.get("purchase_location"),
            data.get("purchase_price") or None,
            data.get("warranty_info"),
            data.get("warranty_expiry") or None,
            data.get("location"),
            data.get("condition"),
            data.get("notes"),
            item_id,
            _user_id(),
        ),
    )

    # Handle newly staged photos
    staged = data.get("staged_photos", "")
    if staged:
        for filename in staged.split(","):
            filename = filename.strip()
            if filename:
                db.execute(
                    "INSERT INTO photos (item_id, filename) VALUES (?, ?)",
                    (item_id, filename),
                )

    db.commit()
    flash("Item updated!", "success")
    return redirect(url_for("view_item", item_id=item_id))


@app.route("/api/items/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(item_id):
    db = get_db()
    if not _owns_item(db, item_id):
        flash("Item not found.", "error")
        return redirect(url_for("index"))

    photos = db.execute(
        "SELECT filename FROM photos WHERE item_id = ?", (item_id,)
    ).fetchall()
    for photo in photos:
        delete_photo_file(app.config["UPLOAD_FOLDER"], photo["filename"])
    db.execute("DELETE FROM photos WHERE item_id = ?", (item_id,))
    db.execute("DELETE FROM items WHERE id = ? AND user_id = ?", (item_id, _user_id()))
    db.commit()
    flash("Item deleted.", "success")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# API — Photos
# ---------------------------------------------------------------------------


@app.route("/api/photos/upload", methods=["POST"])
@login_required
def upload_photo():
    """Upload and compress a photo. Returns the server filename.
    Used during item creation (before item exists) and editing."""
    if "photo" not in request.files:
        return jsonify({"error": "No photo provided"}), 400

    file = request.files["photo"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    filename = save_uploaded_photo(file, app.config["UPLOAD_FOLDER"])
    return jsonify({"filename": filename, "url": url_for("uploaded_file", filename=filename)})


@app.route("/api/photos/<int:photo_id>/delete", methods=["POST"])
@login_required
def delete_photo(photo_id):
    db = get_db()
    # Verify the photo belongs to an item owned by this user
    photo = db.execute(
        """SELECT p.* FROM photos p
           JOIN items i ON p.item_id = i.id
           WHERE p.id = ? AND i.user_id = ?""",
        (photo_id, _user_id()),
    ).fetchone()
    if photo:
        delete_photo_file(app.config["UPLOAD_FOLDER"], photo["filename"])
        db.execute("DELETE FROM photos WHERE id = ?", (photo_id,))
        db.commit()
    return jsonify({"ok": True})


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ---------------------------------------------------------------------------
# API — AI Analysis
# ---------------------------------------------------------------------------


@app.route("/api/ai/analyse", methods=["POST"])
@login_required
def ai_analyse():
    """Send one or more photos to the Claude API for item analysis."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured on server"}), 500

    data = request.get_json()
    filenames = data.get("filenames", [])
    if not filenames:
        return jsonify({"error": "No photos to analyse"}), 400

    import anthropic
    import base64
    import mimetypes

    content = []
    for fname in filenames:
        fpath = os.path.join(app.config["UPLOAD_FOLDER"], fname)
        if not os.path.isfile(fpath):
            continue
        mime = mimetypes.guess_type(fpath)[0] or "image/jpeg"
        with open(fpath, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64},
        })

    content.append({
        "type": "text",
        "text": (
            "You are an inventory assistant. Analyse these photos of a household item. "
            "Return a JSON object (no markdown fencing) with these keys, using null for "
            "anything you cannot determine:\n"
            "name, description, category, brand, serial_number, purchase_price, "
            "condition, notes\n"
            "For category, pick one of: Electronics, Furniture, Kitchen, Clothing, "
            "Tools, Sports, Books, Toys, Appliances, Decor, Office, Outdoor, Other.\n"
            "For condition, pick one of: New, Like New, Good, Fair, Poor.\n"
            "Be concise. Only return the JSON object."
        ),
    })

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )

    import json

    try:
        result = json.loads(message.content[0].text)
    except (json.JSONDecodeError, IndexError):
        result = {"notes": message.content[0].text if message.content else "Analysis failed"}

    return jsonify(result)


# ---------------------------------------------------------------------------
# PWA
# ---------------------------------------------------------------------------


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json")


@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
