# PDF Utility

A simple desktop application for splitting and merging PDF files.

[![Release Date](https://img.shields.io/badge/Release-April%2025,%202025-brightgreen.svg)](https://github.com/imamwahyudime/brainbox-webapp/releases/tag/v0.0.9)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Description:

This application, built with Python and Tkinter, provides a user-friendly interface for performing two common PDF manipulation tasks:

* **Splitting:** Split a PDF file into individual pages, either as separate PDF files or as image files (JPG or PNG).
* **Merging:** Merge multiple PDF files from a folder into a single PDF file. The files are merged in natural sort order (e.g., "page\_1.pdf", "page\_2.pdf", "page\_10.pdf").

## Features:

* **Graphical User Interface (GUI):** Easy-to-use interface with clear options and progress feedback.
* **PDF Splitting:**
    * Split a PDF into single-page PDF files.
    * Split a PDF into image files (JPG or PNG format).
    * Option to select output directory.
* **PDF Merging:**
    * Merge multiple PDF files from a selected folder.
    * Files are merged in natural sort order.
    * Option to select the output file path.
* **Progress and Status Updates:** Real-time feedback on the progress of splitting or merging operations.
* **Error Handling:** Displays informative error messages for common issues such as invalid PDF files, missing files, or write permission problems.
* **About Dialog:** Displays application information, including version, author, and contact links.

## Technologies Used:

* Python
* Tkinter (GUI)
* PyPDF2 (PDF manipulation)
* pdf2image (PDF to image conversion)
* Pillow (Image processing)
* threading (for non-blocking GUI)
* Poppler (for `pdf2image`)

## Usage:

1.  **Install Python:** Ensure you have Python 3.x installed on your system.
2.  **Install Dependencies:** You can install the required Python packages using pip:

    ```bash
    pip install PyPDF2 pdf2image Pillow
    ```

    * **Poppler:** `pdf2image` requires Poppler to be installed on your system.
        * **Windows:** Download Poppler from a suitable source (e.g., [https://github.com/oschwartz10612/poppler-windows/releases/](https://github.com/oschwartz10612/poppler-windows/releases/)) and extract it.  Add the `bin` directory to your system's `PATH` environment variable.
        * **Linux (Debian/Ubuntu):** `sudo apt-get install poppler-utils`
        * **macOS:** `brew install poppler` (using Homebrew)

3.  **Download the Code:** Clone this repository or download the source code as a ZIP file.
4.  **Run the Application:** Navigate to the directory containing the code and run:

    ```bash
    python main.py  # or the name of your main script
    ```
5.  **Select Mode:** Choose either "Split PDF" or "Merge PDFs" using the radio buttons.
6.  **Input Selection:**
    * **Split PDF:** Click "Browse..." to select the PDF file you want to split.
    * **Merge PDFs:** Click "Browse..." to select the folder containing the PDF files you want to merge.
7.  **Output Selection:** Click "Browse..." to choose the output directory (for splitting) or the output file path (for merging).
8.  **Start Processing:** Click the "Start Splitting" or "Start Merging" button to begin the operation.
9.  **Enjoy:** A message box will appear upon successful completion, and the status label will update.

## Contributing

Contributions are welcome!  If you find a bug or have an idea for a new feature, please open an issue or submit a pull request.
