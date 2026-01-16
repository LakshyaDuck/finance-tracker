from flask import redirect, render_template, session
from functools import wraps
from datetime import date


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/account")
        return f(*args, **kwargs)

    return decorated_function


def apology(message, code=400):
    return render_template("apology.html", top=code, bottom=message), code


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"

def convert_date_to_sqlite(date_obj):
    return str(date_obj).split(' ')[0]