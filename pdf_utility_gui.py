import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import PyPDF2
from PIL import Image  # Requires Pillow
from pdf2image import convert_from_path # Requires pdf2image and poppler
import threading # To run processing in a separate thread

# --- Configuration ---
# If poppler is not in your PATH, specify the path to the bin directory here
# Example for Windows: POPPLER_PATH = r"C:\path\to\poppler-XX.XX.X\Library\bin"
# Example for Linux/macOS (if installed but not found): POPPLER_PATH = "/usr/local/bin" or similar
POPPLER_PATH = None # Set this if needed, otherwise leave as None

# --- Backend Logic ---

def split_pdf_to_pdfs(input_path, output_dir, status_callback, progress_callback):
    """Splits a PDF into single-page PDF files."""
    try:
        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        reader = PyPDF2.PdfReader(input_path)
        num_pages = len(reader.pages)
        progress_callback(0, num_pages) # Initialize progress

        for i, page in enumerate(reader.pages):
            writer = PyPDF2.PdfWriter()
            writer.add_page(page)
            output_filename = os.path.join(output_dir, f"{base_filename}_page_{i + 1}.pdf")
            with open(output_filename, "wb") as output_pdf:
                writer.write(output_pdf)
            status_callback(f"Created: {os.path.basename(output_filename)}")
            progress_callback(i + 1, num_pages) # Update progress

        status_callback("Splitting to PDFs complete.")
        return True
    except PyPDF2.errors.PdfReadError:
        messagebox.showerror("Error", f"Invalid or corrupted PDF file: {input_path}")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during PDF splitting:\n{e}")
        status_callback(f"Error splitting: {e}")
        return False

def split_pdf_to_images(input_path, output_dir, img_format, status_callback, progress_callback):
    """Splits a PDF into image files (JPG or PNG)."""
    try:
        status_callback("Converting PDF pages to images (may take time)...")
        progress_callback(0, 1) # Indicate starting conversion
        # Specify poppler path if configured
        poppler_path_arg = {"poppler_path": POPPLER_PATH} if POPPLER_PATH else {}
        images = convert_from_path(input_path, **poppler_path_arg)
        progress_callback(1, 1) # Indicate conversion done

        num_pages = len(images)
        progress_callback(0, num_pages) # Reset progress for saving
        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        img_format = img_format.lower()
        if img_format not in ['jpg', 'png']:
            raise ValueError("Invalid image format selected.")

        for i, image in enumerate(images):
            output_filename = os.path.join(output_dir, f"{base_filename}_page_{i + 1}.{img_format}")
            # For JPG, ensure conversion to RGB as PNG might have alpha channel
            if img_format == 'jpg' and image.mode == 'RGBA':
                 image = image.convert('RGB')
            image.save(output_filename, format=img_format.upper())
            status_callback(f"Saved: {os.path.basename(output_filename)}")
            progress_callback(i + 1, num_pages) # Update progress

        status_callback("Splitting to images complete.")
        return True
    except ImportError:
         messagebox.showerror("Error", "Pillow or pdf2image library not found. Please install them.")
         return False
    except Exception as e:
        # Check common pdf2image errors
        if "poppler" in str(e).lower():
             messagebox.showerror("Poppler Error",
                                 "Poppler not found or configured correctly.\n"
                                 "Ensure Poppler is installed and in your system PATH,\n"
                                 "or set the POPPLER_PATH variable in the script.\n\n"
                                 f"Details: {e}")
        else:
            messagebox.showerror("Error", f"An error occurred during image splitting:\n{e}")
        status_callback(f"Error splitting to images: {e}")
        return False


def merge_pdfs(input_sources, output_path, status_callback, progress_callback):
    """Merges multiple PDF files from a list or folder into one PDF."""
    pdf_files = []
    # If input is a directory
    if len(input_sources) == 1 and os.path.isdir(input_sources[0]):
        folder = input_sources[0]
        status_callback(f"Scanning folder: {folder}")
        try:
            for filename in os.listdir(folder):
                if filename.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(folder, filename))
        except OSError as e:
             messagebox.showerror("Error", f"Could not read directory: {folder}\n{e}")
             status_callback(f"Error reading directory: {e}")
             return False
    # If input is a list of files
    else:
        pdf_files = [f for f in input_sources if f.lower().endswith(".pdf")]

    if not pdf_files:
        messagebox.showerror("Error", "No PDF files found in the selection.")
        status_callback("No PDF files found.")
        return False

    # Sort files lexicographically (alphabetically)
    pdf_files.sort()
    status_callback(f"Found {len(pdf_files)} PDF files to merge.")

    writer = PyPDF2.PdfWriter()
    total_files = len(pdf_files)
    progress_callback(0, total_files) # Initialize progress

    try:
        for i, filename in enumerate(pdf_files):
            status_callback(f"Merging: {os.path.basename(filename)} ({i+1}/{total_files})")
            try:
                reader = PyPDF2.PdfReader(filename, strict=False) # Use strict=False for potentially problematic PDFs
                for page in reader.pages:
                    writer.add_page(page)
            except PyPDF2.errors.PdfReadError:
                 status_callback(f"Skipping invalid/corrupted PDF: {os.path.basename(filename)}")
                 print(f"Warning: Skipping invalid/corrupted PDF: {filename}") # Also print to console
                 continue # Skip this file
            except Exception as page_err:
                status_callback(f"Error reading {os.path.basename(filename)}: {page_err}. Skipping.")
                print(f"Warning: Error reading {filename}: {page_err}. Skipping file.")
                continue # Skip this file
            progress_callback(i + 1, total_files) # Update progress

        if not writer.pages:
             messagebox.showerror("Error", "No valid pages could be extracted from the selected PDF files.")
             status_callback("Merging failed: No valid pages found.")
             return False

        with open(output_path, "wb") as output_pdf:
            writer.write(output_pdf)

        status_callback(f"Merging complete. Output saved to: {os.path.basename(output_path)}")
        return True
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during PDF merging:\n{e}")
        status_callback(f"Error merging: {e}")
        return False


# --- GUI Class ---

class PdfUtilityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Utility")
        self.root.geometry("600x450") # Adjust size as needed

        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam') # Or 'alt', 'default', 'classic'

        # Variables
        self.mode = tk.StringVar(value="split") # 'split' or 'merge'
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.split_output_type = tk.StringVar(value="pdf") # 'pdf' or 'image'
        self.image_format = tk.StringVar(value="PNG") # 'PNG' or 'JPG'

        # Build GUI
        self._create_widgets()
        self._layout_widgets()
        self._update_ui_for_mode() # Initial UI setup

    def _create_widgets(self):
        # --- Mode Selection ---
        self.mode_frame = ttk.LabelFrame(self.root, text="Select Mode")
        self.split_radio = ttk.Radiobutton(self.mode_frame, text="Split PDF", variable=self.mode, value="split", command=self._update_ui_for_mode)
        self.merge_radio = ttk.Radiobutton(self.mode_frame, text="Merge PDFs", variable=self.mode, value="merge", command=self._update_ui_for_mode)

        # --- Input Selection ---
        self.input_frame = ttk.LabelFrame(self.root, text="Input")
        self.input_label_text = tk.StringVar(value="Input PDF File:") # Dynamic label
        self.input_label = ttk.Label(self.input_frame, textvariable=self.input_label_text)
        self.input_entry = ttk.Entry(self.input_frame, textvariable=self.input_path, width=50, state='readonly')
        self.input_button = ttk.Button(self.input_frame, text="Browse...", command=self._select_input)

        # --- Output Selection ---
        self.output_frame = ttk.LabelFrame(self.root, text="Output")
        self.output_label_text = tk.StringVar(value="Output Directory:") # Dynamic label
        self.output_label = ttk.Label(self.output_frame, textvariable=self.output_label_text)
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path, width=50, state='readonly')
        self.output_button = ttk.Button(self.output_frame, text="Browse...", command=self._select_output)

        # --- Split Options ---
        self.split_options_frame = ttk.LabelFrame(self.root, text="Split Options")
        self.split_pdf_radio = ttk.Radiobutton(self.split_options_frame, text="Output as PDFs", variable=self.split_output_type, value="pdf", command=self._toggle_image_format_combo)
        self.split_image_radio = ttk.Radiobutton(self.split_options_frame, text="Output as Images", variable=self.split_output_type, value="image", command=self._toggle_image_format_combo)
        self.image_format_label = ttk.Label(self.split_options_frame, text="Image Format:")
        self.image_format_combo = ttk.Combobox(self.split_options_frame, textvariable=self.image_format, values=["PNG", "JPG"], state='readonly')

        # --- Action Button ---
        self.action_button = ttk.Button(self.root, text="Start Processing", command=self._start_processing_thread)

        # --- Status Area ---
        self.status_frame = ttk.LabelFrame(self.root, text="Status")
        self.status_label = ttk.Label(self.status_frame, text="Ready.", anchor="w", justify="left")
        self.progress_bar = ttk.Progressbar(self.status_frame, orient="horizontal", length=300, mode="determinate")

    def _layout_widgets(self):
        # Mode Frame
        self.mode_frame.pack(pady=10, padx=10, fill="x")
        self.split_radio.pack(side="left", padx=5, pady=5)
        self.merge_radio.pack(side="left", padx=5, pady=5)

        # Input Frame
        self.input_frame.pack(pady=5, padx=10, fill="x")
        self.input_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.input_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.input_button.grid(row=1, column=1, padx=5, pady=5)
        self.input_frame.columnconfigure(0, weight=1) # Make entry expand

        # Output Frame
        self.output_frame.pack(pady=5, padx=10, fill="x")
        self.output_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.output_entry.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.output_button.grid(row=1, column=1, padx=5, pady=5)
        self.output_frame.columnconfigure(0, weight=1) # Make entry expand

        # Split Options Frame
        self.split_options_frame.pack(pady=5, padx=10, fill="x")
        self.split_pdf_radio.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.split_image_radio.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.image_format_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.image_format_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Action Button
        self.action_button.pack(pady=15)

        # Status Frame
        self.status_frame.pack(pady=10, padx=10, fill="x", expand=True)
        self.status_label.pack(pady=5, padx=5, fill="x")
        self.progress_bar.pack(pady=5, padx=5, fill="x")

    def _update_ui_for_mode(self):
        """Updates labels, enables/disables widgets based on selected mode."""
        mode = self.mode.get()
        if mode == "split":
            self.input_label_text.set("Input PDF File:")
            self.output_label_text.set("Output Directory:")
            self.split_options_frame.pack(pady=5, padx=10, fill="x") # Show split options
            self._toggle_image_format_combo() # Update based on split type
            self.action_button.config(text="Start Splitting")
            # Clear paths if they are unsuitable for the new mode
            self.input_path.set("")
            self.output_path.set("")

        elif mode == "merge":
            self.input_label_text.set("Input PDFs (Select Folder):") # Simplified to folder selection
            self.output_label_text.set("Output Merged PDF File:")
            self.split_options_frame.pack_forget() # Hide split options
            self.action_button.config(text="Start Merging")
            # Clear paths if they are unsuitable for the new mode
            self.input_path.set("")
            self.output_path.set("")

        self.status_label.config(text="Ready.")
        self.progress_bar['value'] = 0

    def _toggle_image_format_combo(self):
        """Enables/disables the image format combobox based on split output type."""
        if self.mode.get() == "split" and self.split_output_type.get() == "image":
            self.image_format_label.config(state='normal')
            self.image_format_combo.config(state='readonly')
        else:
            self.image_format_label.config(state='disabled')
            self.image_format_combo.config(state='disabled')

    def _select_input(self):
        mode = self.mode.get()
        if mode == "split":
            filepath = filedialog.askopenfilename(
                title="Select Input PDF File",
                filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
            )
            if filepath:
                self.input_path.set(filepath)
        elif mode == "merge":
             # Option 1: Select multiple files
             # filepaths = filedialog.askopenfilenames(
             #     title="Select Input PDF Files",
             #     filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
             # )
             # if filepaths:
             #     # Displaying multiple files in entry is tricky, maybe just show count?
             #     self.input_path.set(f"{len(filepaths)} files selected")
             #     self._selected_merge_files = list(filepaths) # Store the list internally

             # Option 2: Select a folder (Simpler UI)
             dirpath = filedialog.askdirectory(
                 title="Select Folder Containing PDFs"
             )
             if dirpath:
                 self.input_path.set(dirpath)
                 # Store the directory path, the merge function will handle reading it
                 self._selected_merge_files = [dirpath] # Use a list for consistency


    def _select_output(self):
        mode = self.mode.get()
        if mode == "split":
            dirpath = filedialog.askdirectory(title="Select Output Directory")
            if dirpath:
                self.output_path.set(dirpath)
        elif mode == "merge":
            filepath = filedialog.asksaveasfilename(
                title="Save Merged PDF As...",
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
            )
            if filepath:
                self.output_path.set(filepath)

    def _update_status(self, message):
        """Updates the status label (thread-safe)."""
        self.status_label.config(text=message)
        # self.root.update_idletasks() # Might be needed if called rapidly from thread

    def _update_progress(self, value, maximum):
        """Updates the progress bar (thread-safe)."""
        self.progress_bar['maximum'] = maximum
        self.progress_bar['value'] = value
        # self.root.update_idletasks() # Might be needed if called rapidly from thread

    def _processing_finished(self, success):
        """Called after processing thread completes."""
        self.action_button.config(state='normal') # Re-enable button
        if success:
            messagebox.showinfo("Success", "Processing completed successfully!")
            self.status_label.config(text="Done.")
        else:
            # Error message shown by the function itself
            self.status_label.config(text="Failed. See error message.")
        self.progress_bar['value'] = 0

    def _start_processing_thread(self):
        """Runs the selected PDF operation in a background thread."""
        # --- Basic Validation ---
        inp = self.input_path.get()
        out = self.output_path.get()
        mode = self.mode.get()

        if not inp:
            messagebox.showerror("Error", "Please select an input file or folder.")
            return
        if not out:
             messagebox.showerror("Error", f"Please select an output {'directory' if mode == 'split' else 'file'}.")
             return

        if mode == "split" and not os.path.isfile(inp):
             messagebox.showerror("Error", f"Input file not found: {inp}")
             return
        if mode == "merge":
             # Check if input path exists (it's expected to be a directory in this implementation)
             if not os.path.isdir(inp):
                 messagebox.showerror("Error", f"Input folder not found: {inp}")
                 return
        # Further validation could check output directory permissions etc.

        # Disable button, clear status
        self.action_button.config(state='disabled')
        self.status_label.config(text="Starting...")
        self.progress_bar['value'] = 0
        self.root.update_idletasks()


        # --- Prepare arguments for the target function ---
        args = ()
        target_func = None

        if mode == "split":
            split_type = self.split_output_type.get()
            if split_type == "pdf":
                target_func = split_pdf_to_pdfs
                args = (inp, out, self._update_status, self._update_progress)
            elif split_type == "image":
                img_format = self.image_format.get()
                target_func = split_pdf_to_images
                args = (inp, out, img_format, self._update_status, self._update_progress)
        elif mode == "merge":
             target_func = merge_pdfs
             # Pass the input path (folder) as a list for consistency with merge_pdfs signature
             args = ([inp], out, self._update_status, self._update_progress)

        if target_func:
            # Run in a separate thread to keep GUI responsive
            processing_thread = threading.Thread(target=self._run_task, args=(target_func, args), daemon=True)
            processing_thread.start()
        else:
             messagebox.showerror("Error", "Invalid processing mode selected.")
             self.action_button.config(state='normal') # Re-enable button


    def _run_task(self, func, args):
        """Wrapper to run the backend function and call finish handler."""
        try:
            success = func(*args)
            # Schedule the finish handler to run in the main GUI thread
            self.root.after(0, self._processing_finished, success)
        except Exception as e:
            # Catch unexpected errors in the thread itself
            print(f"Error in processing thread: {e}") # Log to console
            self.root.after(0, messagebox.showerror, "Critical Error", f"An unexpected error occurred in the background task:\n{e}")
            self.root.after(0, self._processing_finished, False)


# --- Main Application Runner ---
if __name__ == "__main__":
    root = tk.Tk()
    app = PdfUtilityApp(root)
    root.mainloop()
