import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import PyPDF2
from PIL import Image  # Requires Pillow
from pdf2image import convert_from_path # Requires pdf2image and poppler
import threading # To run processing in a separate thread
import re # For natural sorting
import datetime # For 'About' dialog date

# --- Configuration ---
# If poppler is not in your PATH, specify the path to the bin directory here
# Example for Windows: POPPLER_PATH = r"C:\path\to\poppler-XX.XX.X\Library\bin"
# Example for Linux/macOS (if installed but not found): POPPLER_PATH = "/usr/local/bin" or similar
POPPLER_PATH = None # Set this if needed, otherwise leave as None

# --- Backend Logic ---

def natural_sort_key(s):
    """
    Key function for natural sorting (handles numbers correctly).
    Example: "page_1.pdf", "page_10.pdf", "page_2.pdf" -> "page_1.pdf", "page_2.pdf", "page_10.pdf"
    """
    # Split string into alternating non-digit and digit parts
    # Convert digit parts to integers for correct numerical comparison
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

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
        status_callback(f"Error: Invalid or corrupted PDF: {os.path.basename(input_path)}")
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
    # Catch specific import errors first
    except NameError as e: # pdf2image might raise NameError if poppler not found indirectly
        if "poppler" in str(e).lower():
             messagebox.showerror("Poppler Error",
                                  "Poppler utility not found or configured correctly.\n"
                                  "Ensure Poppler is installed and in your system PATH,\n"
                                  "or set the POPPLER_PATH variable in the script.\n\n"
                                  f"Details: {e}")
             status_callback(f"Error: Poppler configuration issue: {e}")
             return False
        else: # Re-raise other NameErrors
            raise e
    except ImportError:
        messagebox.showerror("Error", "Pillow or pdf2image library not found. Please install them (pip install Pillow pdf2image).")
        status_callback("Error: Missing required library (Pillow or pdf2image).")
        return False
    # Catch specific pdf2image processing errors
    except Exception as e:
        # Check common pdf2image/poppler errors
        if "poppler" in str(e).lower() or "pdftoppm" in str(e).lower():
            messagebox.showerror("Poppler Error",
                                 "Poppler not found or failed during execution.\n"
                                 "Ensure Poppler is installed and in your system PATH,\n"
                                 "or set the POPPLER_PATH variable in the script.\n\n"
                                 f"Details: {e}")
            status_callback(f"Error: Poppler execution failed: {e}")
        elif isinstance(e, FileNotFoundError):
             messagebox.showerror("Error", f"Input PDF file not found: {input_path}")
             status_callback(f"Error: Input file not found.")
        else:
            messagebox.showerror("Error", f"An error occurred during image splitting:\n{e}")
            status_callback(f"Error splitting to images: {e}")
        return False


def merge_pdfs(input_sources, output_path, status_callback, progress_callback):
     """
     Merges multiple PDF files from a folder into one PDF, sorting naturally.
     Uses writer.append() which might handle resources/fonts better than add_page().
     """
     pdf_files_full_path = []
     # Input is expected to be a list containing one directory path in this GUI implementation
     if len(input_sources) == 1 and os.path.isdir(input_sources[0]):
         folder = input_sources[0]
         status_callback(f"Scanning folder: {folder}")
         try:
             filenames_in_folder = os.listdir(folder)
             # --- Apply natural sorting to filenames ---
             filenames_in_folder.sort(key=natural_sort_key)
             # -----------------------------------------
             for filename in filenames_in_folder:
                 if filename.lower().endswith(".pdf"):
                     pdf_files_full_path.append(os.path.join(folder, filename))
         except OSError as e:
             messagebox.showerror("Error", f"Could not read directory: {folder}\n{e}")
             status_callback(f"Error reading directory: {e}")
             return False
     else:
         # Fallback for list input (less likely with current GUI)
         pdf_files_full_path = [f for f in input_sources if f.lower().endswith(".pdf")]
         pdf_files_full_path.sort(key=lambda f: natural_sort_key(os.path.basename(f)))


     if not pdf_files_full_path:
         messagebox.showerror("Error", "No PDF files found in the selected folder.")
         status_callback("No PDF files found.")
         return False

     status_callback(f"Found {len(pdf_files_full_path)} PDF files to merge (sorted naturally).")

     writer = PyPDF2.PdfWriter()
     total_files = len(pdf_files_full_path)
     progress_callback(0, total_files) # Initialize progress
     files_merged_count = 0
     files_skipped = 0

     try:
         for i, filepath in enumerate(pdf_files_full_path):
             filename = os.path.basename(filepath)
             status_callback(f"Processing: {filename} ({i+1}/{total_files})")
             try:
                 # --- Use writer.append() ---
                 # Open each PDF and append it to the writer
                 # Note: strict=False is used when READING potentially problematic PDFs,
                 # not when appending with PdfWriter.
                 # *** CORRECTED LINE BELOW ***
                 writer.append(filepath)
                 # ***************************
                 files_merged_count += 1
                 status_callback(f"Appended: {filename} ({files_merged_count}/{total_files - files_skipped})")

             except PyPDF2.errors.PdfReadError as read_err:
                 # It's often better to try reading with strict=False first if append fails,
                 # or just let append fail if the file is truly unreadable by PyPDF2.
                 # This error might occur if the file is invalid even without strict=True.
                 status_callback(f"Skipping invalid/corrupted PDF: {filename}")
                 print(f"Warning: Skipping invalid/corrupted PDF: {filepath}. Error: {read_err}")
                 files_skipped += 1
             except FileNotFoundError:
                 status_callback(f"Skipping missing file: {filename}")
                 print(f"Warning: Skipping missing file: {filepath}")
                 files_skipped += 1
             except Exception as append_err:
                 # Catch other errors during append (e.g., password protected, unsupported features)
                 status_callback(f"Error appending {filename}: {append_err}. Skipping.")
                 print(f"Warning: Error appending {filepath}: {append_err}. Skipping file.")
                 files_skipped += 1

             progress_callback(i + 1, total_files) # Update overall progress

         # Check if any pages were actually added after attempting all appends
         if files_merged_count == 0 or not writer.pages: # Check writer.pages as append might fail silently on some errors
             if files_skipped == total_files:
                 messagebox.showerror("Error", "All selected PDF files were skipped due to errors or being invalid.")
             else:
                 messagebox.showerror("Error", "No valid pages could be merged from the selected PDF files.")
             status_callback("Merging failed: No valid content merged.")
             return False

         # Write the merged PDF
         with open(output_path, "wb") as output_pdf:
             writer.write(output_pdf)

         final_msg = f"Merging complete. Output saved to: {os.path.basename(output_path)}"
         if files_skipped > 0:
              final_msg += f" ({files_skipped} file(s) skipped due to errors)."
         status_callback(final_msg)
         return True

     except Exception as e:
         # Catch unexpected errors during the merge process itself
         messagebox.showerror("Error", f"An unexpected error occurred during PDF merging:\n{e}")
         status_callback(f"Error merging: {e}")
         return False
     finally:
         # Ensure writer resources are closed if necessary (though 'with open' handles the output file)
         # PyPDF2 PdfWriter doesn't have an explicit close method like PdfReader
         pass # No explicit close needed for PdfWriter

# --- GUI Class ---

class PdfUtilityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Utility")
        self.root.geometry("600x500") # Increased height slightly for About button

        # Style
        self.style = ttk.Style()
        # Try different themes for potentially better looks on various OS
        try:
            self.style.theme_use('vista') # Good for Windows
        except tk.TclError:
            try:
                self.style.theme_use('clam') # Good cross-platform
            except tk.TclError:
                self.style.theme_use('default') # Fallback

        # Variables
        self.mode = tk.StringVar(value="split") # 'split' or 'merge'
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.split_output_type = tk.StringVar(value="pdf") # 'pdf' or 'image'
        self.image_format = tk.StringVar(value="PNG") # 'PNG' or 'JPG'
        self._selected_merge_files = [] # Internal storage for merge paths

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
        self.image_format_combo = ttk.Combobox(self.split_options_frame, textvariable=self.image_format, values=["PNG", "JPG"], state='readonly', width=5)

        # --- Action Button ---
        # Frame to hold action and about buttons
        self.buttons_frame = ttk.Frame(self.root)
        self.action_button = ttk.Button(self.buttons_frame, text="Start Processing", command=self._start_processing_thread, width=20)
        self.about_button = ttk.Button(self.buttons_frame, text="About", command=self._show_about, width=10) # New About button


        # --- Status Area ---
        self.status_frame = ttk.LabelFrame(self.root, text="Status")
        self.status_label = ttk.Label(self.status_frame, text="Ready.", anchor="w", justify="left", wraplength=550) # Allow wrapping
        self.progress_bar = ttk.Progressbar(self.status_frame, orient="horizontal", length=300, mode="determinate")

    def _layout_widgets(self):
        # Pack frames with padding
        self.mode_frame.pack(pady=(10,5), padx=10, fill="x")
        self.input_frame.pack(pady=5, padx=10, fill="x")
        self.output_frame.pack(pady=5, padx=10, fill="x")
        self.split_options_frame.pack(pady=5, padx=10, fill="x") # Packed/unpacked dynamically

        # Grid layouts within frames
        # Mode
        self.split_radio.pack(side="left", padx=(10, 5), pady=5)
        self.merge_radio.pack(side="left", padx=5, pady=5)

        # Input
        self.input_label.grid(row=0, column=0, padx=5, pady=(5,0), sticky="w")
        self.input_entry.grid(row=1, column=0, padx=5, pady=(0,5), sticky="ew")
        self.input_button.grid(row=1, column=1, padx=(0, 5), pady=(0,5))
        self.input_frame.columnconfigure(0, weight=1) # Make entry expand

        # Output
        self.output_label.grid(row=0, column=0, padx=5, pady=(5,0), sticky="w")
        self.output_entry.grid(row=1, column=0, padx=5, pady=(0,5), sticky="ew")
        self.output_button.grid(row=1, column=1, padx=(0, 5), pady=(0,5))
        self.output_frame.columnconfigure(0, weight=1) # Make entry expand

        # Split Options
        self.split_pdf_radio.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.split_image_radio.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.image_format_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.image_format_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.split_options_frame.columnconfigure(1, weight=1) # Give some space

        # Action and About Buttons Frame
        self.buttons_frame.pack(pady=(15, 5)) # Add padding above
        self.action_button.pack(side=tk.LEFT, padx=10)
        self.about_button.pack(side=tk.LEFT, padx=10)

        # Status Frame (pack last to fill remaining space if needed)
        self.status_frame.pack(pady=(5,10), padx=10, fill="both", expand=True)
        self.status_label.pack(pady=(5,0), padx=5, fill="x")
        self.progress_bar.pack(pady=5, padx=5, fill="x")


    def _update_ui_for_mode(self):
        """Updates labels, enables/disables widgets based on selected mode."""
        mode = self.mode.get()
        # Clear previous selections and status when mode changes
        self.input_path.set("")
        self.output_path.set("")
        self._selected_merge_files = []
        self.status_label.config(text="Ready.")
        self.progress_bar['value'] = 0

        if mode == "split":
            self.input_label_text.set("Input PDF File:")
            self.output_label_text.set("Output Directory:")
            # Make sure split options frame is visible
            if not self.split_options_frame.winfo_ismapped():
                self.split_options_frame.pack(pady=5, padx=10, fill="x", before=self.buttons_frame) # Place before buttons
            self._toggle_image_format_combo() # Update based on split type
            self.action_button.config(text="Start Splitting")


        elif mode == "merge":
            self.input_label_text.set("Input PDFs (Select Folder):")
            self.output_label_text.set("Output Merged PDF File:")
            # Hide split options frame if it's visible
            if self.split_options_frame.winfo_ismapped():
                self.split_options_frame.pack_forget()
            self.action_button.config(text="Start Merging")


    def _toggle_image_format_combo(self):
        """Enables/disables the image format combobox based on split output type."""
        # Ensure this only runs when in split mode
        if self.mode.get() == "split":
            if self.split_output_type.get() == "image":
                self.image_format_label.config(state='normal')
                self.image_format_combo.config(state='readonly')
            else:
                self.image_format_label.config(state='disabled')
                self.image_format_combo.config(state='disabled')
        else: # Disable if not in split mode (belt-and-braces)
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
                # Clear output path for split mode if input changes
                self.output_path.set("")
        elif mode == "merge":
            # Simplified to only select a folder for merging PDFs within it
            dirpath = filedialog.askdirectory(
                title="Select Folder Containing PDFs to Merge"
            )
            if dirpath:
                self.input_path.set(dirpath)
                # Store the directory path; merge function will read files from here
                self._selected_merge_files = [dirpath]
                 # Suggest an output filename based on the folder name
                folder_name = os.path.basename(dirpath)
                suggested_out = os.path.join(os.path.dirname(dirpath), f"{folder_name}_merged.pdf") # Put in parent dir
                self.output_path.set(suggested_out)


    def _select_output(self):
        mode = self.mode.get()
        if mode == "split":
            # Suggest output dir based on input file if possible
            input_file = self.input_path.get()
            initial_dir = os.path.dirname(input_file) if input_file else None
            dirpath = filedialog.askdirectory(
                title="Select Output Directory",
                initialdir=initial_dir
                )
            if dirpath:
                self.output_path.set(dirpath)
        elif mode == "merge":
             # Suggest output file based on input folder if possible
            input_folder = self.input_path.get()
            initial_dir = os.path.dirname(input_folder) if input_folder else None
            initial_file = os.path.basename(self.output_path.get()) # Keep suggestion if already set

            filepath = filedialog.asksaveasfilename(
                title="Save Merged PDF As...",
                defaultextension=".pdf",
                filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")],
                initialdir=initial_dir,
                initialfile=initial_file
            )
            if filepath:
                self.output_path.set(filepath)

    def _update_status(self, message):
        """Updates the status label (thread-safe via root.after)."""
        # Use root.after(0, ...) to ensure GUI updates happen in the main thread
        self.root.after(0, self.status_label.config, {'text': message})
        # print(f"Status: {message}") # Optional: print to console for debugging

    def _update_progress(self, value, maximum):
        """Updates the progress bar (thread-safe via root.after)."""
        # Use root.after(0, ...) to ensure GUI updates happen in the main thread
        if maximum > 0: # Avoid division by zero if max is 0 initially
            self.root.after(0, self.progress_bar.config, {'maximum': maximum, 'value': value})
        else:
            self.root.after(0, self.progress_bar.config, {'maximum': 1, 'value': 0}) # Default state
        # print(f"Progress: {value}/{maximum}") # Optional: print to console for debugging


    def _processing_finished(self, success):
        """Called after processing thread completes (runs in main thread via root.after)."""
        self.action_button.config(state='normal') # Re-enable button
        if success:
            final_message = self.status_label.cget("text") # Get final status from backend
            messagebox.showinfo("Success", "Processing completed successfully!")
            self.status_label.config(text=f"Done. {final_message}") # Keep final status message
        else:
            # Error message should have been shown by the backend function
            # Or caught by the _run_task wrapper
            current_status = self.status_label.cget("text")
            if "Error" not in current_status and "Failed" not in current_status:
                 self.status_label.config(text="Failed. See error message or console output.")
            # Keep the specific error message if it was set by the backend
        # Reset progress bar after a short delay to show completion/failure state
        self.root.after(500, lambda: self.progress_bar.config(value=0))


    def _start_processing_thread(self):
        """Validates inputs and runs the selected PDF operation in a background thread."""
        # --- Basic Validation ---
        inp = self.input_path.get()
        out = self.output_path.get()
        mode = self.mode.get()

        # Input validation
        if not inp:
            messagebox.showerror("Error", "Please select an input file or folder.")
            return
        if mode == "split" and not os.path.isfile(inp):
            messagebox.showerror("Error", f"Input PDF file not found or is not a file:\n{inp}")
            return
        if mode == "merge" and not os.path.isdir(inp):
             messagebox.showerror("Error", f"Input folder not found or is not a directory:\n{inp}")
             return

        # Output validation
        if not out:
            messagebox.showerror("Error", f"Please select an output {'directory' if mode == 'split' else 'file'}.")
            return
        if mode == "split":
            if not os.path.isdir(out):
                 messagebox.showerror("Error", f"Output directory not found or is not a directory:\n{out}")
                 return
             # Optional: Check write permissions for output directory
            if not os.access(out, os.W_OK):
                 messagebox.showwarning("Warning", f"Cannot write to output directory:\n{out}\nPlease check permissions.")
                 # return # Decide if you want to stop or just warn
        elif mode == "merge":
            output_dir = os.path.dirname(out)
            if not os.path.isdir(output_dir):
                 messagebox.showerror("Error", f"The directory for the output file does not exist:\n{output_dir}")
                 return
            if not os.access(output_dir, os.W_OK):
                  messagebox.showwarning("Warning", f"Cannot write to output directory:\n{output_dir}\nPlease check permissions.")
                  # return

        # Disable button, clear status
        self.action_button.config(state='disabled')
        self.status_label.config(text="Starting...")
        self.progress_bar['value'] = 0
        self.root.update_idletasks() # Ensure GUI updates before thread starts

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
            args = ([inp], out, self._update_status, self._update_progress) # inp is the folder path

        if target_func:
            # Run in a separate thread to keep GUI responsive
            processing_thread = threading.Thread(target=self._run_task, args=(target_func, args), daemon=True)
            processing_thread.start()
        else:
            messagebox.showerror("Error", "Invalid processing mode or split type selected.")
            self.action_button.config(state='normal') # Re-enable button


    def _run_task(self, func, args):
        """Wrapper to run the backend function and call finish handler."""
        success = False # Default to failure
        try:
            # Unpack args correctly for the target function
            success = func(*args)
        except Exception as e:
            # Catch unexpected errors in the thread itself (e.g., programming errors)
            print(f"Critical Error in processing thread: {e}") # Log to console
            # Update status/show error via main thread
            self.root.after(0, self._update_status, f"Critical Error: {e}")
            self.root.after(0, messagebox.showerror, "Critical Error", f"An unexpected error occurred in the background task:\n{e}")
            success = False # Ensure it's marked as failed
        finally:
             # Schedule the finish handler to run in the main GUI thread regardless of outcome
            self.root.after(0, self._processing_finished, success)

    def _show_about(self):
        """Displays the About dialog box."""
        today_date = datetime.date.today().strftime("%Y-%m-%d")
        about_message = (
            f"PDF Utility\n\n"
            f"Version: 0.0.9\n"
            f"Release Date: 25 April 2025\n"
            f"Author: Imam Wahyudi\n\n"
            f"GitHub: https://github.com/imamwahyudime\n"
            f"LinkedIn: https://www.linkedin.com/in/imam-wahyudi/"
        )
        messagebox.showinfo("About PDF Utility", about_message)


# --- Main Application Runner ---
if __name__ == "__main__":
    root = tk.Tk()
    app = PdfUtilityApp(root)
    root.mainloop()