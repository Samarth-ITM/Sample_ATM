import threading
import psutil
import time
import os
from logger_utils import get_logger

class ServerMonitor:
    """
    Monitors server utilization metrics including:
    - CPU usage
    - Memory usage
    - Active threads
    - Connection count
    """
    
    def __init__(self, interval=60):
        """
        Initialize the server monitor
        
        Args:
            interval (int): Monitoring interval in seconds (default: 60)
        """
        self.interval = interval
        self.active_connections = 0
        self.max_connections = 0
        self.total_connections = 0
        self.monitor_thread = None
        self.running = False
        self.logger = get_logger("ServerMonitor")
        self.pid = os.getpid()
        self.start_time = time.time()
        
    def increment_connection(self):
        """Increment the active connection counter"""
        with threading.Lock():
            self.active_connections += 1
            self.total_connections += 1
            if self.active_connections > self.max_connections:
                self.max_connections = self.active_connections
    
    def decrement_connection(self):
        """Decrement the active connection counter"""
        with threading.Lock():
            self.active_connections -= 1
    
    def get_thread_count(self):
        """Get the number of active threads in the process"""
        return threading.active_count()
    
    def get_cpu_usage(self):
        """Get the CPU usage percentage for this process"""
        return psutil.Process(self.pid).cpu_percent(interval=0.1)
    
    def get_memory_usage(self):
        """Get the memory usage in MB for this process"""
        process = psutil.Process(self.pid)
        memory_info = process.memory_info()
        return memory_info.rss / (1024 * 1024)  # Convert to MB
    
    def get_uptime(self):
        """Get the server uptime in seconds"""
        return time.time() - self.start_time
    
    def format_uptime(self, seconds):
        """Format uptime in days, hours, minutes, seconds"""
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
    
    def log_metrics(self):
        """Log the current server metrics"""
        uptime = self.get_uptime()
        cpu_usage = self.get_cpu_usage()
        memory_usage = self.get_memory_usage()
        thread_count = self.get_thread_count()
        
        self.logger.info(
            f"SERVER METRICS | "
            f"Uptime: {self.format_uptime(uptime)} | "
            f"CPU: {cpu_usage:.1f}% | "
            f"Memory: {memory_usage:.1f}MB | "
            f"Threads: {thread_count} | "
            f"Active Connections: {self.active_connections} | "
            f"Max Connections: {self.max_connections} | "
            f"Total Connections: {self.total_connections}"
        )
    
    def monitor_loop(self):
        """Main monitoring loop that runs in a separate thread"""
        while self.running:
            self.log_metrics()
            time.sleep(self.interval)
    
    def start(self):
        """Start the monitoring thread"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(
                target=self.monitor_loop,
                daemon=True
            )
            self.monitor_thread.start()
            self.logger.info("Server monitoring started")
    
    def stop(self):
        """Stop the monitoring thread"""
        if self.running:
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=1.0)
            self.logger.info("Server monitoring stopped")

# Singleton instance
_monitor = None

def get_monitor(interval=60):
    """Get the singleton monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = ServerMonitor(interval)
    return _monitor