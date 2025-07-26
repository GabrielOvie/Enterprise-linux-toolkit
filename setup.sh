#!/bin/bash

#################################################################
# Enterprise Linux Toolkit - Quick Setup Script
# Author: Gabriel - Senior Linux Systems Administrator
# Purpose: Automated installation and configuration
#################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}"
    echo "=============================================================="
    echo "    Enterprise Linux Toolkit - Quick Setup"
    echo "    Author: Gabriel - Senior Linux Systems Administrator"
    echo "=============================================================="
    echo -e "${NC}"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root or with sudo"
        echo "Usage: sudo ./setup.sh"
        exit 1
    fi
}

install_dependencies() {
    print_status "Installing system dependencies..."
    
    # Detect package manager
    if command -v dnf >/dev/null 2>&1; then
        PKG_MANAGER="dnf"
    elif command -v yum >/dev/null 2>&1; then
        PKG_MANAGER="yum"
    else
        print_error "No supported package manager found (dnf/yum)"
        exit 1
    fi
    
    # Install required packages
    $PKG_MANAGER install -y python3 python3-pip rsync mailx smartmontools
    
    # Install Python dependencies
    if [ -f requirements.txt ]; then
        pip3 install -r requirements.txt
        print_status "Python dependencies installed"
    fi
}

setup_directories() {
    print_status "Setting up directories..."
    
    # Create log directory
    mkdir -p /var/log/enterprise-toolkit
    chmod 755 /var/log/enterprise-toolkit
    
    # Create reports directory
    mkdir -p /var/reports/system-health
    chmod 755 /var/reports/system-health
    
    # Create backup directory
    mkdir -p /var/backups/toolkit-data
    chmod 750 /var/backups/toolkit-data
    
    print_status "Directories created successfully"
}

configure_toolkit() {
    print_status "Configuring toolkit..."
    
    # Copy configuration template
    if [ ! -f config/toolkit.conf ]; then
        cp config/toolkit.conf.example config/toolkit.conf
        print_status "Configuration template copied to config/toolkit.conf"
        print_warning "Please edit config/toolkit.conf to customize settings"
    fi
    
    # Make scripts executable
    find . -name "*.sh" -type f -exec chmod +x {} \;
    find . -name "*.py" -type f -exec chmod +x {} \;
    
    print_status "Scripts made executable"
}

setup_cron_jobs() {
    print_status "Setting up scheduled tasks..."
    
    # Create cron entries
    cat > /tmp/toolkit-cron << 'EOF'
# Enterprise Linux Toolkit - Automated Tasks
# Daily health check at 6 AM
0 6 * * * /root/enterprise-linux-toolkit/health-checks/rhel-healthcheck.sh >/dev/null 2>&1

# Daily HTML dashboard at 6:30 AM
30 6 * * * /root/enterprise-linux-toolkit/health-checks/system_metrics_report.py -o /var/reports/system-health/dashboard-$(date +\%Y\%m\%d).html >/dev/null 2>&1

# Weekly comprehensive report (Sundays at 7 AM)
0 7 * * 0 /root/enterprise-linux-toolkit/health-checks/rhel-healthcheck.sh && /root/enterprise-linux-toolkit/health-checks/system_metrics_report.py -o /var/reports/system-health/weekly-$(date +\%Y\%m\%d).html --email >/dev/null 2>&1

# Daily backup monitoring at 8 AM
0 8 * * * /root/enterprise-linux-toolkit/backup-engine/rsync_backup_monitor.py >/dev/null 2>&1

# Disk cleanup check every 6 hours
0 */6 * * * /root/enterprise-linux-toolkit/health-checks/auto-disk-cleaner.sh >/dev/null 2>&1
EOF

    # Install cron jobs
    crontab -l > /tmp/current-cron 2>/dev/null || echo "" > /tmp/current-cron
    cat /tmp/current-cron /tmp/toolkit-cron | crontab -
    rm /tmp/toolkit-cron /tmp/current-cron
    
    print_status "Cron jobs installed successfully"
}

test_installation() {
    print_status "Testing installation..."
    
    # Test main health check script
    if ./health-checks/rhel-healthcheck.sh --help >/dev/null 2>&1; then
        print_status "Health check script: OK"
    else
        print_warning "Health check script may have issues"
    fi
    
    # Test Python dashboard
    if python3 health-checks/system_metrics_report.py --help >/dev/null 2>&1; then
        print_status "Dashboard generator: OK"
    else
        print_warning "Dashboard generator may have issues"
    fi
    
    print_status "Installation test completed"
}

main() {
    print_header
    
    # Get current directory
    INSTALL_DIR=$(pwd)
    print_status "Installing Enterprise Linux Toolkit from: $INSTALL_DIR"
    
    # Run installation steps
    check_root
    install_dependencies
    setup_directories
    configure_toolkit
    
    # Ask about cron jobs
    echo -e "${YELLOW}Do you want to install automated cron jobs? (y/n):${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        setup_cron_jobs
    fi
    
    test_installation
    
    echo -e "${GREEN}"
    echo "=============================================================="
    echo "    Installation Complete!"
    echo "=============================================================="
    echo -e "${NC}"
    echo "Next steps:"
    echo "1. Edit config/toolkit.conf to customize settings"
    echo "2. Run your first health check: ./health-checks/rhel-healthcheck.sh"
    echo "3. Generate HTML dashboard: ./health-checks/system_metrics_report.py"
    echo "4. View documentation: cat docs/installation.md"
    echo ""
    echo -e "${BLUE}Enterprise Linux Toolkit is ready for use!${NC}"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
