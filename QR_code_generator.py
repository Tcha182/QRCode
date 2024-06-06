import streamlit as st
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import zipfile

def generate_qr_code_with_text(link, text, add_text):
    # Ensure text is a string
    text = str(text)

    # Generate the QR code without border
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=0  # Set border to 0 to remove margins
    )
    qr.add_data(link)
    qr.make(fit=True)
    qr_img = qr.make_image(fill='black', back_color='white')
    qr_width, qr_height = qr_img.size

    # Load a TrueType or OpenType font file
    try:
        font = ImageFont.truetype("arial.ttf", 10)
    except IOError:
        font = ImageFont.load_default()

    # Calculate text size and position if text is to be added
    if add_text:
        text_width, text_height = font.getsize(text)
        image_height = qr_height + text_height + 10
    else:
        image_height = qr_height

    image_width = qr_width

    # Create a new image with a white background
    combined_image = Image.new('RGB', (image_width, image_height), 'white')
    draw = ImageDraw.Draw(combined_image)

    # Paste the QR code into the combined image
    combined_image.paste(qr_img, (0, 0))

    if add_text:
        # Draw the text at the bottom right corner below the QR code
        text_position = (image_width - text_width, qr_height)  # n pixels padding from the edges
        draw.text(text_position, text, fill='black', font=font)

    # Save the image to a buffer
    img_buffer = BytesIO()
    combined_image.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    return img_buffer

st.title("QR Code Generator")

uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.write("Data Preview:", df.head())

    link_column = st.selectbox("Select the column with URLs", df.columns)
    text_column = st.selectbox("Select the column with names", df.columns)
    add_text = st.checkbox("Add names to QR codes", value=True)

    # Check for duplicate names
    if df[text_column].duplicated().any():
        st.warning("There are duplicate names in the selected column. Please ensure all names are unique.")
    else:
        if st.button("Generate QR Codes"):
            status = st.status("Generating QR codes...", expanded=True)
            images = {}
            for idx, row in df.iterrows():
                link = row[link_column]
                text = row[text_column]
                qr_buffer = generate_qr_code_with_text(link, text, add_text)
                images[text] = qr_buffer
                status.update(label=f"Processing {idx + 1} of {len(df)}", state="running")

            status.update(label="QR code generation complete!", state="complete")

            # Create a zip file
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                for text, qr_buffer in images.items():
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
            for text, qr_buffer in images.items():
                qr_buffer.seek(0)
                st.image(qr_buffer, caption=f"{text}.png", use_column_width=True)
