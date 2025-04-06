# Locker System Project Setup Guide for Windows

This guide will walk you through the setup process for the locker system project on Windows.

## Prerequisites

- Python 3.11.x

## Setup Instructions

### 1. Install Python 3.11.x

Download and install Python 3.11.x from the [official Python website](https://www.python.org/downloads/).

Make sure to check the box that says "Add Python to PATH" during installation.

### 2. Navigate to Project Directory

Open Command Prompt or PowerShell and navigate to your project directory:

```
cd path\to\locker-system-project
```

### 3. Create a Virtual Environment

Create a virtual environment in your project directory:

```
python -m venv .venv
```

### 4. Activate the Virtual Environment

Activate the virtual environment:

```
cd .venv\Scripts\activate
```

When activated, you should see `(.venv)` at the beginning of your command prompt.

### 5. Install Required Packages

Install all required packages using pip:

```
pip install -r requirements.txt
```

### 6. Run the Application

Start the locker system application:

```
py run.py
```

## Troubleshooting

- If you encounter `'python' is not recognized` error, make sure Python is added to your PATH
- If you get permission errors, try running Command Prompt as Administrator
- For package installation issues, verify your internet connection and that the `requirements.txt` file exists in the project directory
