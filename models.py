from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import date

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    hash = Column(String, nullable=False)
    currency = Column(String, nullable=False, default='USD')
    
    # Relationships
    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="user", cascade="all, delete-orphan")
    transfers = relationship("Transfer", back_populates="user", cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    balance = Column(Float, nullable=False, default=0)
    created_at = Column(Date, default=date.today)
    
    __table_args__ = (
        CheckConstraint("type IN ('current', 'savings', 'safe', 'business', 'investment')", name='check_account_type'),
        Index('idx_accounts_user', 'user_id'),
    )
    
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    is_preset = Column(Integer, default=0)
    
    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense')", name='check_category_type'),
        Index('idx_categories_user', 'user_id'),
    )
    
    user = relationship("User", back_populates="categories")
    transactions = relationship("Transaction", back_populates="category")
    budgets = relationship("Budget", back_populates="category")

class Transaction(Base):
    __tablename__ = 'transactions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    account_id = Column(Integer, ForeignKey('accounts.id'), nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    type = Column(String, nullable=False)
    person_name = Column(String, nullable=True)
    direction = Column(String, nullable=True)
    
    __table_args__ = (
        CheckConstraint("type IN ('income', 'expense', 'personal')", name='check_transaction_type'),
        CheckConstraint("direction IS NULL OR direction IN ('lent', 'borrowed')", name='check_direction'),
        Index('idx_transactions_user', 'user_id'),
        Index('idx_transactions_account', 'account_id'),
        Index('idx_transactions_date', 'date'),
    )
    
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

class Budget(Base):
    __tablename__ = 'budgets'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    monthly_limit = Column(Float, nullable=False)
    month = Column(String, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('user_id', 'category_id', 'month', name='unique_budget_per_month'),
        Index('idx_budgets_user', 'user_id'),
    )
    
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")

class Transfer(Base):
    __tablename__ = 'transfers'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    from_account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    to_account_id = Column(Integer, ForeignKey('accounts.id'), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(Date, nullable=False)
    description = Column(String, nullable=True)
    
    __table_args__ = (
        Index('idx_transfers_user', 'user_id'),
    )
    
    user = relationship("User", back_populates="transfers")
    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])

PRESET_CATEGORIES = [
    # Expense categories
    ('Groceries', 'expense'), ('Rent', 'expense'), ('Entertainment', 'expense'),
    ('Transportation', 'expense'), ('Utilities', 'expense'), ('Healthcare', 'expense'),
    ('Shopping', 'expense'), ('Dining Out', 'expense'), ('Education', 'expense'),
    ('Other', 'expense'),
    # Income categories
    ('Salary', 'income'), ('Freelance', 'income'), ('Investment', 'income'),
    ('Gift', 'income'), ('Other', 'income')
]