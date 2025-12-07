import socket
import sys

# ---------------- CONFIG ----------------
SERVER_HOST = "127.0.0.1"   # Change if the server is remote
SERVER_PORT = 65432         # Must match server.py port
BUFFER_SIZE = 2048

# ---------------- CLIENT APP ----------------
def start_client():
    print(" Welcome to ATM Client")
    print(f"Connecting to server at {SERVER_HOST}:{SERVER_PORT}...\n")

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((SERVER_HOST, SERVER_PORT))
    except ConnectionRefusedError:
        print(" Connection failed. Is the server running?")
        sys.exit(1)

    print(" Connected to the ATM server.\n")

    try:
        while True:
            # Receive data from server
            data = client_socket.recv(BUFFER_SIZE).decode()
            if not data:
                print(" Server closed the connection.")
                break

            # Display the received message
            print(data, end="")

            # If server message indicates session end, close
            if any(word in data.lower() for word in ["goodbye", "blacklisted", "connection closing"]):
                break

            # Take user input
            user_input = input()
            client_socket.sendall(user_input.encode())

            # Manual exit by user
            if user_input.strip().lower() in ["exit", "quit", "3"]:
                print(" Exiting ATM Client.")
                break

    except KeyboardInterrupt:
        print("\n Client stopped by user.")
    finally:
        client_socket.close()
        print(" Disconnected from ATM Server.")


if __name__ == "__main__":
    start_client()
