# ui.py
import tkinter as tk
from tkinter import ttk, messagebox
from downloader import download_build
from manager import extract_zip, add_install_record, get_install_folder, load_db, save_db
import os
import subprocess
import shutil
import webbrowser

ARCHITECTURES = ["win64", "win32", "mac", "linux-x86_64"]


class FirefoxManagerApp(tk.Tk):
    # Improvement 3: Use a constant for column names for clarity and easy maintenance.
    COLUMNS = ("version", "arch", "language", "status")

    def __init__(self):
        super().__init__()
        self.title("Firefox Build Manager")
        # Increased window height to better accommodate the installed builds list
        self.geometry("720x450")
        self.resizable(True, True)  # Allowing resize is generally better for usability
        self.minsize(720, 400)

        self.manual_version = tk.StringVar()
        self.selected_arch = tk.StringVar(value=ARCHITECTURES[0])
        self.language_code = tk.StringVar(value="en-US")

        self.create_widgets()

        self.installed_tree = None
        self.create_installed_builds_section()
        self.refresh_installed_builds()

    def create_widgets(self):
        input_frame = ttk.LabelFrame(self, text="Firefox Build Configuration")
        input_frame.pack(fill="x", padx=10, pady=10)

        # --- Input Grid ---
        ttk.Label(input_frame, text="Version:").grid(row=0, column=0, padx=(10, 5), pady=10, sticky="e")
        ttk.Entry(input_frame, textvariable=self.manual_version, width=25).grid(row=0, column=1, padx=5, pady=10)

        ttk.Label(input_frame, text="Architecture:").grid(row=0, column=2, padx=(10, 5), pady=10, sticky="e")
        ttk.Combobox(input_frame, textvariable=self.selected_arch, values=ARCHITECTURES, state="readonly",
                     width=18).grid(row=0, column=3, padx=5, pady=10)

        ttk.Label(input_frame, text="Language:").grid(row=0, column=4, padx=(10, 5), pady=10, sticky="e")
        ttk.Entry(input_frame, textvariable=self.language_code, width=15).grid(row=0, column=5, padx=(5, 10), pady=10)

        # Make columns in the grid resize with the window
        input_frame.grid_columnconfigure(1, weight=1)
        input_frame.grid_columnconfigure(3, weight=1)
        input_frame.grid_columnconfigure(5, weight=1)

        # --- Download Button ---
        ttk.Button(self, text="Download & Install Build", command=self.download_selected).pack(pady=(0, 10))

        # --- Progress Bar ---
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=400)
        self.progress.pack(pady=(0, 10))
        self.progress.pack_forget()  # hide initially

    def download_selected(self):
        version = self.manual_version.get().strip()
        arch = self.selected_arch.get()
        lang = self.language_code.get().strip()

        if not version:
            messagebox.showwarning("Missing Version", "Please enter a version (e.g. 128.0b3)")
            return

        if not version.endswith("-candidates"):
            version += "-candidates"

        try:
            self.title(f"Downloading {version}...")
            self.update_idletasks()  # Force UI update

            zip_path = download_build(version, arch, lang)

            # The app only knows how to extract .zip files currently.
            # For other formats, it just downloads them.
            if zip_path.endswith(".zip"):
                install_path = get_install_folder(version, arch, lang)
                os.makedirs(install_path, exist_ok=True)
                extract_zip(zip_path, install_path)
                add_install_record(version, arch, lang, install_path)
                messagebox.showinfo("Done", f"Successfully installed to:\n{install_path}")
            else:
                messagebox.showinfo("Downloaded",
                                    f"Build downloaded but not installed (unsupported format).\nSaved to:\n{zip_path}")

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.title("Firefox Build Manager")
            self.refresh_installed_builds()


    def create_installed_builds_section(self):
        section = ttk.LabelFrame(self, text="Installed Builds")
        section.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Improvement 3: Use the COLUMNS constant
        self.installed_tree = ttk.Treeview(section, columns=self.COLUMNS, show="headings", height=5)
        for col in self.COLUMNS:
            # A small improvement to make headings like "Installed at" look better
            heading_text = col.replace("_", " ").capitalize()
            self.installed_tree.heading(col, text=heading_text)
            self.installed_tree.column(col, width=150, anchor="w")

        # Add a scrollbar
        scrollbar = ttk.Scrollbar(section, orient="vertical", command=self.installed_tree.yview)
        self.installed_tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.installed_tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)

        # Action Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5, padx=10, fill="x")

        ttk.Button(btn_frame, text="Launch", command=self.launch_selected).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Open Folder", command=self.open_selected_folder).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Remove", command=self.remove_selected).pack(side="right", padx=5)

    def refresh_installed_builds(self):
        for row in self.installed_tree.get_children():
            self.installed_tree.delete(row)

        for entry in load_db():
            install_path = get_install_folder(entry["version"], entry["arch"], entry["language"])
            if os.path.isdir(install_path):
                status = "Installed ✔️"
            else:
                status = "Pending"
            self.installed_tree.insert("", "end", values=(
                entry["version"],
                entry["arch"],
                entry["language"],
                status
            ))

    # Improvement 1: Create a helper to get the selected item and reduce code duplication.
    def _get_selected_build_info(self):
        """Gets the selected item from the tree and returns its values."""
        selection = self.installed_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a build from the list.")
            return None
        item_id = selection[0]
        return self.installed_tree.item(item_id, "values")

    def launch_selected(self):
        values = self._get_selected_build_info()
        if not values:
            return

        version, arch, lang, _ = values
        install_path = get_install_folder(version, arch, lang)

        # Improvement 2: Cross-platform logic for finding the executable.
        if "win" in arch:
            firefox_path = os.path.join(install_path, "firefox", "firefox.exe")
        elif "mac" in arch:
            # This path assumes a .dmg was manually extracted.
            firefox_path = os.path.join(install_path, "Firefox.app", "Contents", "MacOS", "firefox")
        else:  # Assuming Linux
            # This path assumes a .tar.bz2 was manually extracted.
            firefox_path = os.path.join(install_path, "firefox", "firefox")

        if not os.path.isfile(firefox_path):
            messagebox.showerror("Missing Executable", f"Cannot find the Firefox executable at:\n{firefox_path}")
            return

        subprocess.Popen([firefox_path])

    def open_selected_folder(self):
        values = self._get_selected_build_info()
        if not values:
            return

        version, arch, lang, _ = values
        folder = get_install_folder(version, arch, lang)
        if not os.path.isdir(folder):
            messagebox.showerror("Not Found", "The installation folder does not exist.")
            return

        webbrowser.open(folder)

    def remove_selected(self):
        values = self._get_selected_build_info()
        if not values:
            return

        version, arch, lang, _ = values
        folder = get_install_folder(version, arch, lang)

        confirm = messagebox.askyesno("Confirm Deletion",
                                      f"Are you sure you want to permanently delete this build?\n\n{folder}")
        if not confirm:
            return

        try:
            if os.path.isdir(folder):
                shutil.rmtree(folder)

            # Filter out the entry to be removed from the database
            db = [e for e in load_db() if not (e["version"] == version and e["arch"] == arch and e["language"] == lang)]
            save_db(db)

            self.refresh_installed_builds()
            messagebox.showinfo("Removed", "The build was successfully removed.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove the build: {e}")
