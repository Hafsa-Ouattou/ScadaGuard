# 🛡️ SCADAGuard

**From a site visit to a working intrusion detector: how I designed, built and tested a host-based security monitor for a water-utility telemanagement workstation.**

SCADAGuard is a **host-based intrusion detection system (HIDS)** that watches a workstation with access to a SCADA / telemanagement system. It detects ransomware-like behaviour, infected USB drives, suspicious processes and unusual network connections, records everything in a **tamper-evident audit log**, and **emails the administrator** when something critical happens.


## Table of contents

1. [The problem](#1-the-problem)
2. [The approach: four steps](#2-the-approach-four-steps)
3. [Step 1: Understanding the needs](#3-step-1-understanding-the-needs)
4. [Step 2: Designing the architecture](#4-step-2-designing-the-architecture)
5. [Step 3: Building module by module](#5-step-3-building-module-by-module)
6. [Step 4: Integration and testing](#6-step-4-integration-and-testing)
7. [Results](#7-results)
8. [What I learned and what is still missing](#8-what-i-learned-and-what-is-still-missing)
9. [Run it yourself](#9-run-it-yourself)
10. [Project structure](#10-project-structure)

---

## 1. The problem

The internship started with a visit to the site that hosts the water branch's **telemanagement (SCADA) system**: the infrastructure used to monitor and control pumping stations, reservoirs, level and pressure sensors and automated valves from a distance.

That visit changed the direction of the project. These systems are critical for the continuity of a public service, yet they rely on **workstations whose access must be strictly controlled**. A human mistake, a compromised account or a piece of malware could disturb the monitoring of the installations. And SCADA systems were historically designed when they were isolated from larger networks, so security was not a design concern.

> **Research question:** *How can a workstation with access to the telemanagement system be secured and monitored locally, so that signs of compromise are detected in real time?*

### What exists today

Workstations are usually protected by perimeter defences (firewall, access control) and by user awareness. Those watch mostly **incoming traffic, not what happens on the workstation itself**. A threat that gets past the perimeter, such as an infected USB drive or a malicious attachment, can go unnoticed locally.


### Design choice: detect, don't block

SCADAGuard is a **HIDS, not a HIPS**. It observes and alerts, but it never blocks an attack and never sits between the operator and the telemanagement system. The operator keeps direct access, and SCADAGuard's login only protects its own dashboard. On a critical system, a security tool that could interrupt operations would be a risk of its own.

It combines two detection styles:

- **Signature-based:** suspicious file extensions, ransom-note filenames, executables in temp folders.
- **Behaviour-based:** an abnormal number of file changes in a short time.

## 2. The approach: four steps

```
 ┌──────────────┐   ┌──────────────┐   ┌────────────────────┐   ┌──────────────────┐
 │ 1. Gather    │ → │ 2. Design    │ → │ 3. Build iteratively│ → │ 4. Integrate and │
 │    the needs │   │    modular   │   │    module by module │   │    test end to   │
 │              │   │    architecture│  │    (test each alone)│   │    end           │
 └──────────────┘   └──────────────┘   └────────────────────┘   └──────────────────┘
```

| Step | What I did |
|---|---|
| **1. Gather the needs** | Used the site visit to identify the main families of risk to cover: unauthorized access, ransomware-like behaviour, suspicious network activity, malicious processes, unauthorized removable devices. |
| **2. Design the architecture** | Defined a modular architecture with one clear responsibility per module (authentication, files, network, processes, USB, web interface), so each can be developed and tested on its own. |
| **3. Build module by module** | Developed each module and tested it in isolation, for example by simulating ransomware behaviour to validate the file monitor, **before** merging it into the main app. This made it possible to find and fix errors at a fine-grained level instead of on the whole system. |
| **4. Integrate and test end to end** | Assembled the validated modules and tested the full chain: login, navigation between tabs, real alert triggering, email reception, report export. |

The project began as a Tkinter desktop prototype and was then moved to a **Flask web app**, so the dashboard can be opened from any browser. The security logic stayed in Python.

## 3. Step 1: Understanding the needs

The site visit was turned into a functional specification:

| Need | Description |
|---|---|
| Authentication | Secure login with username and password |
| Anti brute-force | Temporary lockout after several failed logins |
| File monitoring | Real-time detection of ransomware-like behaviour |
| Network monitoring | Active connections, flagging unusual ports |
| Process monitoring | Running processes, flagging suspicious paths |
| USB monitoring | Detect removable devices and suspicious content |
| Audit log | Centralize every security event |
| Statistics | Visualize how events are distributed |
| Export | Excel / PDF report, admin only |
| Notifications | Automatic email on a critical event |

## 4. Step 2: Designing the architecture

The application server receives the events produced by the monitoring modules, records them in the audit log and shows them on the dashboard. The authentication module controls access to the interface, and the notification module sends the email alerts.

Monitors (background threads)  ->  Event queue  ->  Flask server  ->  Hash-chained audit log
 files / USB / network / processes                  classifies         |-> Email alert (CRITIQUE)
                                                    every event        |-> Web dashboard
                                                                       '-> Excel / PDF reports (admin)
```

**Every event gets a severity level:**

| Level | Meaning |
|---|---|
| `INFO` | Normal activity (file created, drive removed, ...) |
| `SUSPECT` | Worth a look (unusual port, process from a temp folder, new USB drive) |
| `CRITIQUE` | Likely attack (ransomware burst, ransom note, USB with executables) |


## 5. Step 3: Building module by module

### 🔐 Authentication and anti brute-force (`auth.py`)
Passwords are never stored in clear. Each one is hashed with **Argon2id**, the algorithm recommended by OWASP, deliberately slow and memory-hungry so brute-force attacks are costly. After **3 failed attempts the account is locked for 60 seconds**, and every login attempt is written to an audit file.

### 📁 File monitor: ransomware detection (`surveillance_fichiers.py`)
Built on `watchdog`. Every event (create, modify, delete, rename) is timestamped in a **5-second sliding window**. If **8 or more events** occur in that window, a CRITIQUE alert fires, since that pattern is typical of mass file encryption. A second, independent signal: dropping a file whose name looks like a ransom note (`readme`, `decrypt`, `ransom`, `recover`, ...) triggers an **immediate** CRITIQUE alert, even outside a burst.

### 💾 USB monitor (`surveillance_usb.py`)
USB drives are the textbook way into isolated industrial systems (Stuxnet). The monitor checks removable drives every 2 seconds. When a new one appears, it scans only the **root** of the drive (shallow, so it stays fast) for `.exe .bat .cmd .vbs .vbe .ps1 .scr .js .jar`. Executables found means **CRITIQUE**, a clean drive means **SUSPECT**, and removal is logged as **INFO**.

### 🌐 Network and ⚙️ process monitors (`surveillance_reseau.py`, `surveillance_processus.py`)
With `psutil`, the network monitor lists established connections and flags remote ports outside a list of common ones (80, 443, 53, 22, ...). The process monitor lists running processes and flags executables launched from temporary folders, a classic indicator used by EDR tools.

### 🧾 Tamper-evident audit log (`app.py`)
Every event stores the SHA-256 hash of the previous one:

```
hash_i = SHA-256( time | level | module | message | hash_(i-1) )
```

Editing or deleting any entry breaks the chain from that point on. A **"Vérifier l'intégrité"** button recomputes the entire chain, and the PDF report states whether it is intact.

### 📧 Email alerts (`notifications_email.py`)
Sent through Gmail SMTP when an event reaches the configured level (default CRITIQUE), from a background thread so detection is never slowed down, with a **cooldown** to avoid flooding the inbox.

### 📊 Dashboard and reports
A web interface (HTML/CSS/JavaScript, Chart.js) with tabs for Files, Network, Processes, USB, Audit log and Statistics. Admins can export the audit log to **Excel** and **PDF**. 

## 6. Step 4: Integration and testing

Each module was validated with a dedicated scenario, then the whole application was tested end to end.

**The ransomware simulation.** I wrote a script that reproduces the steps of a real attack on an isolated test folder, with **no real malware**:

1. Drop "normal" work documents
2. "Encrypt" them (overwrite the content with random data)
3. Rename them with a `.locked` extension
4. Delete part of them and drop a ransom note

```bash
python test_alerte.py            # simple burst: 15 files created quickly
python test_alerte_avance.py     # the 4-step ransomware simulation
```

**Other test scenarios:** plug in a drive containing `test.exe` and `update.bat` for the USB monitor; tamper with the log to check that the hash chain catches it; trigger real alerts and confirm the email arrives; export the reports.

## 7. Results

| Test | Expected | Observed |
|---|---|---|
| File burst / ransomware simulation | CRITIQUE alert | ✅ `8 modifications de fichiers en moins de 5s` raised and highlighted |
| USB drive with `test.exe` and `update.bat` | CRITIQUE alert | ✅ Detected within seconds |
| Critical event | Email to the administrator | ✅ Received in the inbox for both file and USB alerts |
| Audit log verification | Chain intact | ✅ `3459 évènement(s) vérifié(s), aucune altération détectée` |
| Tampering with the log | Detected | ✅ Chain broken at the modified entry |

### Screenshots

| Login | Ransomware alert in the Files tab |
|---|---|
| ![Login](screenshots/01-login.png) | ![Files tab](screenshots/02-files-ransomware-alert.png) |

| USB alert | Audit log with integrity check |
|---|---|
| ![USB tab](screenshots/03-usb-alert.png) | ![Audit log](screenshots/04-audit-log-integrity.png) |

| Email alert (USB) | Email alert (ransomware) |
|---|---|
| ![Email USB](screenshots/05-email-alert-usb.png) | ![Email files](screenshots/06-email-alert-files.png) |

## 8. What I learned and what is still missing

**Lessons**

- Splitting the system into **independent modules** made bugs far easier to find: each one was fixed where it lived, not hunted down in the whole app.
- **Simulating the attack** is a better test than reading the code. It showed that a pure "burst" rule is not enough, which is why the ransom-note signal was added.
- Security tools have to be **safe by design**: passive detection, hashed passwords, a lockout, and a log that can prove it was not altered.



**Built with:** Python · Flask · watchdog · psutil · argon2-cffi · openpyxl · ReportLab · smtplib · HTML / CSS / JavaScript · Chart.js · Visual Studio Code

*Hafsa Ouattou · ENSA Fès · Internship at ONEE – Water Branch, July 2026.*
