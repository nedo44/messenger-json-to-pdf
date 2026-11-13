"""
PDF Generator using Playwright Chromium to render HTML/CSS to high-quality print-ready PDF.
Supports:
- Multiple page formats (A5, A4, Letter, A6) and Portrait/Landscape orientation
- Theme presets and full custom color palettes
- Custom typography, font sizes, bubble shapes, and compact spacing
- Granular toggles for headers, avatars, sender names, timestamps, reactions, date dividers, and page numbers
- Multi-language support for month names and date dividers (English default)
- Prevention of bubble clipping across pages (break-inside: avoid)
"""

import os
from dataclasses import dataclass, replace
from datetime import datetime
from typing import List, Dict, Any, Optional
import jinja2
from playwright.sync_api import sync_playwright


LOCALES: Dict[str, Dict[str, Any]] = {
    "en": {
        "name": "English",
        "months": {
            1: "JANUARY", 2: "FEBRUARY", 3: "MARCH", 4: "APRIL",
            5: "MAY", 6: "JUNE", 7: "JULY", 8: "AUGUST",
            9: "SEPTEMBER", 10: "OCTOBER", 11: "NOVEMBER", 12: "DECEMBER",
        },
        "months_title": {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December",
        },
        "messages_label": "messages",
        "complete_title": "COMPLETE CHAT ARCHIVE",
        "date_format": "{month} {day}, {year}",
    },
    "cs": {
        "name": "Čeština (Czech)",
        "months": {
            1: "LEDEN", 2: "ÚNOR", 3: "BŘEZEN", 4: "DUBEN",
            5: "KVĚTEN", 6: "ČERVEN", 7: "ČERVENEC", 8: "SRPEN",
            9: "ZÁŘÍ", 10: "ŘÍJEN", 11: "LISTOPAD", 12: "PROSINEC",
        },
        "months_title": {
            1: "Leden", 2: "Únor", 3: "Březen", 4: "Duben",
            5: "Květen", 6: "Červen", 7: "Červenec", 8: "Srpen",
            9: "Září", 10: "Říjen", 11: "Listopad", 12: "Prosinec",
        },
        "messages_label": "zpráv",
        "complete_title": "KOMPLETNÍ ARCHIV CHATU",
        "date_format": "{day}. {month} {year}",
    },
    "de": {
        "name": "Deutsch (German)",
        "months": {
            1: "JANUAR", 2: "FEBRUAR", 3: "MÄRZ", 4: "APRIL",
            5: "MAI", 6: "JUNI", 7: "JULI", 8: "AUGUST",
            9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DEZEMBER",
        },
        "months_title": {
            1: "Januar", 2: "Februar", 3: "März", 4: "April",
            5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
            9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
        },
        "messages_label": "Nachrichten",
        "complete_title": "VOLLSTÄNDIGES CHAT-ARCHIV",
        "date_format": "{day}. {month} {year}",
    },
    "es": {
        "name": "Español (Spanish)",
        "months": {
            1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
            5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
            9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
        },
        "months_title": {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
        },
        "messages_label": "mensajes",
        "complete_title": "ARCHIVO COMPLETO DEL CHAT",
        "date_format": "{day} de {month} de {year}",
    },
    "fr": {
        "name": "Français (French)",
        "months": {
            1: "JANVIER", 2: "FÉVRIER", 3: "MARS", 4: "AVRIL",
            5: "MAI", 6: "JUIN", 7: "JUILLET", 8: "AOÛT",
            9: "SEPTEMBRE", 10: "OCTOBRE", 11: "NOVEMBRE", 12: "DÉCEMBRE",
        },
        "months_title": {
            1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril",
            5: "Mai", 6: "Juin", 7: "Juillet", 8: "Août",
            9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre",
        },
        "messages_label": "messages",
        "complete_title": "ARCHIVE COMPLÈTE DU CHAT",
        "date_format": "{day} {month} {year}",
    },
}

ENGLISH_MONTHS = LOCALES["en"]["months"]
CZECH_MONTHS = LOCALES["cs"]["months"]

FONT_FAMILIES: Dict[str, str] = {
    "sans": '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji"',
    "serif": 'Georgia, "Times New Roman", "Book Antiqua", Palatino, serif, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji"',
    "rounded": 'ui-rounded, "SF Pro Rounded", "Nunito", "Quicksand", -apple-system, BlinkMacSystemFont, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji"',
    "mono": 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace, "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji"',
}

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    "messenger_blue": {
        "label": "Messenger Classic (Blue)",
        "bg_color": "#ffffff",
        "sent_bubble_color": "#0084ff",
        "sent_text_color": "#ffffff",
        "received_bubble_color": "#f0f2f5",
        "received_text_color": "#050505",
        "accent_color": "#0084ff",
        "avatar_bg_color": "#0084ff",
        "muted_text_color": "#65676b",
        "divider_bg_color": "#f0f2f5",
    },
    "messenger_love": {
        "label": "Messenger Love (Rose & Magenta)",
        "bg_color": "#ffffff",
        "sent_bubble_color": "#e91e63",
        "sent_text_color": "#ffffff",
        "received_bubble_color": "#f0f2f5",
        "received_text_color": "#050505",
        "accent_color": "#e91e63",
        "avatar_bg_color": "#8e24aa",
        "muted_text_color": "#65676b",
        "divider_bg_color": "#fce4ec",
    },
    "dark_mode": {
        "label": "Midnight Dark Mode",
        "bg_color": "#121212",
        "sent_bubble_color": "#7c3aed",
        "sent_text_color": "#ffffff",
        "received_bubble_color": "#262626",
        "received_text_color": "#f3f4f6",
        "accent_color": "#a78bfa",
        "avatar_bg_color": "#6d28d9",
        "muted_text_color": "#9ca3af",
        "divider_bg_color": "#1f2937",
    },
    "emerald": {
        "label": "Forest Emerald",
        "bg_color": "#ffffff",
        "sent_bubble_color": "#059669",
        "sent_text_color": "#ffffff",
        "received_bubble_color": "#f0fdf4",
        "received_text_color": "#064e3b",
        "accent_color": "#059669",
        "avatar_bg_color": "#047857",
        "muted_text_color": "#6b7280",
        "divider_bg_color": "#ecfdf5",
    },
    "warm_book": {
        "label": "Warm Sepia Book",
        "bg_color": "#fdfbf7",
        "sent_bubble_color": "#8c5a3c",
        "sent_text_color": "#ffffff",
        "received_bubble_color": "#efeae1",
        "received_text_color": "#2c221e",
        "accent_color": "#8c5a3c",
        "avatar_bg_color": "#6e4730",
        "muted_text_color": "#786c61",
        "divider_bg_color": "#efeae1",
    },
    "monochrome": {
        "label": "Minimalist B&W (Ink Saver)",
        "bg_color": "#ffffff",
        "sent_bubble_color": "#222222",
        "sent_text_color": "#ffffff",
        "received_bubble_color": "#f3f4f6",
        "received_text_color": "#111111",
        "accent_color": "#111111",
        "avatar_bg_color": "#444444",
        "muted_text_color": "#666666",
        "divider_bg_color": "#f3f4f6",
    },
}


@dataclass
class PdfStyleConfig:
    """Configuration for PDF visual appearance, layout, and included elements."""
    # Page & Print Layout
    page_size: str = "A5"
    landscape: bool = False
    margin_mm: int = 12

    # Theme & Colors
    theme: str = "messenger_blue"
    bg_color: str = "#ffffff"
    sent_bubble_color: str = "#0084ff"
    sent_text_color: str = "#ffffff"
    received_bubble_color: str = "#f0f2f5"
    received_text_color: str = "#050505"
    accent_color: str = "#0084ff"
    avatar_bg_color: str = "#0084ff"
    muted_text_color: str = "#65676b"
    divider_bg_color: str = "#f0f2f5"

    # Typography & Bubbles
    font_family: str = "sans"
    font_size_pt: float = 9.0
    bubble_radius_px: int = 18
    max_bubble_width_pct: int = 75
    compact_mode: bool = False

    # Visibility & Content
    show_header: bool = True
    show_message_count: bool = True
    show_date_dividers: bool = True
    show_avatars: bool = True
    show_sender_names: bool = False
    show_timestamps: bool = True
    time_format_24h: bool = True
    show_reactions: bool = True
    show_photos: bool = True
    show_page_numbers: bool = True

    # Localization & Custom Text
    language: str = "en"
    custom_subtitle: Optional[str] = None

    @classmethod
    def from_theme(cls, theme_name: str = "messenger_blue", **overrides) -> "PdfStyleConfig":
        """Create a PdfStyleConfig pre-populated with a theme preset and optional overrides."""
        preset = THEME_PRESETS.get(theme_name, THEME_PRESETS["messenger_blue"])
        kwargs = {
            "theme": theme_name,
            "bg_color": preset["bg_color"],
            "sent_bubble_color": preset["sent_bubble_color"],
            "sent_text_color": preset["sent_text_color"],
            "received_bubble_color": preset["received_bubble_color"],
            "received_text_color": preset["received_text_color"],
            "accent_color": preset["accent_color"],
            "avatar_bg_color": preset["avatar_bg_color"],
            "muted_text_color": preset["muted_text_color"],
            "divider_bg_color": preset["divider_bg_color"],
        }
        for k, v in overrides.items():
            if v is not None:
                kwargs[k] = v
        return cls(**kwargs)


def is_primary_sender(sender: str, primary_sender: str) -> bool:
    """Check if sender matches primary_sender (exact or word/token prefix match)."""
    if not sender or not primary_sender:
        return False
    s1 = sender.strip().lower()
    s2 = primary_sender.strip().lower()
    if s1 == s2:
        return True
    # Match if one is a distinct name token of the other (e.g., "Alex" vs "Alex Rivera")
    tokens1 = s1.split()
    tokens2 = s2.split()
    if s2 in tokens1 or s1 in tokens2:
        return True
    return False


def format_period_title(period_key: str, language: str = "en") -> str:
    """Format a period key ('YYYY-MM', 'YYYY', or 'Complete') into a localized title."""
    loc = LOCALES.get(language, LOCALES["en"])
    if "-" in period_key:
        parts = period_key.split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            year = int(parts[0])
            month_int = int(parts[1])
            month_name = loc["months"].get(month_int, f"MONTH {month_int}")
            return f"{month_name} {year}"
    if period_key.isdigit():
        return period_key
    if period_key.lower() == "complete":
        return loc["complete_title"]
    return period_key.upper()


def prepare_template_items(
    messages: List[Dict[str, Any]],
    language: str = "en",
    time_format_24h: bool = True,
) -> List[Dict[str, Any]]:
    """
    Prepare list of renderable items with localized date dividers, consecutive grouping,
    and formatted timestamps.
    """
    loc = LOCALES.get(language, LOCALES["en"])
    items = []
    current_date = None

    for i, msg in enumerate(messages):
        dt: datetime = msg["datetime"]
        msg_date = dt.date()

        # Insert Date Divider on day change
        if current_date != msg_date:
            current_date = msg_date
            month_str = loc["months"].get(dt.month, str(dt.month)).upper()
            divider_str = loc["date_format"].format(
                day=dt.day, month=month_str, year=dt.year
            )
            items.append({
                "type": "divider",
                "text": divider_str,
            })

        # Determine if this message is first/last in a consecutive 5-minute group from the same sender
        is_first_in_group = True
        if i > 0:
            prev_msg = messages[i - 1]
            prev_dt: datetime = prev_msg["datetime"]
            if (
                prev_msg["sender"] == msg["sender"]
                and prev_dt.date() == msg_date
                and (dt - prev_dt).total_seconds() < 300
            ):
                is_first_in_group = False

        show_avatar = True
        is_last_in_group = True
        if i + 1 < len(messages):
            next_msg = messages[i + 1]
            next_dt: datetime = next_msg["datetime"]
            if (
                next_msg["sender"] == msg["sender"]
                and next_dt.date() == msg_date
                and (next_dt - dt).total_seconds() < 300
            ):
                show_avatar = False
                is_last_in_group = False

        formatted_time = (
            dt.strftime("%H:%M") if time_format_24h else dt.strftime("%I:%M %p").lstrip("0")
        )

        items.append({
            "type": "message",
            "msg": msg,
            "show_avatar": show_avatar,
            "is_first_in_group": is_first_in_group,
            "is_last_in_group": is_last_in_group,
            "formatted_time": formatted_time,
        })

    return items


class MessengerPdfGenerator:
    def __init__(self, template_dir: Optional[str] = None):
        if not template_dir:
            template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
        )
        self.template = self.jinja_env.get_template("messenger_template.html")

    def _resolve_style(
        self,
        style: Optional[PdfStyleConfig],
        page_size: str = "A5",
    ) -> PdfStyleConfig:
        if style is None:
            return PdfStyleConfig(page_size=page_size)
        if page_size and style.page_size != page_size and page_size != "A5":
            return replace(style, page_size=page_size)
        return style

    def render_html(
        self,
        messages: List[Dict[str, Any]],
        month_key: str,
        primary_sender: str = "",
        chat_heading: Optional[str] = None,
        page_size: str = "A5",
        avatar_url: Optional[str] = None,
        style: Optional[PdfStyleConfig] = None,
    ) -> str:
        """Render the HTML content for a single period (month, year, or complete archive)."""
        active_style = self._resolve_style(style, page_size)
        loc = LOCALES.get(active_style.language, LOCALES["en"])
        period_title = format_period_title(month_key, active_style.language)

        senders = sorted({m["sender"] for m in messages}) if messages else []
        if not primary_sender and senders:
            primary_sender = senders[0]

        if not chat_heading:
            chat_heading = " & ".join(senders) if senders else "Messenger Chat"

        items = prepare_template_items(
            messages=messages,
            language=active_style.language,
            time_format_24h=active_style.time_format_24h,
        )

        font_family_css = FONT_FAMILIES.get(
            active_style.font_family, FONT_FAMILIES["sans"]
        )

        html = self.template.render(
            items=items,
            messages=messages,
            period_title=period_title,
            message_count=len(messages),
            messages_label=loc["messages_label"],
            primary_sender=primary_sender,
            is_primary_sender=is_primary_sender,
            chat_heading=chat_heading,
            avatar_url=avatar_url,
            style=active_style,
            font_family_css=font_family_css,
        )
        return html

    def _export_page_to_pdf(
        self, page: Any, output_filepath: str, style: PdfStyleConfig
    ) -> None:
        valid_formats = {"A4", "A5", "A6", "Letter", "Legal"}
        format_choice = style.page_size if style.page_size in valid_formats else "A5"
        margin_str = f"{style.margin_mm}mm"

        footer_html = "<div></div>"
        if style.show_page_numbers:
            footer_html = f"""
                <div style="font-size: 8px; font-family: -apple-system, sans-serif; color: {style.muted_text_color}; width: 100%; text-align: center;">
                    <span class="pageNumber"></span> / <span class="totalPages"></span>
                </div>
            """

        page.pdf(
            path=output_filepath,
            format=format_choice,
            landscape=style.landscape,
            print_background=True,
            margin={
                "top": margin_str,
                "bottom": margin_str,
                "left": margin_str,
                "right": margin_str,
            },
            display_header_footer=style.show_page_numbers,
            header_template="<div></div>",
            footer_template=footer_html,
        )

    def generate_pdf_for_month(
        self,
        messages: List[Dict[str, Any]],
        month_key: str,
        output_filepath: str,
        primary_sender: str = "",
        chat_heading: Optional[str] = None,
        page_size: str = "A5",
        avatar_url: Optional[str] = None,
        style: Optional[PdfStyleConfig] = None,
    ) -> str:
        """Generate PDF for a single period and save to output_filepath."""
        active_style = self._resolve_style(style, page_size)
        html_content = self.render_html(
            messages=messages,
            month_key=month_key,
            primary_sender=primary_sender,
            chat_heading=chat_heading,
            page_size=active_style.page_size,
            avatar_url=avatar_url,
            style=active_style,
        )

        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content, wait_until="networkidle")
            self._export_page_to_pdf(page, output_filepath, active_style)
            browser.close()

        return output_filepath

    def generate_all_months(
        self,
        grouped_messages: Dict[str, List[Dict[str, Any]]],
        output_dir: str,
        primary_sender: str = "",
        chat_heading: Optional[str] = None,
        page_size: str = "A5",
        avatar_url: Optional[str] = None,
        style: Optional[PdfStyleConfig] = None,
        progress_callback: Optional[Any] = None,
        filename_prefix: str = "Messenger",
    ) -> List[str]:
        """
        Generate separate PDF for each group in grouped_messages.
        Default naming: Messenger_YYYY_MM.pdf
        """
        active_style = self._resolve_style(style, page_size)
        generated_files = []
        os.makedirs(output_dir, exist_ok=True)

        sorted_keys = sorted(grouped_messages.keys())
        total = len(sorted_keys)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            for idx, group_key in enumerate(sorted_keys):
                msgs = grouped_messages[group_key]
                if not msgs:
                    continue

                safe_key = group_key.replace("-", "_")
                filename = f"{filename_prefix}_{safe_key}.pdf"
                filepath = os.path.join(output_dir, filename)

                html_content = self.render_html(
                    messages=msgs,
                    month_key=group_key,
                    primary_sender=primary_sender,
                    chat_heading=chat_heading,
                    page_size=active_style.page_size,
                    avatar_url=avatar_url,
                    style=active_style,
                )

                page.set_content(html_content, wait_until="networkidle")
                self._export_page_to_pdf(page, filepath, active_style)
                generated_files.append(filepath)

                if progress_callback:
                    progress_callback(idx + 1, total, filename)

            browser.close()

        return generated_files
