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


# Locker System Project Setup Guide for Windows with ESP32

This guide will walk you through the setup process for the locker system project on Windows with ESP32 support.

## Prerequisites

- Python 3.11.x
- ESP32 microcontroller

## Setup Instructions

### 1. Install Python 3.11.x

Download and install Python 3.11.x from the [official Python website](https://www.python.org/downloads/).

Make sure to check the box that says "Add Python to PATH" during installation.

### 2. Install CP210x USB to UART Bridge Driver

1. Download the CP210x USB to UART Bridge VCP Driver from the [Silicon Labs website](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
2. Extract the downloaded ZIP file
3. Run the installer (usually named `CP210xVCPInstaller_x64.exe` for 64-bit Windows)
4. Follow the on-screen instructions to complete the installation
5. Restart your computer after installation

### 3. Install Thonny IDE

1. Download Thonny IDE from the [official website](https://thonny.org/)
2. Run the installer
3. Follow the on-screen instructions to complete the installation

### 4. Connect ESP32 to Thonny

1. Connect your ESP32 to your computer using a USB cable
2. Open Thonny IDE
3. Click on "Tools" in the menu bar, then select "Options"
4. In the Options window, select the "Interpreter" tab
5. From the dropdown menu, select "MicroPython (ESP32)"
6. In the "Port" dropdown, select the COM port assigned to your ESP32 (usually something like COM3, COM4, etc.)
   - If you're unsure which port, look in Device Manager under "Ports (COM & LPT)" for a device with "Silicon Labs" or "CP210x" in its name
7. Click "OK" to save the settings
8. The bottom right corner of Thonny should now show "MicroPython (ESP32)" indicating successful connection
