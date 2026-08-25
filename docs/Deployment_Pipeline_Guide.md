# Document B — Deployment Pipeline Guide (Updated)

```
File: Deployment_Pipeline_Guide.md
Path: /Project_Root/Documentation/Deployment_Pipeline_Guide.md
```

---

# Deployment Pipeline Guide
## Packaging, Configuring, and Delivering Client-Ready Calibration Solutions

**Version:** 2.0
**Purpose:** Taking a working Python script and making it client-deliverable — from packaging to professional handover.
**Target Audience:** Automation developers and freelancers preparing software for commercial deployment.

---

## 1. Why Deployment Matters

**1.1.** Clients expect professional software delivery, not raw scripts.

**1.1.1.** Non-technical operators cannot install Python or run `pip install`.

**1.1.2.** Clients need double-click executables that work without terminal interaction.

**1.1.3.** Hardware changes (IP addresses, instrument models) must be adjustable without code modification.

**1.1.4.** Professional delivery builds trust and justifies higher rates.

**1.2.** **Client Expectations — What They Want:**

| **Expectation** | **Why It Matters** |
|-----------------|-------------------|
| Single executable file | No installation friction |
| External configuration | Field-adjustable without coding |
| Professional reports | Ready for compliance/audit |
| Clear documentation | Operational independence |
| Error handling | No crashes — graceful failures |

**1.3.** **Deployment Goals:**

**1.3.1.** Package the Python application into a standalone `.exe` file.

**1.3.2.** Externalize all configuration parameters into `config.json`.

**1.3.3.** Implement production-grade error handling and logging.

**1.3.4.** Deliver a complete handover package with documentation.

**Further Reading:**
- PyInstaller Documentation: https://pyinstaller.org/en/stable/
- Python Packaging User Guide: https://packaging.python.org/

---

## 2. Packaging with PyInstaller

**2.1.** **What PyInstaller Does:**

**2.1.1.** Bundles Python interpreter, all dependencies, and your script into a single executable.

**2.1.2.** Creates a `.exe` file that runs on Windows without Python installed.

**2.1.3.** Supports GPL with a special exception permitting free commercial use of compiled executables.

**2.2.** **Installation:**

```bash
pip install pyinstaller
```

**2.3.** **Basic Compilation Command:**

```bash
pyinstaller --onefile --windowed --name="AutoCalBridge" src/main.py
```

**2.3.1.** Command breakdown:

| **Argument** | **Purpose** |
|--------------|-------------|
| `--onefile` | Creates a single `.exe` (not a folder) |
| `--windowed` | Suppresses the terminal window (use for GUI apps) |
| `--name` | Sets the output filename |
| `src/main.py` | Your entry-point Python script |

**2.4.** **Recommended Compilation for AutoCalBridge:**

```bash
pyinstaller --onefile --console --name="AutoCalBridge" --hidden-import=pyvisa --hidden-import=pyvisa-py --add-data="config.template.json;." src/main.py
```

**2.4.1.** Use `--console` for logging visibility during client runs.

**2.4.2.** Include PyVISA hidden imports to prevent missing dependency errors.

**2.4.3.** Add `config.template.json` as a data file.

**2.5.** **Directory Structure After Compilation:**

| **Path** | **Description** |
|----------|-----------------|
| `dist/AutoCalBridge.exe` | Compiled executable — deploy this file |
| `build/` | Intermediate files — not needed for deployment |
| `AutoCalBridge.spec` | PyInstaller specification file — optional |

**2.6.** **Common PyInstaller Errors and Fixes:**

| **Error** | **Cause** | **Resolution** |
|-----------|-----------|----------------|
| `ModuleNotFoundError: pyvisa` | Missing hidden import | Add `--hidden-import=pyvisa` |
| `FileNotFoundError: config.json` | File not bundled | Use `--add-data "config.template.json;."` |
| `PermissionError` | Antivirus blocking | Add to antivirus exceptions |
| `PyInstaller not found` | Not installed | `pip install pyinstaller` |

**Further Reading:**
- PyInstaller Manual: https://pyinstaller.org/en/stable/usage.html
- Hidden Import Guide: https://pyinstaller.org/en/stable/spec-files.html

---

## 3. External Configuration with config.json (Updated for Two-Ended)

**3.1.** **Why External Configuration?**

**3.1.1.** Clients can change settings without touching code.

**3.1.2.** No rebuild required for IP address changes.

**3.1.3.** Operators can adjust test parameters on the factory floor.

**3.1.4.** Two-ended calibration requires separate configuration for source and DUT.

**3.2.** **Updated config.template.json (Two-Ended):**

```json
{
  "source": {
    "visa_address": "TCPIP0::192.168.1.100::hislip0::INSTR",
    "vendor": "Keysight",
    "instrument_model": "34461A",
    "settle_delay_ms": 100
  },
  "dut": {
    "visa_address": "TCPIP0::192.168.1.101::hislip0::INSTR",
    "vendor": "Keysight",
    "instrument_model": "34461A"
  },
  "calibration": {
    "test_points_volts": [1.000, 2.500, 5.000, 10.000],
    "pass_tolerance_volts": 0.005,
    "operator_name": "Default_Operator"
  },
  "general": {
    "report_directory": "Reports",
    "logging_level": "INFO",
    "connection_mode": "network",
    "use_sync": true,
    "use_error_checking": true
  }
}
```

**3.2.1.** Field definitions:

| **Field** | **Type** | **Description** | **Required** |
|-----------|----------|-----------------|--------------|
| `source.visa_address` | string | VISA address of the reference standard | Yes |
| `source.vendor` | string | Vendor of the source instrument | Yes |
| `source.instrument_model` | string | Model of the source instrument | Yes |
| `source.settle_delay_ms` | number | Delay after source command (milliseconds) | No |
| `dut.visa_address` | string | VISA address of the unit under test | Yes |
| `dut.vendor` | string | Vendor of the DUT instrument | Yes |
| `dut.instrument_model` | string | Model of the DUT instrument | Yes |
| `calibration.test_points_volts` | array of numbers | Test points in volts | Yes |
| `calibration.pass_tolerance_volts` | number | PASS/FAIL tolerance | Yes |
| `calibration.operator_name` | string | Operator identifier for logs | No |
| `general.use_sync` | boolean | Enable `*OPC?` synchronization | No |
| `general.use_error_checking` | boolean | Enable `*ESR?` and `SYST:ERR?` | No |

**3.3.** **Loading config.json in Python (Updated):**

```python
import os
import json

DEFAULT_CONFIG = {
    "source": {
        "visa_address": "TCPIP0::localhost::hislip0::INSTR",
        "vendor": "Keysight",
        "instrument_model": "34461A",
        "settle_delay_ms": 100
    },
    "dut": {
        "visa_address": "TCPIP0::localhost::hislip0::INSTR",
        "vendor": "Keysight",
        "instrument_model": "34461A"
    },
    "calibration": {
        "test_points_volts": [1.0, 2.5, 5.0, 10.0],
        "pass_tolerance_volts": 0.005,
        "operator_name": "Default_Operator"
    },
    "general": {
        "report_directory": "Reports",
        "logging_level": "INFO",
        "connection_mode": "network",
        "use_sync": True,
        "use_error_checking": True
    }
}

CONFIG_FILE = "config.json"

def load_config():
    """Load configuration from config.json with fallback defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                user_config = json.load(f)
            return user_config
        except Exception as e:
            print(f"Config error: {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        print("config.json not found. Using defaults.")
        return DEFAULT_CONFIG.copy()
```

---

## 4. Schema Validation (Updated for Two-Ended)

**4.1.** **Why Validate?**

**4.1.1.** Prevents runtime crashes from malformed config.

**4.1.2.** Gives clear error messages to operators.

**4.1.3.** Ensures required fields are present.

**4.2.** **Updated Validation Function:**

```python
def validate_config(config):
    """Validate configuration dictionary against required schema."""
    errors = []
    
    # Check source section
    if "source" not in config:
        errors.append("Missing 'source' section")
    else:
        source = config["source"]
        if "visa_address" not in source:
            errors.append("source.visa_address is required")
        if "vendor" not in source:
            errors.append("source.vendor is required")
        if "instrument_model" not in source:
            errors.append("source.instrument_model is required")
    
    # Check DUT section
    if "dut" not in config:
        errors.append("Missing 'dut' section")
    else:
        dut = config["dut"]
        if "visa_address" not in dut:
            errors.append("dut.visa_address is required")
        if "vendor" not in dut:
            errors.append("dut.vendor is required")
        if "instrument_model" not in dut:
            errors.append("dut.instrument_model is required")
    
    # Check calibration section
    if "calibration" not in config:
        errors.append("Missing 'calibration' section")
    else:
        cal = config["calibration"]
        if "test_points_volts" not in cal:
            errors.append("calibration.test_points_volts is required")
        elif not isinstance(cal["test_points_volts"], list) or len(cal["test_points_volts"]) == 0:
            errors.append("calibration.test_points_volts must be a non-empty list")
        if "pass_tolerance_volts" not in cal:
            errors.append("calibration.pass_tolerance_volts is required")
        elif not isinstance(cal["pass_tolerance_volts"], (int, float)):
            errors.append("calibration.pass_tolerance_volts must be a number")
        elif cal["pass_tolerance_volts"] < 0:
            errors.append("calibration.pass_tolerance_volts must be positive")
    
    return errors
```

---

## 5. Production-Grade Code Skeleton (Updated)

**5.1.** **Complete Production Script Template:**

```python
#!/usr/bin/env python3
"""
File: src/main.py
Path: /Project_Root/src/main.py
Purpose: Production-grade calibration automation with two-ended support.
"""

import os
import sys
import json
import csv
import time
import logging
from datetime import datetime
import pyvisa
from pyvisa.errors import VisaIOError

# Constants
CONFIG_FILE = "config.json"

# =============================================================================
# Configuration Management
# =============================================================================

DEFAULT_CONFIG = {
    "source": {
        "visa_address": "TCPIP0::localhost::hislip0::INSTR",
        "vendor": "Keysight",
        "instrument_model": "34461A",
        "settle_delay_ms": 100
    },
    "dut": {
        "visa_address": "TCPIP0::localhost::hislip0::INSTR",
        "vendor": "Keysight",
        "instrument_model": "34461A"
    },
    "calibration": {
        "test_points_volts": [1.0, 2.5, 5.0, 10.0],
        "pass_tolerance_volts": 0.005,
        "operator_name": "Default_Operator"
    },
    "general": {
        "report_directory": "Reports",
        "logging_level": "INFO",
        "connection_mode": "network",
        "use_sync": True,
        "use_error_checking": True
    }
}

def load_config():
    """Load configuration with fallback defaults."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Config load error: {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        return DEFAULT_CONFIG.copy()

def validate_config(config):
    """Validate configuration."""
    errors = []
    if "source" not in config:
        errors.append("Missing 'source' section")
    else:
        if "visa_address" not in config["source"]:
            errors.append("source.visa_address is required")
    if "dut" not in config:
        errors.append("Missing 'dut' section")
    else:
        if "visa_address" not in config["dut"]:
            errors.append("dut.visa_address is required")
    if "calibration" not in config:
        errors.append("Missing 'calibration' section")
    else:
        if "test_points_volts" not in config["calibration"]:
            errors.append("calibration.test_points_volts is required")
        if "pass_tolerance_volts" not in config["calibration"]:
            errors.append("calibration.pass_tolerance_volts is required")
    return errors

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging(level="INFO"):
    """Configure logging to both console and file."""
    log_dir = "Logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"autocalbridge_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
    )
    logging.info(f"Logging initialized. Log file: {log_file}")

# =============================================================================
# Instrument Communication (Two-Ended)
# =============================================================================

def connect_instrument(visa_address, timeout=5.0):
    """Connect to an instrument and return resource."""
    try:
        rm = pyvisa.ResourceManager()
        instrument = rm.open_resource(visa_address)
        instrument.timeout = timeout
        return instrument, rm
    except Exception as e:
        logging.error(f"Connection error: {e}")
        return None, None

def wait_for_settle(instrument, use_sync=True, delay_ms=100):
    """Wait for instrument to settle after a command."""
    if use_sync:
        try:
            instrument.query("*OPC?")
        except Exception as e:
            logging.warning(f"Sync failed: {e}. Using delay.")
            time.sleep(delay_ms / 1000.0)
    else:
        time.sleep(delay_ms / 1000.0)

def check_errors(instrument):
    """Check instrument error queue."""
    try:
        esr = instrument.query("*ESR?")
        if esr.strip() != "0":
            error = instrument.query("SYST:ERR?")
            logging.error(f"Instrument error: {error}")
            return False
        return True
    except Exception as e:
        logging.warning(f"Error check failed: {e}")
        return True

def set_source(instrument, value, config):
    """Set the source to the specified value."""
    try:
        vendor = config["source"].get("vendor", "Keysight")
        if vendor.lower() == "keysight":
            instrument.write(f"SOUR:VOLT {value}")
        elif vendor.lower() == "tektronix":
            instrument.write(f"SOUR:VOLT {value}")
        elif vendor.lower() == "keithley":
            instrument.write(f"SOUR:VOLT {value}")
        else:
            instrument.write(f"SOUR:VOLT {value}")
        return True
    except Exception as e:
        logging.error(f"Source set failed: {e}")
        return False

def measure_dut(instrument, config):
    """Read measurement from DUT."""
    try:
        vendor = config["dut"].get("vendor", "Keysight")
        if vendor.lower() == "keysight":
            instrument.write("CONF:VOLT:DC")
            instrument.write("SENS:VOLT:DC:NPLC 1")
            raw = instrument.query("READ?")
        elif vendor.lower() == "tektronix":
            raw = instrument.query("MEASU:IMM:VAL?")
        elif vendor.lower() == "keithley":
            instrument.write("SENS:FUNC 'VOLT:DC'")
            raw = instrument.query("READ?")
        else:
            raw = instrument.query("READ?")
        return float(raw)
    except Exception as e:
        logging.error(f"DUT measurement failed: {e}")
        return None

# =============================================================================
# Core Calibration Sequence
# =============================================================================

def run_calibration_sequence(config):
    """Execute the calibration sequence with two-ended control."""
    logging.info("=" * 60)
    logging.info("CALIBRATION SEQUENCE STARTED")
    logging.info("=" * 60)

    # Extract config
    source_address = config["source"]["visa_address"]
    dut_address = config["dut"]["visa_address"]
    test_points = config["calibration"]["test_points_volts"]
    tolerance = config["calibration"]["pass_tolerance_volts"]
    operator = config["calibration"].get("operator_name", "Default")
    report_dir = config["general"].get("report_directory", "Reports")
    use_sync = config["general"].get("use_sync", True)
    use_error_checking = config["general"].get("use_error_checking", True)
    settle_delay_ms = config["source"].get("settle_delay_ms", 100)

    # Create report directory
    os.makedirs(report_dir, exist_ok=True)

    # Connect to source
    logging.info(f"Connecting to source at: {source_address}")
    source, source_rm = connect_instrument(source_address)
    if not source:
        logging.error("Failed to connect to source.")
        return False

    # Connect to DUT
    logging.info(f"Connecting to DUT at: {dut_address}")
    dut, dut_rm = connect_instrument(dut_address)
    if not dut:
        logging.error("Failed to connect to DUT.")
        return False

    try:
        # Query identities
        source_idn = source.query("*IDN?").strip()
        logging.info(f"Source: {source_idn}")
        dut_idn = dut.query("*IDN?").strip()
        logging.info(f"DUT: {dut_idn}")

        # Execute test points
        results = []
        for target_voltage in test_points:
            logging.info(f"Measuring {target_voltage:.3f} V...")

            # Set source
            logging.debug(f"Setting source to {target_voltage} V")
            if not set_source(source, target_voltage, config):
                logging.error("Failed to set source — skipping point")
                continue

            # Wait for settlement
            wait_for_settle(source, use_sync, settle_delay_ms)

            # Check source errors
            if use_error_checking and not check_errors(source):
                logging.error("Source error detected — skipping point")
                continue

            # Read DUT
            measured = measure_dut(dut, config)
            if measured is None:
                logging.error("Failed to read DUT — skipping point")
                continue

            # Check DUT errors
            if use_error_checking and not check_errors(dut):
                logging.error("DUT error detected — skipping point")
                continue

            # Compare
            error = abs(measured - target_voltage)
            status = "PASS" if error <= tolerance else "FAIL"

            logging.info(f"  Target: {target_voltage:.4f} V | Measured: {measured:.4f} V | Error: {error:.4f} V -> {status}")

            results.append({
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Operator": operator,
                "Source_V": target_voltage,
                "Measured_V": measured,
                "Error_V": round(error, 4),
                "Status": status
            })

        # Generate report
        if results:
            report_path = os.path.join(report_dir, f"Cal_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
            with open(report_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)

            logging.info(f"Report saved: {report_path}")

            # Summary
            total = len(results)
            passed = sum(1 for r in results if r["Status"] == "PASS")
            logging.info("=" * 60)
            logging.info(f"SUMMARY: {passed}/{total} PASSED")
            if passed == total:
                logging.info("ALL TESTS PASSED ✓")
            else:
                logging.warning(f"{total - passed} TESTS FAILED")
            logging.info("=" * 60)

            return True
        else:
            logging.error("No results collected.")
            return False

    except Exception as e:
        logging.error(f"Sequence error: {e}")
        return False
    finally:
        try:
            source.close()
            source_rm.close()
            dut.close()
            dut_rm.close()
            logging.info("Connections closed.")
        except Exception as e:
            logging.warning(f"Cleanup error: {e}")

# =============================================================================
# Entry Point
# =============================================================================

def main():
    """Main entry point."""
    config = load_config()
    log_level = config.get("general", {}).get("logging_level", "INFO")
    setup_logging(log_level)

    errors = validate_config(config)
    if errors:
        for err in errors:
            logging.error(f"Config error: {err}")
        logging.info("Please fix config.json and restart.")
        input("Press ENTER to exit...")
        sys.exit(1)

    try:
        success = run_calibration_sequence(config)
        if success:
            logging.info("Sequence completed successfully.")
        else:
            logging.error("Sequence failed.")
    except KeyboardInterrupt:
        logging.warning("Sequence interrupted by user.")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    input("\nPress ENTER to close...")

if __name__ == "__main__":
    main()
```

---

## 6. Client Handover Package Structure (Updated)

**6.1.** **Complete Package Layout:**

```
AutoCalBridge_Deployment/
│
├── Application/
│   ├── AutoCalBridge.exe          # Compiled executable
│   └── config.template.json        # Configuration template
│
├── Reports/                        # Output directory (empty initially)
│   └── (Reports generated here)
│
├── Documentation/
│   ├── User_Guide.pdf              # End-user instructions
│   ├── Quick_Start.md              # Quick reference
│   └── Release_Notes.txt           # Version and changes
│
├── Pre-Requisites.md               # Required software for client
└── README.md                       # Package overview
```

**6.2.** **Pre-Requisites.md Template:**

```markdown
# Pre-Requisites for AutoCalBridge

## Required Software on Client Machine

**1. Keysight IO Libraries Suite (FREE)**
- Download: https://www.keysight.com/us/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html
- Install with default options
- Required for VISA communication

**2. Windows 10/11**
- The application is compiled for Windows
- No Python installation required

## Hardware Requirements
- Source instrument (reference standard) — LAN/USB connection
- DUT instrument (unit under test) — LAN/USB connection
- Both instruments on the same network (if using LAN)

## Network Configuration (if using LAN)
- Firewall must allow inbound/outbound on port 4880 (HiSLIP)
- Both instruments and PC on same subnet

## Installation
1. Extract the ZIP package
2. Copy `config.template.json` to `config.json`
3. Edit `config.json` with your instrument addresses
4. Double-click AutoCalBridge.exe
```

---

## 7. Deployment Checklist (Updated)

**7.1.** **Before Compilation:**

**7.1.1.** Code ready:
- [ ] Main script runs without errors
- [ ] Script uses config.json for all variable parameters
- [ ] Two-ended (source + DUT) support implemented
- [ ] Synchronization (`*OPC?`) implemented
- [ ] Error handling (`*ESR?`, `SYST:ERR?`) implemented
- [ ] Logging implemented (not just print statements)
- [ ] Validation function implemented

**7.2.** **Before Deployment:**

**7.2.1.** Package structure:
- [ ] PyInstaller compiled successfully
- [ ] `.exe` file runs on a fresh Windows machine
- [ ] config.template.json is in the same folder as `.exe`
- [ ] Reports folder is automatically created

**7.2.2.** Documentation:
- [ ] Pre-Requisites.md complete
- [ ] Quick Start Guide written
- [ ] config.template.json annotated with comments
- [ ] Sample report CSV provided

**7.3.** **Before Client Delivery:**

**7.3.1.** Final checks:
- [ ] Package zipped with correct folder structure
- [ ] Version number in release notes
- [ ] Test run on a non-development machine
- [ ] All sensitive information removed

---

## 8. Summary — Deployment Workflow

**8.1.** The complete workflow from script to client delivery:

| **Step** | **Action** | **Section** |
|----------|------------|-------------|
| 1 | Build working script with config.json | Section 3 |
| 2 | Add validation and logging | Sections 4, 5 |
| 3 | Compile with PyInstaller | Section 2 |
| 4 | Build handover package | Section 6 |
| 5 | Write documentation | Section 7 |
| 6 | Run deployment checklist | Section 8 |
| 7 | Deliver to client | Section 6.2 |

**Further Reading:**
- PyInstaller Usage: https://pyinstaller.org/en/stable/usage.html
- Python Logging: https://docs.python.org/3/library/logging.html
- JSON Schema: https://json-schema.org/

---

**End of Document B — Deployment Pipeline Guide**