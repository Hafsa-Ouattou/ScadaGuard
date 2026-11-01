# ScadaGuard
Host-based intrusion detection system (HIDS) for workstations with access to a SCADA telemanagement system. Real-time ransomware, USB, network and process monitoring, tamper-evident audit log, and email alerts.

## Roadmap

### ✅ v1.0: Current
- Argon2id authentication, brute-force lockout, role-based access (admin / agent)
- Real-time monitoring: files (ransomware), USB, network, processes
- SHA-256 hash-chained audit log with integrity verification
- Email alerts on CRITICAL events
- Excel / PDF export, statistics dashboard

### 🔜 Next
- [ ] Persist the audit log and brute-force counters in a database (SQLite) so they survive restarts
- [ ] Configurable thresholds and watched folders from the UI or a config file
- [ ] HTTPS support and secure cookie settings by default
- [ ] Unit tests for detection rules (pytest)

### 🔭 Later
- [ ] Centralize logs from several workstations to one supervision server
- [ ] Run as a Windows service (always on, starts at boot)
- [ ] Two-factor authentication for the dashboard
- [ ] Baseline / allow-list to reduce false positives (known processes and ports)
- [ ] Optional SMS / Telegram alerts in addition to email
