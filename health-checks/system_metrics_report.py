#!/usr/bin/env python3

"""
System Metrics Dashboard Generator - Enterprise Grade
Author: Gabriel - Senior Linux Systems Administrator
Version: 2.1
Compatible: RHEL/CentOS 7, 8, 9
Purpose: Generate professional HTML dashboards for system metrics and health status
"""

import os
import sys
import json
import subprocess
import platform
import datetime
import socket
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import argparse
import logging

# Configuration
CONFIG = {
    'output_dir': '/var/www/html/metrics',
    'backup_reports': True,
    'email_enabled': False,
    'email_smtp': 'localhost',
    'email_from': 'noreply@company.com',
    'email_to': ['admin@company.com'],
    'retention_days': 30
}

class SystemMetrics:
    """Collect and analyze system metrics"""
    
    def __init__(self):
        self.hostname = socket.gethostname()
        self.fqdn = socket.getfqdn()
        self.timestamp = datetime.datetime.now()
        self.metrics = {}
        
    def collect_system_info(self):
        """Collect basic system information"""
        try:
            # OS Information
            with open('/etc/redhat-release', 'r') as f:
                os_info = f.read().strip()
        except FileNotFoundError:
            os_info = platform.platform()
            
        # Uptime
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.read().split()[0])
            uptime_days = int(uptime_seconds // 86400)
            uptime_hours = int((uptime_seconds % 86400) // 3600)
            uptime_str = f"{uptime_days}d {uptime_hours}h"
            
        # Load average
        load_avg = os.getloadavg()
        
        # CPU cores
        cpu_cores = os.cpu_count()
        
        self.metrics['system'] = {
            'hostname': self.hostname,
            'fqdn': self.fqdn,
            'os_info': os_info,
            'kernel': platform.release(),
            'architecture': platform.machine(),
            'uptime': uptime_str,
            'uptime_seconds': int(uptime_seconds),
            'load_avg': {
                '1min': round(load_avg[0], 2),
                '5min': round(load_avg[1], 2),
                '15min': round(load_avg[2], 2)
            },
            'cpu_cores': cpu_cores,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }
        
    def collect_cpu_metrics(self):
        """Collect CPU usage and process information"""
        try:
            # CPU usage from /proc/stat
            with open('/proc/stat', 'r') as f:
                cpu_line = f.readline().strip().split()
                cpu_times = [int(x) for x in cpu_line[1:]]
                
            total_time = sum(cpu_times)
            idle_time = cpu_times[3]  # idle time is 4th column
            cpu_usage = round(((total_time - idle_time) / total_time) * 100, 1)
            
            # Top processes by CPU
            top_cpu_cmd = "ps aux --sort=-%cpu --no-headers | head -5"
            top_cpu_output = subprocess.check_output(top_cpu_cmd, shell=True, text=True)
            top_cpu_processes = []
            
            for line in top_cpu_output.strip().split('\n'):
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    top_cpu_processes.append({
                        'user': parts[0],
                        'pid': parts[1],
                        'cpu': parts[2],
                        'mem': parts[3],
                        'command': parts[10][:50] + ('...' if len(parts[10]) > 50 else '')
                    })
                    
            # CPU model information
            cpu_model = "Unknown"
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            cpu_model = line.split(':', 1)[1].strip()
                            break
            except:
                pass
                
            self.metrics['cpu'] = {
                'usage_percent': cpu_usage,
                'model': cpu_model,
                'cores': self.metrics['system']['cpu_cores'],
                'load_avg': self.metrics['system']['load_avg'],
                'top_processes': top_cpu_processes
            }
            
        except Exception as e:
            logging.error(f"Error collecting CPU metrics: {e}")
            self.metrics['cpu'] = {'error': str(e)}
            
    def collect_memory_metrics(self):
        """Collect memory and swap information"""
        try:
            mem_info = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    key, value = line.split(':', 1)
                    mem_info[key] = int(value.split()[0]) * 1024  # Convert KB to bytes
                    
            total_mem = mem_info['MemTotal']
            available_mem = mem_info.get('MemAvailable', mem_info['MemFree'])
            used_mem = total_mem - available_mem
            mem_usage_percent = round((used_mem / total_mem) * 100, 1)
            
            # Swap information
            swap_total = mem_info.get('SwapTotal', 0)
            swap_free = mem_info.get('SwapFree', 0)
            swap_used = swap_total - swap_free
            swap_usage_percent = round((swap_used / swap_total) * 100, 1) if swap_total > 0 else 0
            
            # Top processes by memory
            top_mem_cmd = "ps aux --sort=-%mem --no-headers | head -5"
            top_mem_output = subprocess.check_output(top_mem_cmd, shell=True, text=True)
            top_mem_processes = []
            
            for line in top_mem_output.strip().split('\n'):
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    top_mem_processes.append({
                        'user': parts[0],
                        'pid': parts[1],
                        'cpu': parts[2],
                        'mem': parts[3],
                        'command': parts[10][:50] + ('...' if len(parts[10]) > 50 else '')
                    })
                    
            def bytes_to_human(bytes_val):
                """Convert bytes to human readable format"""
                for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                    if bytes_val < 1024.0:
                        return f"{bytes_val:.1f} {unit}"
                    bytes_val /= 1024.0
                return f"{bytes_val:.1f} PB"
                
            self.metrics['memory'] = {
                'total_bytes': total_mem,
                'used_bytes': used_mem,
                'available_bytes': available_mem,
                'total_human': bytes_to_human(total_mem),
                'used_human': bytes_to_human(used_mem),
                'available_human': bytes_to_human(available_mem),
                'usage_percent': mem_usage_percent,
                'swap_total_bytes': swap_total,
                'swap_used_bytes': swap_used,
                'swap_total_human': bytes_to_human(swap_total),
                'swap_used_human': bytes_to_human(swap_used),
                'swap_usage_percent': swap_usage_percent,
                'top_processes': top_mem_processes
            }
            
        except Exception as e:
            logging.error(f"Error collecting memory metrics: {e}")
            self.metrics['memory'] = {'error': str(e)}
            
    def collect_disk_metrics(self):
        """Collect disk space and I/O information"""
        try:
            # Disk space information
            df_cmd = "df -h | grep -vE '^Filesystem|tmpfs|cdrom|udev'"
            df_output = subprocess.check_output(df_cmd, shell=True, text=True)
            
            filesystems = []
            for line in df_output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 6:
                    usage_percent = int(parts[4].rstrip('%'))
                    status = 'critical' if usage_percent >= 90 else 'warning' if usage_percent >= 80 else 'ok'
                    
                    filesystems.append({
                        'filesystem': parts[0],
                        'size': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'usage_percent': usage_percent,
                        'mountpoint': parts[5],
                        'status': status
                    })
                    
            # Inode information
            df_inode_cmd = "df -i | grep -vE '^Filesystem|tmpfs|cdrom|udev'"
            df_inode_output = subprocess.check_output(df_inode_cmd, shell=True, text=True)
            
            inode_info = {}
            for line in df_inode_output.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 6:
                    inode_usage = int(parts[4].rstrip('%'))
                    inode_info[parts[5]] = {
                        'total': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'usage_percent': inode_usage
                    }
                    
            # Large files in common directories
            large_files = []
            try:
                large_files_cmd = "find /var/log -type f -size +100M -exec ls -lh {} \\; 2>/dev/null | head -5"
                large_files_output = subprocess.check_output(large_files_cmd, shell=True, text=True)
                for line in large_files_output.strip().split('\n'):
                    if line:
                        parts = line.split()
                        if len(parts) >= 9:
                            large_files.append({
                                'size': parts[4],
                                'date': f"{parts[5]} {parts[6]} {parts[7]}",
                                'path': parts[8]
                            })
            except:
                pass
                
            self.metrics['disk'] = {
                'filesystems': filesystems,
                'inodes': inode_info,
                'large_files': large_files
            }
            
        except Exception as e:
            logging.error(f"Error collecting disk metrics: {e}")
            self.metrics['disk'] = {'error': str(e)}
            
    def collect_network_metrics(self):
        """Collect network interface and connectivity information"""
        try:
            # Network interfaces
            interfaces = []
            ip_cmd = "ip addr show"
            ip_output = subprocess.check_output(ip_cmd, shell=True, text=True)
            
            current_interface = None
            for line in ip_output.split('\n'):
                if line.startswith(' ') == False and ':' in line:
                    # New interface
                    parts = line.split()
                    if len(parts) >= 2:
                        interface_name = parts[1].rstrip(':')
                        current_interface = {
                            'name': interface_name,
                            'status': 'UP' if 'UP' in line else 'DOWN',
                            'addresses': []
                        }
                        interfaces.append(current_interface)
                elif 'inet ' in line and current_interface:
                    # IP address
                    parts = line.strip().split()
                    for i, part in enumerate(parts):
                        if part == 'inet' and i + 1 < len(parts):
                            current_interface['addresses'].append(parts[i + 1])
                            
            # Default gateway
            default_gw = None
            try:
                route_cmd = "ip route | grep default"
                route_output = subprocess.check_output(route_cmd, shell=True, text=True)
                if route_output:
                    default_gw = route_output.split()[2]
            except:
                pass
                
            # DNS test
            dns_status = 'ok'
            try:
                subprocess.check_output(['nslookup', 'google.com'], stderr=subprocess.DEVNULL, timeout=5)
            except:
                dns_status = 'failed'
                
            # Network connections
            netstat_cmd = "ss -tuln | grep LISTEN | wc -l"
            listening_ports = int(subprocess.check_output(netstat_cmd, shell=True, text=True).strip())
            
            self.metrics['network'] = {
                'interfaces': interfaces,
                'default_gateway': default_gw,
                'dns_status': dns_status,
                'listening_ports': listening_ports
            }
            
        except Exception as e:
            logging.error(f"Error collecting network metrics: {e}")
            self.metrics['network'] = {'error': str(e)}
            
    def collect_service_metrics(self):
        """Collect systemd service status"""
        try:
            # Critical services to monitor
            critical_services = [
                'sshd', 'NetworkManager', 'chronyd', 'rsyslog', 
                'firewalld', 'postfix', 'httpd', 'nginx', 'mariadb', 'postgresql'
            ]
            
            services_status = []
            for service in critical_services:
                try:
                    # Check if service exists
                    check_cmd = f"systemctl list-unit-files | grep -q '^{service}.service'"
                    subprocess.check_output(check_cmd, shell=True, stderr=subprocess.DEVNULL)
                    
                    # Get service status
                    status_cmd = f"systemctl is-active {service}"
                    status = subprocess.check_output(status_cmd, shell=True, text=True).strip()
                    
                    enabled_cmd = f"systemctl is-enabled {service}"
                    enabled = subprocess.check_output(enabled_cmd, shell=True, text=True).strip()
                    
                    services_status.append({
                        'name': service,
                        'status': status,
                        'enabled': enabled,
                        'health': 'ok' if status == 'active' else 'critical'
                    })
                except:
                    # Service doesn't exist or other error
                    continue
                    
            # Failed services
            failed_cmd = "systemctl list-units --failed --no-legend"
            try:
                failed_output = subprocess.check_output(failed_cmd, shell=True, text=True)
                failed_services = len(failed_output.strip().split('\n')) if failed_output.strip() else 0
            except:
                failed_services = 0
                
            self.metrics['services'] = {
                'critical_services': services_status,
                'failed_count': failed_services
            }
            
        except Exception as e:
            logging.error(f"Error collecting service metrics: {e}")
            self.metrics['services'] = {'error': str(e)}
            
    def collect_security_metrics(self):
        """Collect security-related information"""
        try:
            security_info = {}
            
            # SELinux status
            try:
                selinux_status = subprocess.check_output(['getenforce'], text=True).strip()
                security_info['selinux'] = {
                    'status': selinux_status,
                    'health': 'ok' if selinux_status == 'Enforcing' else 'warning'
                }
            except:
                security_info['selinux'] = {'status': 'Not available', 'health': 'unknown'}
                
            # Firewall status
            firewall_status = 'inactive'
            try:
                subprocess.check_output(['systemctl', 'is-active', 'firewalld'], stderr=subprocess.DEVNULL)
                firewall_status = 'active (firewalld)'
            except:
                try:
                    subprocess.check_output(['systemctl', 'is-active', 'iptables'], stderr=subprocess.DEVNULL)
                    firewall_status = 'active (iptables)'
                except:
                    pass
                    
            security_info['firewall'] = {
                'status': firewall_status,
                'health': 'ok' if 'active' in firewall_status else 'warning'
            }
            
            # Available updates
            updates_count = 0
            try:
                if os.path.exists('/usr/bin/dnf'):
                    updates_cmd = "dnf check-update -q | wc -l"
                else:
                    updates_cmd = "yum check-update -q | wc -l"
                updates_output = subprocess.check_output(updates_cmd, shell=True, text=True)
                updates_count = int(updates_output.strip())
            except:
                pass
                
            security_info['updates'] = {
                'available': updates_count,
                'health': 'ok' if updates_count == 0 else 'warning'
            }
            
            # Failed login attempts (last 24 hours)
            failed_logins = 0
            try:
                failed_cmd = "grep 'Failed password' /var/log/secure | grep '$(date +%b' | wc -l"
                failed_output = subprocess.check_output(failed_cmd, shell=True, text=True)
                failed_logins = int(failed_output.strip())
            except:
                pass
                
            security_info['failed_logins'] = {
                'count': failed_logins,
                'health': 'ok' if failed_logins < 10 else 'warning'
            }
            
            self.metrics['security'] = security_info
            
        except Exception as e:
            logging.error(f"Error collecting security metrics: {e}")
            self.metrics['security'] = {'error': str(e)}
            
    def collect_all_metrics(self):
        """Collect all system metrics"""
        print("Collecting system metrics...")
        self.collect_system_info()
        self.collect_cpu_metrics()
        self.collect_memory_metrics()
        self.collect_disk_metrics()
        self.collect_network_metrics()
        self.collect_service_metrics()
        self.collect_security_metrics()
        print("Metrics collection completed.")
        
class HTMLReportGenerator:
    """Generate professional HTML reports"""
    
    def __init__(self, metrics):
        self.metrics = metrics
        
    def generate_html(self):
        """Generate the complete HTML report"""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System Health Dashboard - {hostname}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .dashboard {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 300;
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.8;
        }}
        
        .content {{
            padding: 30px;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: #f8f9fa;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            transition: transform 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        
        .metric-card h3 {{
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.3em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        
        .metric-label {{
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .status-ok {{ color: #27ae60; }}
        .status-warning {{ color: #f39c12; }}
        .status-critical {{ color: #e74c3c; }}
        
        .progress-bar {{
            width: 100%;
            height: 20px;
            background: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }}
        
        .progress-ok {{ background: linear-gradient(90deg, #27ae60, #2ecc71); }}
        .progress-warning {{ background: linear-gradient(90deg, #f39c12, #e67e22); }}
        .progress-critical {{ background: linear-gradient(90deg, #e74c3c, #c0392b); }}
        
        .table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        
        .table th, .table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }}
        
        .table th {{
            background: #3498db;
            color: white;
            font-weight: 600;
        }}
        
        .table tr:hover {{
            background: #f8f9fa;
        }}
        
        .alert {{
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
        }}
        
        .alert-success {{
            background: #d4edda;
            border-left: 4px solid #27ae60;
            color: #155724;
        }}
        
        .alert-warning {{
            background: #fff3cd;
            border-left: 4px solid #f39c12;
            color: #856404;
        }}
        
        .alert-danger {{
            background: #f8d7da;
            border-left: 4px solid #e74c3c;
            color: #721c24;
        }}
        
        .footer {{
            background: #2c3e50;
            color: white;
            text-align: center;
            padding: 20px;
            font-size: 0.9em;
        }}
        
        @media (max-width: 768px) {{
            .metrics-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
            
            .content {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🖥️ System Health Dashboard</h1>
            <div class="subtitle">
                {hostname} | {timestamp}
            </div>
        </div>
        
        <div class="content">
            {system_overview}
            {performance_metrics}
            {disk_analysis}
            {network_status}
            {security_status}
            {services_status}
        </div>
        
        <div class="footer">
            Generated by Enterprise Linux Toolkit | © 2024 Gabriel - Senior Linux Systems Administrator
        </div>
    </div>
</body>
</html>
        """
        
        # Generate each section
        system_overview = self._generate_system_overview()
        performance_metrics = self._generate_performance_metrics()
        disk_analysis = self._generate_disk_analysis()
        network_status = self._generate_network_status()
        security_status = self._generate_security_status()
        services_status = self._generate_services_status()
        
        # Fill the template
        html_content = html_template.format(
            hostname=self.metrics['system']['hostname'],
            timestamp=self.metrics['system']['timestamp'],
            system_overview=system_overview,
            performance_metrics=performance_metrics,
            disk_analysis=disk_analysis,
            network_status=network_status,
            security_status=security_status,
            services_status=services_status
        )
        
        return html_content
        
    def _generate_system_overview(self):
        """Generate system overview section"""
        system = self.metrics['system']
        uptime_days = system['uptime_seconds'] // 86400
        
        # Determine overall health
        overall_health = "ok"
        health_issues = []
        
        if 'cpu' in self.metrics and self.metrics['cpu'].get('usage_percent', 0) > 80:
            overall_health = "warning"
            health_issues.append("High CPU usage")
            
        if 'memory' in self.metrics and self.metrics['memory'].get('usage_percent', 0) > 85:
            overall_health = "warning"
            health_issues.append("High memory usage")
            
        if 'disk' in self.metrics:
            for fs in self.metrics['disk'].get('filesystems', []):
                if fs.get('usage_percent', 0) > 90:
                    overall_health = "critical"
                    health_issues.append(f"Critical disk space on {fs['mountpoint']}")
                    
        health_class = f"status-{overall_health}"
        health_text = "Excellent" if overall_health == "ok" else "Needs Attention" if overall_health == "warning" else "Critical Issues"
        
        return f"""
        <div class="alert alert-{'success' if overall_health == 'ok' else 'warning' if overall_health == 'warning' else 'danger'}">
            <strong>Overall System Health: <span class="{health_class}">{health_text}</span></strong>
            {('<br>Issues: ' + ', '.join(health_issues)) if health_issues else '<br>All systems operating normally'}
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>📊 System Information</h3>
                <div style="line-height: 1.8;">
                    <strong>OS:</strong> {system['os_info']}<br>
                    <strong>Kernel:</strong> {system['kernel']}<br>
                    <strong>Architecture:</strong> {system['architecture']}<br>
                    <strong>Uptime:</strong> {system['uptime']} ({uptime_days} days)<br>
                    <strong>CPU Cores:</strong> {system['cpu_cores']}
                </div>
            </div>
            
            <div class="metric-card">
                <h3>⚡ Load Average</h3>
                <div class="metric-value {self._get_load_status(system['load_avg']['1min'], system['cpu_cores'])}">{system['load_avg']['1min']}</div>
                <div class="metric-label">1 Minute Average</div>
                <div style="margin-top: 15px; font-size: 0.9em;">
                    5min: {system['load_avg']['5min']} | 15min: {system['load_avg']['15min']}
                </div>
            </div>
        </div>
        """
        
    def _generate_performance_metrics(self):
        """Generate performance metrics section"""
        cpu = self.metrics.get('cpu', {})
        memory = self.metrics.get('memory', {})
        
        cpu_usage = cpu.get('usage_percent', 0)
        cpu_status = self._get_usage_status(cpu_usage)
        
        memory_usage = memory.get('usage_percent', 0)
        memory_status = self._get_usage_status(memory_usage)
        
        swap_usage = memory.get('swap_usage_percent', 0)
        swap_status = self._get_usage_status(swap_usage, warning=25, critical=50)
        
        return f"""
        <h2 style="margin: 30px 0 20px 0; color: #2c3e50;">🚀 Performance Metrics</h2>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>💻 CPU Usage</h3>
                <div class="metric-value status-{cpu_status}">{cpu_usage}%</div>
                <div class="progress-bar">
                    <div class="progress-fill progress-{cpu_status}" style="width: {cpu_usage}%"></div>
                </div>
                <div class="metric-label">Processor Utilization</div>
                {self._generate_top_processes_table(cpu.get('top_processes', []), 'CPU')}
            </div>
            
            <div class="metric-card">
                <h3>🧠 Memory Usage</h3>
                <div class="metric-value status-{memory_status}">{memory_usage}%</div>
                <div class="progress-bar">
                    <div class="progress-fill progress-{memory_status}" style="width: {memory_usage}%"></div>
                </div>
                <div class="metric-label">RAM Utilization</div>
                <div style="margin-top: 10px; font-size: 0.9em;">
                    Used: {memory.get('used_human', 'N/A')} / Total: {memory.get('total_human', 'N/A')}
                </div>
                {self._generate_top_processes_table(memory.get('top_processes', []), 'Memory')}
            </div>
            
            <div class="metric-card">
                <h3>💾 Swap Usage</h3>
                <div class="metric-value status-{swap_status}">{swap_usage}%</div>
                <div class="progress-bar">
                    <div class="progress-fill progress-{swap_status}" style="width: {swap_usage}%"></div>
                </div>
                <div class="metric-label">Swap Utilization</div>
                <div style="margin-top: 10px; font-size: 0.9em;">
                    Used: {memory.get('swap_used_human', 'N/A')} / Total: {memory.get('swap_total_human', 'N/A')}
                </div>
            </div>
        </div>
        """
        
    def _generate_disk_analysis(self):
        """Generate disk analysis section"""
        disk = self.metrics.get('disk', {})
        filesystems = disk.get('filesystems', [])
        
        disk_html = """
        <h2 style="margin: 30px 0 20px 0; color: #2c3e50;">💽 Disk Space Analysis</h2>
        
        <div class="metric-card">
            <h3>📁 Filesystem Usage</h3>
        """
        
        if filesystems:
            disk_html += '<table class="table">'
            disk_html += '''
            <thead>
                <tr>
                    <th>Filesystem</th>
                    <th>Size</th>
                    <th>Used</th>
                    <th>Available</th>
                    <th>Usage</th>
                    <th>Mountpoint</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
            '''
            
            for fs in filesystems:
                status_class = f"status-{fs['status']}"
                disk_html += f'''
                <tr>
                    <td>{fs['filesystem']}</td>
                    <td>{fs['size']}</td>
                    <td>{fs['used']}</td>
                    <td>{fs['available']}</td>
                    <td>
                        <div class="progress-bar" style="width: 100px; height: 15px;">
                            <div class="progress-fill progress-{fs['status']}" style="width: {fs['usage_percent']}%"></div>
                        </div>
                        <span class="{status_class}">{fs['usage_percent']}%</span>
                    </td>
                    <td>{fs['mountpoint']}</td>
                    <td><span class="{status_class}">●</span></td>
                </tr>
                '''
            disk_html += '</tbody></table>'
        else:
            disk_html += '<p>No filesystem data available</p>'
            
        # Large files section
        large_files = disk.get('large_files', [])
        if large_files:
            disk_html += '''
            <h4 style="margin-top: 25px; color: #34495e;">🗂️ Large Files (>100MB in /var/log)</h4>
            <table class="table">
                <thead>
                    <tr>
                        <th>Size</th>
                        <th>Date Modified</th>
                        <th>File Path</th>
                    </tr>
                </thead>
                <tbody>
            '''
            for file in large_files:
                disk_html += f'''
                <tr>
                    <td>{file['size']}</td>
                    <td>{file['date']}</td>
                    <td style="font-family: monospace; font-size: 0.9em;">{file['path']}</td>
                </tr>
                '''
            disk_html += '</tbody></table>'
            
        disk_html += '</div>'
        return disk_html
        
    def _generate_network_status(self):
        """Generate network status section"""
        network = self.metrics.get('network', {})
        interfaces = network.get('interfaces', [])
        
        network_html = """
        <h2 style="margin: 30px 0 20px 0; color: #2c3e50;">🌐 Network Status</h2>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>🔗 Network Interfaces</h3>
        """
        
        if interfaces:
            for interface in interfaces:
                status_class = "status-ok" if interface['status'] == 'UP' else "status-critical"
                addresses = ', '.join(interface['addresses']) if interface['addresses'] else 'No IP assigned'
                
                network_html += f'''
                <div style="margin-bottom: 15px; padding: 10px; background: #f8f9fa; border-radius: 8px;">
                    <strong>{interface['name']}</strong> 
                    <span class="{status_class}">({interface['status']})</span><br>
                    <small style="color: #7f8c8d;">{addresses}</small>
                </div>
                '''
        else:
            network_html += '<p>No network interface data available</p>'
            
        network_html += '</div>'
        
        # Connectivity status
        default_gw = network.get('default_gateway')
        dns_status = network.get('dns_status', 'unknown')
        listening_ports = network.get('listening_ports', 0)
        
        network_html += f'''
            <div class="metric-card">
                <h3>🔌 Connectivity Status</h3>
                <div style="line-height: 2;">
                    <strong>Default Gateway:</strong> 
                    <span class="{"status-ok" if default_gw else "status-warning"}">{default_gw or "Not configured"}</span><br>
                    
                    <strong>DNS Resolution:</strong> 
                    <span class="status-{dns_status}">{"Working" if dns_status == "ok" else "Failed"}</span><br>
                    
                    <strong>Listening Services:</strong> 
                    <span class="status-ok">{listening_ports} ports</span>
                </div>
            </div>
        </div>
        '''
        
        return network_html
        
    def _generate_security_status(self):
        """Generate security status section"""
        security = self.metrics.get('security', {})
        
        security_html = """
        <h2 style="margin: 30px 0 20px 0; color: #2c3e50;">🔒 Security Status</h2>
        
        <div class="metrics-grid">
        """
        
        # SELinux status
        selinux = security.get('selinux', {})
        selinux_status = selinux.get('status', 'Unknown')
        selinux_health = selinux.get('health', 'unknown')
        
        security_html += f'''
            <div class="metric-card">
                <h3>🛡️ SELinux Status</h3>
                <div class="metric-value status-{selinux_health}">{selinux_status}</div>
                <div class="metric-label">Mandatory Access Control</div>
            </div>
        '''
        
        # Firewall status
        firewall = security.get('firewall', {})
        firewall_status = firewall.get('status', 'Unknown')
        firewall_health = firewall.get('health', 'unknown')
        
        security_html += f'''
            <div class="metric-card">
                <h3>🔥 Firewall Status</h3>
                <div class="metric-value status-{firewall_health}">{firewall_status}</div>
                <div class="metric-label">Network Protection</div>
            </div>
        '''
        
        # Available updates
        updates = security.get('updates', {})
        updates_count = updates.get('available', 0)
        updates_health = updates.get('health', 'unknown')
        
        security_html += f'''
            <div class="metric-card">
                <h3>📦 System Updates</h3>
                <div class="metric-value status-{updates_health}">{updates_count}</div>
                <div class="metric-label">Available Updates</div>
            </div>
        '''
        
        # Failed logins
        failed_logins = security.get('failed_logins', {})
        login_count = failed_logins.get('count', 0)
        login_health = failed_logins.get('health', 'unknown')
        
        security_html += f'''
            <div class="metric-card">
                <h3>🚫 Failed Logins</h3>
                <div class="metric-value status-{login_health}">{login_count}</div>
                <div class="metric-label">Last 24 Hours</div>
            </div>
        </div>
        '''
        
        return security_html
        
    def _generate_services_status(self):
        """Generate services status section"""
        services = self.metrics.get('services', {})
        critical_services = services.get('critical_services', [])
        failed_count = services.get('failed_count', 0)
        
        services_html = f"""
        <h2 style="margin: 30px 0 20px 0; color: #2c3e50;">⚙️ System Services</h2>
        
        <div class="alert alert-{'success' if failed_count == 0 else 'warning'}">
            <strong>Service Status Summary:</strong> 
            {len(critical_services)} critical services monitored, {failed_count} failed services detected
        </div>
        
        <div class="metric-card">
            <h3>🔧 Critical Services Status</h3>
        """
        
        if critical_services:
            services_html += '''
            <table class="table">
                <thead>
                    <tr>
                        <th>Service</th>
                        <th>Status</th>
                        <th>Enabled</th>
                        <th>Health</th>
                    </tr>
                </thead>
                <tbody>
            '''
            
            for service in critical_services:
                status_class = f"status-{service['health']}"
                enabled_class = "status-ok" if service['enabled'] == 'enabled' else "status-warning"
                
                services_html += f'''
                <tr>
                    <td><strong>{service['name']}</strong></td>
                    <td><span class="{status_class}">{service['status']}</span></td>
                    <td><span class="{enabled_class}">{service['enabled']}</span></td>
                    <td><span class="{status_class}">●</span></td>
                </tr>
                '''
            services_html += '</tbody></table>'
        else:
            services_html += '<p>No service data available</p>'
            
        services_html += '</div>'
        return services_html
        
    def _generate_top_processes_table(self, processes, metric_type):
        """Generate top processes table"""
        if not processes:
            return ''
            
        table_html = f'''
        <h4 style="margin-top: 20px; color: #34495e;">Top {metric_type} Processes</h4>
        <table class="table">
            <thead>
                <tr>
                    <th>User</th>
                    <th>PID</th>
                    <th>CPU%</th>
                    <th>MEM%</th>
                    <th>Command</th>
                </tr>
            </thead>
            <tbody>
        '''
        
        for process in processes[:5]:  # Limit to top 5
            table_html += f'''
            <tr>
                <td>{process['user']}</td>
                <td>{process['pid']}</td>
                <td>{process['cpu']}</td>
                <td>{process['mem']}</td>
                <td style="font-family: monospace; font-size: 0.8em;">{process['command']}</td>
            </tr>
            '''
            
        table_html += '</tbody></table>'
        return table_html
        
    def _get_usage_status(self, usage, warning=75, critical=90):
        """Determine status based on usage percentage"""
        if usage >= critical:
            return "critical"
        elif usage >= warning:
            return "warning"
        else:
            return "ok"
            
    def _get_load_status(self, load_avg, cpu_cores):
        """Determine load average status"""
        normalized_load = load_avg / cpu_cores
        if normalized_load >= 2.0:
            return "status-critical"
        elif normalized_load >= 1.0:
            return "status-warning"
        else:
            return "status-ok"

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate system metrics HTML dashboard')
    parser.add_argument('--output', '-o', default='/tmp/system-dashboard.html',
                       help='Output HTML file path')
    parser.add_argument('--config', '-c', 
                       help='Configuration file path')
    parser.add_argument('--email', action='store_true',
                       help='Send report via email')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Check if running as root
        if os.geteuid() != 0:
            print("Warning: Some metrics may not be available without root privileges")
            
        # Collect metrics
        metrics_collector = SystemMetrics()
        metrics_collector.collect_all_metrics()
        
        # Generate HTML report
        report_generator = HTMLReportGenerator(metrics_collector.metrics)
        html_content = report_generator.generate_html()
        
        # Write to file
        output_path = args.output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
            
        print(f"✅ System dashboard generated successfully!")
        print(f"📊 Report saved to: {output_path}")
        print(f"🌐 Open in browser: file://{os.path.abspath(output_path)}")
        
        # Optional: Send email
        if args.email and CONFIG.get('email_enabled'):
            send_email_report(html_content, metrics_collector.metrics)
            
    except Exception as e:
        logging.error(f"Error generating dashboard: {e}")
        sys.exit(1)

def send_email_report(html_content, metrics):
    """Send email report (if configured)"""
    try:
        msg = MIMEMultipart()
        msg['From'] = CONFIG['email_from']
        msg['To'] = ', '.join(CONFIG['email_to'])
        msg['Subject'] = f"System Health Report - {metrics['system']['hostname']}"
        
        # Add HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        server = smtplib.SMTP(CONFIG['email_smtp'])
        text = msg.as_string()
        server.sendmail(CONFIG['email_from'], CONFIG['email_to'], text)
        server.quit()
        
        print("📧 Email report sent successfully!")
        
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

if __name__ == "__main__":
    main()
