import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import PyPDF2
from PIL import Image  # Requires Pillow
from pdf2image import convert_from_path  # Requires pdf2image and poppler
import threading  # To run processing in a separate thread
import io  # For handling images in memory
import webbrowser  # For opening links in About dialog
import re # For natural sorting

# --- Configuration ---
# If poppler is not in your PATH, specify the path to the bin directory here
# Example for Windows: POPPLER_PATH = r"C:\path\to\poppler-XX.XX.X\Library\bin"
# Example for Linux/macOS (if installed but not found): POPPLER_PATH = "/usr/local/bin" or similar
POPPLER_PATH = None  # Set this if needed, otherwise leave as None

# --- Constants for About Dialog ---
APP_VERSION = "1.1.2" # Version updated
RELEASE_DATE = "May 9, 2025"
AUTHOR_NAME = "Imam Wahyudi"
GITHUB_URL = "https://github.com/imamwahyudime"
LINKEDIN_URL = "https://www.linkedin.com/in/imam-wahyudi/"

# --- Backend Logic ---

def natural_sort_key(s):
    """
    Key function for natural sorting (handles numbers correctly).
    Input 's' is expected to be a full path or just a filename.
    """
    # Extract filename if full path is given, for consistent sorting based on filename
    filename_part = os.path.basename(s)
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', filename_part)]

def split_pdf_to_pdfs(input_path, output_dir, status_callback, progress_callback):
    """Splits a PDF into single-page PDF files."""
    try:
        if not os.path.isfile(input_path):
            messagebox.showerror("Error", f"Input PDF file not found: {input_path}")
            status_callback(f"Error: Input PDF not found {os.path.basename(input_path)}")
            return False
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                status_callback(f"Created output directory: {output_dir}")
            except OSError as e:
                messagebox.showerror("Error", f"Output directory does not exist and cannot be created: {output_dir}\n{e}")
                status_callback(f"Error: Output directory creation failed {output_dir}")
                return False

        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        reader = PyPDF2.PdfReader(input_path)
        num_pages = len(reader.pages)
        progress_callback(0, num_pages)

        for i, page in enumerate(reader.pages):
            writer = PyPDF2.PdfWriter()
            writer.add_page(page)
            output_filename = os.path.join(output_dir, f"{base_filename}_page_{i + 1}.pdf")
            with open(output_filename, "wb") as output_pdf:
                writer.write(output_pdf)
            status_callback(f"Created: {os.path.basename(output_filename)}")
            progress_callback(i + 1, num_pages)

        status_callback("Splitting to PDFs complete.")
        return True
    except PyPDF2.errors.PdfReadError:
        messagebox.showerror("Error", f"Invalid or corrupted PDF file: {input_path}")
        status_callback(f"Error splitting: Invalid PDF {os.path.basename(input_path)}")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during PDF splitting:\n{e}")
        status_callback(f"Error splitting: {e}")
        return False

def split_pdf_to_images(input_path, output_dir, img_format, status_callback, progress_callback):
    """Splits a PDF into image files (JPG or PNG)."""
    try:
        if not os.path.isfile(input_path):
            messagebox.showerror("Error", f"Input PDF file not found: {input_path}")
            status_callback(f"Error: Input PDF not found {os.path.basename(input_path)}")
            return False
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
                status_callback(f"Created output directory: {output_dir}")
            except OSError as e:
                messagebox.showerror("Error", f"Output directory does not exist and cannot be created: {output_dir}\n{e}")
                status_callback(f"Error: Output directory creation failed {output_dir}")
                return False

        status_callback("Converting PDF pages to images (may take time)...")
        progress_callback(0, 1)
        poppler_path_arg = {"poppler_path": POPPLER_PATH} if POPPLER_PATH else {}
        
        try:
            images = convert_from_path(input_path, **poppler_path_arg)
        except Exception as e_convert:
            if "poppler" in str(e_convert).lower() or "pdftoppm" in str(e_convert).lower() or "PDFInfoNotInstalledError" in str(type(e_convert)):
                messagebox.showerror("Poppler Error",
                                     "Poppler utility not found or failed during execution.\n"
                                     "Ensure Poppler is installed and in your system PATH,\n"
                                     "or set the POPPLER_PATH variable in the script.\n\n"
                                     f"Details: {e_convert}")
                status_callback(f"Error: Poppler execution failed: {e_convert}")
                return False
            raise # Re-raise if not a poppler-related error

        progress_callback(1, 1)

        num_pages = len(images)
        progress_callback(0, num_pages)
        base_filename = os.path.splitext(os.path.basename(input_path))[0]
        img_format_lower = img_format.lower()
        if img_format_lower not in ['jpg', 'png']:
            raise ValueError("Invalid image format selected.")

        for i, image in enumerate(images):
            output_filename = os.path.join(output_dir, f"{base_filename}_page_{i + 1}.{img_format_lower}")
            if img_format_lower == 'jpg' and image.mode == 'RGBA':
                image = image.convert('RGB')
            image.save(output_filename, format=img_format_lower.upper())
            status_callback(f"Saved: {os.path.basename(output_filename)}")
            progress_callback(i + 1, num_pages)

        status_callback("Splitting to images complete.")
        return True
    except ImportError:
        messagebox.showerror("Error", "Pillow or pdf2image library not found. Please install them (e.g., pip install Pillow pdf2image).")
        status_callback("Error: Missing required library for image splitting.")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during image splitting:\n{e}")
        status_callback(f"Error splitting to images: {e}")
        return False


def merge_pdfs(input_sources_list_or_path, output_path, status_callback, progress_callback):
    writer = PyPDF2.PdfWriter()
    actual_files_to_process = []

    if isinstance(input_sources_list_or_path, list):
        temp_files = [f for f in input_sources_list_or_path if os.path.isfile(f)]
        actual_files_to_process = sorted(temp_files, key=natural_sort_key)
    elif isinstance(input_sources_list_or_path, str):
        single_path = input_sources_list_or_path
        if os.path.isdir(single_path):
            folder = single_path
            status_callback(f"Scanning folder: {folder}")
            try:
                filenames_in_folder = os.listdir(folder)
                # Create full paths then sort
                full_paths_in_folder = [os.path.join(folder, fn) for fn in filenames_in_folder if fn.lower().endswith((".pdf", ".jpg", ".jpeg", ".png"))]
                actual_files_to_process = sorted(full_paths_in_folder, key=natural_sort_key)
            except OSError as e:
                messagebox.showerror("Error", f"Could not read directory: {folder}\n{e}")
                status_callback(f"Error reading directory: {e}")
                return False
        elif os.path.isfile(single_path):
            if single_path.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
                 actual_files_to_process.append(single_path)
            else:
                messagebox.showerror("Error", f"Unsupported file type for merging: {os.path.basename(single_path)}")
                status_callback(f"Error: Unsupported file type: {os.path.basename(single_path)}")
                return False
        else:
            messagebox.showerror("Error", f"Input path not found or invalid: {single_path}")
            status_callback(f"Error: Input path not found: {single_path}")
            return False
    else:
        messagebox.showerror("Error", "Invalid input source type for merging.")
        status_callback("Error: Invalid input for merge.")
        return False

    if not actual_files_to_process:
        messagebox.showerror("Error", "No valid PDF or Image files found for merging.")
        status_callback("No valid files found to merge.")
        return False

    status_callback(f"Found {len(actual_files_to_process)} file(s) to merge (sorted naturally).")
    total_files = len(actual_files_to_process)
    progress_callback(0, total_files)
    successful_merges = 0
    files_skipped = 0

    for i, filepath in enumerate(actual_files_to_process):
        base_filename = os.path.basename(filepath)
        status_callback(f"Processing: {base_filename} ({i+1}/{total_files})")
        try:
            file_ext = filepath.lower().split('.')[-1]
            if file_ext in ("jpg", "jpeg", "png"):
                image = Image.open(filepath)
                if image.mode == 'RGBA' or image.mode == 'P':
                    image = image.convert('RGB')
                pdf_bytes_io = io.BytesIO()
                image.save(pdf_bytes_io, format='PDF', resolution=100.0, save_all=False)
                pdf_bytes_io.seek(0)
                writer.append(pdf_bytes_io) # Append in-memory PDF
                successful_merges += 1
                status_callback(f"Converted and appended image: {base_filename}")
            elif file_ext == "pdf":
                try:
                    writer.append(filepath) # Append existing PDF file
                    successful_merges += 1
                    status_callback(f"Appended PDF: {base_filename}")
                except PyPDF2.errors.PdfReadError as read_err:
                    status_callback(f"Skipping invalid/corrupted PDF: {base_filename}. Error: {read_err}")
                    files_skipped +=1
                    continue
                except Exception as append_err:
                    status_callback(f"Error appending PDF {base_filename}: {append_err}. Skipping.")
                    files_skipped += 1
                    continue
            else: # Should not happen due to earlier filtering, but as a safeguard
                status_callback(f"Skipping unsupported file type: {base_filename}")
                files_skipped += 1
                continue
        except FileNotFoundError:
            status_callback(f"File not found during merge: {base_filename}. Skipping.")
            files_skipped += 1
        except Image.UnidentifiedImageError:
            status_callback(f"Cannot identify or open image file: {base_filename}. Skipping.")
            files_skipped += 1
        except Exception as e:
            status_callback(f"Error processing file {base_filename}: {e}. Skipping.")
            files_skipped += 1
        progress_callback(i + 1, total_files)

    if successful_merges == 0 or not writer.pages:
        if files_skipped == total_files and total_files > 0:
             messagebox.showerror("Error", "All selected files were skipped due to errors or being invalid.")
        else:
            messagebox.showerror("Error", "No valid pages could be extracted or converted from the selected files.")
        status_callback("Merging failed: No valid content merged.")
        return False

    try:
        with open(output_path, "wb") as output_pdf:
            writer.write(output_pdf)
        final_msg = f"Merging complete. Output: {os.path.basename(output_path)}"
        if files_skipped > 0:
            final_msg += f" ({files_skipped} file(s) skipped)."
        status_callback(final_msg)
        return True
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred while saving the merged PDF:\n{e}")
        status_callback(f"Error saving merged PDF: {e}")
        return False

# --- GUI Class ---
class PdfUtilityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF Utility")
        self.root.geometry("600x570")

        self.style = ttk.Style()
        try: self.style.theme_use('vista')
        except tk.TclError:
            try: self.style.theme_use('clam')
            except tk.TclError: self.style.theme_use('default')

        self.mode = tk.StringVar(value="split")
        self.input_path = tk.StringVar()
        self._selected_merge_files = []
        self.output_path = tk.StringVar()
        self.split_output_type = tk.StringVar(value="pdf")
        self.image_format = tk.StringVar(value="PNG")

        self._create_widgets()
        self._layout_widgets() # This will call _layout_dynamic_elements
        self._update_ui_for_mode()

    def _create_widgets(self):
        self.mode_about_frame = ttk.Frame(self.root)
        self.mode_frame = ttk.LabelFrame(self.mode_about_frame, text="Select Mode")
        self.split_radio = ttk.Radiobutton(self.mode_frame, text="Split PDF", variable=self.mode, value="split", command=self._update_ui_for_mode)
        self.merge_radio = ttk.Radiobutton(self.mode_frame, text="Merge Files (PDF/Image)", variable=self.mode, value="merge", command=self._update_ui_for_mode)
        self.about_button = ttk.Button(self.mode_about_frame, text="About", command=self._show_about_dialog)

        self.input_frame = ttk.LabelFrame(self.root, text="Input")
        self.input_label_text = tk.StringVar(value="Input PDF File:")
        self.input_label = ttk.Label(self.input_frame, textvariable=self.input_label_text)
        self.input_entry = ttk.Entry(self.input_frame, textvariable=self.input_path, width=50, state='normal')
        self.input_button = ttk.Button(self.input_frame, text="Browse...", command=self._select_input)

        self.output_frame = ttk.LabelFrame(self.root, text="Output")
        self.output_label_text = tk.StringVar(value="Output Directory:")
        self.output_label = ttk.Label(self.output_frame, textvariable=self.output_label_text)
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path, width=50, state='normal')
        self.output_button = ttk.Button(self.output_frame, text="Browse...", command=self._select_output)

        self.split_options_frame = ttk.LabelFrame(self.root, text="Split Options")
        self.split_pdf_radio = ttk.Radiobutton(self.split_options_frame, text="Output as PDFs", variable=self.split_output_type, value="pdf", command=self._toggle_image_format_combo)
        self.split_image_radio = ttk.Radiobutton(self.split_options_frame, text="Output as Images", variable=self.split_output_type, value="image", command=self._toggle_image_format_combo)
        self.image_format_label = ttk.Label(self.split_options_frame, text="Image Format:")
        self.image_format_combo = ttk.Combobox(self.split_options_frame, textvariable=self.image_format, values=["PNG", "JPG"], state='readonly', width=7)

        self.action_button = ttk.Button(self.root, text="Start Processing", command=self._start_processing_thread, width=20)

        self.status_frame = ttk.LabelFrame(self.root, text="Status")
        self.status_label = ttk.Label(self.status_frame, text="Ready.", anchor="w", justify="left", wraplength=550)
        self.progress_bar = ttk.Progressbar(self.status_frame, orient="horizontal", length=300, mode="determinate")

    def _layout_widgets(self):
        # Pack main static frames
        self.mode_about_frame.pack(pady=(10,5), padx=10, fill="x")
        self.mode_frame.pack(side="left", fill="x", expand=True, padx=(0,5))
        self.split_radio.pack(side="left", padx=(10,5), pady=5)
        self.merge_radio.pack(side="left", padx=5, pady=5)
        self.about_button.pack(side="right", padx=5, pady=5, anchor="ne")

        self.input_frame.pack(pady=5, padx=10, fill="x")
        self.input_label.grid(row=0, column=0, padx=5, pady=(5,0), sticky="w")
        self.input_entry.grid(row=1, column=0, padx=5, pady=(0,5), sticky="ew")
        self.input_button.grid(row=1, column=1, padx=(0,5), pady=(0,5))
        self.input_frame.columnconfigure(0, weight=1)

        self.output_frame.pack(pady=5, padx=10, fill="x")
        self.output_label.grid(row=0, column=0, padx=5, pady=(5,0), sticky="w")
        self.output_entry.grid(row=1, column=0, padx=5, pady=(0,5), sticky="ew")
        self.output_button.grid(row=1, column=1, padx=(0,5), pady=(0,5))
        self.output_frame.columnconfigure(0, weight=1)

        # Grid widgets within split_options_frame (it will be packed by _layout_dynamic_elements)
        self.split_pdf_radio.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.split_image_radio.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.image_format_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.image_format_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Pack widgets within status_frame (it will be packed by _layout_dynamic_elements)
        self.status_label.pack(pady=(5,0), padx=5, fill="x")
        self.progress_bar.pack(pady=5, padx=5, fill="x")

        # Call this to pack split_options_frame, action_button, and status_frame in order
        self._layout_dynamic_elements()

    def _layout_dynamic_elements(self):
        """Handles packing of elements that change with mode or are below other frames."""
        self.split_options_frame.pack_forget()
        self.action_button.pack_forget()
        self.status_frame.pack_forget()

        if self.mode.get() == "split":
            self.split_options_frame.pack(pady=5, padx=10, fill="x")
        
        self.action_button.pack(pady=(15, 5)) 
        self.status_frame.pack(pady=(5,10), padx=10, fill="both", expand=True)

    def _update_ui_for_mode(self):
        mode = self.mode.get()
        self.input_path.set("")
        self.output_path.set("")
        self._selected_merge_files = []

        if mode == "split":
            self.input_label_text.set("Input PDF File:")
            self.output_label_text.set("Output Directory:")
            self.action_button.config(text="Start Splitting")
            self._toggle_image_format_combo()
        elif mode == "merge":
            self.input_label_text.set("Input Files/Folder (PDF, JPG, PNG):")
            self.output_label_text.set("Output Merged PDF File:")
            self.action_button.config(text="Start Merging")
            self.image_format_label.config(state='disabled') # Ensure disabled if not split image
            self.image_format_combo.config(state='disabled')
        
        self._layout_dynamic_elements()
        self._update_status("Ready.")
        self._update_progress(0, 1)

    def _toggle_image_format_combo(self):
        if self.mode.get() == "split" and self.split_output_type.get() == "image":
            self.image_format_label.config(state='normal')
            self.image_format_combo.config(state='readonly')
        else:
            self.image_format_label.config(state='disabled')
            self.image_format_combo.config(state='disabled')

    def _select_input(self):
        mode = self.mode.get()
        if mode == "split":
            filepath = filedialog.askopenfilename(title="Select Input PDF File", filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")])
            if filepath:
                self.input_path.set(filepath)
                self.output_path.set(os.path.dirname(filepath))
                self._selected_merge_files = []
        elif mode == "merge":
            filepaths = filedialog.askopenfilenames(
                title="Select Input PDF and Image Files",
                filetypes=[("Supported Files", "*.pdf *.jpg *.jpeg *.png"), ("PDF Files", "*.pdf"), ("Image Files", "*.jpg *.jpeg *.png"), ("All Files", "*.*")])
            if filepaths:
                self._selected_merge_files = sorted(list(filepaths), key=natural_sort_key)
                self.input_path.set(f"{len(self._selected_merge_files)} file(s) selected")
                if self._selected_merge_files:
                    self.output_path.set(os.path.join(os.path.dirname(self._selected_merge_files[0]), "merged_output.pdf"))

    def _select_output(self):
        mode = self.mode.get()
        current_output_val = self.output_path.get()
        initial_dir_val = None

        # Determine initial directory robustly
        if mode == "split":
            if current_output_val and os.path.isdir(current_output_val):
                initial_dir_val = current_output_val
            elif self.input_path.get() and os.path.isfile(self.input_path.get()):
                 initial_dir_val = os.path.dirname(self.input_path.get())
        elif mode == "merge":
            if current_output_val and os.path.isfile(current_output_val): # If a file path is set
                initial_dir_val = os.path.dirname(current_output_val)
            elif self._selected_merge_files and os.path.isfile(self._selected_merge_files[0]): # From selected files
                 initial_dir_val = os.path.dirname(self._selected_merge_files[0])
            elif self.input_path.get() and f"file(s) selected" not in self.input_path.get(): # If input path is typed
                if os.path.isfile(self.input_path.get()): initial_dir_val = os.path.dirname(self.input_path.get())
                elif os.path.isdir(self.input_path.get()): initial_dir_val = self.input_path.get()
        
        if initial_dir_val is None: # Fallback
            initial_dir_val = os.getcwd()


        if mode == "split":
            dirpath = filedialog.askdirectory(title="Select Output Directory", initialdir=initial_dir_val)
            if dirpath: self.output_path.set(dirpath)
        elif mode == "merge":
            initial_file = os.path.basename(current_output_val) if current_output_val and not os.path.isdir(current_output_val) else "merged_output.pdf"
            filepath = filedialog.asksaveasfilename(
                title="Save Merged PDF As...", initialdir=initial_dir_val, initialfile=initial_file,
                defaultextension=".pdf", filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")])
            if filepath: self.output_path.set(filepath)

    def _update_status(self, message):
        self.root.after(0, self.status_label.config, {'text': message})

    def _update_progress(self, value, maximum):
        def do_update():
            self.progress_bar['maximum'] = maximum if maximum > 0 else 1
            self.progress_bar['value'] = value
        self.root.after(0, do_update)

    def _processing_finished(self, success):
        self.action_button.config(state='normal')
        if success:
            final_message = self.status_label.cget("text")
            messagebox.showinfo("Success", "Processing completed successfully!")
            if "complete" in final_message.lower() or "output" in final_message.lower():
                 self._update_status(final_message) # Keep detailed success message
            else:
                 self._update_status("Done. Processing completed successfully.")
        else:
            current_status = self.status_label.cget("text")
            if "Error" not in current_status and "Failed" not in current_status and "Skipping" not in current_status:
                self._update_status("Failed. See error messages or console for details.")
        if not success or self.progress_bar['value'] == self.progress_bar['maximum']:
            self.root.after(500, lambda: self._update_progress(0,1))


    def _start_processing_thread(self):
        typed_input_path = self.input_path.get()
        output_target = self.output_path.get()
        mode = self.mode.get()
        actual_input_source_for_processing = None

        if not output_target:
            messagebox.showerror("Error", f"Please select or enter an output {'directory' if mode == 'split' else 'file path'}.")
            return

        if mode == "split":
            if not typed_input_path:
                messagebox.showerror("Error", "Please select or enter an input PDF file.")
                return
            if not os.path.isfile(typed_input_path):
                 messagebox.showerror("Error", f"Input PDF file not found: {typed_input_path}")
                 return
            actual_input_source_for_processing = typed_input_path
        elif mode == "merge":
            if self._selected_merge_files and typed_input_path == f"{len(self._selected_merge_files)} file(s) selected":
                actual_input_source_for_processing = self._selected_merge_files
            elif typed_input_path:
                actual_input_source_for_processing = typed_input_path
            else:
                messagebox.showerror("Error", "Please select or enter input files/folder for merging.")
                return
            
            output_dir_merge = os.path.dirname(output_target)
            if not os.path.isdir(output_dir_merge) and output_dir_merge: # Ensure output_dir_merge is not empty if output_target is just a filename
                try:
                    os.makedirs(output_dir_merge, exist_ok=True)
                except OSError as e:
                    messagebox.showerror("Error", f"Output directory does not exist and cannot be created: {output_dir_merge}\n{e}")
                    return
            elif not output_dir_merge and not os.path.isdir(os.getcwd()): # Edge case: saving to root of a non-existent drive?
                messagebox.showerror("Error", f"Cannot determine output directory: {output_target}")
                return


        check_output_dir = output_target if mode == "split" else os.path.dirname(output_target)
        if not check_output_dir: check_output_dir = os.getcwd() # If dirname is empty (e.g. just "file.pdf"), check current dir

        if not os.access(check_output_dir, os.W_OK):
            messagebox.showwarning("Permission Warning", f"Cannot write to the output location: {check_output_dir}\nPlease check permissions.")
            # return # Optional: stop execution

        self.action_button.config(state='disabled')
        self._update_status("Starting processing...")
        self._update_progress(0, 1)

        args = ()
        target_func = None

        if mode == "split":
            split_type = self.split_output_type.get()
            if split_type == "pdf":
                target_func = split_pdf_to_pdfs
            elif split_type == "image":
                target_func = split_pdf_to_images
                args = (actual_input_source_for_processing, output_target, self.image_format.get(), self._update_status, self._update_progress)
            if target_func and not args: # For split_pdf_to_pdfs
                 args = (actual_input_source_for_processing, output_target, self._update_status, self._update_progress)

        elif mode == "merge":
            target_func = merge_pdfs
            args = (actual_input_source_for_processing, output_target, self._update_status, self._update_progress)

        if target_func:
            processing_thread = threading.Thread(target=self._run_task, args=(target_func, args), daemon=True)
            processing_thread.start()
        else:
            messagebox.showerror("Error", "Invalid processing mode or options selected.")
            self.action_button.config(state='normal')
            self._update_status("Error: Invalid mode or options.")

    def _run_task(self, func, args):
        success = False
        try:
            success = func(*args)
        except Exception as e:
            print(f"Critical Error in processing thread for function {func.__name__}: {e}")
            import traceback
            traceback.print_exc() # Print full traceback to console
            self.root.after(0, messagebox.showerror, "Critical Background Error", f"An unexpected error occurred in the background task:\n{e}")
            self.root.after(0, self._update_status, f"Critical Error: {e}")
            success = False
        finally:
            self.root.after(0, self._processing_finished, success)

    def _show_about_dialog(self):
        about_win = tk.Toplevel(self.root)
        about_win.title(f"About {self.root.title()}")
        about_win.geometry("380x280")
        about_win.resizable(False, False)
        about_win.transient(self.root)
        about_win.grab_set()

        main_frame = ttk.Frame(about_win, padding="20")
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text=self.root.title(), font=("Helvetica", 16, "bold")).pack(pady=(0,10))
        ttk.Label(main_frame, text=f"Version: {APP_VERSION}").pack()
        ttk.Label(main_frame, text=f"Release Date: {RELEASE_DATE}").pack()
        ttk.Label(main_frame, text=f"Author: {AUTHOR_NAME}").pack(pady=(10,5))

        link_font = ("Helvetica", 10, "underline")
        def open_link(url): webbrowser.open_new_tab(url)
        
        gh_label = ttk.Label(main_frame, text="GitHub Profile", foreground="blue", cursor="hand2", font=link_font)
        gh_label.pack(pady=2); gh_label.bind("<Button-1>", lambda e: open_link(GITHUB_URL))
        
        li_label = ttk.Label(main_frame, text="LinkedIn Profile", foreground="blue", cursor="hand2", font=link_font)
        li_label.pack(pady=2); li_label.bind("<Button-1>", lambda e: open_link(LINKEDIN_URL))
        
        ttk.Label(main_frame, text="\nPowered by PyPDF2, Pillow, pdf2image.").pack(pady=(5,0))
        ttk.Button(main_frame, text="Close", command=about_win.destroy).pack(pady=(5,0))
        
        about_win.update_idletasks()
        x_root, y_root = self.root.winfo_x(), self.root.winfo_y()
        w_root, h_root = self.root.winfo_width(), self.root.winfo_height()
        w_about, h_about = about_win.winfo_width(), about_win.winfo_height()
        x_about = x_root + (w_root - w_about) // 2
        y_about = y_root + (h_root - h_about) // 2
        about_win.geometry(f"+{x_about}+{y_about}")

# --- Main Application Runner ---
if __name__ == "__main__":
    root = tk.Tk()
    app = PdfUtilityApp(root)
    root.mainloop()
