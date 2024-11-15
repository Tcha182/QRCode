import streamlit as st
import pandas as pd
import qrcode
import qrcode.image.svg
from PIL import ImageFont, ImageDraw, Image
from io import BytesIO
import zipfile
import os
from collections import defaultdict

st.set_page_config(page_title="QR Code Explore", page_icon=":material/qr_code_2:")

st.markdown(
    """
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .css-1v0mbdj {padding-top: 0rem;}
    </style>
    """,
    unsafe_allow_html=True
)

st.logo("explore.png")

# Path to the bundled Arial font file
FONT_PATH = os.path.join(os.path.dirname(__file__), "arial.ttf")

def generate_qr_code(link, text=None, add_text=False, box_size=30, format='PNG', dpi=300):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=0
    )
    qr.add_data(link)
    qr.make(fit=True)

    if format == 'SVG':
        # Generate SVG directly using SVG image factory
        img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        buffer = BytesIO()
        img.save(buffer)
        buffer.seek(0)
        return buffer
    else:
        # Generate PNG
        img = qr.make_image(fill='black', back_color='white')
        qr_width, qr_height = img.size

        if add_text and text:
            try:
                font = ImageFont.truetype(FONT_PATH, 60)
            except IOError:
                st.error("Font file not found. Using default font.")
                font = ImageFont.load_default()

            text = str(text)

            # Get text dimensions using getbbox
            text_bbox = font.getbbox(text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            # Add padding to the image height to avoid cropping
            padding = 30  # Increase padding as needed
            combined_image = Image.new('RGB', (qr_width, qr_height + text_height + padding), 'white')
            draw = ImageDraw.Draw(combined_image)
            combined_image.paste(img, (0, 0))

            # Align text to the right, slightly higher to avoid cropping
            text_position = (qr_width - text_width - 10, qr_height + 10)  # Right alignment with 10px padding from the edge
            draw.text(text_position, text, fill='black', font=font)
            img = combined_image

        buffer = BytesIO()
        img.save(buffer, format="PNG", dpi=(dpi, dpi))
        buffer.seek(0)
        return buffer


def find_most_likely_url_column(df):
    """Identify the column most likely to contain URLs."""
    url_keywords = ['http://', 'https://', 'www.']
    url_scores = {}

    for column in df.columns:
        score = sum(df[column].astype(str).str.contains('|'.join(url_keywords)))
        url_scores[column] = score

    # Get the column with the highest score
    likely_url_column = max(url_scores, key=url_scores.get, default=None)
    return likely_url_column

st.title("QR Code Generator")

# Store the previous file and columns in session state
if 'prev_uploaded_file' not in st.session_state:
    st.session_state.prev_uploaded_file = None
if 'prev_link_column' not in st.session_state:
    st.session_state.prev_link_column = None
if 'prev_text_column' not in st.session_state:
    st.session_state.prev_text_column = None

uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])

# Clear session state if a new file is uploaded or columns change
if uploaded_file and (uploaded_file != st.session_state.prev_uploaded_file):
    st.session_state.prev_uploaded_file = uploaded_file
    st.session_state.images_png = {}
    st.session_state.images_svg = {}

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        
        # Sanity check: Ensure the dataframe has at least one row and two columns
        if df.shape[0] < 1 or df.shape[1] < 2:
            st.error("The file must contain at least one row and two columns. Please upload a valid file.")
        else:
            with st.expander("**Data**", expanded=True, icon=":material/table:"):
                st.dataframe(df, use_container_width=True)

            qr_codes_count = len(df)
            plural = "s" if qr_codes_count > 1 else ""

            col1, col2 = st.columns(2)

            # Attempt to automatically detect the most likely URL column
            likely_url_column = None
            try:
                likely_url_column = find_most_likely_url_column(df)
            except Exception as e:
                st.warning(f"Failed to automatically detect URL column: {e}")

            # Set default selection based on detection, fallback to default selection
            if likely_url_column:
                link_column = col1.selectbox(f"Select the column with URL{plural}", df.columns, index=df.columns.get_loc(likely_url_column))
            else:
                link_column = col1.selectbox(f"Select the column with URL{plural}", df.columns)

            text_column = col2.selectbox(f"Select the column with name{plural}", df.columns, key='text_column')
            add_text = st.checkbox(f"Add name{plural} to QR code{plural}", value=True)

            # Clear session state if columns change
            if (link_column != st.session_state.prev_link_column) or (text_column != st.session_state.prev_text_column):
                st.session_state.images_png = {}
                st.session_state.images_svg = {}
                st.session_state.prev_link_column = link_column
                st.session_state.prev_text_column = text_column

            name_count = defaultdict(int)  # Track occurrences of each name
            duplicate_detected = df[text_column].duplicated().any()

            if duplicate_detected:
                st.warning("There are duplicate names in the selected column. Unique filenames will be generated.")

            col1, col2 = st.columns(2)

            generate_qr_codes = col1.button(f"**Generate QR Code{plural}**", use_container_width=True)

            if generate_qr_codes:
                if 'images_png' not in st.session_state:
                    st.session_state.images_png = {}
                if 'images_svg' not in st.session_state:
                    st.session_state.images_svg = {}

                progress_container = col2.empty()
                progress_bar = progress_container.progress(0)

                for idx, row in df.iterrows():
                    link = row[link_column]
                    text = row[text_column]

                    if pd.isna(link) or pd.isna(text):
                        st.error(f"Missing data in row {idx + 1}. Skipping.")
                        continue

                    name_count[text] += 1
                    filename = f"{text}_{name_count[text]}" if duplicate_detected else text

                    png_buffer = generate_qr_code(link, text, add_text, format='PNG')
                    svg_buffer = generate_qr_code(link, text, add_text, format='SVG')
                    st.session_state.images_png[filename] = png_buffer
                    st.session_state.images_svg[filename] = svg_buffer

                    progress = (idx + 1) / qr_codes_count
                    progress_bar.progress(progress, f"Processing {idx + 1}/{qr_codes_count}")

                progress_container.empty()
                st.toast(f"QR code{plural} generation complete!", icon="✅")

    except Exception as e:
        st.error(f"Failed to load the file: {e}")

    if 'images_png' in st.session_state and st.session_state.images_png:
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_file:
            for filename, png_buffer in st.session_state.images_png.items():
                png_buffer.seek(0)
                zip_file.writestr(f"PNG/{filename}.png", png_buffer.read())
            for filename, svg_buffer in st.session_state.images_svg.items():
                svg_buffer.seek(0)
                zip_file.writestr(f"SVG/{filename}.svg", svg_buffer.read())
        zip_buffer.seek(0)

        col2.download_button(
            label=f"**Download QR Code{plural}**", 
            data=zip_buffer,
            file_name="qr_codes.zip",
            mime="application/zip",
            use_container_width=True
        )

        QR_Review = st.expander(f"**QR Code{plural}**", expanded=True, icon=":material/qr_code:")

        qr_codes_keys = list(st.session_state.images_png.keys())

        if len(qr_codes_keys) > 1:
            selected_name = QR_Review.selectbox("Select a QR Code to display", qr_codes_keys)
        else:
            selected_name = qr_codes_keys[0]  # Automatically select the only available option

        if selected_name:
            png_buffer = st.session_state.images_png[selected_name]
            png_buffer.seek(0)
            QR_Review.image(png_buffer, caption=f"{selected_name}.png", use_container_width=True)
