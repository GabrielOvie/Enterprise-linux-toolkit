#!/bin/bash

#################################################################
# RHEL Health Check Script - Enterprise Grade
# Author: Gabriel - Senior Linux Systems Administrator
# Version: 2.1
# Compatible: RHEL/CentOS 7, 8, 9
# Purpose: Comprehensive system health analysis and reporting
#################################################################

# Color codes for professional output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/rhel-healthcheck.log"
REPORT_FILE="/tmp/healthcheck-$(date +%Y%m%d-%H%M%S).txt"
EMAIL_RECIPIENT="${ADMIN_EMAIL:-root@localhost}"
HOSTNAME=$(hostname -f)
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Thresholds (configurable)
DISK_WARNING=80
DISK_CRITICAL=90
CPU_WARNING=70
CPU_CRITICAL=85
MEMORY_WARNING=80
MEMORY_CRITICAL=90
LOAD_WARNING=5
LOAD_CRITICAL=10

#################################################################
# UTILITY FUNCTIONS
#################################################################

print_header() {
    echo -e "\n${BLUE}================================================================================================${NC}"
    echo -e "${CYAN}                    RHEL ENTERPRISE HEALTH CHECK REPORT${NC}"
    echo -e "${BLUE}================================================================================================${NC}"
    echo -e "${PURPLE}Server:${NC} $HOSTNAME"
    echo -e "${PURPLE}Date:${NC} $DATE"
    echo -e "${PURPLE}Report:${NC} $REPORT_FILE"
    echo -e "${BLUE}================================================================================================${NC}\n"
}

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

print_section() {
    echo -e "\n${YELLOW}► $1${NC}"
    echo "----------------------------------------"
    log_message "Starting: $1"
}

print_status() {
    local status=$1
    local message=$2
    case $status in
        "OK")
            echo -e "${GREEN}✓ OK${NC} - $message"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠ WARNING${NC} - $message"
            ;;
        "CRITICAL")
            echo -e "${RED}✗ CRITICAL${NC} - $message"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ INFO${NC} - $message"
            ;;
    esac
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}Error: This script must be run as root or with sudo${NC}"
        exit 1
    fi
}

#################################################################
# SYSTEM INFORMATION
#################################################################

check_system_info() {
    print_section "SYSTEM INFORMATION"
    
    # OS Information
    if [ -f /etc/redhat-release ]; then
        OS_INFO=$(cat /etc/redhat-release)
        print_status "INFO" "OS: $OS_INFO"
    fi
    
    # Kernel Information
    KERNEL=$(uname -r)
    print_status "INFO" "Kernel: $KERNEL"
    
    # Architecture
    ARCH=$(uname -m)
    print_status "INFO" "Architecture: $ARCH"
    
    # Uptime
    UPTIME=$(uptime -p 2>/dev/null || uptime | awk '{print $3,$4}' | sed 's/,//')
    print_status "INFO" "Uptime: $UPTIME"
    
    # Last reboot
    LAST_BOOT=$(who -b | awk '{print $3,$4}')
    print_status "INFO" "Last Boot: $LAST_BOOT"
    
    # System load
    LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | sed 's/^ *//')
    LOAD_1MIN=$(echo $LOAD_AVG | awk -F',' '{print $1}' | sed 's/^ *//')
    LOAD_1MIN_INT=$(echo "$LOAD_1MIN" | awk '{print int($1)}')
    
    if [ "$LOAD_1MIN_INT" -gt "$LOAD_CRITICAL" ]; then
        print_status "CRITICAL" "Load Average (1min): $LOAD_1MIN - System heavily loaded"
    elif [ "$LOAD_1MIN_INT" -gt "$LOAD_WARNING" ]; then
        print_status "WARNING" "Load Average (1min): $LOAD_1MIN - System moderately loaded"
    else
        print_status "OK" "Load Average (1min): $LOAD_1MIN"
    fi
}

#################################################################
# CPU ANALYSIS
#################################################################

check_cpu() {
    print_section "CPU ANALYSIS"
    
    # CPU Information
    CPU_MODEL=$(grep "model name" /proc/cpuinfo | head -1 | cut -d':' -f2 | sed 's/^ *//')
    CPU_CORES=$(nproc)
    print_status "INFO" "CPU: $CPU_MODEL"
    print_status "INFO" "CPU Cores: $CPU_CORES"
    
    # CPU Usage (average over 3 seconds)
    echo "Measuring CPU usage (3 seconds)..."
    CPU_USAGE=$(top -bn2 -d1 | grep "Cpu(s)" | tail -1 | awk '{print $2}' | sed 's/%us,//')
    CPU_USAGE_INT=$(echo "$CPU_USAGE" | awk '{print int($1)}')
    
    if [ "$CPU_USAGE_INT" -gt "$CPU_CRITICAL" ]; then
        print_status "CRITICAL" "CPU Usage: ${CPU_USAGE}% - High CPU utilization"
    elif [ "$CPU_USAGE_INT" -gt "$CPU_WARNING" ]; then
        print_status "WARNING" "CPU Usage: ${CPU_USAGE}% - Moderate CPU utilization"
    else
        print_status "OK" "CPU Usage: ${CPU_USAGE}%"
    fi
    
    # Top CPU processes
    echo -e "\n${CYAN}Top 5 CPU consuming processes:${NC}"
    ps aux --sort=-%cpu | head -6 | tail -5 | awk '{printf "%-8s %-6s %-8s %s\n", $1, $2, $3"%", $11}'
    
    # CPU temperature (if available)
    if command -v sensors >/dev/null 2>&1; then
        TEMP=$(sensors 2>/dev/null | grep -E "(Core|CPU)" | head -1 | awk '{print $3}' | sed 's/+//;s/°C//')
        if [ ! -z "$TEMP" ]; then
            print_status "INFO" "CPU Temperature: ${TEMP}°C"
        fi
    fi
}

#################################################################
# MEMORY ANALYSIS
#################################################################

check_memory() {
    print_section "MEMORY ANALYSIS"
    
    # Memory information
    TOTAL_MEM=$(free -h | grep "Mem:" | awk '{print $2}')
    USED_MEM=$(free -h | grep "Mem:" | awk '{print $3}')
    FREE_MEM=$(free -h | grep "Mem:" | awk '{print $4}')
    AVAILABLE_MEM=$(free -h | grep "Mem:" | awk '{print $7}')
    
    # Memory usage percentage
    MEM_USAGE_PERCENT=$(free | grep "Mem:" | awk '{printf "%.0f", ($3/$2)*100}')
    
    print_status "INFO" "Total Memory: $TOTAL_MEM"
    print_status "INFO" "Used Memory: $USED_MEM"
    print_status "INFO" "Available Memory: $AVAILABLE_MEM"
    
    if [ "$MEM_USAGE_PERCENT" -gt "$MEMORY_CRITICAL" ]; then
        print_status "CRITICAL" "Memory Usage: ${MEM_USAGE_PERCENT}% - Critical memory usage"
    elif [ "$MEM_USAGE_PERCENT" -gt "$MEMORY_WARNING" ]; then
        print_status "WARNING" "Memory Usage: ${MEM_USAGE_PERCENT}% - High memory usage"
    else
        print_status "OK" "Memory Usage: ${MEM_USAGE_PERCENT}%"
    fi
    
    # Swap information
    SWAP_TOTAL=$(free -h | grep "Swap:" | awk '{print $2}')
    SWAP_USED=$(free -h | grep "Swap:" | awk '{print $3}')
    SWAP_USAGE_PERCENT=$(free | grep "Swap:" | awk '{if($2>0) printf "%.0f", ($3/$2)*100; else print "0"}')
    
    if [ "$SWAP_USAGE_PERCENT" -gt 50 ]; then
        print_status "WARNING" "Swap Usage: ${SWAP_USAGE_PERCENT}% (${SWAP_USED}/${SWAP_TOTAL}) - High swap usage"
    else
        print_status "OK" "Swap Usage: ${SWAP_USAGE_PERCENT}% (${SWAP_USED}/${SWAP_TOTAL})"
    fi
    
    # Top memory processes
    echo -e "\n${CYAN}Top 5 memory consuming processes:${NC}"
    ps aux --sort=-%mem | head -6 | tail -5 | awk '{printf "%-8s %-6s %-8s %s\n", $1, $2, $4"%", $11}'
}

#################################################################
# DISK ANALYSIS
#################################################################

check_disk() {
    print_section "DISK SPACE ANALYSIS"
    
    # Disk space check
    echo -e "${CYAN}Filesystem usage:${NC}"
    df -h | grep -vE '^Filesystem|tmpfs|cdrom|udev' | awk '{print $1 " " $2 " " $3 " " $4 " " $5 " " $6}' | while read filesystem size used avail percent mountpoint; do
        usage=$(echo $percent | sed 's/%//')
        if [ "$usage" -gt "$DISK_CRITICAL" ]; then
            print_status "CRITICAL" "$mountpoint: ${percent} used (${used}/${size}) - Critical disk space"
        elif [ "$usage" -gt "$DISK_WARNING" ]; then
            print_status "WARNING" "$mountpoint: ${percent} used (${used}/${size}) - Low disk space"
        else
            print_status "OK" "$mountpoint: ${percent} used (${used}/${size})"
        fi
    done
    
    # Inode usage
    echo -e "\n${CYAN}Inode usage:${NC}"
    df -i | grep -vE '^Filesystem|tmpfs|cdrom|udev' | awk '{print $1 " " $5 " " $6}' | while read filesystem percent mountpoint; do
        usage=$(echo $percent | sed 's/%//')
        if [ "$usage" -gt 90 ]; then
            print_status "WARNING" "$mountpoint: ${percent} inodes used - High inode usage"
        else
            print_status "OK" "$mountpoint: ${percent} inodes used"
        fi
    done
    
    # Largest directories in /var/log
    echo -e "\n${CYAN}Largest log directories:${NC}"
    if [ -d /var/log ]; then
        du -sh /var/log/* 2>/dev/null | sort -hr | head -5
    fi
    
    # Check for large files
    echo -e "\n${CYAN}Files larger than 1GB:${NC}"
    find /var/log -type f -size +1G -exec ls -lh {} \; 2>/dev/null | head -5
}

#################################################################
# NETWORK ANALYSIS
#################################################################

check_network() {
    print_section "NETWORK ANALYSIS"
    
    # Network interfaces
    echo -e "${CYAN}Network interfaces:${NC}"
    ip addr show | grep -E "^[0-9]+:|inet " | awk '
        /^[0-9]+:/ {iface=$2; gsub(/:/, "", iface)} 
        /inet / {print iface ": " $2}
    ' | while read line; do
        print_status "INFO" "$line"
    done
    
    # Default gateway
    DEFAULT_GW=$(ip route | grep default | awk '{print $3}' | head -1)
    if [ ! -z "$DEFAULT_GW" ]; then
        if ping -c 1 -W 2 "$DEFAULT_GW" >/dev/null 2>&1; then
            print_status "OK" "Default Gateway: $DEFAULT_GW (reachable)"
        else
            print_status "CRITICAL" "Default Gateway: $DEFAULT_GW (unreachable)"
        fi
    fi
    
    # DNS resolution test
    if nslookup google.com >/dev/null 2>&1; then
        print_status "OK" "DNS Resolution: Working"
    else
        print_status "CRITICAL" "DNS Resolution: Failed"
    fi
    
    # Network connections
    ESTABLISHED_CONNECTIONS=$(ss -tuln | grep -c LISTEN)
    print_status "INFO" "Listening Services: $ESTABLISHED_CONNECTIONS"
    
    # Check for high network usage (if iftop is available)
    if command -v iftop >/dev/null 2>&1; then
        print_status "INFO" "Network monitoring tools available"
    fi
}

#################################################################
# SERVICE ANALYSIS
#################################################################

check_services() {
    print_section "CRITICAL SERVICES STATUS"
    
    # Define critical services (customize based on your environment)
    CRITICAL_SERVICES=(
        "sshd"
        "NetworkManager"
        "chronyd"
        "rsyslog"
        "firewalld"
    )
    
    for service in "${CRITICAL_SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            print_status "OK" "Service $service: Active"
        else
            if systemctl list-unit-files | grep -q "^$service.service"; then
                print_status "CRITICAL" "Service $service: Inactive/Failed"
            else
                print_status "INFO" "Service $service: Not installed"
            fi
        fi
    done
    
    # Failed services
    FAILED_SERVICES=$(systemctl list-units --failed --no-legend | wc -l)
    if [ "$FAILED_SERVICES" -gt 0 ]; then
        print_status "WARNING" "Failed Services: $FAILED_SERVICES services in failed state"
        echo -e "${CYAN}Failed services:${NC}"
        systemctl list-units --failed --no-legend | awk '{print $1}'
    else
        print_status "OK" "Failed Services: None"
    fi
}

#################################################################
# SECURITY CHECKS
#################################################################

check_security() {
    print_section "SECURITY STATUS"
    
    # SELinux status
    if command -v getenforce >/dev/null 2>&1; then
        SELINUX_STATUS=$(getenforce)
        if [ "$SELINUX_STATUS" = "Enforcing" ]; then
            print_status "OK" "SELinux: $SELINUX_STATUS"
        else
            print_status "WARNING" "SELinux: $SELINUX_STATUS - Should be Enforcing for security"
        fi
    fi
    
    # Firewall status
    if systemctl is-active --quiet firewalld; then
        print_status "OK" "Firewall: Active (firewalld)"
    elif systemctl is-active --quiet iptables; then
        print_status "OK" "Firewall: Active (iptables)"
    else
        print_status "WARNING" "Firewall: No active firewall detected"
    fi
    
    # Check for updates
    if command -v yum >/dev/null 2>&1; then
        UPDATES=$(yum check-update -q | wc -l 2>/dev/null || echo "0")
    elif command -v dnf >/dev/null 2>&1; then
        UPDATES=$(dnf check-update -q | wc -l 2>/dev/null || echo "0")
    else
        UPDATES="Unknown"
    fi
    
    if [ "$UPDATES" = "Unknown" ]; then
        print_status "INFO" "Available Updates: Cannot determine"
    elif [ "$UPDATES" -gt 0 ]; then
        print_status "WARNING" "Available Updates: $UPDATES packages need updating"
    else
        print_status "OK" "Available Updates: System up to date"
    fi
    
    # Last login attempts
    FAILED_LOGINS=$(grep "Failed password" /var/log/secure 2>/dev/null | tail -10 | wc -l)
    if [ "$FAILED_LOGINS" -gt 5 ]; then
        print_status "WARNING" "Failed Login Attempts: $FAILED_LOGINS recent failed attempts detected"
    else
        print_status "OK" "Failed Login Attempts: $FAILED_LOGINS (normal)"
    fi
}

#################################################################
# SYSTEM LOGS ANALYSIS
#################################################################

check_logs() {
    print_section "SYSTEM LOGS ANALYSIS"
    
    # Check system log for errors
    ERROR_COUNT=$(grep -i "error" /var/log/messages 2>/dev/null | tail -50 | wc -l)
    if [ "$ERROR_COUNT" -gt 10 ]; then
        print_status "WARNING" "System Errors: $ERROR_COUNT recent errors in system log"
    else
        print_status "OK" "System Errors: $ERROR_COUNT recent errors (normal)"
    fi
    
    # Check for kernel panics
    PANIC_COUNT=$(grep -i "kernel panic" /var/log/messages* 2>/dev/null | wc -l)
    if [ "$PANIC_COUNT" -gt 0 ]; then
        print_status "CRITICAL" "Kernel Panics: $PANIC_COUNT kernel panics detected"
    else
        print_status "OK" "Kernel Panics: None detected"
    fi
    
    # Log rotation status
    if [ -f /var/log/messages ]; then
        LOG_SIZE=$(du -sh /var/log/messages | awk '{print $1}')
        print_status "INFO" "Main system log size: $LOG_SIZE"
    fi
}

#################################################################
# HARDWARE STATUS
#################################################################

check_hardware() {
    print_section "HARDWARE STATUS"
    
    # Check for hardware errors
    if command -v dmesg >/dev/null 2>&1; then
        HW_ERRORS=$(dmesg | grep -i "error\|fail\|critical" | tail -10 | wc -l)
        if [ "$HW_ERRORS" -gt 5 ]; then
            print_status "WARNING" "Hardware Errors: $HW_ERRORS potential hardware issues in dmesg"
        else
            print_status "OK" "Hardware Errors: $HW_ERRORS (normal)"
        fi
    fi
    
    # Disk health (if smartctl is available)
    if command -v smartctl >/dev/null 2>&1; then
        DISK_DEVICES=$(lsblk -nd -o NAME | grep -E "^(sd|nvme)" | head -3)
        for device in $DISK_DEVICES; do
            SMART_STATUS=$(smartctl -H /dev/$device 2>/dev/null | grep "SMART overall-health" | awk '{print $6}')
            if [ "$SMART_STATUS" = "PASSED" ]; then
                print_status "OK" "Disk Health (/dev/$device): $SMART_STATUS"
            elif [ ! -z "$SMART_STATUS" ]; then
                print_status "WARNING" "Disk Health (/dev/$device): $SMART_STATUS"
            fi
        done
    fi
}

#################################################################
# SUMMARY AND REPORTING
#################################################################

generate_summary() {
    print_section "HEALTH CHECK SUMMARY"
    
    echo -e "${CYAN}System Performance Summary:${NC}"
    echo "• CPU Usage: ${CPU_USAGE}%"
    echo "• Memory Usage: ${MEM_USAGE_PERCENT}%"
    echo "• Swap Usage: ${SWAP_USAGE_PERCENT}%"
    echo "• Load Average: $LOAD_1MIN"
    echo "• Available Updates: $UPDATES"
    echo "• Failed Services: $FAILED_SERVICES"
    
    echo -e "\n${CYAN}Recommendations:${NC}"
    
    # Generate recommendations based on findings
    if [ "$CPU_USAGE_INT" -gt "$CPU_WARNING" ]; then
        echo "• Monitor CPU usage and investigate high-consuming processes"
    fi
    
    if [ "$MEM_USAGE_PERCENT" -gt "$MEMORY_WARNING" ]; then
        echo "• Consider memory optimization or upgrade"
    fi
    
    if [ "$SWAP_USAGE_PERCENT" -gt 25 ]; then
        echo "• Investigate high swap usage, may indicate memory pressure"
    fi
    
    if [ "$UPDATES" != "0" ] && [ "$UPDATES" != "Unknown" ]; then
        echo "• Schedule system updates during maintenance window"
    fi
    
    if [ "$FAILED_SERVICES" -gt 0 ]; then
        echo "• Investigate and resolve failed services"
    fi
    
    echo -e "\n${GREEN}Health check completed successfully!${NC}"
    echo -e "${BLUE}Report saved to: $REPORT_FILE${NC}"
    echo -e "${BLUE}Full log available at: $LOG_FILE${NC}"
}

#################################################################
# MAIN EXECUTION
#################################################################

main() {
    # Initialize
    check_root
    log_message "Health check started by $(whoami)"
    
    # Redirect output to both console and report file
    exec > >(tee -a "$REPORT_FILE")
    exec 2>&1
    
    # Run all checks
    print_header
    check_system_info
    check_cpu
    check_memory
    check_disk
    check_network
    check_services
    check_security
    check_logs
    check_hardware
    generate_summary
    
    # Final logging
    log_message "Health check completed successfully"
    
    # Optional: Email report (if mail command is available and configured)
    if command -v mail >/dev/null 2>&1 && [ "$EMAIL_RECIPIENT" != "root@localhost" ]; then
        mail -s "RHEL Health Check Report - $HOSTNAME" "$EMAIL_RECIPIENT" < "$REPORT_FILE"
        echo -e "${GREEN}Report emailed to: $EMAIL_RECIPIENT${NC}"
    fi
}

# Script execution
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
