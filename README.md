# OdooConf Tool

![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-GPLv2-green.svg)

CLI tool for managing and optimizing Odoo configurations (`odoo.conf`).

## 📦 Installation

### Option 1: Install with pip
```bash
pip install git+https://github.com/Alitux/odooconf.git
```

### Option 2: Install with pipx (recommended for isolation)
```bash
pipx install git+https://github.com/Alitux/odooconf.git
```
### 🔧 Key Features

- 🛠 Generation of optimized base configurations
- 🔍 Automatic detection of addons paths
- 👁 Real-time monitoring with watchdog
- ⚡ Automatic optimization of server parameters
- 🔒 Secure credential management

## 🚀 Basic Usage

### Generate initial configuration
```bash
odooconf new /path/to/destination
```
- users: Number of concurrent users the server is expected to have (default: 2)

### Find addons and update paths

```bash
odooconf paths /path/to/addons --odoo-conf /path/to/odoo.conf --internal-path /mnt/odoo/addons
```

- /path/to/addons: Path on the filesystem where addons will be searched (host).

- --odoo-conf: Path to the file or folder containing the odoo.conf to be updated.

- --internal-path: (Optional) Internal path to be used instead of the host path when writing to odoo.conf. Ideal for containerized environments (e.g., Docker).

### Optimize server for 50 users

```bash
odooconf server /path/to/odoo.conf --users 50 --auto-ram
```

## 🔧 Advanced Server Configuration (`server`)

The `server` command automatically optimizes performance parameters in `odoo.conf`:

### 🖥️ Hardware Parameters
```bash
--users N       # Calculates workers: (users/6) + 1 (required for automatic calculation)
--ram X         # RAM total in GB (e.g., --ram 8 for 8GB)
--auto-ram      # Automatically detects RAM (overrides --ram if present)
```
## ⏱️ Time Limits
```bash
--time-cpu N    # CPU limit per request (default: 60s)
--time-real N   # Maximum real time per request (default: 120s)
```
## 🔐 Database Configuration
```bash
--db-host HOST  # PostgreSQL host (default: db)
--db-port PORT  # Port (default: 5432)
--db-user USER  # User (default: odoo)
--db-pass PASS  # Password (default: odoo)
--hide-db       # Hide the list of databases (web/database/selector)
```
## 🔄 Automatic Values
With --auto-ram or --ram, the following are calculated:

- limit_memory_soft: 75% RAM/worker
- limit_memory_hard: 95% RAM/worker
- workers: Based on --users (default: 2)

## 🔒 Security
The admin password can be generated with:
```bash
--admin-passwd PASS  # Generates PBKDF2 hash (does not store plain text)
```
## 💻 Complete Example
```bash
odooconf server /etc/odoo.conf \
  --users 100 \
  --auto-ram \
  --time-cpu 90 \
  --time-real 180 \
  --admin-passwd "S3cr3tP@ss" \
  --db-host db-prod \
  --db-port 5433
```

## 📄 License

This project is licensed under the GNU GPLv2.

## 🌍 Repository

git+https://github.com/Alitux/odooconf

## 🤝 Contributions

Contributions are accepted via merge requests in the Github repository.

## 💡 Support

Report issues at: https://github.com/Alitux/odooconf/issues
