import streamlit as st
import pandas as pd
import qrcode
import qrcode.image.svg
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import zipfile

st.set_page_config(page_title="QR Code Explore", page_icon=":black_medium_square:")

st.markdown("""
<style>
    [data-testid="stDecoration"] {
        display: none;
    }
</style>""", unsafe_allow_html=True)

def generate_qr_code(link, text=None, add_text=False, box_size=30, format='PNG'):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size,
        border=0
    )
    qr.add_data(link)
    qr.make(fit=True)

    if format == 'SVG':
        img = qr.make_image(image_factory=qrcode.image.svg.SvgImage)
        svg_str = img.to_string().decode("utf-8")
        buffer = BytesIO()
        buffer.write(svg_str.encode('utf-8'))
        buffer.seek(0)
        return buffer
    else:
        img = qr.make_image(fill='black', back_color='white')
        qr_width, qr_height = img.size

        if add_text and text:
            try:
                # Use a more common font or bundle a specific font
                font = ImageFont.truetype("arial.ttf", 60)  # Font size
            except IOError:
                font = ImageFont.load_default()
            text_bbox = font.getbbox(text)
            text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
            combined_image = Image.new('RGB', (qr_width, qr_height + text_height + 20), 'white')  # Border size
            draw = ImageDraw.Draw(combined_image)
            combined_image.paste(img, (0, 0))
            text_position = (qr_width - text_width - 10, qr_height + 0)  # Bottom right corner
            draw.text(text_position, text, fill='black', font=font)
            img = combined_image

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer


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
    df = pd.read_excel(uploaded_file)
    st.dataframe(df, use_container_width=True)

    link_column = st.selectbox("Select the column with URLs", df.columns, key='link_column')
    text_column = st.selectbox("Select the column with names", df.columns, key='text_column')
    add_text = st.checkbox("Add names to QR codes", value=True)

    # Clear session state if columns change
    if (link_column != st.session_state.prev_link_column) or (text_column != st.session_state.prev_text_column):
        st.session_state.images_png = {}
        st.session_state.images_svg = {}
        st.session_state.prev_link_column = link_column
        st.session_state.prev_text_column = text_column

    if df[text_column].duplicated().any():
        st.warning("There are duplicate names in the selected column. Please ensure all names are unique.")
    else:
        if st.button("Generate QR Codes"):
            if 'images_png' not in st.session_state:
                st.session_state.images_png = {}
            if 'images_svg' not in st.session_state:
                st.session_state.images_svg = {}

            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, row in df.iterrows():
                link = row[link_column]
                text = row[text_column]

                if pd.isna(link) or pd.isna(text):
                    st.error(f"Missing data in row {idx + 1}. Skipping.")
                    continue

                png_buffer = generate_qr_code(link, text, add_text, format='PNG')
                svg_buffer = generate_qr_code(link, text, add_text, format='SVG')
                st.session_state.images_png[text] = png_buffer
                st.session_state.images_svg[text] = svg_buffer

                progress = (idx + 1) / len(df)
                progress_bar.progress(progress)
                status_text.text(f"Processing {idx + 1}/{len(df)}")

            status_text.success("QR code generation complete!")

if 'images_png' in st.session_state and st.session_state.images_png and 'images_svg' in st.session_state and st.session_state.images_svg:
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for text, png_buffer in st.session_state.images_png.items():
            png_buffer.seek(0)
            zip_file.writestr(f"PNG/{text}.png", png_buffer.read())
        for text, svg_buffer in st.session_state.images_svg.items():
            svg_buffer.seek(0)
            zip_file.writestr(f"SVG/{text}.svg", svg_buffer.read())
    zip_buffer.seek(0)

    st.download_button(
        label="Download QR Codes as ZIP", 
        data=zip_buffer,
        file_name="qr_codes.zip",
        mime="application/zip"
    )

    st.write("Generated QR Codes:")
    for text, png_buffer in st.session_state.images_png.items():
        png_buffer.seek(0)
        st.image(png_buffer, caption=f"{text}.png", use_column_width=True)
    for text, svg_buffer in st.session_state.images_svg.items():
        svg_buffer.seek(0)
        st.write(f"{text}.svg", svg_buffer.getvalue().decode())
