"""
Command Line Interface (CLI) for converting Messenger JSON chats into customizable print-ready PDFs.

Examples:
    python cli.py --input sample_data/sample_chat.json --output output_pdf --primary "Alex Rivera"
    python cli.py --folder /path/to/json_folder --theme dark_mode --size A4 --font serif
"""

import os
import glob
import argparse
from datetime import datetime
from chat_parser import (
    load_chat_files,
    filter_messages_by_date_range,
    group_messages,
)
from pdf_generator import (
    MessengerPdfGenerator,
    PdfStyleConfig,
    THEME_PRESETS,
    FONT_FAMILIES,
    LOCALES,
)


def parse_date_arg(date_str: str):
    """Parse YYYY-MM-DD string into a date object."""
    if not date_str:
        return None
    return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(
        description="Messenger Chat JSON to Customizable Printable PDF Converter",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Input / Output
    io_group = parser.add_argument_group("Input & Output")
    io_group.add_argument("-i", "--input", nargs="+", help="Path to one or more Messenger JSON files")
    io_group.add_argument("-f", "--folder", help="Path to a folder containing JSON files")
    io_group.add_argument("-o", "--output", default="output_pdf", help="Output directory for generated PDFs")
    io_group.add_argument("--prefix", default="Messenger", help="Filename prefix for generated PDFs")
    io_group.add_argument(
        "--group-by",
        default="month",
        choices=["month", "year", "single"],
        help="How to split generated PDF files (by month, by year, or single combined PDF)",
    )
    io_group.add_argument("--start-date", default=None, help="Filter messages from date (YYYY-MM-DD)")
    io_group.add_argument("--end-date", default=None, help="Filter messages up to date (YYYY-MM-DD)")

    # Participants & Header
    header_group = parser.add_argument_group("Sender & Header")
    header_group.add_argument(
        "-p",
        "--primary",
        default="",
        help="Name of the primary sender for right-hand bubbles (auto-detects first participant if omitted)",
    )
    header_group.add_argument("-t", "--title", default=None, help="Custom chat heading in the PDF header")
    header_group.add_argument("--subtitle", default=None, help="Optional custom subtitle in the PDF header")
    header_group.add_argument("--avatar-url", default=None, help="Optional URL or data URI for received avatar image")

    # Page & Print Layout
    page_group = parser.add_argument_group("Page & Print Layout")
    page_group.add_argument(
        "-s",
        "--size",
        default="A5",
        choices=["A5", "A4", "Letter", "A6"],
        help="Page size format",
    )
    page_group.add_argument("--landscape", action="store_true", help="Use landscape page orientation")
    page_group.add_argument("--margin", type=int, default=12, help="Page margins in millimeters (mm)")

    # Theme & Custom Colors
    theme_group = parser.add_argument_group("Theme & Colors")
    theme_group.add_argument(
        "--theme",
        default="messenger_blue",
        choices=list(THEME_PRESETS.keys()),
        help="Visual color theme preset",
    )
    theme_group.add_argument("--bg-color", default=None, help="Override page background hex color (e.g. #ffffff)")
    theme_group.add_argument("--sent-color", default=None, help="Override sent bubble hex color (e.g. #0084ff)")
    theme_group.add_argument("--sent-text-color", default=None, help="Override sent text hex color (e.g. #ffffff)")
    theme_group.add_argument("--received-color", default=None, help="Override received bubble hex color (e.g. #f0f2f5)")
    theme_group.add_argument("--received-text-color", default=None, help="Override received text hex color (e.g. #050505)")
    theme_group.add_argument("--accent-color", default=None, help="Override header accent hex color")
    theme_group.add_argument("--avatar-color", default=None, help="Override avatar badge hex color")

    # Typography & Bubbles
    typo_group = parser.add_argument_group("Typography & Bubble Style")
    typo_group.add_argument(
        "--font",
        default="sans",
        choices=list(FONT_FAMILIES.keys()),
        help="Font family style",
    )
    typo_group.add_argument("--font-size", type=float, default=9.0, help="Base font size in points (pt)")
    typo_group.add_argument("--bubble-radius", type=int, default=18, help="Bubble corner radius in pixels (px)")
    typo_group.add_argument("--bubble-width", type=int, default=75, help="Maximum bubble width as percentage (55-90)")
    typo_group.add_argument("--compact", action="store_true", help="Enable compact vertical spacing to fit more messages")

    # Visibility & Localization
    vis_group = parser.add_argument_group("Elements & Localization")
    vis_group.add_argument(
        "--lang",
        default="en",
        choices=list(LOCALES.keys()),
        help="Language for month names and date dividers",
    )
    vis_group.add_argument("--time-12h", action="store_true", help="Use 12-hour timestamp format (AM/PM) instead of 24-hour")
    vis_group.add_argument("--show-sender-names", action="store_true", help="Display sender names above received bubbles")
    vis_group.add_argument("--no-header", action="store_true", help="Hide the top cover header")
    vis_group.add_argument("--no-message-count", action="store_true", help="Hide message count in the header")
    vis_group.add_argument("--no-dividers", action="store_true", help="Hide date dividers between days")
    vis_group.add_argument("--no-avatars", action="store_true", help="Hide sender avatars")
    vis_group.add_argument("--no-timestamps", action="store_true", help="Hide message timestamps")
    vis_group.add_argument("--no-reactions", action="store_true", help="Hide emoji reaction badges")
    vis_group.add_argument("--no-photos", action="store_true", help="Hide attached photos")
    vis_group.add_argument("--no-page-numbers", action="store_true", help="Hide page numbers in the PDF footer")

    args = parser.parse_args()

    file_list = []
    if args.input:
        file_list.extend(args.input)
    if args.folder:
        matched = glob.glob(os.path.join(args.folder, "*.json"))
        file_list.extend(matched)

    if not file_list:
        print("❌ Error: Please specify at least one JSON file via --input or a folder via --folder.")
        print("Example: python cli.py --input sample_data/sample_chat.json --output output_pdf")
        return

    print(f"🔍 Loading chat files ({len(file_list)} file(s) found)...")
    messages, meta = load_chat_files(file_list)

    start_dt = parse_date_arg(args.start_date)
    end_dt = parse_date_arg(args.end_date)
    messages = filter_messages_by_date_range(messages, start_dt, end_dt)

    if not messages:
        print("⚠️ No messages found after loading and filtering.")
        return

    participants = meta["participants"]
    primary_sender = args.primary or (participants[0] if participants else "")

    print(f"✅ Loaded {len(messages)} messages.")
    print(f"👥 Participants: {', '.join(participants)}")
    print(f"👉 Primary sender (right-side bubbles): {primary_sender}")

    grouped = group_messages(messages, mode=args.group_by)
    print(f"📅 Grouped into {len(grouped)} PDF document(s): {', '.join(sorted(grouped.keys()))}")

    style = PdfStyleConfig.from_theme(
        args.theme,
        page_size=args.size,
        landscape=args.landscape,
        margin_mm=args.margin,
        bg_color=args.bg_color,
        sent_bubble_color=args.sent_color,
        sent_text_color=args.sent_text_color,
        received_bubble_color=args.received_color,
        received_text_color=args.received_text_color,
        accent_color=args.accent_color,
        avatar_bg_color=args.avatar_color,
        font_family=args.font,
        font_size_pt=args.font_size,
        bubble_radius_px=args.bubble_radius,
        max_bubble_width_pct=args.bubble_width,
        compact_mode=args.compact,
        show_header=not args.no_header,
        show_message_count=not args.no_message_count,
        show_date_dividers=not args.no_dividers,
        show_avatars=not args.no_avatars,
        show_sender_names=args.show_sender_names,
        show_timestamps=not args.no_timestamps,
        time_format_24h=not args.time_12h,
        show_reactions=not args.no_reactions,
        show_photos=not args.no_photos,
        show_page_numbers=not args.no_page_numbers,
        language=args.lang,
        custom_subtitle=args.subtitle,
    )

    def on_progress(current, total, filename):
        print(f"  [{current}/{total}] Generated: {filename}")

    gen = MessengerPdfGenerator()
    print(
        f"\n🚀 Generating PDFs (Size: {args.size}, Theme: {args.theme}, Font: {args.font})..."
    )
    results = gen.generate_all_months(
        grouped_messages=grouped,
        output_dir=args.output,
        primary_sender=primary_sender,
        chat_heading=args.title,
        page_size=args.size,
        avatar_url=args.avatar_url,
        style=style,
        progress_callback=on_progress,
        filename_prefix=args.prefix,
    )

    print(f"\n🎉 Done! Generated {len(results)} PDF file(s) in '{args.output}'.")


if __name__ == "__main__":
    main()
