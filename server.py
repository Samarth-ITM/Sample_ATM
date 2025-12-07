import socket
import threading
import configparser
import time
from db_handler import (
    initialize_database,
    register_user,
    authenticate_user,
    withdraw,
    deposit,
    log_transaction
)
from logger_utils import log_info, log_error
from server_monitor import get_monitor

# ---------------- CONFIGURATION ----------------
config = configparser.ConfigParser()
config.read("config.ini")

HOST = config.get("server", "host", fallback="127.0.0.1")
PORT = int(config.get("server", "port", fallback="65432"))
WORKER_THREADS = int(config.get("server", "worker_threads", fallback="5"))

# -----------------------------
# Handle Individual Client
# -----------------------------
def handle_client(conn, addr):
    log_info(f"New connection from {addr}")
    session_start = time.time()
    mobile = None
    
    # Track connection in server monitor
    monitor = get_monitor()
    monitor.increment_connection()

    try:
        conn.sendall(b"Welcome to ATM.\nEnter your mobile number to begin (or 'exit' to quit): ")
        mobile = conn.recv(1024).decode().strip()
        
        if mobile.lower() == 'exit':
            conn.sendall(b"Thank you for visiting. Goodbye!\n")
            return
            
        if not mobile.isdigit() or len(mobile) < 5:
            conn.sendall(b" Invalid mobile number. Connection closed.\n")
            conn.close()
            return

        # Auto-register user if not found
        reg_result = register_user(mobile)
        conn.sendall(f"{reg_result['message']}\n".encode())
        
        # Ensure the client receives the message before continuing
        time.sleep(0.1)
        
        # Log login attempt
        log_transaction(mobile, "login", None, None, session_start)

        # Authenticate
        authenticated = False
        attempts = 0
        while not authenticated and attempts < 5:
            conn.sendall(b"Enter your 5-digit PIN (or 'exit' to quit): ")
            pin = conn.recv(1024).decode().strip()
            
            if pin.lower() == 'exit':
                conn.sendall(b"Thank you for visiting. Goodbye!\n")
                log_transaction(mobile, "exit", None, None, session_start)
                return
                
            auth_result = authenticate_user(mobile, pin)
            conn.sendall(f"{auth_result['message']}\n".encode())
            
            # Ensure the client receives the message before continuing
            time.sleep(0.1)

            if auth_result["status"] == "ok":
                authenticated = True
            elif "blacklisted" in auth_result["message"].lower():
                log_transaction(mobile, "blacklisted", None, None, session_start)
                conn.close()
                return
            else:
                attempts += 1
                if attempts >= 5:
                    conn.sendall(b"Too many failed attempts. Please try again later.\n")
                    log_transaction(mobile, "auth_failed", None, None, session_start)
                    return

        # Main transaction loop
        while True:
            menu = (
                "\nSelect an option:\n"
                "1. Withdraw\n"
                "2. Deposit\n"
                "3. Exit\n"
                "Enter choice (1, 2, or 3): "
            )
            conn.sendall(menu.encode())
            choice = conn.recv(1024).decode().strip()
            
            if choice.lower() == 'exit' or choice == '3':
                conn.sendall(b"Thank you for using ATM. Goodbye!\n")
                log_transaction(mobile, "exit", None, None, session_start)
                log_info(f"Connection closed for {mobile} ({addr})")
                break

            # Handle invalid menu choices with error handling
            if choice not in ['1', '2', '3']:
                conn.sendall(b"Invalid option. Please enter 1 for Withdraw, 2 for Deposit, or 3 to Exit.\n")
                continue

            if choice == "1":
                conn.sendall(b"Enter amount to withdraw (or 'exit' to cancel): ")
                amount_str = conn.recv(1024).decode().strip()
                
                if amount_str.lower() == 'exit':
                    conn.sendall(b"Transaction cancelled.\n")
                    continue
                    
                # Handle non-numeric input with 5 attempts
                attempts = 0
                while attempts < 5:
                    try:
                        amount = float(amount_str)
                        break
                    except ValueError:
                        attempts += 1
                        if attempts >= 5:
                            conn.sendall(b"Too many invalid inputs. Transaction cancelled.\n")
                            break
                        conn.sendall(b"Invalid amount. Please enter a number (or 'exit' to cancel): ")
                        amount_str = conn.recv(1024).decode().strip()
                        if amount_str.lower() == 'exit':
                            conn.sendall(b"Transaction cancelled.\n")
                            break
                
                if attempts >= 5 or amount_str.lower() == 'exit':
                    continue

                result = withdraw(mobile, amount)
                conn.sendall(f"{result['message']}\n".encode())
                
                # Ensure the client receives the message before continuing
                time.sleep(0.1)
                
                # Log transaction if successful
                if result["status"] == "ok":
                    log_transaction(mobile, "withdraw", amount, result.get("balance"), session_start, result.get("bank_balance"))

            elif choice == "2":
                conn.sendall(b"Enter amount to deposit (or 'exit' to cancel): ")
                amount_str = conn.recv(1024).decode().strip()
                
                if amount_str.lower() == 'exit':
                    conn.sendall(b"Transaction cancelled.\n")
                    continue
                
                # Handle non-numeric input with 5 attempts
                attempts = 0
                while attempts < 5:
                    try:
                        amount = float(amount_str)
                        break
                    except ValueError:
                        attempts += 1
                        if attempts >= 5:
                            conn.sendall(b"Too many invalid inputs. Transaction cancelled.\n")
                            break
                        conn.sendall(b"Invalid amount. Please enter a number (or 'exit' to cancel): ")
                        amount_str = conn.recv(1024).decode().strip()
                        if amount_str.lower() == 'exit':
                            conn.sendall(b"Transaction cancelled.\n")
                            break
                
                if attempts >= 5 or amount_str.lower() == 'exit':
                    continue

                result = deposit(mobile, amount)
                conn.sendall(f"{result['message']}\n".encode())
                
                # Ensure the client receives the message before continuing
                time.sleep(0.1)
                
                # Log transaction if successful
                if result["status"] == "ok":
                    log_transaction(mobile, "deposit", amount, result.get("balance"), session_start, result.get("bank_balance"))

            elif choice == "3":
                conn.sendall(b"Thank you for using ATM. Goodbye!\n")
                log_transaction(mobile, "logout", None, None, session_start)
                log_info(f"Connection closed for {mobile} ({addr})")
                break

    except Exception as e:
        log_error(f"Error with client {addr}: {e}")
        conn.sendall(b" Server error. Connection closing.\n")
    finally:
        # Decrement connection count in server monitor
        monitor.decrement_connection()
        conn.close()


# -----------------------------
# Main Server Function
# -----------------------------
def start_server():
    initialize_database()
    
    # Initialize and start server monitoring
    monitor_interval = int(config.get("server", "monitor_interval", fallback="60"))
    monitor = get_monitor(interval=monitor_interval)
    monitor.start()
    log_info(f"Server monitoring started with {monitor_interval}s interval")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        log_info(f"ATM Server running on {HOST}:{PORT}")

        while True:
            conn, addr = server_socket.accept()
            client_thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            client_thread.start()


if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        log_info("Server stopped manually.")
        # Stop the server monitor
        get_monitor().stop()
    except Exception as e:
        log_error(f"Server crashed: {e}")
        # Stop the server monitor
        get_monitor().stop()
