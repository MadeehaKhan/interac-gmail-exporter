# INTERAC E-Transfer Gmail Exporter

Extract INTERAC e-Transfer notification emails from Gmail (sent and received) into a CSV with reference number, name, and amount.

Includes a simple desktop GUI and an optional CLI.

## Requirements

- Python 3.10+
- A Google account with Gmail
- Google Cloud OAuth credentials (one-time setup)

## Google Cloud setup (one time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or use an existing one).
3. Enable **Gmail API**: APIs & Services → Library → search "Gmail API" → Enable.
4. Configure **OAuth consent screen**:
   - User type: External (or Internal if using Workspace)
   - Add your Gmail address as a **test user** while the app is in testing mode
5. Create credentials: APIs & Services → Credentials → **Create Credentials** → **OAuth client ID** → Application type **Desktop app**.
6. Download the JSON file and save it as `credentials.json` in this project root.

## Install

```bash
cd ~\suleiman
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## GUI (recommended)

```bash
python -m src.gui
```

1. Click **💾** to choose where to save the CSV (or type a path).
2. Optionally set **After** / **Before** dates (`YYYY/MM/DD`).
3. Click **Export**. On first run, your browser opens for Gmail sign-in; the token is saved to `token.json`.

To run without a console window on Windows:

```bash
pythonw -m src.gui
```

## CLI

```bash
python -m src.main --output output/interac_transfers.csv
python -m src.main --after 2025/01/01 --before 2026/01/01
python -m src.main --dry-run
```

Options:

| Flag | Description |
|------|-------------|
| `--output`, `-o` | CSV file path |
| `--after` | Gmail `after:` date |
| `--before` | Gmail `before:` date |
| `--max` | Max emails (default 500) |
| `--query` | Custom Gmail search query |
| `--dry-run` | Parse only, no CSV write |

## CSV columns

`date`, `direction`, `amount`, `currency`, `name`, `reference_number`, `subject`, `from_email`, `message_id`, `parse_ok`

- `direction`: `sent`, `received`, or `unknown`
- `parse_ok`: `true` when amount, name, and reference were all extracted
- Re-running appends only new `message_id` rows (no duplicates)

## Default Gmail search

```
(from:notify@payments.interac.ca OR from:payments.interac.ca)
(subject:"INTERAC" OR subject:"e-Transfer" OR subject:"e-transfer")
```

## Troubleshooting

- **Missing credentials.json** — Complete Google Cloud setup above.
- **Access blocked / app not verified** — Add your account as a test user on the OAuth consent screen.
- **Empty or partial fields** — Bank-specific email templates may need extra regex patterns; use `--dry-run` and compare with the original email.
- **Token expired** — Delete `token.json` and run again to re-authenticate.

## Security

Never commit `credentials.json` or `token.json`. Both are listed in `.gitignore`.
