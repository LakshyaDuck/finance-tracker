import requests

from flask import redirect, render_template, session
from functools import wraps
from sqlalchemy import select

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


def get_user_by_id():
    return session.get("user_id")


def get_account_with_verification():
    user_id = get_user_by_id()
    if not user_id:
        return None
    account_id = session.get("account_id")
    if account_id is None:
        return None
    a_ids = select(Account.id).where(Account.user_id == user_id)
    if account_id not in a_ids:
        return None
    return account_id

