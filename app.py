"""
Interactive Streamlit Web Application for converting Messenger JSON chats into customizable print-ready PDFs.
"""

import os
import io
import json
import glob
import base64
import zipfile
import tempfile
import streamlit as st
import streamlit.components.v1 as components

from chat_parser import (
    load_messages_from_data,
    load_chat_files,
    filter_messages_by_date_range,
    group_messages,
)
from pdf_generator import (
    MessengerPdfGenerator,
    PdfStyleConfig,
    THEME_PRESETS,
    LOCALES,
    format_period_title,
    is_primary_sender,
)

st.set_page_config(
    page_title="Messenger Chat to PDF Converter",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Streamlit UI
st.markdown(
    """
<style>
    .header-card {
        background: linear-gradient(135deg, rgba(0, 132, 255, 0.14) 0%, rgba(233, 30, 99, 0.12) 100%);
        border: 1px solid rgba(0, 132, 255, 0.3);
        border-radius: 14px;
        padding: 24px;
        margin-bottom: 20px;
        text-align: center;
    }
    .header-title {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(90deg, #0084ff, #a033ff, #ff4081);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
    }
    .header-desc {
        color: #9ca3af;
        font-size: 1rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


def encode_uploaded_image(uploaded_img) -> str:
    """Convert an uploaded image file into a base64 data URI."""
    mime = uploaded_img.type or "image/png"
    b64 = base64.b64encode(uploaded_img.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def main():
    st.markdown(
        """
    <div class="header-card">
        <div class="header-title">Messenger JSON to Printable PDF</div>
        <div class="header-desc">
            Transform exported Facebook Messenger JSON chats into customizable, print-ready PDF booklets.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------------------
    # SIDEBAR: PDF Appearance & Export Settings
    # -------------------------------------------------------------------------
    with st.sidebar:
        st.header("PDF Appearance & Layout")

        # 1. Theme & Colors
        theme_keys = list(THEME_PRESETS.keys())
        theme_labels = {k: THEME_PRESETS[k]["label"] for k in theme_keys}
        selected_theme = st.selectbox(
            "Theme Preset",
            options=theme_keys,
            format_func=lambda k: theme_labels[k],
            index=0,
            help="Choose a visual style preset. You can further customize every color below.",
        )
        preset = THEME_PRESETS[selected_theme]

        with st.expander("Customize Colors", expanded=False):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                bg_color = st.color_picker("Page Background", value=preset["bg_color"], key=f"bg_{selected_theme}")
                sent_bubble_color = st.color_picker("Sent Bubble", value=preset["sent_bubble_color"], key=f"sb_{selected_theme}")
                sent_text_color = st.color_picker("Sent Text", value=preset["sent_text_color"], key=f"st_{selected_theme}")
                accent_color = st.color_picker("Header Accent", value=preset["accent_color"], key=f"ac_{selected_theme}")
            with col_c2:
                received_bubble_color = st.color_picker("Received Bubble", value=preset["received_bubble_color"], key=f"rb_{selected_theme}")
                received_text_color = st.color_picker("Received Text", value=preset["received_text_color"], key=f"rt_{selected_theme}")
                avatar_bg_color = st.color_picker("Avatar Badge", value=preset["avatar_bg_color"], key=f"av_{selected_theme}")
                divider_bg_color = st.color_picker("Date Badge", value=preset["divider_bg_color"], key=f"dv_{selected_theme}")

        # 2. Page & Print Setup
        with st.expander("Page & Print Setup", expanded=True):
            group_mode = st.selectbox(
                "Split PDFs By",
                options=["month", "year", "single"],
                format_func=lambda x: {
                    "month": "Month (e.g. Messenger_2025_06.pdf)",
                    "year": "Year (e.g. Messenger_2025.pdf)",
                    "single": "Single Combined PDF",
                }[x],
                index=0,
            )

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                page_size = st.selectbox(
                    "Page Size",
                    options=["A5", "A4", "Letter", "A6"],
                    index=0,
                    help="A5 is great for printed booklets; A4 and Letter are standard document sizes.",
                )
            with col_p2:
                orientation = st.selectbox(
                    "Orientation",
                    options=["Portrait", "Landscape"],
                    index=0,
                )

            margin_mm = st.slider(
                "Page Margins (mm)",
                min_value=6,
                max_value=25,
                value=12,
                step=1,
            )

            filename_prefix = st.text_input(
                "Filename Prefix",
                value="Messenger",
                help="Prefix for generated PDF filenames (e.g., Messenger_2025_06.pdf).",
            )

        # 3. Typography & Bubble Shape
        with st.expander("Typography & Bubble Style", expanded=False):
            font_family = st.selectbox(
                "Font Family",
                options=["sans", "serif", "rounded", "mono"],
                format_func=lambda f: {
                    "sans": "Modern Sans-Serif (Default)",
                    "serif": "Classic Serif (Book Style)",
                    "rounded": "Soft Rounded Sans",
                    "mono": "Monospace",
                }[f],
                index=0,
            )

            font_size_pt = st.slider(
                "Font Size (pt)",
                min_value=7.0,
                max_value=13.0,
                value=9.0,
                step=0.5,
            )

            bubble_radius_px = st.slider(
                "Bubble Corner Radius (px)",
                min_value=0,
                max_value=24,
                value=18,
                step=2,
            )

            max_bubble_width_pct = st.slider(
                "Max Bubble Width (%)",
                min_value=55,
                max_value=90,
                value=75,
                step=5,
            )

            compact_mode = st.checkbox(
                "Compact Spacing Mode",
                value=False,
                help="Reduces vertical spacing and padding to fit more messages per page.",
            )

        # 4. Elements & Localization
        with st.expander("Visible Elements & Language", expanded=False):
            language = st.selectbox(
                "PDF Language (Months & Dates)",
                options=list(LOCALES.keys()),
                format_func=lambda k: LOCALES[k]["name"],
                index=0,
            )

            time_format_choice = st.radio(
                "Timestamp Format",
                options=["24h", "12h"],
                format_func=lambda x: "24-hour (14:30)" if x == "24h" else "12-hour (2:30 PM)",
                horizontal=True,
            )

            show_header = st.checkbox("Show Cover Header", value=True)
            show_message_count = st.checkbox("Show Message Count in Header", value=True)
            show_date_dividers = st.checkbox("Show Date Dividers", value=True)
            show_avatars = st.checkbox("Show Sender Avatars", value=True)
            show_sender_names = st.checkbox(
                "Show Sender Names Above Bubbles",
                value=False,
                help="Useful for group chats with more than two participants.",
            )
            show_timestamps = st.checkbox("Show Message Timestamps", value=True)
            show_reactions = st.checkbox("Show Emoji Reactions", value=True)
            show_photos = st.checkbox("Show Attached Photos", value=True)
            show_page_numbers = st.checkbox("Show Page Numbers in Footer", value=True)

        # 5. Header & Avatar Customization
        with st.expander("Custom Header & Avatar", expanded=False):
            custom_title = st.text_input(
                "Custom Header Title (optional)",
                placeholder="e.g. Alex & Sam",
                help="Leave blank to automatically join participant names.",
            )
            custom_subtitle = st.text_input(
                "Custom Subtitle (optional)",
                placeholder="e.g. Summer Memories",
            )
            avatar_file = st.file_uploader(
                "Custom Avatar Image (optional)",
                type=["png", "jpg", "jpeg", "webp"],
                help="Upload an avatar image for received messages (otherwise sender initials are used).",
            )
            avatar_url = encode_uploaded_image(avatar_file) if avatar_file else None

    # Build the PdfStyleConfig object from sidebar controls
    style_config = PdfStyleConfig(
        page_size=page_size,
        landscape=(orientation == "Landscape"),
        margin_mm=margin_mm,
        theme=selected_theme,
        bg_color=bg_color,
        sent_bubble_color=sent_bubble_color,
        sent_text_color=sent_text_color,
        received_bubble_color=received_bubble_color,
        received_text_color=received_text_color,
        accent_color=accent_color,
        avatar_bg_color=avatar_bg_color,
        muted_text_color=preset["muted_text_color"],
        divider_bg_color=divider_bg_color,
        font_family=font_family,
        font_size_pt=font_size_pt,
        bubble_radius_px=bubble_radius_px,
        max_bubble_width_pct=max_bubble_width_pct,
        compact_mode=compact_mode,
        show_header=show_header,
        show_message_count=show_message_count,
        show_date_dividers=show_date_dividers,
        show_avatars=show_avatars,
        show_sender_names=show_sender_names,
        show_timestamps=show_timestamps,
        time_format_24h=(time_format_choice == "24h"),
        show_reactions=show_reactions,
        show_photos=show_photos,
        show_page_numbers=show_page_numbers,
        language=language,
        custom_subtitle=custom_subtitle.strip() if custom_subtitle else None,
    )

    # -------------------------------------------------------------------------
    # DATA SOURCE TABS
    # -------------------------------------------------------------------------
    tab_upload, tab_folder, tab_sample = st.tabs([
        "Upload JSON Files",
        "Load from Local Folder",
        "Try Sample Chat",
    ])

    raw_messages = []

    with tab_upload:
        uploaded_files = st.file_uploader(
            "Select one or more Messenger JSON files (e.g. message_1.json, message_2.json)",
            type=["json"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            for f in uploaded_files:
                try:
                    data = json.loads(f.read().decode("utf-8"))
                    msgs = load_messages_from_data(data)
                    raw_messages.extend(msgs)
                except Exception as e:
                    st.error(f"Error reading file {f.name}: {e}")
            if raw_messages:
                st.session_state["loaded_messages"] = raw_messages

    with tab_folder:
        folder_path = st.text_input(
            "Path to a local folder containing JSON files:",
            placeholder="/path/to/messenger_export/",
        )
        if folder_path and os.path.exists(folder_path):
            json_files = glob.glob(os.path.join(folder_path, "*.json"))
            if json_files:
                st.info(f"Found {len(json_files)} JSON file(s) in folder.")
                if st.button("Load JSON Files from Folder"):
                    msgs, _ = load_chat_files(json_files)
                    st.session_state["loaded_messages"] = msgs
            else:
                st.warning("No .json files found in the specified folder.")

    with tab_sample:
        st.write(
            "Load the built-in sample conversation (**Alex Rivera & Sam Carter**, June–July 2025) "
            "to preview themes, fonts, and PDF generation."
        )
        if st.button("Load Sample Conversation"):
            sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "sample_chat.json")
            msgs, _ = load_chat_files([sample_path])
            st.session_state["loaded_messages"] = msgs

    if not raw_messages and "loaded_messages" in st.session_state:
        raw_messages = st.session_state["loaded_messages"]

    # -------------------------------------------------------------------------
    # MAIN WORKSPACE: Filter, Preview & Generate PDFs
    # -------------------------------------------------------------------------
    if raw_messages:
        raw_messages.sort(key=lambda m: m["datetime"])
        all_participants = sorted(list({m["sender"] for m in raw_messages}))

        min_date = raw_messages[0]["datetime"].date()
        max_date = raw_messages[-1]["datetime"].date()

        st.markdown("### Chat Configuration & Filtering")
        cfg_col1, cfg_col2, cfg_col3 = st.columns([2, 2, 2])

        with cfg_col1:
            active_primary = st.selectbox(
                "Primary Sender (Right-hand bubbles):",
                options=all_participants,
                index=0,
                help="Messages from this participant appear on the right side.",
            )
        with cfg_col2:
            start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
        with cfg_col3:
            end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

        filtered_messages = filter_messages_by_date_range(raw_messages, start_date, end_date)
        grouped = group_messages(filtered_messages, mode=group_mode)

        if not filtered_messages:
            st.warning("No messages match the selected date range.")
            return

        # Metrics Summary
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Total Messages", len(filtered_messages))
        with m_col2:
            st.metric("Participants", ", ".join(all_participants))
        with m_col3:
            st.metric("PDF Files to Generate", len(grouped))

        st.markdown("---")

        # Workspace Tabs: Live Preview vs Generate PDFs
        preview_tab, export_tab = st.tabs([
            "Live Appearance Preview",
            "Generate & Download PDFs",
        ])

        gen = MessengerPdfGenerator()
        sorted_group_keys = sorted(grouped.keys())

        with preview_tab:
            p_col1, p_col2 = st.columns([3, 1])
            with p_col1:
                preview_key = st.selectbox(
                    "Select Period to Preview:",
                    options=sorted_group_keys,
                    format_func=lambda k: f"{format_period_title(k, language)} ({len(grouped[k])} messages)",
                )
            with p_col2:
                max_preview_msgs = st.number_input(
                    "Max Preview Messages",
                    min_value=10,
                    max_value=500,
                    value=100,
                    step=25,
                    help="Limit messages shown in the live preview for fast rendering.",
                )

            preview_msgs = grouped[preview_key][: int(max_preview_msgs)]
            preview_html = gen.render_html(
                messages=preview_msgs,
                month_key=preview_key,
                primary_sender=active_primary,
                chat_heading=custom_title.strip() if custom_title else None,
                page_size=page_size,
                avatar_url=avatar_url,
                style=style_config,
            )

            # Wrap in a realistic page frame for live preview
            preview_wrapper = f"""
            <div style="background: #1e1e24; padding: 24px; border-radius: 12px; display: flex; justify-content: center;">
                <div style="width: 100%; max-width: {'720px' if page_size in ['A4', 'Letter'] else '540px'};
                            background: {style_config.bg_color};
                            padding: {style_config.margin_mm * 2.5}px;
                            border-radius: 8px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.45);
                            overflow-y: auto;
                            max-height: 680px;">
                    {preview_html}
                </div>
            </div>
            """
            components.html(preview_wrapper, height=740, scrolling=True)

            st.download_button(
                label=f"Download Preview HTML ({preview_key}.html)",
                data=preview_html.encode("utf-8"),
                file_name=f"{filename_prefix}_{preview_key.replace('-', '_')}.html",
                mime="text/html",
            )

        with export_tab:
            st.subheader("Select Periods to Export")
            selected_keys = st.multiselect(
                "Choose which periods to render into PDF:",
                options=sorted_group_keys,
                default=sorted_group_keys,
                format_func=lambda k: f"{format_period_title(k, language)} ({len(grouped[k])} messages)",
            )

            if st.button(
                "Generate Printable PDFs",
                type="primary",
                use_container_width=True,
                disabled=(len(selected_keys) == 0),
            ):
                progress_bar = st.progress(0)
                status_text = st.empty()

                with tempfile.TemporaryDirectory() as tmp_dir:
                    total_items = len(selected_keys)
                    generated_files_data = []

                    for idx, g_key in enumerate(selected_keys):
                        title_str = format_period_title(g_key, language)
                        status_text.write(
                            f"Rendering PDF for **{title_str}** ({idx + 1}/{total_items})..."
                        )

                        safe_prefix = (filename_prefix.strip() or "Messenger").replace(" ", "_")
                        filename = f"{safe_prefix}_{g_key.replace('-', '_')}.pdf"
                        pdf_path = os.path.join(tmp_dir, filename)

                        gen.generate_pdf_for_month(
                            messages=grouped[g_key],
                            month_key=g_key,
                            output_filepath=pdf_path,
                            primary_sender=active_primary,
                            chat_heading=custom_title.strip() if custom_title else None,
                            page_size=page_size,
                            avatar_url=avatar_url,
                            style=style_config,
                        )

                        with open(pdf_path, "rb") as pf:
                            generated_files_data.append((filename, pf.read()))

                        progress_bar.progress((idx + 1) / total_items)

                    status_text.success(f"Successfully generated {len(generated_files_data)} PDF file(s)!")

                    # Build ZIP archive in memory
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for fname, fbytes in generated_files_data:
                            zip_file.writestr(fname, fbytes)
                    zip_buffer.seek(0)

                    st.download_button(
                        label="Download All PDFs as ZIP Archive",
                        data=zip_buffer,
                        file_name=f"{filename_prefix.strip() or 'Messenger'}_PDF_Export.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True,
                    )

                    if len(generated_files_data) <= 12:
                        st.markdown("#### Individual PDF Downloads")
                        cols = st.columns(min(3, len(generated_files_data)))
                        for i, (fname, fbytes) in enumerate(generated_files_data):
                            with cols[i % len(cols)]:
                                st.download_button(
                                    label=f"⬇️ {fname}",
                                    data=fbytes,
                                    file_name=fname,
                                    mime="application/pdf",
                                    key=f"dl_{fname}",
                                    use_container_width=True,
                                )


if __name__ == "__main__":
    main()
