# 🧭 JDash System Overview  
**By Biomarker Development Group, INM-7**
JDash is a Django-based web platform developed by the **Biomarker Development Group, INM-7**, for managing digital health studies conducted through **JTrack** mobile applications. It provides a unified interface to design, monitor, and manage behavioral and sensor-based research studies.

The system connects mobile app data with researcher-controlled dashboards. Its main goal is to simplify the lifecycle of digital studies — from **study setup and survey design** to **subject enrollment, progress monitoring, and data validation**.

# 🚀 JTrack Dashboard — Deployment Instructions

Comprehensive guide to deploying the **JTrack Dashboard (JDash)** both **locally** for development and **in production** using **Apache + mod_wsgi**.

---

## 🧩 Local Deployment (Development)

Local deployment is intended for **development**, **testing**, and **debugging**.  
Django’s built-in development server is used for this mode.

### Requirements

Install system prerequisites:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip git
```

Clone the repository:

```bash
git clone https://github.com/mamaka7/JTrack-dashboard.git
cd JTrack-dashboard
```

---

### Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

(Optional setup script):

```bash
chmod +x setup.sh
./setup.sh
```

---

### Database Setup (MariaDB)

JDash uses **MariaDB** for both development and production.

Ensure MariaDB is running:

```bash
sudo systemctl enable mariadb
sudo systemctl start mariadb
```

Run the MariaDB setup script from the project root:

```bash
chmod +x setup_mysql.sh
./setup_mysql.sh
```

This script typically:
- Creates a database (e.g., `jtrack`)
- Creates a database user with privileges
- Optionally imports schema/data from `jtrack.sql`

Then apply Django migrations:

```bash
python manage.py migrate
```

---

### Run the Development Server

Start Django’s built-in server:

```bash
python manage.py runserver
```

Open in your browser:

👉 **http://127.0.0.1:8000**

In this mode:
- Debug is active  
- Auto-reload is enabled  
- No external web server is required  

---

## 🌐 Production Deployment (Apache + mod_wsgi)

This configuration is recommended for real-world hosting.

---

### Prerequisites

Install required packages:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip                  apache2 libapache2-mod-wsgi-py3 git
```

---

### Clone Application into Server Directory

Example installation directory: `/srv/jdash`

```bash
sudo mkdir -p /srv/jdash
sudo chown $USER:$USER /srv/jdash
cd /srv/jdash

git clone https://github.com/mamaka7/JTrack-dashboard.git .
```

---

### Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Database Setup (MariaDB)

Run the setup script:

```bash
cd /srv/jdash
chmod +x setup_mysql.sh
./setup_mysql.sh
```

(or, if named `mysql_set.sh`):

```bash
chmod +x mysql_set.sh
./mysql_set.sh
```

This will:
- Create the MariaDB database (e.g., `jtrack`)
- Create a DB user and grant privileges
- Optionally import the base schema (`jtrack.sql`)

---

### Django Database Configuration

Edit `jdash/settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",  # MariaDB-compatible
        "NAME": "jtrack",
        "USER": "jtrack_user",
        "PASSWORD": "securepassword",
        "HOST": "localhost",
        "PORT": "3306",
    }
}
```

Disable DEBUG mode:

```python
DEBUG = False
```

Set Allowed Hosts:

```python
ALLOWED_HOSTS = ["your-domain.com", "127.0.0.1"]
```

Apply migrations:

```bash
python manage.py migrate
```

---

### Collect Static Files

Edit settings:

```python
STATIC_ROOT = "/srv/jdash/static_collected"
```

Then collect static assets:

```bash
python manage.py collectstatic
```

---

### Configure Apache (mod_wsgi)

Create a new Apache config file:  
`/etc/apache2/sites-available/jdash.conf`

```apache
<VirtualHost *:80>
    ServerName your-domain.com

    Alias /static/ /srv/jdash/static_collected/
    <Directory /srv/jdash/static_collected/>
        Require all granted
    </Directory>

    <Directory /srv/jdash/jdash>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    WSGIDaemonProcess jdash python-path=/srv/jdash                       python-home=/srv/jdash/venv
    WSGIProcessGroup jdash
    WSGIScriptAlias / /srv/jdash/jdash/wsgi.py

    ErrorLog ${APACHE_LOG_DIR}/jdash_error.log
    CustomLog ${APACHE_LOG_DIR}/jdash_access.log combined
</VirtualHost>
```

Enable the site and module:

```bash
sudo a2enmod wsgi
sudo a2ensite jdash.conf
sudo systemctl reload apache2
```

(Optional) disable the default site:

```bash
sudo a2dissite 000-default.conf
sudo systemctl reload apache2
```

---

### 🔒 Enable HTTPS (Recommended)

Use Let’s Encrypt for automatic SSL certificates:

```bash
sudo apt install certbot python3-certbot-apache
sudo certbot --apache -d your-domain.com
```

---


