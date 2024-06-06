# QR Code Generator for RATP Dev Teams

This application is designed to help generate QR codes for the teams of RATP Dev. These QR codes are intended to be placed at bus stops to provide users with real-time passenger information and vehicle arrival times, but it can really be used to generate any kind of QR codes.

## Features

- Upload an Excel file with URLs and names.
- Generate QR codes for each URL.
- Optionally add names to the QR codes.
- Download the generated QR codes as a ZIP file.

## Access

The app is available here: [QR Code Generator](https://qrcodegenerator-corentin-t.streamlit.app/)

## Example

1. Prepare an Excel file with the following structure:

   | URL                  | Name   |
   |----------------------|--------|
   | https://example1.com | Stop 1 |
   | https://example2.com | Stop 2 |

2. Upload the file using the app interface.
3. Select the columns for URLs and names.
4. Check the option to add names to the QR codes if desired.
5. Click "Generate QR Codes" and wait for the process to complete.
6. Download the ZIP file containing the QR codes.

## Dependencies

- streamlit
- pandas
- qrcode
- Pillow

## License

This project is licensed under the MIT License.
