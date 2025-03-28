import streamlit as st
import pandas as pd
import qrcode
import qrcode.image.svg
from PIL import ImageFont, ImageDraw, Image
from io import BytesIO
import zipfile
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Set page configuration and hide default Streamlit UI elements
st.set_page_config(page_title="QR Code RATP DEV", page_icon=":material/qr_code_2:")
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


# Path to the bundled Arial font file
FONT_PATH = os.path.join(os.path.dirname(__file__), "arial.ttf")

@st.cache_resource
def load_font(font_path=FONT_PATH, font_size=60):
    """
    Load the TrueType font once, with caching.
    """
    try:
        return ImageFont.truetype(font_path, font_size)
    except IOError:
        st.warning("Font file not found. Using default font.")
        return ImageFont.load_default()

# Preload the font
FONT = load_font()

def generate_qr_object(link, box_size=30):
    """
    Generate a QRCode object for the given link.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=0
    )
    qr.add_data(link)
    qr.make(fit=True)
    return qr

def qr_to_svg(qr):
    """
    Convert a QRCode object to an SVG buffer.
    """
    buffer = BytesIO()
    img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
    img.save(buffer)
    buffer.seek(0)
    return buffer

def qr_to_png(qr, text=None, add_text=False, dpi=300):
    """
    Convert a QRCode object to a PNG buffer.
    If add_text is True and text is provided, append the text to the QR image.
    """
    img = qr.make_image(fill="black", back_color="white").convert("RGB")
    if add_text and text:
        text = str(text)
        qr_width, qr_height = img.size
        # Create a temporary image to calculate text dimensions
        draw_temp = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        text_bbox = draw_temp.textbbox((0, 0), text, font=FONT)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        padding = 30
        combined_image = Image.new("RGB", (qr_width, qr_height + text_height + padding), "white")
        combined_image.paste(img, (0, 0, qr_width, qr_height))
        draw = ImageDraw.Draw(combined_image)
        text_position = (qr_width - text_width - 10, qr_height + 10)
        draw.text(text_position, text, fill="black", font=FONT)
        img = combined_image

    buffer = BytesIO()
    img.save(buffer, format="PNG", dpi=(dpi, dpi))
    buffer.seek(0)
    return buffer

def find_most_likely_url_column(df):
    """
    Identify the column in a DataFrame that is most likely to contain URLs.
    """
    url_keywords = ['http://', 'https://', 'www.']
    url_scores = {}
    pattern = '|'.join(url_keywords)
    for column in df.columns:
        score = df[column].astype(str).str.contains(pattern).sum()
        url_scores[column] = score
    likely_url_column = max(url_scores, key=url_scores.get, default=None)
    return likely_url_column

def process_row(row, link_column, text_column, add_text, duplicate_detected, name_count):
    """
    Process a single DataFrame row to generate QR code buffers.
    Returns a tuple: (filename, png_buffer, svg_buffer)
    """
    link = row[link_column]
    text = row[text_column]
    if pd.isna(link) or pd.isna(text):
        return None, None, None

    name_count[text] += 1
    filename = f"{text}_{name_count[text]}" if duplicate_detected else text

    qr = generate_qr_object(link)
    png_buffer = qr_to_png(qr, text, add_text)
    svg_buffer = qr_to_svg(qr)
    return filename, png_buffer, svg_buffer

def main():
    st.title("QR Code Generator")
    st.caption("When creating QR codes for public use, be cautious of displaying links that could be exploited for phishing or other malicious purposes.")

    # Initialize session state variables
    if 'prev_uploaded_file' not in st.session_state:
        st.session_state.prev_uploaded_file = None
    if 'prev_link_column' not in st.session_state:
        st.session_state.prev_link_column = None
    if 'prev_text_column' not in st.session_state:
        st.session_state.prev_text_column = None

    uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])
    if uploaded_file and (uploaded_file != st.session_state.prev_uploaded_file):
        st.session_state.prev_uploaded_file = uploaded_file
        st.session_state.images_png = {}
        st.session_state.images_svg = {}

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file, dtype=str)
            if df.shape[0] < 1 or df.shape[1] < 2:
                st.error("The file must contain at least one row and two columns. Please upload a valid file.")
            else:
                with st.expander("**Data**", expanded=True, icon=":material/table:"):
                    st.dataframe(df, use_container_width=True)

                qr_codes_count = len(df)
                plural = "s" if qr_codes_count > 1 else ""

                col1, col2 = st.columns(2)
                likely_url_column = None
                try:
                    likely_url_column = find_most_likely_url_column(df)
                except Exception as e:
                    st.warning(f"Failed to automatically detect URL column: {e}")

                if likely_url_column:
                    link_column = col1.selectbox(f"Select the column with URL{plural}", df.columns, index=df.columns.get_loc(likely_url_column))
                else:
                    link_column = col1.selectbox(f"Select the column with URL{plural}", df.columns)

                text_column = col2.selectbox(f"Select the column with name{plural}", df.columns, key='text_column')
                add_text = st.checkbox(f"Add name{plural} to QR code{plural}", value=True)

                # Clear images if columns change
                if (link_column != st.session_state.prev_link_column) or (text_column != st.session_state.prev_text_column):
                    st.session_state.images_png = {}
                    st.session_state.images_svg = {}
                    st.session_state.prev_link_column = link_column
                    st.session_state.prev_text_column = text_column

                name_count = defaultdict(int)
                duplicate_detected = df[text_column].duplicated().any()
                if duplicate_detected:
                    st.warning("There are duplicate names in the selected column. Unique filenames will be generated.")

                col1, col2 = st.columns(2)
                generate_qr_codes = col1.button(f"**Generate QR Code{plural}**", use_container_width=True)

                if generate_qr_codes:
                    # start_time = time.time()
                    st.session_state.images_png = {}
                    st.session_state.images_svg = {}

                    progress_container = col2.empty()
                    progress_bar = progress_container.progress(0)

                    futures = []
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        for _, row in df.iterrows():
                            futures.append(
                                executor.submit(process_row, row, link_column, text_column, add_text, duplicate_detected, name_count)
                            )

                        completed = 0
                        for future in as_completed(futures):
                            filename, png_buffer, svg_buffer = future.result()
                            if filename is None:
                                st.error("Missing data in one of the rows. Skipping.")
                                continue

                            st.session_state.images_png[filename] = png_buffer
                            st.session_state.images_svg[filename] = svg_buffer
                            completed += 1

                            if completed % 5 == 0 or completed == qr_codes_count:
                                progress_bar.progress(completed / qr_codes_count, f"Processing {completed}/{qr_codes_count}")

                    progress_container.empty()
                    st.success(f"QR code{plural} generation complete!")
                    # end_time = time.time()
                    # elapsed_time = end_time - start_time
                    # st.info(f"⏱️ QR code generation completed in {elapsed_time:.2f} seconds.")

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

            # Display the generated QR codes for review
            with st.expander("**QR Code(s)**", expanded=True, icon=":material/qr_code:"):
                qr_codes_keys = list(st.session_state.images_png.keys())
                if qr_codes_keys:
                    if len(qr_codes_keys) > 1:
                        selected_name = st.selectbox("Select a QR Code to display", qr_codes_keys)
                    else:
                        selected_name = qr_codes_keys[0]
                    if selected_name:
                        png_buffer = st.session_state.images_png[selected_name]
                        png_buffer.seek(0)
                        st.image(png_buffer, caption=f"{selected_name}.png", use_container_width=True)

if __name__ == "__main__":
    main()
 