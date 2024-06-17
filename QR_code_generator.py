import streamlit as st
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import zipfile

st.set_page_config(page_title="QR Code Explore", page_icon=":black_medium_square:")

st.markdown("""
<style>
	[data-testid="stDecoration"] {
		display: none;
	}

</style>""",
unsafe_allow_html=True)

#st.logo("explore.png",link="https://media1.tenor.com/m/PBTNHWOOJqgAAAAC/raptor-dinosaur.gif")
st.logo("explore.png")

def generate_qr_code_with_text(link, text, add_text):
    text = str(text)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0
    )
    qr.add_data(link)
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')
    qr_width, qr_height = qr_img.size

    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except IOError:
        font = ImageFont.load_default()

    if add_text:
        text_bbox = font.getbbox(text)
        text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        image_height = qr_height + text_height + 10
    else:
        image_height = qr_height

    image_width = qr_width
    combined_image = Image.new('RGB', (image_width, image_height), 'white')
    draw = ImageDraw.Draw(combined_image)
    combined_image.paste(qr_img, (0, 0))

    if add_text:
        text_position = (image_width - text_width, qr_height)
        draw.text(text_position, text, fill='black', font=font)

    img_buffer = BytesIO()
    combined_image.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    return img_buffer

st.title("QR Code")

# Store the previous file in session state
if 'prev_uploaded_file' not in st.session_state:
    st.session_state.prev_uploaded_file = None

uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])

# Clear session state if a new file is uploaded
if uploaded_file and uploaded_file != st.session_state.prev_uploaded_file:
    st.session_state.prev_uploaded_file = uploaded_file
    st.session_state.images = {}

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.dataframe(df,use_container_width=True)
    #st.write("Data Preview:", df)

    link_column = st.selectbox("Select the column with URLs", df.columns)
    text_column = st.selectbox("Select the column with names", df.columns)
    add_text = st.checkbox("Add names to QR codes", value=True)

    if df[text_column].duplicated().any():
        st.warning("There are duplicate names in the selected column. Please ensure all names are unique.")
    else:
        if st.button("Generate QR Codes"):
            if 'images' not in st.session_state:
                st.session_state.images = {}

            progress_bar = st.progress(0)
            status_text = st.empty()
            for idx, row in df.iterrows():
                link = row[link_column]
                text = row[text_column]

                if pd.isna(link) or pd.isna(text):
                    st.error(f"Missing data in row {idx + 1}. Skipping.")
                    continue

                qr_buffer = generate_qr_code_with_text(link, text, add_text)
                st.session_state.images[text] = qr_buffer
                progress = (idx + 1) / len(df)
                progress_bar.progress(progress)
                status_text.text(f"Processing {idx + 1}/{len(df)}")

            status_text.success("QR code generation complete!")

if 'images' in st.session_state and st.session_state.images:
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        for text, qr_buffer in st.session_state.images.items():
            qr_buffer.seek(0)
            zip_file.writestr(f"{text}.png", qr_buffer.read())
    zip_buffer.seek(0)

    st.download_button(
        label="Download QR Codes as ZIP",
        data=zip_buffer,
        file_name="qr_codes.zip",
        mime="application/zip"
    )

    st.write("Generated QR Codes:")
    for text, qr_buffer in st.session_state.images.items():
        qr_buffer.seek(0)
        st.image(qr_buffer, caption=f"{text}.png", use_column_width=True)
