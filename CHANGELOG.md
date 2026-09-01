# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2026-09-01

### Added
- **Security:** Added `ALLOWED_CHAT_IDS` whitelist in `config.py` to prevent unauthorized users from issuing IDE commands.
- **Dependencies:** Added `portalocker` to `requirements.txt` for reliable OS-level file locking.

### Fixed
- **Concurrency:** Replaced custom race-condition-prone file locking in `queue_manager.py` with `portalocker`.
- **Robustness:** Replaced `int(time.time())` with `time.time_ns()` to completely eliminate file name collisions for incoming media.
- **API Stability:** Fixed `tg_api_post` to correctly handle empty payloads (`{}`) without dropping parameters.
- **Diagnostics:** Fixed a logical bug in `bridge_health_watchdog.py` where `/status` would falsely report queue auto-healing instead of identifying it as stalled.
- **Portability:** Replaced hardcoded IDE paths in `session_manager.py` with `%LOCALAPPDATA%` and `shutil.which()`.

### Removed
- **Dead Code:** Removed obsolete HTTP-based trigger in `bridge_health_watchdog.py` and `RECEIVER_PORT` from `config.py`.
- **Duplication:** Consolidated redundant Telegram API functions (`tg_api_call` and `tg_api_post`) into a single method in `send_tg.py`.
