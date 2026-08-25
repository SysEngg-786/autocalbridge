# Document A — Technical Implementation Guide (Updated)

```
File: Technical_Implementation_Guide.md
Path: /Project_Root/Documentation/Technical_Implementation_Guide.md
```

---

# Technical Implementation Guide
## Hardware Test Automation with Python & PyVISA

**Version:** 2.0
**Purpose:** End-to-end technical setup guide — from zero to a working multi-vendor automation script.
**Target Audience:** Engineers, automation developers, and technical freelancers building hardware test automation pipelines.

---

## 1. Understanding the Communication Stack

**1.1.** Before writing any code, you must understand the four layers that enable communication between your Python script and a physical instrument.

**1.1.1.** Application Layer — Your Python script sends commands and receives data.

**1.1.2.** API Layer — PyVISA library translates Python calls to VISA standards.

**1.1.3.** Driver Layer — VISA Runtime (Keysight IO Libraries, NI-VISA, pyvisa-py) manages hardware communication.

**1.1.4.** Hardware Layer — Physical instrument over USB/LAN/GPIB executes commands.

**1.2.** **ASCII Diagram — Communication Stack:**

```
+------------------------------------------+
|         YOUR PYTHON SCRIPT                |
|    (instrument.write("READ?"))            |
+------------------+-----------------------+
                   ↓
+------------------------------------------+
|              PyVISA API                   |
|    (translates to VISA standard)          |
+------------------+-----------------------+
                   ↓
+------------------------------------------+
|           VISA Runtime                    |
|    (Keysight IO / pyvisa-py / NI-VISA)    |
+------------------+-----------------------+
                   ↓
+------------------------------------------+
|        Hardware (USB/LAN/GPIB)            |
|    (Instrument executes SCPI command)     |
+------------------------------------------+
```

**1.3.** **SCPI (Standard Commands for Programmable Instruments):**

**1.3.1.** SCPI is the language instruments understand.

**1.3.2.** Commands are text-based and hierarchical (e.g., `SENS:FREQ:CENT 2.4GHz`).

**1.3.3.** All major vendors (Keysight, Tektronix, R&S, Keithley) support SCPI with vendor-specific extensions.

**1.4.** **VISA (Virtual Instrument Software Architecture):**

**1.4.1.** VISA is the standard API for instrument control.

**1.4.2.** Abstracts away the physical connection (USB, LAN, GPIB are all addressed the same way).

**1.4.3.** VISA addresses are formatted as: `[interface]::[address]::[protocol]::INSTR`.

**1.5.** **Calibration-Specific Communication:**

**1.5.1.** Calibration requires **two-ended control** — controlling both the reference standard (source) and the unit under test (DUT).

**1.5.2.** The source is set to a known value, and the DUT is read.

**1.5.3.** Comparison between source and DUT determines PASS/FAIL.

**1.5.4.** This requires **two simultaneous VISA sessions** — one for the source, one for the DUT.

**1.6.** **Synchronization & Error Handling:**

**1.6.1.** After setting the source, the instrument must settle before reading the DUT.

**1.6.2.** `*OPC?` (Operation Complete) queries if the command has finished.

**1.6.3.** `*WAI` (Wait) blocks further commands until the instrument is ready.

**1.6.4.** `*ESR?` (Event Status Register) queries the instrument's status.

**1.6.5.** `SYST:ERR?` (System Error) retrieves the error queue.

**1.6.6.** These are essential for reliable calibration results.

**Further Reading:**
- PyVISA Documentation: https://pyvisa.readthedocs.io/
- SCPI Standard: https://www.ivifoundation.org/scpi/
- IEEE 488.2 Common Commands: https://www.ivifoundation.org/docs/

---

## 2. Single-Machine Setup

**2.1.** **Prerequisites:**

**2.1.1.** Windows 10/11, Linux, or macOS.

**2.1.2.** Administrator/local admin rights for driver installation.

**2.1.3.** Network access (for LAN-connected instruments) or USB port.

**2.2.** **Step-by-Step Installation:**

**2.2.1.** Install Python:

| **Step** | **Action** | **Verification** |
|----------|------------|------------------|
| 1 | Download Python from https://python.org | Choose latest stable version (3.10+) |
| 2 | Run installer | **CRITICAL:** Check "Add Python to PATH" |
| 3 | Verify installation | Open terminal: `python --version` → shows version number |

**2.2.2.** Install PyVISA and pyvisa-py:

```bash
pip install pyvisa pyvisa-py
```

**2.2.3.** Install Vendor VISA Runtime (choose one):

| **Vendor** | **Software** | **Download URL** | **Note** |
|------------|--------------|------------------|----------|
| Keysight | IO Libraries Suite | https://www.keysight.com/us/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html | Free, perpetual license |
| NI (National Instruments) | NI-VISA | https://www.ni.com/en/support/downloads/drivers.html | Free runtime, paid development |
| Open Source | pyvisa-py (pure Python) | Installed via pip | No external driver needed, but limited for some hardware |

**2.2.4.** Verify Installation:

```python
import pyvisa
rm = pyvisa.ResourceManager()
print(rm.list_resources())
```

**2.2.4.1.** This should print a list of available instruments (may be empty if no hardware connected).

**2.3.** **Common Installation Errors and Fixes:**

| **Error** | **Likely Cause** | **Fix** |
|-----------|------------------|---------|
| `ModuleNotFoundError: No module named 'pyvisa'` | PyVISA not installed | Run `pip install pyvisa pyvisa-py` |
| `VisaIOError: VI_ERROR_RSRC_NFOUND` | No VISA runtime found | Install Keysight IO Libraries or NI-VISA |
| `PermissionError` on Linux/macOS | USB device permissions | Add user to dialout group: `sudo usermod -a -G dialout $USER` |

**Further Reading:**
- PyVISA Installation Guide: https://pyvisa.readthedocs.io/en/latest/introduction/getting.html
- Keysight IO Libraries Download: https://www.keysight.com/us/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html

---

## 3. Verifying Your Setup

**3.1.** **Test Script — Basic Instrument Discovery:**

```python
import pyvisa

def discover_instruments():
    """Discover and list all available VISA instruments."""
    try:
        rm = pyvisa.ResourceManager()
        resources = rm.list_resources()
        print(f"Found {len(resources)} instrument(s):")
        for idx, resource in enumerate(resources, 1):
            print(f"  {idx}. {resource}")
        return resources
    except Exception as e:
        print(f"Error discovering instruments: {e}")
        return []

if __name__ == "__main__":
    discover_instruments()
```

**3.2.** **Test Script — Query Instrument Identity:**

```python
import pyvisa

def query_instrument(visa_address):
    """Connect to an instrument and query its identity."""
    try:
        rm = pyvisa.ResourceManager()
        instrument = rm.open_resource(visa_address)
        instrument.timeout = 2.0  # 2 seconds timeout
        
        idn = instrument.query("*IDN?")
        print(f"Connected to: {idn.strip()}")
        return idn
    except pyvisa.errors.VisaIOError as e:
        print(f"VISA Error: {e}")
    except Exception as e:
        print(f"Unexpected Error: {e}")
    return None

if __name__ == "__main__":
    # Replace with your instrument's VISA address
    test_address = "TCPIP0::localhost::hislip0::INSTR"
    query_instrument(test_address)
```

**3.3.** **Expected Outputs:**

**3.3.1.** With no instrument connected:
```
Found 0 instrument(s):
```

**3.3.2.** With an instrument connected:
```
Found 1 instrument(s):
  1. TCPIP0::192.168.1.100::inst0::INSTR
Connected to: KEYSIGHT TECHNOLOGIES,34461A,MY12345678,A.02.10
```

**3.4.** **Troubleshooting — Common Errors:**

| **Error** | **Cause** | **Resolution** |
|-----------|-----------|----------------|
| `VI_ERROR_RSRC_NFOUND` | VISA runtime not properly installed | Reinstall Keysight IO Libraries or NI-VISA |
| `VI_ERROR_TMO` (Timeout) | Instrument not responding | Check physical connection; verify IP address; check firewall |
| `VI_ERROR_RSRC_LOCKED` | Resource already in use | Close other applications using the instrument |
| `ValueError: invalid literal for float()` | Instrument returned non-numeric data | Check instrument settings; may require different query command |

**Further Reading:**
- PyVISA Examples: https://github.com/pyvisa/pyvisa/tree/main/examples
- Keysight Connection Expert Guide: https://www.keysight.com/us/en/assets/9018-06040/user-manuals/9018-06040.pdf

---

## 4. Dual-Machine Architecture

**4.1.** **Why Dual-Machine?**

**4.1.1.** Separates development from simulation.

**4.1.2.** Allows virtual instrument simulation without physical hardware.

**4.1.3.** Mirrors real deployment scenarios where instruments are on separate network machines.

**4.1.4.** Enables testing and demo without risk to expensive equipment.

**4.2.** **Architecture Overview:**

| **Machine** | **Role** | **Software** | **Purpose** |
|-------------|----------|--------------|-------------|
| Machine A | Automation Client | Python + PyVISA + Keysight IO Libraries | Runs automation scripts; sends commands |
| Machine B | Simulator Server | Mock Instrument or Vendor Simulator | Hosts virtual instruments; receives commands |

**4.3.** **Two-Ended Architecture (Calibration-Specific):**

| **Machine** | **Role** | **What It Simulates** |
|-------------|----------|----------------------|
| Machine A | Automation Client | ACB controlling both source and DUT |
| Machine B | Source Simulator | Reference standard (e.g., voltage calibrator) |
| Machine C | DUT Simulator | Unit under test (e.g., DMM) |

**4.3.1.** ACB sends `SOUR:VOLT` to the source simulator.

**4.3.2.** ACB sends `READ?` to the DUT simulator.

**4.3.3.** ACB compares the values and determines PASS/FAIL.

---

## 5. Keysight Implementation

**5.1.** **VISA Address Format for Keysight Instruments:**

**5.1.1.** LAN (HiSLIP):
```
TCPIP0::[IP_ADDRESS]::hislip[INDEX]::INSTR
```
Example: `TCPIP0::192.168.1.15::hislip0::INSTR`

**5.1.2.** LAN (Sockets):
```
TCPIP0::[IP_ADDRESS]::[PORT]::SOCKET
```
Example: `TCPIP0::192.168.1.15::5025::SOCKET`

**5.1.3.** USB:
```
USB0::[MANUFACTURER_ID]::[MODEL_CODE]::[SERIAL]::INSTR
```
Example: `USB0::0x0957::0x1507::MY12345678::INSTR`

**5.1.4.** GPIB:
```
GPIB[INDEX]::[ADDRESS]::INSTR
```
Example: `GPIB0::1::INSTR`

**5.2.** **Keysight-Specific SCPI Commands:**

| **Command** | **Description** | **Usage** |
|-------------|-----------------|-----------|
| `*IDN?` | Query instrument identity | Works on all VISA instruments |
| `*RST` | Reset instrument to default state | Always send before starting a test sequence |
| `*CLS` | Clear error/event registers | Use after `*RST` for clean state |
| `*OPC?` | Operation complete query | Use after setting source to confirm completion |
| `*WAI` | Wait for completion | Blocks until instrument is ready |
| `*ESR?` | Event status register query | Check for errors after commands |
| `CONF:VOLT:DC` | Configure for DC voltage measurement | Keysight multimeters (344xxA series) |
| `SENS:VOLT:DC:NPLC 1` | Set integration time (1 = 1 power line cycle) | Improves measurement stability |
| `READ?` | Perform measurement and read result | Common on Keysight DMMs |
| `SOUR:VOLT [value]` | Set source voltage | For calibrators and signal generators |

**5.3.** **Synchronization Commands:**

| **Command** | **Purpose** | **When to Use** |
|-------------|-------------|-----------------|
| `*OPC?` | Query if command is complete | After `SOUR:VOLT` before `READ?` |
| `*WAI` | Block until complete | After `SOUR:VOLT` before `READ?` |

**5.4.** **Error Handling Commands:**

| **Command** | **Purpose** | **When to Use** |
|-------------|-------------|-----------------|
| `*ESR?` | Query event status register | After each command to check for errors |
| `SYST:ERR?` | Query error queue | After each command to get error details |

---

## 6. Multi-Vendor Extension

**6.1.** **Why Multi-Vendor?**

**6.1.1.** Real laboratories have mixed vendor environments.

**6.1.2.** Clients need scripts that work across their entire instrument inventory.

**6.1.3.** Demonstrates framework-level thinking, not single-device specialization.

**6.2.** **Vendor-Specific VISA Address Formats:**

| **Vendor** | **Interface** | **Format Example** |
|------------|---------------|-------------------|
| Keysight | LAN (HiSLIP) | `TCPIP0::192.168.1.15::hislip0::INSTR` |
| Keysight | USB | `USB0::0x0957::0x1507::MY12345678::INSTR` |
| Tektronix | LAN (Sockets) | `TCPIP0::192.168.1.20::5025::SOCKET` |
| Tektronix | USB | `USB0::0x0699::0x0400::C123456::INSTR` |
| R&S | LAN (HiSLIP) | `TCPIP0::192.168.1.25::hislip0::INSTR` |
| Keithley | LAN (Sockets) | `TCPIP0::192.168.1.30::5025::SOCKET` |
| Keithley | GPIB | `GPIB0::28::INSTR` |

**6.3.** **Vendor-Specific SCPI Commands (Source + DUT):**

| **Vendor** | **Source Command** | **DUT Command** | **Description** |
|------------|-------------------|-----------------|-----------------|
| Keysight | `SOUR:VOLT [value]` | `READ?` | Set source, read DUT |
| Keysight | `SOUR:CURR [value]` | `CONF:VOLT:DC` | Set current source, configure DUT for voltage |
| Tektronix | `SOUR:VOLT` | `MEASU:IMM:VAL?` | Set source, read DUT |
| Keithley | `SOUR:VOLT [value]` | `READ?` | Set source, read DUT |

---

## 7. Two-Ended Calibration Architecture (New)

**7.1.** **What Is Two-Ended Calibration?**

**7.1.1.** Calibration compares a Device Under Test (DUT) against a reference standard (source).

**7.1.2.** The source is set to a known value.

**7.1.3.** The DUT is read.

**7.1.4.** The difference between source and DUT determines PASS/FAIL.

**7.1.5.** This requires **two simultaneous VISA sessions**.

**7.2.** **ASCII Diagram — Two-Ended Architecture:**

```
+------------------------------------------+
|           AutoCalBridge                    |
|  +------------------------------------+   |
|  |   TestEngine                        |   |
|  |   (Source + DUT Control)            |   |
|  +------------------+-----------------+   |
|                     |                      |
|     +---------------+-----------------+    |
|     |                                 |    |
|     ↓                                 ↓    |
|  +--------+                      +--------+
|  | Source |                      |  DUT   |
|  | (Ref)  |                      | (UUT)  |
|  +--------+                      +--------+
|  VISA Session 1                  VISA Session 2
+------------------------------------------+
```

**7.3.** **Implementation Pattern:**

| **Step** | **Action** | **VISA Session** |
|----------|------------|------------------|
| 1 | Open source connection | Session 1 |
| 2 | Open DUT connection | Session 2 |
| 3 | Send `SOUR:VOLT 1.0` to source | Session 1 |
| 4 | Wait for settlement (`*OPC?` or `*WAI`) | Session 1 |
| 5 | Send `READ?` to DUT | Session 2 |
| 6 | Read DUT response | Session 2 |
| 7 | Compare values | Application |
| 8 | Log PASS/FAIL | Application |

**7.4.** **Design Hooks for Two-Ended Architecture:**

| **Hook** | **Location** | **Purpose** |
|----------|--------------|-------------|
| `source_instrument` | `TestEngine` | Reference the source instrument |
| `dut_instrument` | `TestEngine` | Reference the DUT instrument |
| `set_source()` | `TestEngine` | Send command to source |
| `measure_dut()` | `TestEngine` | Read from DUT |
| `compare_values()` | `TestEngine` | Compare source and DUT values |

---

## 8. Synchronization & Error Handling (New)

**8.1.** **Why Synchronization Is Critical:**

**8.1.1.** After setting the source, the instrument needs time to settle.

**8.1.2.** Without synchronization, the DUT reading may be taken before the source is stable.

**8.1.3.** This results in invalid comparison and false PASS/FAIL decisions.

**8.1.4.** **Synchronization is not optional — it is essential for calibration.**

**8.2.** **Synchronization Commands:**

| **Command** | **Description** | **Usage** |
|-------------|-----------------|-----------|
| `*OPC?` | Query if operation is complete | Send after `SOUR:VOLT`, wait for response |
| `*WAI` | Wait for operation to complete | Send after `SOUR:VOLT`, blocks until done |

**8.3.** **Synchronization Implementation Pattern:**

```python
# Set source
source.write("SOUR:VOLT 1.0")

# Wait for completion using *OPC?
source.query("*OPC?")

# Now read DUT
dut_value = float(dut.query("READ?"))

# Compare
error = abs(dut_value - 1.0)
status = "PASS" if error <= tolerance else "FAIL"
```

**8.4.** **Why Error Handling Is Critical:**

**8.4.1.** Without error checking, failures are silent.

**8.4.2.** Silent failures lead to unreliable results.

**8.4.3.** **Error handling is not optional — it is essential for reliable calibration.**

**8.5.** **Error Handling Commands:**

| **Command** | **Description** | **Usage** |
|-------------|-----------------|-----------|
| `*ESR?` | Query event status register | Check for command, execution, or query errors |
| `SYST:ERR?` | Query error queue | Retrieve detailed error message |

**8.6.** **Error Handling Implementation Pattern:**

```python
# After each command, check for errors
error_code = instrument.query("*ESR?")
if error_code != "0":
    error_message = instrument.query("SYST:ERR?")
    logging.error(f"Instrument error: {error_message}")
    raise RuntimeError(f"Instrument error: {error_message}")
```

---

## 9. SCPI Command Reference Table (Updated)

**9.1.** **Common Commands (All Vendors):**

| **Command** | **Description** | **Returns** |
|-------------|-----------------|-------------|
| `*IDN?` | Identity query | Manufacturer, model, serial, version |
| `*RST` | Reset instrument | None |
| `*CLS` | Clear error queue | None |
| `*OPC?` | Operation complete | 1 when done |
| `*WAI` | Wait for completion | None |
| `*ESR?` | Event status register | Status code |
| `SYST:ERR?` | System error | Error code + message |
| `*TST?` | Self-test | 0 = PASS, non-zero = FAIL |

**9.2.** **Measurement Commands by Vendor (Updated):**

| **Function** | **Keysight** | **Tektronix** | **R&S** | **Keithley** |
|--------------|--------------|---------------|---------|--------------|
| DC Voltage (Source) | `SOUR:VOLT` | `SOUR:VOLT` | `SOUR:VOLT` | `SOUR:VOLT` |
| DC Voltage (DUT) | `READ?` | `MEASU:IMM:VAL?` | `READ?` | `READ?` |
| Sync Command | `*OPC?` | `*OPC?` | `*OPC?` | `*OPC?` |
| Error Query | `*ESR?` | `*ESR?` | `*ESR?` | `*ESR?` |

---

## 10. VISA Address Formats Cheat Sheet (Updated)

**10.1.** **LAN (TCP/IP) Addresses:**

| **Protocol** | **Format** | **Example** | **Typical Port** |
|--------------|------------|-------------|------------------|
| HiSLIP | `TCPIP0::[IP]::hislip[0]::INSTR` | `TCPIP0::192.168.1.15::hislip0::INSTR` | 4880 |
| Sockets | `TCPIP0::[IP]::[PORT]::SOCKET` | `TCPIP0::192.168.1.15::5025::SOCKET` | 5025 |
| VXI-11 | `TCPIP0::[IP]::inst0::INSTR` | `TCPIP0::192.168.1.15::inst0::INSTR` | N/A |

**10.2.** **USB Addresses:**

| **Format** | **Example** |
|------------|-------------|
| `USB0::[VID]::[PID]::[SERIAL]::INSTR` | `USB0::0x0957::0x1507::MY12345678::INSTR` |

**10.3.** **GPIB (IEEE-488) Addresses:**

| **Format** | **Example** |
|------------|-------------|
| `GPIB[INDEX]::[ADDRESS]::INSTR` | `GPIB0::1::INSTR` |

---

## 11. Troubleshooting Guide (Updated)

**11.1.** **Connection Errors:**

| **Error** | **Likely Cause** | **Resolution** |
|-----------|------------------|----------------|
| `VisaIOError: VI_ERROR_RSRC_NFOUND` | VISA runtime not installed | Install Keysight IO Libraries or NI-VISA |
| `VisaIOError: VI_ERROR_TMO` | Instrument not responding | Check IP; verify firewall; test with ping |
| `VisaIOError: VI_ERROR_RSRC_LOCKED` | Resource locked by another process | Close other VISA applications; restart system |
| `ConnectionRefusedError` | Port not open | Check instrument remote interface settings |

**11.2.** **Synchronization Errors:**

| **Error** | **Likely Cause** | **Resolution** |
|-----------|------------------|----------------|
| `*OPC?` times out | Instrument did not complete command | Check instrument state; reset and retry |
| `*WAI` hangs | Instrument is busy | Check instrument for errors; reset |

**11.3.** **Error Handling Errors:**

| **Error** | **Likely Cause** | **Resolution** |
|-----------|------------------|----------------|
| `*ESR?` returns non-zero | Command error or execution error | Query `SYST:ERR?` for details |
| `SYST:ERR?` returns error | Instrument-specific error | Check instrument manual for error code |

---

## 12. Pre-Flight Checklist (Updated)

**12.1.** **Before Running a Calibration Sequence:**

**12.1.1.** Hardware/Simulator:
- [ ] Source instrument (reference standard) is connected and powered on
- [ ] DUT instrument (unit under test) is connected and powered on
- [ ] Both instruments are configured for remote control

**12.1.2.** VISA Sessions:
- [ ] Source VISA address is correct
- [ ] DUT VISA address is correct
- [ ] Both addresses are in config.json

**12.1.3.** Synchronization:
- [ ] `*OPC?` or `*WAI` is implemented after source commands
- [ ] Settlement delay is appropriate for the instrument

**12.1.4.** Error Handling:
- [ ] `*ESR?` is checked after each command
- [ ] `SYST:ERR?` is queried if `*ESR?` indicates an error

**12.2.** **Test Sequence Before Full Run:**

**12.2.1.** Run identity query on source instrument.

**12.2.2.** Run identity query on DUT instrument.

**12.2.3.** Set source to a known value and verify with `*OPC?`.

**12.2.4.** Read DUT and verify value.

**12.2.5.** Compare values and verify PASS/FAIL logic.

---

## 13. Summary — End-to-End Workflow

**13.1.** The complete workflow from zero to two-ended calibration:

| **Step** | **Action** | **Section** |
|----------|------------|-------------|
| 1 | Understand VISA/SCPI communication stack | Section 1 |
| 2 | Set up Python + PyVISA on Machine A | Section 2 |
| 3 | Set up mock instruments for source and DUT | Section 4 |
| 4 | Get VISA addresses from Connection Expert | Section 4 |
| 5 | Test identity query | Section 3 |
| 6 | Implement two-ended calibration | Section 7 |
| 7 | Implement synchronization | Section 8 |
| 8 | Implement error handling | Section 8 |
| 9 | Save reports and iterate | Section 5 / 6 |

**Further Reading:**
- PyVISA Documentation: https://pyvisa.readthedocs.io/
- Keysight IO Libraries: https://www.keysight.com/us/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html
- SCPI Standard: https://www.ivifoundation.org/scpi/

---

**End of Document A — Technical Implementation Guide**