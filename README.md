# AutoCalBridge (ACB)

**Automated Calibration for Multi-Vendor Instruments**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## Overview

AutoCalBridge is a standalone, distributable software tool for automated calibration of multi-vendor measurement equipment. It provides a GUI-based interface for controlling instruments from Keysight, Tektronix, Rohde & Schwarz, and Keithley, with extensible support for additional vendors.

**Key Features:**

- **Multi-Vendor Support** — Keysight, Tektronix, Rohde & Schwarz, Keithley
- **GUI Interface** — Easy-to-use Tkinter-based operator interface
- **External Configuration** — config.json for instrument addresses, test points, and tolerances
- **Automated Reports** — CSV output with PASS/FAIL status and timestamps
- **Standalone Executable** — Deploy as a single .exe file (via PyInstaller)
- **Single/Dual Machine** — Works with local simulators or remote instruments over network

---

## Quick Start

### Prerequisites

- Python 3.10 or higher
- VISA runtime (Keysight IO Libraries or pyvisa-py backend)

### Installation

```bash
# Clone the repository
git clone https://github.com/SysEngg-786/autocalbridge.git
cd autocalbridge

# Install dependencies
pip install -r requirements.txt

# Copy and configure the template
cp config.template.json config.json
# Edit config.json with your instrument details