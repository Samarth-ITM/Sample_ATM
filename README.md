# ATM System

A secure and robust ATM (Automated Teller Machine) simulation system with client-server architecture, transaction logging, and server monitoring capabilities.

## System Overview

This ATM system simulates a real-world banking environment with the following features:

- **Client-Server Architecture**: Secure socket-based communication
- **User Authentication**: PIN-based security with blacklisting for multiple failed attempts
- **Transaction Support**: Withdraw and deposit functionality
- **Database Integration**: Persistent storage of user accounts and transactions
- **Logging System**: Comprehensive transaction and error logging
- **Server Monitoring**: Real-time tracking of server performance metrics

## Components

The system consists of the following key components:

1. **Server (`server.py`)**: Handles client connections, authentication, and transactions
2. **Client (`atm_client.py`)**: Provides user interface for ATM operations
3. **Database Handler (`db_handler.py`)**: Manages data persistence and transaction processing
4. **Logger (`logger_utils.py`)**: Handles system logging
5. **Server Monitor (`server_monitor.py`)**: Tracks server performance metrics

## Installation

### Prerequisites

- Python 3.8 or higher
- MySQL (optional, for production use)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/atm-system.git
   cd atm-system
   ```

2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure the system:
   - Edit `config.ini` to set server address, port, and other parameters
   - For production, configure MySQL connection details

## Usage

### Starting the Server

1. Start the server:
   ```bash
   python server.py
   ```
   The server will initialize the database and start listening for connections.

### Using the Client

2. Start the client:
   ```bash
   python atm_client.py
   ```

3. Follow the on-screen instructions:
   - Enter your mobile number (will be registered if new)
   - Enter your PIN (5-digit number)
   - Select transaction type (withdraw, deposit, or exit)
   - Enter amount for transactions

## Configuration

The system is configured through `config.ini` with the following sections:

### Server Configuration
```ini
[server]
host = 0.0.0.0
port = 65432
worker_threads = 4
monitor_interval = 60
```

### Database Configuration
```ini
[mysql]
host = 127.0.0.1
port = 3306
user = root
password = your_password
database = bank_db
```

### Logging Configuration
```ini
[logging]
logfile = bank_server.log
```

## Data Storage

The system uses two CSV files for data storage:

1. **client.csv**: Stores user account information and balances
   - Format: `Mobile_Number, Action, Amount, User_Balance, Bank_Balance, Timestamp, Session_Start, Elapsed_Time`

2. **bank.csv**: Stores bank transaction records
   - Format: `Mobile_Number, Action, Amount, Bank_Balance, Timestamp`

## Server Monitoring

The server monitoring module tracks:
- CPU usage
- Memory usage
- Active threads
- Connection count (active, max, total)
- Server uptime

Metrics are logged at the interval specified in `config.ini`.

## Security Features

- PIN-based authentication
- Automatic blacklisting after multiple failed attempts
- Secure socket communication
- Transaction logging for audit trails

## Troubleshooting

- Check `bank_server.log` for error messages and transaction history
- Ensure the correct port is open and not blocked by firewall
- Verify database connection settings in `config.ini`

## License

This project is licensed under the MIT License - see the LICENSE file for details.
3. Follow the on-screen instructions to perform transactions.
