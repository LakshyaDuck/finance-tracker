# Development Process:
# - Core logic and database design: Created by me
# - Code structure and implementation: Developed with AI assistance (Claude/Perplexity)
# - All code is reviewed and modified by me
# - Features designed and debugged through iterative problem-solving

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
import splite3
from datetime import date
from contextlib import contextmanager

from helpers import apology, login_required, usd

app = Flask(__name__)

app.jinja_env.filters["usd"] = usd # For formatting in usd

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@contextmanager
def get_db():
    """
    Creates a database connection with row_factory set to sqlite3.Row.
    This allows you to access columns by name (like dict) instead of index.
    Automatically closes the connection after use.
    """
    conn = sqlite3.connect('finance.db')  # Creates DB if doesn't exist
    conn.row_factory = sqlite3.Row  # Makes rows act like dicts
    try:
        yield conn
    finally:
        conn.close()

'''
First page will give user two optiocd
1. Register
2. Login
The web app can not be used without it.
'''
@app.route('/account', methods=["GET", "POST"])
def account():
	return render_template("account.html")

# ====================
# Toggle theme
# ====================
@app.route('/toggle_theme', methods=["POST"])
@login_required
def toggle_theme():
    current_theme = session.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    session['theme'] = new_theme
    return redirect('/settings')

# ====================
# Login
# ====================
@app.route('/login', methods=["GET", "POST"])
def login():
    session.clear()

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    if not username or not password:
        return apology("Must provide username and password", 403)

    rows = db.execute("SELECT * FROM users WHERE username = ?", username)

    if len(rows) != 1:
        return apology("Invalid username", 403)

    if not check_password_hash(rows[0]["hash"], password):
        return apology("Invalid password", 403)

    session["user_id"] = rows[0]["id"]

    # Get user's Main Account
    main_account = db.execute("""
        SELECT id FROM accounts
        WHERE user_id = ? AND type = 'current'
        ORDER BY created_at ASC
        LIMIT 1
    """, session["user_id"])

    # If no main account exists, create one
    if not main_account:
        db.execute("INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)",
                   session["user_id"], "Main Account", "current", 0)
        main_account = db.execute("""
            SELECT id FROM accounts
            WHERE user_id = ? AND type = 'current'
            ORDER BY created_at ASC
            LIMIT 1
        """, session["user_id"])

    session["account_id"] = main_account[0]["id"]

    return redirect("/")

# ====================
# Register
# ====================
@app.route('/register', methods=["GET", "POST"])
def register():
    session.clear()

    if request.method == 'GET':
        return render_template("register.html")

    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")
    currency = request.form.get("currency")

    if not username or not password or not confirmation:
        return apology("Must provide all fields", 403)

    if password != confirmation:
        return apology("Passwords don't match", 403)

    try:
        pass_hash = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash, currency) VALUES (?, ?, ?)",
                   username, pass_hash, currency)

        user = db.execute("SELECT * FROM users WHERE username = ?", username)
        session["user_id"] = user[0]["id"]

        # CREATE DEFAULT CURRENT ACCOUNT
        db.execute("INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)",
                   session["user_id"], "Main Account", "current", 0)

        new_account = db.execute("""
            SELECT id FROM accounts
            WHERE user_id = ? AND type = 'current'
            ORDER BY created_at ASC
            LIMIT 1
        """, session["user_id"])

        session["account_id"] = new_account[0]["id"]

        return redirect("/")
    except:
        return apology("Username already exists", 403)

# ====================
# Home
# ====================
@app.route('/')
def home():
    # Manual login check
    if "user_id" not in session:
        return render_template('account.html')

    user_id = session["user_id"]

    # Check if account is selected in session
    if "account_id" not in session:
        # Create Main Account if it doesn't exist
        main_account = db.execute("""
            SELECT id FROM accounts
            WHERE user_id = ? AND type = 'current'
            ORDER BY created_at ASC
            LIMIT 1
        """, user_id)

        if not main_account:
            db.execute("INSERT INTO accounts (user_id, name, type, balance) VALUES (?, ?, ?, ?)",
                       user_id, "Main Account", "current", 0)
            main_account = db.execute("""
                SELECT id FROM accounts
                WHERE user_id = ? AND type = 'current'
                ORDER BY created_at ASC
                LIMIT 1
            """, user_id)

        session["account_id"] = main_account[0]["id"]

    account_id = session["account_id"]
    current_month = date.today().strftime("%Y-%m")

    # Get current account details
    account = db.execute("SELECT * FROM accounts WHERE id = ? AND user_id = ?", account_id, user_id)

    if not account:
        return apology("Account not found", 404)

    account_balance = account[0]["balance"]
    account_name = account[0]["name"]
    account_type = account[0]["type"]

    # Get this month's income for THIS account only
    income_result = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total FROM transactions
        WHERE user_id = ? AND account_id = ? AND type = 'income'
        AND strftime('%Y-%m', date) = ?
    """, user_id, account_id, current_month)
    monthly_income = income_result[0]["total"]

    # Get this month's expenses for THIS account only
    expense_result = db.execute("""
        SELECT COALESCE(SUM(amount), 0) as total FROM transactions
        WHERE user_id = ? AND account_id = ? AND type = 'expense'
        AND strftime('%Y-%m', date) = ?
    """, user_id, account_id, current_month)
    monthly_expenses = expense_result[0]["total"]

    # Calculate monthly net
    monthly_net = monthly_income - monthly_expenses

    # Get budget alerts (spending across ALL accounts)
    budget_alerts = db.execute("""
        SELECT
            c.name as category_name,
            b.monthly_limit as budget_limit,
            COALESCE(SUM(t.amount), 0) as spent,
            (COALESCE(SUM(t.amount), 0) / b.monthly_limit * 100) as percent
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t ON t.category_id = c.id
            AND t.user_id = ?
            AND strftime('%Y-%m', t.date) = ?
            AND t.type = 'expense'
            WHERE b.user_id = ? AND b.month = ?
        GROUP BY b.id, c.name, b.monthly_limit
        HAVING percent >= 80
        ORDER BY percent DESC
        LIMIT 5
        """, user_id, current_month, user_id, current_month)


    # Get recent transactions for THIS account only
    recent_transactions = db.execute("""
        SELECT t.id, t.amount, t.date, t.type, t.person_name, t.direction,
               c.name as category_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ? AND t.account_id = ?
        ORDER BY t.date DESC, t.id DESC
        LIMIT 8
    """, user_id, account_id)

    return render_template('home.html',
                         account_balance=account_balance,
                         account_name=account_name,
                         account_type=account_type,
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expenses,
                         monthly_net=monthly_net,
                         budget_alerts=budget_alerts,
                         recent_transactions=recent_transactions)


# ====================
# Create user account
# ====================
@app.route('/create_user_account', methods=["GET", "POST"])
@login_required
def create_user_account():
    if request.method == 'GET':
        return render_template('create_user_account.html')

    if request.method == 'POST':
        name = request.form.get('name')
        type = request.form.get('type')

        if not name or not type:
            return apology("Please enter the details", 400)
        try:
            db.execute("INSERT INTO accounts (user_id, name, type) VALUES (?, ?, ?)",
                      session['user_id'], name, type)
            return redirect('/')
        except:
            return apology("Either name is same or type entered was invalid", 400)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect("/")

# ====================
# Transactions
# ====================
@app.route('/transactions')
@login_required
def transactions():
    # Join with categories to get category names
    transactions = db.execute("""
        SELECT t.id, t.amount, t.description, t.date, t.type,
               t.person_name, t.direction, c.name as category_name
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.date DESC
    """, session["user_id"])

    return render_template('transactions.html', transactions=transactions)







##### BELOW FUNCTION IS NOT REVIEWED #######






# ====================
# Add transaction
# ====================
@app.route('/add_transaction', methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == 'GET':
        # Get user's accounts
        accounts = db.execute("SELECT id, name, type, balance FROM accounts WHERE user_id = ?", session["user_id"])

        # Get categories for dropdown
        expense_categories = db.execute("SELECT * FROM categories WHERE type = 'expense' AND (user_id = ? OR user_id IS NULL)", session["user_id"])
        income_categories = db.execute("SELECT * FROM categories WHERE type = 'income' AND (user_id = ? OR user_id IS NULL)", session["user_id"])

        return render_template('add_transaction.html',
                             accounts=accounts,
                             expense_categories=expense_categories,
                             income_categories=income_categories)

    if request.method == 'POST':
        amount = request.form.get('amount')
        description = request.form.get('description')
        trans_date = request.form.get('date')
        trans_type = request.form.get('type')

        if not amount or not trans_date or not trans_type:
            return apology("Please enter all essential details", 400)

        # Convert amount to float
        amount = float(amount)

        # Handle TRANSFER transactions
        if trans_type == "transfer":
            from_account_id = request.form.get('from_account_id')
            to_account_id = request.form.get('to_account_id')

            if not from_account_id or not to_account_id:
                return apology("Please select both accounts", 400)

            if from_account_id == to_account_id:
                return apology("Cannot transfer to the same account", 400)

            # Verify both accounts belong to user
            from_account = db.execute("SELECT * FROM accounts WHERE id = ? AND user_id = ?", from_account_id, session["user_id"])
            to_account = db.execute("SELECT * FROM accounts WHERE id = ? AND user_id = ?", to_account_id, session["user_id"])

            if not from_account or not to_account:
                return apology("Invalid accounts", 400)

            # Check sufficient balance
            if from_account[0]["balance"] < amount:
                return apology("Insufficient balance in source account", 400)

            try:
                # 1. Create transfer record in transfers table
                db.execute("""
                    INSERT INTO transfers (user_id, from_account_id, to_account_id, amount, date, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, session["user_id"], from_account_id, to_account_id, amount, trans_date, description)

                # 2. Update account balances
                db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, from_account_id)
                db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, to_account_id)

                # 3. Create two transaction records for display in transaction history
                # Outgoing transaction (from source account)
                db.execute("""
                    INSERT INTO transactions
                    (user_id, account_id, category_id, amount, description, date, type, person_name, direction)
                    VALUES (?, ?, NULL, ?, ?, ?, 'expense', ?, NULL)
                """, session["user_id"], from_account_id, amount,
                     f"Transfer to {to_account[0]['name']}" + (f" - {description}" if description else ""),
                     trans_date, to_account[0]['name'])

                # Incoming transaction (to destination account)
                db.execute("""
                    INSERT INTO transactions
                    (user_id, account_id, category_id, amount, description, date, type, person_name, direction)
                    VALUES (?, ?, NULL, ?, ?, ?, 'income', ?, NULL)
                """, session["user_id"], to_account_id, amount,
                     f"Transfer from {from_account[0]['name']}" + (f" - {description}" if description else ""),
                     trans_date, from_account[0]['name'])

                flash(f"Transferred {amount} from {from_account[0]['name']} to {to_account[0]['name']}", "success")
                return redirect("/transactions")

            except Exception as e:
                print(f"Transfer error: {e}")
                return apology("Transfer failed", 400)

        # Handle other transaction types (income, expense, personal)
        account_id = request.form.get('account_id')

        if not account_id:
            return apology("Please select an account", 400)

        # Validate account belongs to user
        account = db.execute("SELECT * FROM accounts WHERE id = ? AND user_id = ?", account_id, session["user_id"])
        if not account:
            return apology("Invalid account", 400)

        # Handle personal transactions
        if trans_type == "personal":
            person_name = request.form.get('person_name')
            direction = request.form.get('direction')

            if not person_name or not direction:
                return apology("Please enter person name and direction", 400)

            try:
                db.execute("""INSERT INTO transactions
                           (user_id, account_id, category_id, amount, description, date, type, person_name, direction)
                           VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)""",
                           session['user_id'], account_id, amount, description, trans_date, trans_type, person_name, direction)

                if direction == "lent":
                    db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, account_id)
                else:  # borrowed
                    db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, account_id)

                return redirect("/transactions")
            except Exception as e:
                print(f"Error: {e}")
                return apology("Something went wrong", 400)

        # Handle income/expense transactions
        else:
            category_name = request.form.get('category')
            if not category_name:
                return apology("Please select a category", 400)

            category = db.execute("SELECT id FROM categories WHERE name = ?", category_name)
            if not category:
                return apology("Invalid category", 400)

            category_id = category[0]["id"]

            try:
                db.execute("""INSERT INTO transactions
                           (user_id, account_id, category_id, amount, description, date, type, person_name, direction)
                           VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL)""",
                           session['user_id'], account_id, category_id, amount, description, trans_date, trans_type)

                if trans_type == "income":
                    db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, account_id)
                elif trans_type == "expense":
                    db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, account_id)

                return redirect("/transactions")
            except Exception as e:
                print(f"Error: {e}")
                return apology("Something went wrong", 400)



##### ABOVE FUNCTION IS NOT REVIEWED #######








# ====================
# Delete transactions
# ====================
@app.route('/delete_transaction', methods=["POST"])
@login_required
def delete_transaction():
    transaction_id = request.form.get('transaction_id')

    if not transaction_id:
        return apology("Invalid transaction", 400)

    # Get full transaction details before deleting
    transaction = db.execute("""
        SELECT user_id, account_id, amount, type, direction
        FROM transactions
        WHERE id = ?
    """, transaction_id)

    if not transaction or transaction[0]["user_id"] != session["user_id"]:
        return apology("Unauthorized", 403)

    # Extract transaction details
    account_id = transaction[0]["account_id"]
    amount = transaction[0]["amount"]
    trans_type = transaction[0]["type"]
    direction = transaction[0]["direction"]

    # Update Account balance according to transaction type
    if trans_type == "income":
        # Subtrat the money if income
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, account_id)
    elif trans_type == "expense":
        # Add the money if expense
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, account_id)
    elif trans_type == "personal":
        if direction == "lent":
            # Add if lent
            db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, account_id)
        elif direction == "borrowed":
            # Subtract if borrowed
            db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, account_id)

    # Delete the transaction
    db.execute("DELETE FROM transactions WHERE id = ?", transaction_id)

    return redirect("/transactions")


# ====================
# Budgets
# ====================
@app.route('/budgets', methods=["GET", "POST"])
@login_required
def budgets():
    if request.method == "GET":
        current_month = date.today().strftime("%Y-%m")

        # Get all expense categories (preset + user-created)
        categories = db.execute("""
            SELECT name, id FROM categories
            WHERE (user_id = ? OR user_id IS NULL) AND type = 'expense'
        """, session['user_id'])

        # Get budgets for current month
        budgets = db.execute("""
            SELECT * FROM budgets
            WHERE user_id = ? AND month = ?
        """, session['user_id'], current_month)

        # Calculate spent amount for each category this month
        spent = db.execute("""
            SELECT category_id, SUM(amount) as total_spent
            FROM transactions
            WHERE user_id = ? AND type = 'expense' AND strftime('%Y-%m', date) = ?
            GROUP BY category_id
        """, session['user_id'], current_month)

        # Convert to dictionaries for easier lookup in template
        # AI used for converting to dictionaries
        budgets_dict = {b['category_id']: b['monthly_limit'] for b in budgets}
        spent_dict = {s['category_id']: s['total_spent'] for s in spent}

        return render_template('budgets.html',
                             current_month=current_month,
                             categories=categories,
                             budgets=budgets_dict,
                             spent=spent_dict)

    if request.method == "POST":
        current_month = date.today().strftime("%Y-%m")
        category_id = request.form.get("category_id")
        monthly_limit = request.form.get("monthly_limit")

        if not category_id or not monthly_limit:
            return apology("Please provide all fields", 400)

        # Check if budget already exists
        existing_budget = db.execute("""
            SELECT * FROM budgets
            WHERE user_id = ? AND category_id = ? AND month = ?
        """, session['user_id'], category_id, current_month)

        if len(existing_budget) == 0:
            # Insert new budget
            db.execute("""
                INSERT INTO budgets (user_id, category_id, monthly_limit, month)
                VALUES (?, ?, ?, ?)
            """, session['user_id'], category_id, monthly_limit, current_month)
        else:
            # Update existing budget
            db.execute("""
                UPDATE budgets
                SET monthly_limit = ?
                WHERE user_id = ? AND category_id = ? AND month = ?
            """, monthly_limit, session['user_id'], category_id, current_month)

        return redirect('/budgets')

# ====================
# Settings
# ====================
@app.route('/settings', methods=["GET"])
@login_required
def settings():
    user_id = session["user_id"]

    # Get all user accounts
    accounts = db.execute("""
        SELECT id, name, type, balance
        FROM accounts
        WHERE user_id = ?
        ORDER BY created_at ASC
    """, user_id)

    # Get current account
    current_account_id = session.get("account_id")
    current_account = db.execute("""
        SELECT id, name, type
        FROM accounts
        WHERE id = ?
    """, current_account_id)

    # Get user currency
    user = db.execute("SELECT currency FROM users WHERE id = ?", user_id)
    user_currency = user[0]["currency"] if user else "USD"

    # Get user's custom categories
    user_categories = db.execute("""
        SELECT id, name, type
        FROM categories
        WHERE user_id = ? AND is_preset = 0
        ORDER BY type, name
    """, user_id)

    return render_template('settings.html',
                         accounts=accounts,
                         current_account_id=current_account_id,
                         current_account=current_account[0] if current_account else None,
                         user_currency=user_currency,
                         user_categories=user_categories)

# ====================
# Switch account
# ====================
@app.route('/switch_account', methods=["POST"])
@login_required
def switch_account():
    new_account_id = request.form.get('account_id')

    if not new_account_id:
        flash("Please select an account", "error")
        return redirect("/settings")

    # Verify the account belongs to the user
    account = db.execute("""
        SELECT id, name FROM accounts
        WHERE id = ? AND user_id = ?
    """, new_account_id, session["user_id"])

    if not account:
        flash("Invalid account", "error")
        return redirect("/settings")

    # Update session with new account
    session["account_id"] = int(new_account_id)

    # Flash success message
    flash(f"Switched to {account[0]['name']} successfully!", "success")

    return redirect("/")

# ====================
# Create account
# ====================
@app.route('/create_account', methods=["POST"])
@login_required
def create_account():
    account_name = request.form.get('account_name')
    account_type = request.form.get('account_type')
    initial_balance = request.form.get('initial_balance')

    if not account_name or not account_type:
        flash("Account name and type are required", "error")
        return redirect("/settings")

    # Validate account type
    valid_types = ['current', 'savings', 'safe', 'business', 'investment']
    if account_type not in valid_types:
        flash("Invalid account type", "error")
        return redirect("/settings")

    try:
        initial_balance = float(initial_balance) if initial_balance else 0

        db.execute("""
            INSERT INTO accounts (user_id, name, type, balance)
            VALUES (?, ?, ?, ?)
        """, session["user_id"], account_name, account_type, initial_balance)

        flash(f"Account '{account_name}' created successfully!", "success")
    except Exception as e:
        flash("Failed to create account", "error")

    return redirect("/settings")

# ====================
# Rename account
# ====================
@app.route('/rename_account', methods=["POST"])
@login_required
def rename_account():
    account_id = request.form.get('account_id')
    new_name = request.form.get('new_account_name')

    if not account_id or not new_name:
        flash("Account ID and new name are required", "error")
        return redirect("/settings")

    # Verify account belongs to user
    account = db.execute("""
        SELECT id FROM accounts
        WHERE id = ? AND user_id = ?
    """, account_id, session["user_id"])

    if not account:
        flash("Account not found", "error")
        return redirect("/settings")

    try:
        db.execute("UPDATE accounts SET name = ? WHERE id = ?", new_name, account_id)
        flash(f"Account renamed to '{new_name}' successfully!", "success")
    except Exception as e:
        flash("Failed to rename account", "error")

    return redirect("/settings")

# ====================
# Delete account
# ====================
@app.route('/delete_account', methods=["POST"])
@login_required
def delete_account():
    account_id = request.form.get('account_id')

    if not account_id:
        flash("Account ID is required", "error")
        return redirect("/settings")

    # Verify that account belongs to user
    account = db.execute("""
        SELECT id FROM accounts
        WHERE id = ? AND user_id = ?
    """, account_id, session["user_id"])

    if not account:
        flash("Account not found", "error")
        return redirect("/settings")

    # Check if it's the current account
    if int(account_id) == session.get("account_id"):
        flash("Cannot delete the currently active account", "error")
        return redirect("/settings")

    # Check if user has more than one account
    accounts = db.execute("SELECT COUNT(*) as count FROM accounts WHERE user_id = ?", session["user_id"])
    if accounts[0]["count"] <= 1:
        flash("Cannot delete your only account", "error")
        return redirect("/settings")

    try:
        # Delete all transactions for this account
        db.execute("DELETE FROM transactions WHERE account_id = ?", account_id)

        # Delete the account
        db.execute("DELETE FROM accounts WHERE id = ?", account_id)

        flash("Account deleted successfully!", "success")
    except Exception as e:
        flash("Failed to delete account", "error")

    return redirect("/settings")

# ====================
# Change password
# ====================
@app.route('/change_password', methods=["POST"])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')

    if not current_password or not new_password or not confirm_password:
        flash("All fields are required", "error")
        return redirect("/settings")

    if new_password != confirm_password:
        flash("New passwords don't match", "error")
        return redirect("/settings")

    # Get current user hash
    curr_hash = db.execute("SELECT hash FROM users WHERE id = ?", session["user_id"])

    if not curr_hash or not check_password_hash(curr_hash[0]["hash"], current_password):
        flash("Current password is incorrect", "error")
        return redirect("/settings")

    try:
        new_hash = generate_password_hash(new_password)
        db.execute("UPDATE users SET hash = ? WHERE id = ?", new_hash, session["user_id"])
        flash("Password changed successfully!", "success")
    except Exception as e:
        flash("Failed to change password", "error")

    return redirect("/settings")

# ====================
# Change currency
# ====================
@app.route('/change_currency', methods=["POST"])
@login_required
def change_currency():
    new_currency = request.form.get('currency')

    if not new_currency:
        flash("Currency is required", "error")
        return redirect("/settings")

    valid_currencies = ['USD', 'EUR', 'GBP', 'INR', 'JPY']
    if new_currency not in valid_currencies:
        flash("Invalid currency", "error")
        return redirect("/settings")

    try:
        db.execute("UPDATE users SET currency = ? WHERE id = ?", new_currency, session["user_id"])
        flash(f"Currency changed to {new_currency} successfully!", "success")
    except Exception as e:
        flash("Failed to change currency", "error")

    return redirect("/settings")

# ====================
# Create category
# ====================
@app.route('/create_category', methods=["POST"])
@login_required
def create_category():
    category_name = request.form.get('category_name')
    category_type = request.form.get('category_type')

    if not category_name or not category_type:
        flash("Category name and type are required", "error")
        return redirect("/settings")

    if category_type not in ['income', 'expense']:
        flash("Invalid category type", "error")
        return redirect("/settings")

    try:
        db.execute("""
            INSERT INTO categories (user_id, name, type, is_preset)
            VALUES (?, ?, ?, 0)
        """, session["user_id"], category_name, category_type)

        flash(f"Category '{category_name}' created successfully!", "success")
    except Exception as e:
        flash("Failed to create category", "error")

    return redirect("/settings")

# ====================
# Delete category
# ====================
@app.route('/delete_category', methods=["POST"])
@login_required
def delete_category():
    category_id = request.form.get('category_id')

    if not category_id:
        flash("Category ID is required", "error")
        return redirect("/settings")

    # Verify category belongs to user and is not preset
    category = db.execute("""
        SELECT id FROM categories
        WHERE id = ? AND user_id = ? AND is_preset = 0
    """, category_id, session["user_id"])

    if not category:
        flash("Category not found or cannot be deleted", "error")
        return redirect("/settings")

    try:
        # Set category_id to NULL for transactions using this category
        db.execute("UPDATE transactions SET category_id = NULL WHERE category_id = ?", category_id)

        # Delete the category
        db.execute("DELETE FROM categories WHERE id = ?", category_id)

        flash("Category deleted successfully!", "success")
    except Exception as e:
        flash("Failed to delete category", "error")

    return redirect("/settings")

# ====================
# ANALYTICS ROUTE
# ====================

@app.route('/analytics')
@login_required
def analytics():
    from datetime import datetime, timedelta
    from dateutil.relativedelta import relativedelta

    user_id = session["user_id"]

    # Get last 12 months
    today = date.today()
    twelve_months_ago = today - relativedelta(months=12)

    # 1. Income vs Expense by Month (last 12 months)
    monthly_data = db.execute("""
        SELECT
            strftime('%Y-%m', date) as month,
            SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) as income,
            SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) as expense
        FROM transactions
        WHERE user_id = ? AND date >= ?
        GROUP BY month
        ORDER BY month ASC
    """, user_id, twelve_months_ago.strftime("%Y-%m-%d"))

    # 2. Budget vs Actual Spending (current month)
    current_month = today.strftime("%Y-%m")
    budget_data = db.execute("""
        SELECT
            c.name as category,
            b.monthly_limit as budget,
            COALESCE(SUM(t.amount), 0) as actual
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t ON t.category_id = c.id
            AND t.user_id = ?
            AND strftime('%Y-%m', t.date) = ?
            AND t.type = 'expense'
        WHERE b.user_id = ? AND b.month = ?
        GROUP BY c.name, b.monthly_limit
        ORDER BY c.name
    """, user_id, current_month, user_id, current_month)

    # 3. Account Balance Over Time (simulate with current balances)
    # Note: For real timeline, you'd need to track balance history
    account_balances = db.execute("""
        SELECT name, balance, created_at
        FROM accounts
        WHERE user_id = ?
        ORDER BY created_at
    """, user_id)

    # 4. Income Sources Breakdown (last 12 months)
    income_sources = db.execute("""
        SELECT
            c.name as category,
            SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
            AND t.type = 'income'
            AND t.date >= ?
        GROUP BY c.name
        ORDER BY total DESC
    """, user_id, twelve_months_ago.strftime("%Y-%m-%d"))

    # 5. Expense Categories Breakdown (for donut chart)
    expense_breakdown = db.execute("""
        SELECT
            c.name as category,
            SUM(t.amount) as total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
            AND t.type = 'expense'
            AND t.date >= ?
        GROUP BY c.name
        ORDER BY total DESC
    """, user_id, twelve_months_ago.strftime("%Y-%m-%d"))

    return render_template('analytics.html',
                         monthly_data=monthly_data,
                         budget_data=budget_data,
                         account_balances=account_balances,
                         income_sources=income_sources,
                         expense_breakdown=expense_breakdown)
