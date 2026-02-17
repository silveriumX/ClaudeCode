# 🤖 FinanceBot

> Enterprise-grade Telegram bot for financial request management with Google Sheets integration

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [Project Structure](#-project-structure)
- [Technology Stack](#-technology-stack)
- [Deployment](#-deployment)
- [Development](#-development)
- [Contributing](#-contributing)
- [Support](#-support)

---

## ✨ Features

### Core Functionality
- ✅ **Multi-currency support:** RUB, BYN, KZT, CNY, USDT
- ✅ **Request lifecycle management:** Create → Edit → Pay → Track
- ✅ **Role-based access control:** Owner, Manager, Executor, Report
- ✅ **QR code support:** Upload and manage QR codes for CNY payments
- ✅ **Receipt management:** Attach receipts to paid requests
- ✅ **Pagination:** Efficient browsing of large request lists
- ✅ **Fact expenses:** Direct expense reporting for accountants

### User Experience
- 💬 **Conversational interface:** Step-by-step guided flows
- ⌨️ **Quick access buttons:** Persistent keyboard for main actions
- 📱 **Mobile-friendly:** Optimized for mobile Telegram clients
- 🔔 **Real-time updates:** Instant notifications and status changes
- 🌐 **Multi-language:** Support for Cyrillic and Latin characters

### Technical Features
- 🔒 **Secure:** OAuth2, environment variables, encrypted credentials
- 📊 **Google Sheets integration:** Acts as a relational database
- 💾 **Google Drive integration:** File storage for QR codes and receipts
- 🚀 **Production-ready:** systemd service, logging, error handling
- 📈 **Scalable:** Designed for growth and extensibility

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- Google Cloud Platform account
- Telegram Bot Token
- VPS (for production deployment)

### Installation

```bash
# 1. Clone repository
git clone https://github.com/yourusername/finance_bot.git
cd finance_bot

# 2. Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Edit with your credentials

# 5. Setup Google credentials
# Place service_account.json in project root

# 6. Run bot
python bot.py
```

### Configuration

Edit `.env` file:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Google Sheets
GOOGLE_SHEETS_ID=your_sheet_id
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json

# Google Drive (optional, for QR codes)
GOOGLE_DRIVE_CLIENT_ID=your_client_id
GOOGLE_DRIVE_CLIENT_SECRET=your_client_secret
GOOGLE_DRIVE_REFRESH_TOKEN=your_refresh_token
GOOGLE_DRIVE_FOLDER_ID=your_folder_id
```

---

## 📚 Documentation

### Getting Started
- 📖 [**Quick Start Guide**](docs/user_guides/QUICK_START.md) - Get up and running in 5 minutes
- 🔧 [**Configuration Guide**](docs/user_guides/CONFIGURATION.md) - Detailed configuration options
- 🐛 [**Troubleshooting Guide**](docs/troubleshooting/TROUBLESHOOTING_GUIDE.md) - Common issues and solutions

### Technical Documentation
- 🏗️ [**Architecture Overview**](ARCHITECTURE.md) - System design and components
- 📐 [**API Reference**](docs/api/API_REFERENCE.md) - Function and class documentation
- 🔐 [**Security Guidelines**](docs/security/SECURITY.md) - Security best practices

### Deployment
- 🚀 [**Deployment Guide**](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- 🐧 [**VPS Setup**](docs/deployment/VPS_SETUP.md) - Server configuration
- 🔄 [**CI/CD Setup**](docs/deployment/CICD.md) - Automation and testing

### Development
- 🤝 [**Contributing Guide**](CONTRIBUTING.md) - How to contribute
- 📝 [**Changelog**](CHANGELOG.md) - Version history
- 🎓 [**Skills Required**](SKILLS_REQUIRED.md) - Developer knowledge base

### Google Cloud
- ☁️ [**Google Sheets Setup**](docs/google/GOOGLE_SHEETS_SETUP.md) - Sheets API configuration
- 💾 [**Google Drive Setup**](docs/google/GOOGLE_DRIVE_SETUP.md) - Drive API configuration
- 📊 [**Sheets Structure**](docs/google/SHEETS_STRUCTURE.md) - Database schema

---

## 📁 Project Structure

```
FinanceBot/
├── src/                      # Source code
│   ├── bot.py               # Main application
│   ├── config.py            # Configuration
│   ├── sheets.py            # Google Sheets manager
│   ├── drive_manager.py     # Google Drive manager
│   ├── handlers/            # Command handlers
│   │   ├── request.py       # Request creation
│   │   ├── payment.py       # Payment processing
│   │   ├── edit_handlers.py # Request editing
│   │   ├── menu.py          # Menu navigation
│   │   └── ...
│   └── utils/               # Utilities
│       ├── auth.py          # Authentication
│       ├── formatters.py    # Data formatting
│       └── categories.py    # Categorization
│
├── scripts/                  # Helper scripts
│   ├── deployment/          # Deployment scripts
│   ├── monitoring/          # Health checks
│   ├── testing/             # Test helpers
│   └── maintenance/         # Maintenance tasks
│
├── tests/                    # Tests
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── e2e/                 # End-to-end tests
│
├── docs/                     # Documentation
│   ├── architecture/        # Architecture docs
│   ├── api/                 # API reference
│   ├── deployment/          # Deployment guides
│   ├── user_guides/         # User documentation
│   └── troubleshooting/     # Problem solving
│
├── requirements/             # Dependencies
│   ├── base.txt             # Core dependencies
│   ├── dev.txt              # Development tools
│   └── prod.txt             # Production extras
│
├── .github/                  # GitHub configuration
│   └── workflows/           # CI/CD pipelines
│
├── README.md                 # This file
├── CHANGELOG.md              # Version history
├── CONTRIBUTING.md           # Contribution guide
├── ARCHITECTURE.md           # Architecture overview
├── DEPLOYMENT_GUIDE.md       # Deployment instructions
├── SKILLS_REQUIRED.md        # Developer guide
├── .env.example              # Environment template
├── .gitignore                # Git ignore rules
├── .editorconfig             # Editor configuration
└── .pre-commit-config.yaml   # Pre-commit hooks
```

---

## 🛠️ Technology Stack

### Core
- **Python 3.10+** - Programming language
- **python-telegram-bot 21.7** - Telegram Bot API
- **gspread 6.0** - Google Sheets integration
- **google-api-python-client** - Google Drive integration

### Infrastructure
- **Ubuntu 22.04** - Operating system
- **systemd** - Service management
- **journalctl** - Logging
- **Git** - Version control

### Development
- **pytest** - Testing framework
- **black** - Code formatter
- **flake8** - Linter
- **mypy** - Type checker
- **pre-commit** - Git hooks

---

## 🚀 Deployment

### Production VPS

**Server Details:**
- **IP:** 195.177.94.189
- **Path:** `/root/finance_bot`
- **Service:** `finance_bot`
- **OS:** Ubuntu 22.04 LTS

### Quick Deploy

```bash
# On VPS
cd /root/finance_bot
git pull origin main
systemctl restart finance_bot
systemctl status finance_bot
```

### Service Management

```bash
# Check status
systemctl status finance_bot

# View logs
journalctl -u finance_bot -f

# Restart
systemctl restart finance_bot

# Stop
systemctl stop finance_bot

# Start
systemctl start finance_bot
```

### Health Check

```bash
# Is bot running?
systemctl is-active finance_bot

# Recent logs
journalctl -u finance_bot -n 50 --no-pager

# Process count
ps aux | grep "finance_bot.*bot.py" | grep -v grep | wc -l
```

**📖 Full deployment guide:** [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## 💻 Development

### Setup Development Environment

```bash
# Clone and setup
git clone https://github.com/yourusername/finance_bot.git
cd finance_bot
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements/dev.txt

# Install pre-commit hooks
pre-commit install
```

### Code Quality

```bash
# Format code
black .

# Sort imports
isort .

# Lint
flake8 .

# Type check
mypy .

# Run all checks
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test
pytest tests/unit/test_sheets.py::test_get_user
```

### Project Reorganization

```bash
# Analyze current structure and plan reorganization
python reorganize_project.py --dry-run

# Execute reorganization
python reorganize_project.py
```

---

## 🤝 Contributing

We welcome contributions! Please see:

- [**Contributing Guide**](CONTRIBUTING.md) - How to contribute
- [**Code of Conduct**](CODE_OF_CONDUCT.md) - Community guidelines
- [**Skills Required**](SKILLS_REQUIRED.md) - Developer prerequisites

### Quick Contribution Guide

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linters
5. Commit (`git commit -m 'feat: add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open Pull Request

---

## 📊 Project Status

### Current Version
**v2.5.0** - February 13, 2026

### Recent Updates
- ✅ Fixed encoding issue in user authentication
- ✅ Complete project reorganization
- ✅ Comprehensive documentation
- ✅ Deployment automation

### Statistics
- **Users:** ~100
- **Requests/day:** ~500
- **Uptime:** 99.5%
- **Response time:** <2s

---

## 🆘 Support

### Documentation
- 📖 [Full documentation](docs/)
- 🐛 [Troubleshooting](docs/troubleshooting/TROUBLESHOOTING_GUIDE.md)
- ❓ [FAQ](docs/FAQ.md)

### Getting Help
- 💬 [GitHub Discussions](https://github.com/yourusername/finance_bot/discussions)
- 🐛 [Issue Tracker](https://github.com/yourusername/finance_bot/issues)
- 📧 Email: support@example.com

### Common Issues

1. **Bot not responding** → Check service status: `systemctl status finance_bot`
2. **Google Sheets error** → Verify service account permissions
3. **Encoding issues** → Ensure UTF-8 encoding in all files

---

## 📜 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 👥 Authors & Contributors

- **Lead Developer** - *Initial work and maintenance*
- **Contributors** - See [CONTRIBUTORS.md](CONTRIBUTORS.md)

---

## 🙏 Acknowledgments

- python-telegram-bot community
- Google Cloud Platform
- All contributors and users

---

## 📞 Contact

- **Project Link:** [https://github.com/yourusername/finance_bot](https://github.com/yourusername/finance_bot)
- **Issues:** [https://github.com/yourusername/finance_bot/issues](https://github.com/yourusername/finance_bot/issues)
- **VPS:** 195.177.94.189

---

**Made with ❤️ for efficient financial management**

**Last Updated:** February 13, 2026
**Version:** 2.5.0
