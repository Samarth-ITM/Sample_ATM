import csv
import os
import time
import datetime
import mysql.connector
import configparser
import decimal

# -----------------------------
# Transaction Logging
# -----------------------------
CLIENT_TRANSACTION_FILE = "client.csv"
BANK_TRANSACTION_FILE = "bank.csv"

def log_transaction(mobile, action, amount, balance, start_time=None, bank_balance=None):
    """Log transaction details to CSV file"""
    # Create file with headers if it doesn't exist
    client_file_exists = os.path.isfile(CLIENT_TRANSACTION_FILE)
    bank_file_exists = os.path.isfile(BANK_TRANSACTION_FILE)
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elapsed_time = ""
    if start_time:
        elapsed_time = f"{time.time() - start_time:.2f}"
    
    # Log client transaction
    with open(CLIENT_TRANSACTION_FILE, 'a', newline='') as csvfile:
        fieldnames = ['Mobile_Number', 'Action', 'Amount', 'User_Balance', 'Bank_Balance', 'Timestamp', 'Session_Start', 'Elapsed_Time']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='\t')
        
        if not client_file_exists:
            writer.writeheader()
            
        writer.writerow({
            'Mobile_Number': mobile,
            'Action': action,
            'Amount': amount if amount else "",
            'User_Balance': balance if balance else "",
            'Bank_Balance': bank_balance if bank_balance else "",
            'Timestamp': current_time,
            'Session_Start': start_time if start_time else "",
            'Elapsed_Time': elapsed_time
        })
    
    # Log bank transaction if it affects bank balance
    if action in ["withdraw", "deposit"] and bank_balance is not None:
        with open(BANK_TRANSACTION_FILE, 'a', newline='') as csvfile:
            fieldnames = ['Mobile_Number', 'Action', 'Amount', 'Bank_Balance', 'Timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter='\t')
            
            if not bank_file_exists:
                writer.writeheader()
                
            writer.writerow({
                'Mobile_Number': mobile,
                'Action': action,
                'Amount': amount if amount else "",
                'Bank_Balance': bank_balance,
                'Timestamp': current_time
            })
    
    return True

# -----------------------------
# Database Connection
# -----------------------------
def get_db_connection():
    """Create a database connection using config.ini parameters."""
    config = configparser.ConfigParser()
    config.read("config.ini")

    host = config.get("mysql", "host", fallback="127.0.0.1")
    port = int(config.get("mysql", "port", fallback="3306"))
    user = config.get("mysql", "user", fallback="root")
    password = config.get("mysql", "password", fallback="")
    database = config.get("mysql", "database", fallback="bank_db")

    try:
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# -----------------------------
# Database Initialization
# -----------------------------
def initialize_database():
    """Initialize the database with required tables."""
    # Connect to MySQL server without database
    config = configparser.ConfigParser()
    config.read("config.ini")

    host = config.get("mysql", "host", fallback="127.0.0.1")
    port = int(config.get("mysql", "port", fallback="3306"))
    user = config.get("mysql", "user", fallback="root")
    password = config.get("mysql", "password", fallback="")
    database = config.get("mysql", "database", fallback="bank_db")

    try:
        # First connect without database to create it if needed
        connection = mysql.connector.connect(
            host=host,
            port=port,
            user=user,
            password=password
        )
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
        cursor.execute(f"USE {database}")
        
        # Drop existing users table to recreate with correct schema
        cursor.execute("DROP TABLE IF EXISTS users")
        
        # Create users table with required fields
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            mobile VARCHAR(20) UNIQUE NOT NULL,
            pin VARCHAR(5) NOT NULL,
            balance DECIMAL(10, 2) DEFAULT 0.00,
            failed_attempts INT DEFAULT 0,
            blacklisted BOOLEAN DEFAULT FALSE
        )
        """)
        
        # Create bank table for tracking total funds
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bank (
            id INT PRIMARY KEY DEFAULT 1,
            total_funds DECIMAL(15, 2) DEFAULT 10000.00
        )
        """)
        
        # Initialize bank funds if not already set
        cursor.execute("SELECT COUNT(*) FROM bank")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO bank (id, total_funds) VALUES (1, 10000.00)")
            
        connection.commit()
        cursor.close()
        connection.close()
        
        print("Database initialized successfully.")
        return True
    except mysql.connector.Error as err:
        print(f"Database initialization error: {err}")
        return False

# -----------------------------
# User Registration
# -----------------------------
def register_user(mobile):
    """Register a new user if not already registered."""
    connection = get_db_connection()
    if not connection:
        return {"status": "error", "message": "Database connection failed."}
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Check if user exists
        cursor.execute("SELECT * FROM users WHERE mobile = %s", (mobile,))
        user = cursor.fetchone()
        
        if user:
            return {"status": "ok", "message": "User already registered. Please continue."}
        
        # Generate PIN as first 5 digits of mobile number
        pin = mobile[:5] if len(mobile) >= 5 else mobile
        
        # Register new user
        cursor.execute(
            "INSERT INTO users (mobile, pin, balance, failed_attempts, blacklisted) VALUES (%s, %s, %s, %s, %s)",
            (mobile, pin, 1000.00, 0, False)
        )
        connection.commit()
        
        return {
            "status": "ok",
            "message": f"New user registered. Your PIN is {pin}. Initial balance: ₹1000.00.\nPress Enter to continue:"
        }
    except Exception as e:
        connection.rollback()
        return {"status": "error", "message": f"Registration error: {str(e)}"}
    finally:
        cursor.close()
        connection.close()

# -----------------------------
# User Authentication
# -----------------------------
def authenticate_user(mobile, pin):
    """Authenticate user with mobile and PIN."""
    connection = get_db_connection()
    if not connection:
        return {"status": "error", "message": "Database connection failed."}
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Check if user exists and is not blacklisted
        cursor.execute("SELECT * FROM users WHERE mobile = %s", (mobile,))
        user = cursor.fetchone()
        
        if not user:
            return {"status": "error", "message": "User not registered."}
        
        # Check if user is blacklisted
        if user["blacklisted"]:
            return {"status": "error", "message": "This number is blacklisted due to multiple failed attempts."}
        
        # Check PIN
        if user["pin"] != pin:
            # Increment failed attempts
            failed_attempts = user["failed_attempts"] + 1
            
            # Check if should be blacklisted (5 attempts)
            if failed_attempts >= 5:
                cursor.execute(
                    "UPDATE users SET failed_attempts = %s, blacklisted = %s WHERE mobile = %s",
                    (failed_attempts, True, mobile)
                )
                connection.commit()
                return {"status": "error", "message": "Wrong PIN. This number is now blacklisted due to multiple failed attempts."}
            else:
                cursor.execute(
                    "UPDATE users SET failed_attempts = %s WHERE mobile = %s",
                    (failed_attempts, mobile)
                )
                connection.commit()
                return {"status": "error", "message": f"Wrong PIN. {5 - failed_attempts} attempts remaining."}
        
        # Reset failed attempts on successful login
        cursor.execute(
            "UPDATE users SET failed_attempts = 0 WHERE mobile = %s",
            (mobile,)
        )
        connection.commit()
        
        return {
            "status": "ok",
            "message": "Authentication successful. \n Press Enter to continue:",
            "balance": user["balance"]
        }
    except Exception as e:
        return {"status": "error", "message": f"Authentication error: {str(e)}"}
    finally:
        cursor.close()
        connection.close()

# -----------------------------
# Get Balance
# -----------------------------
def get_balance(mobile):
    """Get user balance."""
    connection = get_db_connection()
    if not connection:
        return {"status": "error", "message": "Database connection failed."}
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT balance FROM users WHERE mobile = %s", (mobile,))
        user = cursor.fetchone()
        
        if not user:
            return {"status": "error", "message": "User not found."}
        
        return {"status": "ok", "balance": user["balance"]}
    except Exception as e:
        return {"status": "error", "message": f"Error retrieving balance: {str(e)}"}
    finally:
        cursor.close()
        connection.close()

# -----------------------------
# Get Bank Balance
# -----------------------------
def get_bank_balance():
    """Get total bank funds."""
    connection = get_db_connection()
    if not connection:
        return {"status": "error", "message": "Database connection failed."}
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT total_funds FROM bank WHERE id = 1")
        bank = cursor.fetchone()
        
        if not bank:
            return {"status": "error", "message": "Bank data not found."}
        
        return {"status": "ok", "bank_balance": bank["total_funds"]}
    except Exception as e:
        return {"status": "error", "message": f"Error retrieving bank balance: {str(e)}"}
    finally:
        cursor.close()
        connection.close()

# -----------------------------
# Withdraw
# -----------------------------
def withdraw(mobile, amount):
    """Withdraw money from user account."""
    # Validate amount
    try:
        amount = decimal.Decimal(str(amount))
    except:
        return {"status": "error", "message": "Invalid amount format."}
        
    if amount <= 0:
        return {"status": "error", "message": "Withdrawal amount must be positive."}
    
    if amount < 100:
        return {"status": "error", "message": "Minimum withdrawal amount is ₹100."}
        
    if amount > 5000:
        return {"status": "error", "message": "Maximum withdrawal limit is ₹5000 per transaction."}
    
    connection = get_db_connection()
    if not connection:
        return {"status": "error", "message": "Database connection failed."}
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Get user balance
        cursor.execute("SELECT balance FROM users WHERE mobile = %s", (mobile,))
        user = cursor.fetchone()
        
        if not user:
            return {"status": "error", "message": "User not found."}
        
        balance = decimal.Decimal(str(user["balance"]))
        
        # Check if sufficient balance
        if balance < amount:
            return {"status": "error", "message": "Insufficient balance."}
        
        # Get bank balance
        cursor.execute("SELECT total_funds FROM bank WHERE id = 1")
        bank = cursor.fetchone()
        
        if not bank:
            return {"status": "error", "message": "Bank data not found."}
        
        bank_balance = decimal.Decimal(str(bank["total_funds"]))
        
        # Check if bank has sufficient funds
        if bank_balance < amount:
            return {"status": "error", "message": "ATM out of cash. Please try a smaller amount."}
        
        # Update user balance
        new_balance = balance - amount
        cursor.execute(
            "UPDATE users SET balance = %s WHERE mobile = %s",
            (new_balance, mobile)
        )
        
        # Update bank balance
        new_bank_balance = bank_balance - amount
        cursor.execute(
            "UPDATE bank SET total_funds = %s WHERE id = 1",
            (new_bank_balance,)
        )
        
        connection.commit()
        
        return {
            "status": "ok",
            "message": f"Withdrawal successful. New balance: ₹{new_balance:.2f} \n Press Enter to continue",
            "balance": new_balance,
            "bank_balance": new_bank_balance
        }
    except Exception as e:
        connection.rollback()
        return {"status": "error", "message": f"Withdrawal error: {str(e)}"}
    finally:
        cursor.close()
        connection.close()

# -----------------------------
# Deposit
# -----------------------------
def deposit(mobile, amount):
    """Deposit money to user account."""
    # Validate amount
    try:
        amount = decimal.Decimal(str(amount))
    except:
        return {"status": "error", "message": "Invalid amount format."}
        
    if amount <= 0:
        return {"status": "error", "message": "Deposit amount must be positive."}
    
    connection = get_db_connection()
    if not connection:
        return {"status": "error", "message": "Database connection failed."}
    
    cursor = connection.cursor(dictionary=True)
    
    try:
        # Get user balance
        cursor.execute("SELECT balance FROM users WHERE mobile = %s", (mobile,))
        user = cursor.fetchone()
        
        if not user:
            return {"status": "error", "message": "User not found."}
        
        balance = decimal.Decimal(str(user["balance"]))
        
        # Get bank balance
        cursor.execute("SELECT total_funds FROM bank WHERE id = 1")
        bank = cursor.fetchone()
        
        if not bank:
            return {"status": "error", "message": "Bank data not found."}
        
        bank_balance = decimal.Decimal(str(bank["total_funds"]))
        
        # Update user balance
        new_balance = balance + amount
        cursor.execute(
            "UPDATE users SET balance = %s WHERE mobile = %s",
            (new_balance, mobile)
        )
        
        # Update bank balance
        new_bank_balance = bank_balance + amount
        cursor.execute(
            "UPDATE bank SET total_funds = %s WHERE id = 1",
            (new_bank_balance,)
        )
        
        connection.commit()
        
        return {
            "status": "ok",
            "message": f"Deposit successful. New balance: ₹{new_balance:.2f} \n Press Enter to continue",
            "balance": new_balance,
            "bank_balance": new_bank_balance
        }
    except Exception as e:
        connection.rollback()
        return {"status": "error", "message": f"Deposit error: {str(e)}"}
    finally:
        cursor.close()
        connection.close()

