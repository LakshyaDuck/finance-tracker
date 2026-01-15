from flask import Flask, flash, redirect, render_template, request, session, g
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
from sqlalchemy import select, func
from database import init_db, get_db, close_db
from models import User, Account, Transaction, Category, Budget, Transfer
from helpers import apology, login_required, usd
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.jinja_env.filters["usd"] = usd

with app.app_context():
    init_db()

@app.before_request
def before_request():
    g.db = get_db()

@app.teardown_appcontext
def shutdown_session(exception=None):
    close_db()

'''
First page will give user two options
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

    user = g.db.query(User).filter_by(username=username).first()

    if not user:
        return apology("Invalid username", 403)

    if not check_password_hash(user.hash, password):
        return apology("Invalid password", 403)

    session["user_id"] = user.id

    # Get user's Main Account
    main_account = g.db.query(Account).filter_by(user_id=user.id, type="current").order_by(Account.created_at).first()
    # If no main account exists, create one
    if not main_account:
        main_account = Account(
            user_id=user.id,
            type="current",
            name="Main Account",
            balance=0
        )
        g.db.add(main_account)
        g.db.commit()
    

    session["account_id"] = main_account.id

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
        user = User(
            username=username,
            hash=pass_hash,
            currency=currency
        )

        g.db.add(user)
        g.db.flush()

        # CREATE DEFAULT CURRENT ACCOUNT
        main_account = Account(
            user_id=user.id,
            type="current",
            name="Main Account",
            balance=0
        )
        g.db.add(main_account)
        g.db.flush()
        session["user_id"] = user.id
        session["account_id"] = main_account.id
        g.db.commit()
        return redirect("/")
    except:
        g.db.rollback()
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
        main_account = g.db.query(Account).filter_by(user_id=user_id, type="current").order_by(Account.created_at).first()

        if not main_account:
            main_account = Account(
                user_id=user_id,
                name="Main Account",
                type="current",
                balance=0
            )
            g.db.add(main_account)
            g.db.commit()

        session["account_id"] = main_account.id

    account_id = session["account_id"]
    current_month = date.today().strftime("%Y-%m")

    # Get current account details
    account = g.db.query(Account).filter_by(id=account_id, user_id=user_id).first()

    if not account:
        return apology("Account not found", 404)

    account_balance = account.balance
    account_name = account.name
    account_type = account.type
    # Get this month's income for THIS account only
    monthly_income = g.db.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == user_id,
        Transaction.account_id == account_id,
        Transaction.type == 'income',
        func.strftime('%Y-%m', Transaction.date) == current_month
    ).scalar()

    # Get this month's expenses for THIS account only
    monthly_expense = g.db.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == user_id,
        Transaction.account_id == account_id,
        Transaction.type == 'expense',
        func.strftime('%Y-%m', Transaction.date) == current_month
    ).scalar()
    # Calculate monthly net
    monthly_net = monthly_income - monthly_expense

    # Get budget alerts (spending across ALL accounts)
    budget_alerts = g.db.query(
        Category.name.label('category_name'),
        Budget.monthly_limit.label('budget_limit'),
        func.coalesce(func.sum(Transaction.amount), 0).label('spent'),
        (func.coalesce(func.sum(Transaction.amount), 0) / Budget.monthly_limit * 100).label('percent')
    )\
    .select_from(Budget)\
    .join(Category, Budget.category_id == Category.id)\
    .outerjoin(
        Transaction,
        (Transaction.category_id == Category.id) &
        (Transaction.user_id == user_id) &
        (func.strftime('%Y-%m', Transaction.date) == current_month) &
        (Transaction.type == 'expense')
    )\
    .filter(Budget.user_id == user_id, Budget.month == current_month)\
    .group_by(Budget.id, Category.name, Budget.monthly_limit)\
    .having((func.coalesce(func.sum(Transaction.amount), 0) / Budget.monthly_limit * 100) >= 80)\
    .order_by((func.coalesce(func.sum(Transaction.amount), 0) / Budget.monthly_limit * 100).desc())\
    .limit(5)\
    .all()

    # Get recent transactions for THIS account only
    recent_transactions = g.db.query(
        Transaction.id.label("id"),
        Transaction.amount.label("amount"),
        Transaction.date.label("date"),
        Transaction.type.label("type"),
        Transaction.person_name.label("person_name"),
        Transaction.direction.label("direction"),
        Category.name.label("name")
    )\
    .select_from(Transaction)\
    .join(Category, Transaction.category_id == Category.id)\
    .outer_join(
        Transaction,
        (Transaction.category_id == Category.id) &
        (Transaction.user_id == user_id) &
        (func.strftime('%Y-%m', Transaction.date) == current_month)
    )\
    .filter(Budget.user_id == user_id)\
    .order_by(Transaction.date.desc(), Transaction.id.desc())\
    .limit(8)\
    .all()

    return render_template('home.html',
                         account_balance=account_balance,
                         account_name=account_name,
                         account_type=account_type,
                         monthly_income=monthly_income,
                         monthly_expenses=monthly_expense,
                         monthly_net=monthly_net,
                         budget_alerts=budget_alerts,
                         recent_transactions=recent_transactions)




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
    user_id = session["user_id"]
    transactions = g.db.query(
        Transaction.id.label("id"),
        Transaction.amount.label("amount"),
        Transaction.description.label("description"),
        Transaction.date.label("date"),
        Transaction.type.label("type"),
        Transaction.person_name.label("person_name"),
        Transaction.direction.label("direction"),
        Category.name.label("name")
        )\
        .select_from(Budget)\
        .join(Category, Transaction.category_id == Category.id)\
        .outerjoin(
            Transaction,
            (Transaction.category_id == Category.id) &
            (Transaction.user_id == user_id)
        )\
        .filter(Transaction.user_id == user_id)\
        .order_by(Transaction.date.desc())\
        .all()

    return render_template('transactions.html', transactions=transactions)


# ====================
# Add transaction
# ====================
@app.route('/add_transaction', methods=["GET", "POST"])
@login_required
def add_transaction():
    if request.method == 'GET':
        # Get user's accounts
        accounts = g.db.query(Account).filter_by(user_id=session["user_id"]).all()

        # Get categories for dropdown
        expense_categories = g.db.query(Category).filter(
            (Category.user_id == session["user_id"]) | (Category.user_id == None),
            Category.type == 'expense'
        ).all()
        
        income_categories = g.db.query(Category).filter(
            (Category.user_id == session["user_id"]) | (Category.user_id == None),
            Category.type == 'income'
        ).all()

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
            from_account = g.db.query(Account).filter_by(
                id=from_account_id,
                user_id=session["user_id"]
            ).first()
            
            to_account = g.db.query(Account).filter_by(
                id=to_account_id,
                user_id=session["user_id"]
            ).first()

            if not from_account or not to_account:
                return apology("Invalid accounts", 400)

            # Check sufficient balance
            if from_account.balance < amount:
                return apology("Insufficient balance in source account", 400)

            try:
                # 1. Create transfer record in transfers table
                new_transfer = Transfer(
                    user_id=session["user_id"],
                    from_account_id=from_account_id,
                    to_account_id=to_account_id,
                    amount=amount,
                    date=trans_date,
                    description=description
                )
                g.db.add(new_transfer)

                # 2. Update account balances
                from_account.balance -= amount
                to_account.balance += amount

                # 3. Create two transaction records for display in transaction history
                # Outgoing transaction (from source account)
                outgoing_transaction = Transaction(
                    user_id=session["user_id"],
                    account_id=from_account_id,
                    category_id=None,
                    amount=amount,
                    description=f"Transfer to {to_account.name}" + (f" - {description}" if description else ""),
                    date=trans_date,
                    type='expense',
                    person_name=to_account.name,
                    direction=None
                )
                g.db.add(outgoing_transaction)

                # Incoming transaction (to destination account)
                incoming_transaction = Transaction(
                    user_id=session["user_id"],
                    account_id=to_account_id,
                    category_id=None,
                    amount=amount,
                    description=f"Transfer from {from_account.name}" + (f" - {description}" if description else ""),
                    date=trans_date,
                    type='income',
                    person_name=from_account.name,
                    direction=None
                )
                g.db.add(incoming_transaction)

                g.db.commit()
                flash(f"Transferred {amount} from {from_account.name} to {to_account.name}", "success")
                return redirect("/transactions")

            except Exception as e:
                g.db.rollback()
                print(f"Transfer error: {e}")
                return apology("Transfer failed", 400)

        # Handle other transaction types (income, expense, personal)
        account_id = request.form.get('account_id')

        if not account_id:
            return apology("Please select an account", 400)

        # Validate account belongs to user
        account = g.db.query(Account).filter_by(
            id=account_id,
            user_id=session["user_id"]
        ).first()
        
        if not account:
            return apology("Invalid account", 400)

        # Handle personal transactions
        if trans_type == "personal":
            person_name = request.form.get('person_name')
            direction = request.form.get('direction')

            if not person_name or not direction:
                return apology("Please enter person name and direction", 400)

            try:
                new_transaction = Transaction(
                    user_id=session['user_id'],
                    account_id=account_id,
                    category_id=None,
                    amount=amount,
                    description=description,
                    date=trans_date,
                    type=trans_type,
                    person_name=person_name,
                    direction=direction
                )
                g.db.add(new_transaction)

                if direction == "lent":
                    account.balance -= amount
                else:  # borrowed
                    account.balance += amount

                g.db.commit()
                return redirect("/transactions")
            except Exception as e:
                g.db.rollback()
                print(f"Error: {e}")
                return apology("Something went wrong", 400)

        # Handle income/expense transactions
        else:
            category_name = request.form.get('category')
            if not category_name:
                return apology("Please select a category", 400)

            category = g.db.query(Category).filter_by(name=category_name).first()
            if not category:
                return apology("Invalid category", 400)

            category_id = category.id

            try:
                new_transaction = Transaction(
                    user_id=session['user_id'],
                    account_id=account_id,
                    category_id=category_id,
                    amount=amount,
                    description=description,
                    date=trans_date,
                    type=trans_type,
                    person_name=None,
                    direction=None
                )
                g.db.add(new_transaction)

                if trans_type == "income":
                    account.balance += amount
                elif trans_type == "expense":
                    account.balance -= amount

                g.db.commit()
                return redirect("/transactions")
            except Exception as e:
                g.db.rollback()
                print(f"Error: {e}")
                return apology("Something went wrong", 400)

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
    transaction = g.db.query(Transaction).filter(Transaction.id == transaction_id).first()

    if not transaction or transaction.user_id != session["user_id"]:
        return apology("Unauthorized", 403)

    # Extract transaction details
    account_id = transaction.account_id
    amount = transaction.amount
    trans_type = transaction.type
    direction = transaction.direction

    # Update Account balance according to transaction type
    try:
        if trans_type == "income":
            # Subtrat the money if income
            g.db.query(Account)\
                .filter_by(account_id=account_id)\
                .update({"balance": Account.balance - amount})
        elif trans_type == "expense":
            # Add the money if expense
            g.db.query(Account)\
                .filter_by(account_id=account_id)\
                .update({"balance": Account.balance + amount})
        elif trans_type == "personal":
            if direction == "lent":
                # Add if lent
                g.db.query(Account)\
                    .filter_by(account_id=account_id)\
                    .update({"balance": Account.balance + amount})
            elif direction == "borrowed":
                # Subtract if borrowed
                g.db.query(Account)\
                    .filter_by(account_id=account_id)\
                    .update({"balance": Account.balance - amount})
                
        # Delete the transaction
        g.db.query(Transaction)\
            .filter_by(id=transaction_id)\
            .delete()
        g.db.commit()
    except:
        g.db.rollback()
        return apology("Could not delete transaction", 400)

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
        categories = g.db.query(Category.name, Category.id).filter(
            (Category.user_id == session['user_id']) | (Category.user_id == None),
            Category.type == 'expense'
        ).all()

        # Get budgets for current month
        budgets = g.db.query(Budget).filter_by(
            user_id=session['user_id'],
            month=current_month
        ).all()

        # Calculate spent amount for each category this month
        spent = g.db.query(
            Transaction.category_id,
            func.sum(Transaction.amount).label('total_spent')
        ).filter(
            Transaction.user_id == session['user_id'],
            Transaction.type == 'expense',
            func.strftime('%Y-%m', Transaction.date) == current_month
        ).group_by(Transaction.category_id).all()

        # Convert to dictionaries for easier lookup in template
        budgets_dict = {b.category_id: b.monthly_limit for b in budgets}
        spent_dict = {s.category_id: s.total_spent for s in spent}

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
    monthly_income = g.db.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.user_id == session["user_id"],
        Transaction.account_id == session["account_id"],
        Transaction.type == 'income',
        func.strftime('%Y-%m', Transaction.date) == current_month
    ).scalar()
        # Check if budget already exists
    existing_budget = g.db.query(Budget).filter_by(
            user_id=session['user_id'],
            category_id=category_id,
            month=current_month
        ).first()

    if not existing_budget:
        # Insert new budget
        new_budget = Budget(
                user_id=session['user_id'],
                category_id=category_id,
                monthly_limit=monthly_limit,
                month=current_month
            )
        g.db.add(new_budget)
    else:
        # Update existing budget
        existing_budget.monthly_limit = monthly_limit

    g.db.commit()
    return redirect('/budgets')

# ====================
# Settings
# ====================
@app.route('/settings', methods=["GET"])
@login_required
def settings():
    user_id = session["user_id"]

    # Get all user accounts
    accounts = g.db.query(Account)\
        .filter_by(user_id=session["user_id"])\
        .order_by(Account.created_at)\
        .all()

    # Get current account
    current_account_id = session.get("account_id")
    current_account = g.db.query(Account)\
        .filter_by(id=current_account_id)\
        .first()

    # Get user currency
    user = g.db.query(User)\
        .filter_by(id=user_id)\
        .first()
    user_currency = user.currency if user else "USD"

    # Get user's custom categories
    user_categories = g.db.query(Category)\
        .filter_by(
            user_id=current_account_id,
            is_preset=0
        )\
        .order_by(Category.type, Category.name)\
        .all()

    return render_template('settings.html',
                         accounts=accounts,
                         current_account_id=current_account_id,
                         current_account=current_account if current_account else None,
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
    account = g.db.query(Account)\
        .filter_by(
            id=new_account_id,
            user_id=session["user_id"]
        )\
        .first()

    if not account:
        flash("Invalid account", "error")
        return redirect("/settindgs")

    # Update session with new account
    session["account_id"] = int(new_account_id)

    # Flash success message
    flash(f"Switched to {account.name} successfully!", "success")

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
        account = Account(
            user_id=session["user_id"],
            name=account_name,
            type=account_type,
            balance=initial_balance
        )

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
    account = g.db.query(Account)\
        .filter_by(
            id=account_id,
            user_id=session["user_id"]
        )\
        .first()

    if not account:
        flash("Account not found", "error")
        return redirect("/settings")

    try:
        g.db.query(Account)\
            .filter_by(id=account_id)\
            .update({"name": new_name})
        g.db.commit()
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
    account = g.db.query(Account)\
        .filter_by(
            id=account_id,
            user_id=session["user_id"]
        )\
        .first()

    if not account:
        flash("Account not found", "error")
        return redirect("/settings")

    # Check if it's the current account
    if int(account_id) == session.get("account_id"):
        flash("Cannot delete the currently active account", "error")
        return redirect("/settings")

    # Check if user has more than one account
    account = g.db.query(func.coalesce(func.count(Account.id)).label("count")).filter_by(user_id=session["user_id"])
    if account.count <= 1:
        flash("Cannot delete your only account", "error")
        return redirect("/settings")

    try:
        # Delete all transactions for this account
        g.db.query(Transaction)\
            .filter_by(account_id=account_id)\
            .delete()

        # Delete the account
        g.db.query(Account)\
            .filter_by(id=account_id)\
            .delete()
        g.db.commit()
        flash("Account deleted successfully!", "success")
    except Exception as e:
        g.db.rollback()
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
    curr_hash = g.db.query(User).filter_by(id=session["user_id"]).first().hash

    if not curr_hash or not check_password_hash(curr_hash, current_password):
        flash("Current password is incorrect", "error")
        return redirect("/settings")

    try:
        new_hash = generate_password_hash(new_password)
        g.db.query(User)\
            .filter_by(id=session["user_id"])\
            .update({"hash": new_hash})
        g.db.commit()
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
        g.db.query(User)\
            .filter_by(id=session["user_id"])\
            .update({"currency": new_currency})
        g.db.commit()
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
        new_category = Category(
            user_id=session["user_id"],
            name=category_name,
            type=category_type,
            is_preset=0
        )
        g.db.add(new_category)
        g.db.commit()

        flash(f"Category '{category_name}' created successfully!", "success")
    except Exception as e:
        g.db.rollback()
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
    category_id = g.db.query(Category)\
        .filter_by(
            id=category_id,
            user_id=session["user_id"]
        ).first().id

    if not category_id:
        flash("Category not found or cannot be deleted", "error")
        return redirect("/settings")

    try:
        # Set category_id to NULL for transactions using this category
        g.db.query(Transaction)\
            .filter_by(category_id=category_id)\
            .update({"category_id": None})

        # Delete the category
        g.db.query(Category)\
            .filter_by(id=category_id)\
            .delete()
        g.db.commit()
        flash("Category deleted successfully!", "success")
    except Exception as e:
        g.db.rollback()
        flash("Failed to delete category", "error")

    return redirect("/settings")

# ====================
# ANALYTICS ROUTE
# ====================
@app.route('/analytics')
@login_required
def analytics():
    from dateutil.relativedelta import relativedelta

    user_id = session["user_id"]

    # Get last 12 months
    today = date.today()
    twelve_months_ago = today - relativedelta(months=12)

    # 1. Income vs Expense by Month (last 12 months)
    monthly_data = g.db.query(
        func.strftime('%Y-%m', Transaction.date).label('month'),
        func.sum(func.case((Transaction.type == 'income', Transaction.amount), else_=0)).label('income'),
        func.sum(func.case((Transaction.type == 'expense', Transaction.amount), else_=0)).label('expense')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.date >= twelve_months_ago
    ).group_by(func.strftime('%Y-%m', Transaction.date))\
    .order_by(func.strftime('%Y-%m', Transaction.date)).all()

    # 2. Budget vs Actual Spending (current month)
    current_month = today.strftime("%Y-%m")
    budget_data = g.db.query(
        Category.name.label('category'),
        Budget.monthly_limit.label('budget'),
        func.coalesce(func.sum(Transaction.amount), 0).label('actual')
    ).select_from(Budget)\
    .join(Category, Budget.category_id == Category.id)\
    .outerjoin(
        Transaction,
        (Transaction.category_id == Category.id) &
        (Transaction.user_id == user_id) &
        (func.strftime('%Y-%m', Transaction.date) == current_month) &
        (Transaction.type == 'expense')
    ).filter(Budget.user_id == user_id, Budget.month == current_month)\
    .group_by(Category.name, Budget.monthly_limit)\
    .order_by(Category.name).all()

    # 3. Account Balance Over Time
    account_balances = g.db.query(
        Account.name,
        Account.balance,
        Account.created_at
    ).filter_by(user_id=user_id)\
    .order_by(Account.created_at).all()

    # 4. Income Sources Breakdown (last 12 months)
    income_sources = g.db.query(
        Category.name.label('category'),
        func.sum(Transaction.amount).label('total')
    ).select_from(Transaction)\
    .join(Category, Transaction.category_id == Category.id)\
    .filter(
        Transaction.user_id == user_id,
        Transaction.type == 'income',
        Transaction.date >= twelve_months_ago
    ).group_by(Category.name)\
    .order_by(func.sum(Transaction.amount).desc()).all()

    # 5. Expense Categories Breakdown
    expense_breakdown = g.db.query(
        Category.name.label('category'),
        func.sum(Transaction.amount).label('total')
    ).select_from(Transaction)\
    .join(Category, Transaction.category_id == Category.id)\
    .filter(
        Transaction.user_id == user_id,
        Transaction.type == 'expense',
        Transaction.date >= twelve_months_ago
    ).group_by(Category.name)\
    .order_by(func.sum(Transaction.amount).desc()).all()

    return render_template('analytics.html',
                         monthly_data=monthly_data,
                         budget_data=budget_data,
                         account_balances=account_balances,
                         income_sources=income_sources,
                         expense_breakdown=expense_breakdown)