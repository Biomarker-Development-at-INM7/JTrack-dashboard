#!/bin/bash

echo "Installing MySQL using Homebrew..."
brew install mysql

echo "Starting MySQL service..."
brew services start mysql

echo "Waiting for MySQL to start..."
sleep 5

echo "Setting up MySQL root user..."
mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'root123'; FLUSH PRIVILEGES;"

echo "Creating new MySQL user and database..."
mysql -u root -p'root123' <<EOF
CREATE DATABASE jtrack;
CREATE USER 'jtrackuser'@'localhost' IDENTIFIED BY 'jtrackuser@JDASH123';
GRANT ALL PRIVILEGES ON jtrack.* TO 'jtrackuser'@'localhost';
FLUSH PRIVILEGES;
EOF

echo "MySQL setup completed!"

