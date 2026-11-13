# Messenger JSON to Printable PDF Converter

Turn your exported Facebook Messenger JSON chat archives into customizable, print-ready PDF booklets. Whether you are creating a printed memory book, archiving a conversation, or exporting chats by month or year, this tool provides both an interactive **Streamlit Web UI** (with live visual preview) and a full-featured **Command Line Interface (CLI)**.

---

## Features

- **Rich Visual Customization**:
  - **6 Built-in Theme Presets**:
    - `messenger_blue` — Classic Messenger Blue
    - `messenger_love` — Rose & Magenta
    - `dark_mode` — Midnight Dark Mode
    - `emerald` — Forest Emerald
    - `warm_book` — Warm Sepia Book
    - `monochrome` — Minimalist B&W (Ink Saver)
  - **Custom Color Pickers**: Customize page background, sent/received bubble colors, text colors, header accents, and avatar badges.
  - **Typography & Bubble Controls**: Choose between Sans-Serif, Classic Serif, Rounded, or Monospace fonts; adjust font size (`pt`), bubble corner radius (`px`), maximum bubble width (`%`), and toggle **Compact Spacing Mode**.
- **Flexible Page & Print Layouts**:
  - Supports **A5** (ideal for printed booklets), **A4**, **Letter**, and **A6** formats in **Portrait** or **Landscape** orientation.
  - Adjustable page margins (`mm`) and automatic page numbering.
  - Smart print pagination (`break-inside: avoid`) ensures chat bubbles are never sliced in half across page breaks.
  - Split output PDFs by **Month** (`Messenger_2025_06.pdf`), by **Year** (`Messenger_2025.pdf`), or export as a **Single Combined PDF**.
- **Granular Element Toggles & Localization**:
  - Show or hide the cover header, message count, date dividers, sender avatars, sender names above bubbles (great for group chats), timestamps (24h or 12h AM/PM), emoji reactions, attached photos, and page numbers.
  - Upload a custom avatar image or automatically display sender initials.
  - Multi-language support for month names and date dividers (**English**, **Czech**, **German**, **Spanish**, **French**).
- **Smart JSON Parser**:
  - Supports native Facebook Messenger JSON exports (`message_1.json`, `message_2.json`, etc.) as well as simplified custom JSON schemas.
  - Automatically repairs Facebook's notorious Latin-1 / UTF-8 mojibake encoding so international characters and emojis (`❤️`, `😍`, `🔥`) render accurately.
  - Merges multiple JSON files and sorts messages chronologically with optional date range filtering.

---

## Quick Start

### 1. Clone & Install

**Option A — One-command launch script (macOS / Linux):**

```bash
chmod +x run_app.sh
./run_app.sh
```

**Option B — Manual setup:**

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

---

### 2. Run the Interactive Web App (Streamlit)

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser:
1. Upload one or more Messenger `.json` files, point to a local folder, or click **Load Sample Conversation**.
2. Use the left sidebar to customize the **Theme Preset**, **Colors**, **Page Size**, **Typography**, and **Visible Elements**.
3. Preview your design instantaneously in the **Live Appearance Preview** tab.
4. Switch to **Generate & Download PDFs** to export individual PDFs or download a complete `.zip` archive.

---

### 3. Command Line Interface (CLI)

You can also batch-generate PDFs directly from the terminal:

```bash
# Basic usage with sample data
python cli.py --input sample_data/sample_chat.json --output output_pdf --primary "Alex Rivera"

# Customize theme, page format, font, and grouping
python cli.py \
  --folder /path/to/messenger_export \
  --output output_pdf \
  --theme warm_book \
  --size A5 \
  --font serif \
  --group-by month \
  --compact

# Custom hex colors and 12-hour timestamps
python cli.py \
  --input sample_data/sample_chat.json \
  --sent-color "#ff4081" \
  --received-color "#f3f4f6" \
  --bubble-radius 12 \
  --time-12h
```

#### CLI Options Overview

| Flag | Description | Default |
| :--- | :--- | :--- |
| `-i, --input` | One or more `.json` chat files | — |
| `-f, --folder` | Folder containing `.json` chat files | — |
| `-o, --output` | Output directory for generated PDFs | `output_pdf` |
| `--prefix` | Filename prefix for generated PDFs | `Messenger` |
| `--group-by` | Split PDFs by `month`, `year`, or `single` | `month` |
| `--start-date` / `--end-date` | Filter messages by date (`YYYY-MM-DD`) | — |
| `-p, --primary` | Primary sender name (right-side bubbles) | Auto-detected |
| `-t, --title` | Custom header title | Participant names |
| `--subtitle` | Optional custom subtitle in the header | — |
| `-s, --size` | Page size: `A5`, `A4`, `Letter`, `A6` | `A5` |
| `--landscape` | Use landscape page orientation | `False` |
| `--margin` | Page margins in millimeters (`mm`) | `12` |
| `--theme` | `messenger_blue`, `messenger_love`, `dark_mode`, `emerald`, `warm_book`, `monochrome` | `messenger_blue` |
| `--bg-color`, `--sent-color`, `--received-color`, ... | Override any individual theme hex color | Theme default |
| `--font` | Font style: `sans`, `serif`, `rounded`, `mono` | `sans` |
| `--font-size` | Base font size in points (`pt`) | `9.0` |
| `--bubble-radius` | Bubble corner radius in pixels (`px`) | `18` |
| `--bubble-width` | Max bubble width percentage (`55`–`90`) | `75` |
| `--compact` | Enable compact vertical spacing | `False` |
| `--lang` | Language for dates & months (`en`, `cs`, `de`, `es`, `fr`) | `en` |
| `--time-12h` | Use 12-hour timestamps (`AM`/`PM`) | `False` |
| `--show-sender-names` | Show sender names above received bubbles | `False` |
| `--no-header`, `--no-avatars`, `--no-timestamps`, `--no-reactions`, `--no-dividers`, `--no-page-numbers` | Hide specific visual elements | `False` |

---

## How to Export Your Chat from Facebook Messenger

1. Go to **Facebook Settings & Privacy** → **Settings** → **Accounts Center** → **Your information and permissions** → **Download your information**.
2. Select **Messages** and choose **JSON** as the format.
3. Once downloaded and extracted, locate your conversation folder under `your_facebook_activity/messages/inbox/<chat_name>/`.
4. Upload `message_1.json` (and `message_2.json`, etc.) into the app!

---

## Project Structure

- [`app.py`](app.py) — Interactive Streamlit web application with live preview and full styling controls.
- [`cli.py`](cli.py) — Command-line interface for automated or batch PDF generation.
- [`chat_parser.py`](chat_parser.py) — JSON parser with UTF-8/Mojibake repair, date filtering, and chronological grouping.
- [`pdf_generator.py`](pdf_generator.py) — Jinja2 + Playwright Chromium rendering engine, theme presets, and localization.
- [`templates/messenger_template.html`](templates/messenger_template.html) — Customizable CSS-variables print template.
- [`sample_data/sample_chat.json`](sample_data/sample_chat.json) — Anonymized sample conversation for testing.

---

## License

Released under the [MIT License](LICENSE).
