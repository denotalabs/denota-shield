#!/bin/bash

git pull origin main  # or master, depending on your default branch

# Restart your Flask app
# This could be done using systemd, Supervisor, or other methods depending on your setup
sudo systemctl restart shield
