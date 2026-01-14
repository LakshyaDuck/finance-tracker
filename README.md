# Finance Tracker

A personal finance management web application built with Flask and SQLAlchemy. Track income, expenses, budgets, and analyze spending patterns across multiple accounts.

## Features

- **Multi-Account Management**: Create and switch between current, savings, safe, business, and investment accounts
- **Transaction Tracking**: Record income, expenses, personal loans (lent/borrowed), and account transfers
- **Budget Management**: Set monthly spending limits by category with real-time alerts
- **Analytics Dashboard**: Visualize spending patterns, income sources, and budget performance
- **Custom Categories**: Create personalized income and expense categories
- **Multi-Currency Support**: USD, EUR, GBP, INR, JPY

## Tech Stack

- **Backend**: Flask, SQLAlchemy
- **Database**: SQLite
- **Authentication**: Werkzeug password hashing
- **Sessions**: Flask-Session (server-side)

## Installation

1. **Clone repository**
```bash
git clone https://github.com/LakshyaDuck/finance-tracker.git
cd finance-tracker
```

2. **Create virtual environment**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
Create `.env` file:
```
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
DATABASE_URL=sqlite:///data/fortuna.db
```

Generate SECRET_KEY:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

5. **Initialize database**
```bash
python init_db.py
```

6. **Run application**
```bash
flask run
```

Access at `http://localhost:5000`

## Project Structure

```
finance-tracker/
├── app.py              # Main application routes
├── models.py           # SQLAlchemy database models
├── database.py         # Database initialization
├── helpers.py          # Authentication decorators
├── init_db.py          # Database setup script
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (not in git)
├── data/              # SQLite database storage
├── static/            # CSS, JS files
└── templates/         # HTML templates
```

## Database Schema

- **users**: User accounts and authentication
- **accounts**: Financial accounts (current, savings, etc.)
- **transactions**: Income, expense, personal loan records
- **categories**: Preset and custom transaction categories
- **budgets**: Monthly spending limits by category
- **transfers**: Inter-account money transfers

## Usage

1. **Register/Login**: Create account with username, password, preferred currency
2. **Add Transactions**: Record income, expenses, or personal loans
3. **Set Budgets**: Define monthly limits for expense categories
4. **Create Accounts**: Add multiple accounts to organize finances
5. **View Analytics**: Track spending trends and budget performance

## Development Notes

- Original CS50 project converted to use SQLAlchemy ORM
- No CS50 libraries or helper functions used
- All database queries use SQLAlchemy instead of raw SQL
- Server-side sessions for security

## Future Enhancements

- Export transactions to CSV
- Recurring transaction templates
- Email budget alerts
- Mobile-responsive design improvements

## Author

Lakshya - [GitHub](https://github.com/LakshyaDuck)
