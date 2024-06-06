QR Code Generator for RATP Dev Teams
This application is designed to help generate QR codes for the teams of RATP Dev. These QR codes are intended to be placed at bus stops to provide users with real-time passenger information and vehicle arrival times, but it ca really be used to generate any kind of QR codes.

Features
Upload an Excel file with URLs and names.
Generate QR codes for each URL.
Optionally add names to the QR codes.
Download the generated QR codes as a ZIP file.

Access
The app is available here: https://qrcodegenerator-corentin-t.streamlit.app/

Installation
Clone this repository to your local machine:

bash
Copier le code
git clone https://github.com/yourusername/ratpdev-qr-code-generator.git
Navigate to the project directory:

bash
Copier le code
cd ratpdev-qr-code-generator
Install the required dependencies:

bash
Copier le code
pip install -r requirements.txt
Usage
Run the Streamlit application:

bash
Copier le code
streamlit run app.py
Upload an Excel file containing the URLs and names.

Select the appropriate columns for URLs and names.

Choose whether to add names to the QR codes.

Click the "Generate QR Codes" button to start the generation process.

Download the generated QR codes as a ZIP file.

Example
Prepare an Excel file with the following structure:

URL	Name
https://example1.com	Stop 1
https://example2.com	Stop 2
Upload the file using the app interface.

Select the columns for URLs and names.

Check the option to add names to the QR codes if desired.

Click "Generate QR Codes" and wait for the process to complete.

Download the ZIP file containing the QR codes.

Dependencies
streamlit
pandas
qrcode
Pillow
License
This project is licensed under the MIT License.
