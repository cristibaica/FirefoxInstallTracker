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
    COLUMNS = ("version", "arch", "language", "status")

    def __init__(self):
        super().__init__()
        self.title("Firefox Build Manager")
        self.geometry("720x450")
        self.resizable(True, True)
        self.minsize(720, 400)

        self.manual_version = tk.StringVar()
        self.selected_arch = tk.StringVar(value=ARCHITECTURES[0])
        self.language_code = tk.StringVar(value="en-US")

        self.create_widgets()
        self.create_installed_builds_section()
        self.verify_and_clean_installs(silent=True)  # <--- Verify silently on startup

    def create_widgets(self):
        input_frame = ttk.LabelFrame(self, text="Firefox Build Configuration")
        input_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(input_frame, text="Version:").grid(row=0, column=0, padx=(10, 5), pady=10, sticky="e")
        ttk.Entry(input_frame, textvariable=self.manual_version, width=25).grid(row=0, column=1, padx=5, pady=10)

        ttk.Label(input_frame, text="Architecture:").grid(row=0, column=2, padx=(10, 5), pady=10, sticky="e")
        ttk.Combobox(input_frame, textvariable=self.selected_arch, values=ARCHITECTURES, state="readonly",
                     width=18).grid(row=0, column=3, padx=5, pady=10)

        ttk.Label(input_frame, text="Language:").grid(row=0, column=4, padx=(10, 5), pady=10, sticky="e")
        ttk.Entry(input_frame, textvariable=self.language_code, width=15).grid(row=0, column=5, padx=(5, 10), pady=10)

        input_frame.grid_columnconfigure(1, weight=1)
        input_frame.grid_columnconfigure(3, weight=1)
        input_frame.grid_columnconfigure(5, weight=1)

        ttk.Button(self, text="Download & Install Build", command=self.download_selected).pack(pady=(0, 10))

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

            # Show the progress bar frame below the buttons. The buttons are not touched.
            self.progress_frame.pack(pady=5, padx=10, fill="x")
            self.progress["value"] = 0
            self.update_idletasks()

            zip_path = download_build(version, arch, lang, progress_callback=self.update_progress)

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
            # Hide the progress bar frame, leaving the buttons untouched.
            self.progress_frame.pack_forget()
            self.title("Firefox Build Manager")
            self.refresh_installed_builds()

    def update_progress(self, percent):
        self.progress["value"] = percent
        self.update_idletasks()

    def create_installed_builds_section(self):
        section = ttk.LabelFrame(self, text="Installed Builds")
        section.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.installed_tree = ttk.Treeview(section, columns=self.COLUMNS, show="headings", height=5)
        for col in self.COLUMNS:
            heading_text = col.replace("_", " ").capitalize()
            self.installed_tree.heading(col, text=heading_text)
            self.installed_tree.column(col, width=150, anchor="w")

        scrollbar = ttk.Scrollbar(section, orient="vertical", command=self.installed_tree.yview)
        self.installed_tree.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.installed_tree.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)

        # --- Button Frame ---
        self.btn_frame = ttk.Frame(self)
        self.btn_frame.pack(pady=5, padx=10, fill="x")

        # Left-aligned buttons
        ttk.Button(self.btn_frame, text="Launch", command=self.launch_selected).pack(side="left", padx=5)
        ttk.Button(self.btn_frame, text="Open Folder", command=self.open_selected_folder).pack(side="left", padx=5)

        # Right-aligned buttons (packed in reverse order of appearance)
        ttk.Button(self.btn_frame, text="Remove", command=self.remove_selected).pack(side="right", padx=5)
        ttk.Button(self.btn_frame, text="Refresh List", command=self.verify_and_clean_installs).pack(side="right",
                                                                                                     padx=5)
        # --- Progress Bar Frame (initially hidden) ---
        # This frame has its own row and will be shown/hidden as needed.
        self.progress_frame = ttk.Frame(self)
        self.progress = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", expand=True, padx=5, pady=(0, 5))


    def refresh_installed_builds(self):
        for row in self.installed_tree.get_children():
            self.installed_tree.delete(row)

        for entry in load_db():
            install_path = get_install_folder(entry["version"], entry["arch"], entry["language"])
            status = "Installed ✔️" if os.path.isdir(install_path) else "Missing"
            self.installed_tree.insert("", "end", values=(
                entry["version"],
                entry["arch"],
                entry["language"],
                status
            ))

    def _get_selected_build_info(self):
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

        version, arch, lang, status = values
        if status == "Missing":
            messagebox.showinfo(
                "Auto-Removing Missing Build",
                "This build's folder is missing. It will be automatically removed from the list."
            )
            try:
                self._remove_entry(version, arch, lang)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to auto-remove the build: {e}")
            return

        install_path = get_install_folder(version, arch, lang)

        if "win" in arch:
            firefox_path = os.path.join(install_path, "firefox", "firefox.exe")
        elif "mac" in arch:
            firefox_path = os.path.join(install_path, "Firefox.app", "Contents", "MacOS", "firefox")
        else:
            firefox_path = os.path.join(install_path, "firefox", "firefox")

        if not os.path.isfile(firefox_path):
            messagebox.showinfo(
                "Auto-Removing Corrupt Build",
                "The Firefox executable is missing from the installation folder. This entry will be automatically removed."
            )
            try:
                self._remove_entry(version, arch, lang)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to auto-remove the build: {e}")
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
        confirm = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you sure you want to permanently delete this build?"
        )
        if confirm:
            try:
                self._remove_entry(version, arch, lang)
                messagebox.showinfo("Removed", "The build was successfully removed.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove the build: {e}")

    def verify_and_clean_installs(self, silent=False):
        """
        Checks all DB entries against the filesystem and removes any entries
        where the installation folder is missing.
        If silent is False, shows a message to the user.
        """
        db_entries = load_db()

        # No need to show a message if the list is empty and the user didn't click the button
        if not db_entries and silent:
            self.refresh_installed_builds()
            return

        entries_to_keep = []
        removed_count = 0

        for entry in db_entries:
            install_path = get_install_folder(entry["version"], entry["arch"], entry["language"])
            if os.path.isdir(install_path):
                entries_to_keep.append(entry)
            else:
                removed_count += 1

        if removed_count > 0:
            save_db(entries_to_keep)
            if not silent:  # Only show the message if not in silent mode
                messagebox.showinfo(
                    "Refresh Complete",
                    f"Removed {removed_count} missing build(s) from the list."
                )
        else:
            if not silent: # Only show a message if the user clicked the button
                messagebox.showinfo("Refresh Complete", "All build installations are verified.")

        self.refresh_installed_builds()

    def _remove_entry(self, version, arch, lang):
        """Removes a build entry from the DB and its folder from the filesystem."""
        folder = get_install_folder(version, arch, lang)
        if os.path.isdir(folder):
            shutil.rmtree(folder)

        db = [e for e in load_db() if not (e["version"] == version and e["arch"] == arch and e["language"] == lang)]
        save_db(db)

        self.refresh_installed_builds()


if __name__ == "__main__":
    app = FirefoxManagerApp()
    app.mainloop()