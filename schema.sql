-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    hash TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD'
);

-- Accounts table
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('current', 'savings', 'safe', 'business', 'investment')),
    balance REAL NOT NULL DEFAULT 0,
    created_at DATE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Categories table (preset + user-created)
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    is_preset INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Transactions table
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    account_id INTEGER,
    category_id INTEGER,
    amount REAL NOT NULL,
    description TEXT,
    date DATE NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('income', 'expense', 'personal')),
    person_name TEXT,
    direction TEXT CHECK(direction IN ('lent', 'borrowed')),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

-- Budgets table
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    monthly_limit REAL NOT NULL,
    month TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    UNIQUE(user_id, category_id, month)
);

-- Transfers table (money moved between accounts)
CREATE TABLE transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    from_account_id INTEGER NOT NULL,
    to_account_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    date DATE NOT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (from_account_id) REFERENCES accounts(id),
    FOREIGN KEY (to_account_id) REFERENCES accounts(id)
);

-- Indexes for faster queries
CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_accounts_user ON accounts(user_id);
CREATE INDEX idx_transactions_user ON transactions(user_id);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_categories_user ON categories(user_id);
CREATE INDEX idx_budgets_user ON budgets(user_id);
CREATE INDEX idx_transfers_user ON transfers(user_id);

-- Insert preset expense categories
INSERT INTO categories (user_id, name, type, is_preset) VALUES
(NULL, 'Groceries', 'expense', 1),
(NULL, 'Rent', 'expense', 1),
(NULL, 'Entertainment', 'expense', 1),
(NULL, 'Transportation', 'expense', 1),
(NULL, 'Utilities', 'expense', 1),
(NULL, 'Healthcare', 'expense', 1),
(NULL, 'Shopping', 'expense', 1),
(NULL, 'Dining Out', 'expense', 1),
(NULL, 'Education', 'expense', 1),
(NULL, 'Other', 'expense', 1);

-- Insert preset income categories
INSERT INTO categories (user_id, name, type, is_preset) VALUES
(NULL, 'Salary', 'income', 1),
(NULL, 'Freelance', 'income', 1),
(NULL, 'Investment', 'income', 1),
(NULL, 'Gift', 'income', 1),
(NULL, 'Other', 'income', 1);
