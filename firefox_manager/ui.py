import tkinter as tk
from tkinter import ttk, messagebox
from downloader import download_build
from manager import extract_zip, extract_tar_bz2, extract_tar_xz, add_install_record, get_install_folder, load_db, save_db
import os
import subprocess
import shutil
import webbrowser
import re

ARCHITECTURES = ["win64", "win32", "mac", "linux-x86_64"]


def get_actual_firefox_version(firefox_path):
    try:
        # Ensure the executable exists before trying to run it
        if not os.path.isfile(firefox_path):
            return None
        result = subprocess.run([firefox_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                timeout=5, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        match = re.search(r"Mozilla Firefox (\S+)", result.stdout)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Could not get Firefox version from {firefox_path}: {e}")
    return None


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
        self.verify_and_clean_installs(silent=True)

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

        # Check if this exact build is already installed
        for entry in load_db():
            if (entry["version"] == version and entry["arch"] == arch and entry["language"] == lang):
                install_path = get_install_folder(entry["version"], entry["arch"], entry["language"])
                if os.path.isdir(install_path):
                    messagebox.showinfo("Already Installed", f"This build ({version}) is already installed.")
                    return

        try:
            self.title(f"Downloading {version}...")
            self.progress_frame.pack(pady=5, padx=10, fill="x")
            self.progress["value"] = 0
            self.update_idletasks()

            zip_path = download_build(version, arch, lang, dest_folder="downloads",
                                      progress_callback=self.update_progress)

            install_path = get_install_folder(version, arch, lang)
            extracted = False

            if zip_path.endswith(".zip"):
                os.makedirs(install_path, exist_ok=True)
                extract_zip(zip_path, install_path)
                extracted = True
            elif zip_path.endswith(".tar.bz2"):
                os.makedirs(install_path, exist_ok=True)
                extract_tar_bz2(zip_path, install_path)
                extracted = True
            elif zip_path.endswith(".tar.xz"):
                os.makedirs(install_path, exist_ok=True)
                extract_tar_xz(zip_path, install_path)
                extracted = True

            if extracted:
                add_install_record(version, arch, lang, install_path)
                messagebox.showinfo("Done", f"Successfully installed to:\n{install_path}")
            else:
                messagebox.showinfo("Downloaded",
                                    f"Build downloaded but not installed (unsupported format).\nSaved to:\n{zip_path}")

        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
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

        self.btn_frame = ttk.Frame(self)
        self.btn_frame.pack(pady=5, padx=10, fill="x")

        ttk.Button(self.btn_frame, text="Launch", command=self.launch_selected).pack(side="left", padx=5)
        ttk.Button(self.btn_frame, text="Open Folder", command=self.open_selected_folder).pack(side="left", padx=5)

        ttk.Button(self.btn_frame, text="Remove", command=self.remove_selected).pack(side="right", padx=5)
        ttk.Button(self.btn_frame, text="Refresh List", command=self.verify_and_clean_installs).pack(side="right",
                                                                                                     padx=5)

        self.progress_frame = ttk.Frame(self)
        self.progress = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", expand=True, padx=5, pady=(0, 5))

    def refresh_installed_builds(self):
        # Clear the treeview
        for row in self.installed_tree.get_children():
            self.installed_tree.delete(row)

        # Repopulate from the database
        for entry in load_db():
            install_path = get_install_folder(entry["version"], entry["arch"], entry["language"])
            status = "Installed ✔️" if os.path.isdir(install_path) else "Missing"
            self.installed_tree.insert("", "end", values=(entry["version"], entry["arch"], entry["language"], status))

    def _get_selected_build_info(self):
        selection = self.installed_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a build from the list.")
            return None
        return self.installed_tree.item(selection[0], "values")

    def _get_exec_path(self, install_path, arch):
        """Helper to get the platform-specific executable path."""
        if "win" in arch:
            return os.path.join(install_path, "firefox", "firefox.exe")
        elif "mac" in arch:
            return os.path.join(install_path, "Firefox.app", "Contents", "MacOS", "firefox")
        else:  # linux
            return os.path.join(install_path, "firefox", "firefox")

    def launch_selected(self):
        values = self._get_selected_build_info()
        if not values:
            return

        version, arch, lang, status = values
        if status == "Missing":
            messagebox.showinfo("Auto-Removing Missing Build",
                                "This build's folder is missing. It will be automatically removed from the list.")
            try:
                self._remove_entry(version, arch, lang)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to auto-remove the build: {e}")
            return

        install_path = get_install_folder(version, arch, lang)
        firefox_path = self._get_exec_path(install_path, arch)

        if not os.path.isfile(firefox_path):
            messagebox.showinfo("Auto-Removing Corrupt Build",
                                "The Firefox executable is missing. This entry will be removed.")
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
        confirm = messagebox.askyesno("Confirm Deletion", "Are you sure you want to permanently delete this build?")
        if confirm:
            try:
                self._remove_entry(version, arch, lang)
                messagebox.showinfo("Removed", "The build was successfully removed.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove the build: {e}")

    def verify_and_clean_installs(self, silent=False):
        db_entries = load_db()
        if not db_entries and silent:
            self.refresh_installed_builds()
            return

        updated_db = []
        removed_count = 0
        updated_count = 0

        for entry in db_entries:
            current_install_path = get_install_folder(entry["version"], entry["arch"], entry["language"])

            if not os.path.isdir(current_install_path):
                removed_count += 1
                continue  # Skip to next entry, it will be removed from the DB

            # Folder exists, check for version updates
            firefox_exec = self._get_exec_path(current_install_path, entry["arch"])
            actual_version = get_actual_firefox_version(firefox_exec)

            if actual_version and actual_version != entry["version"]:
                # Version has changed, we need to rename the folder and update the DB
                new_install_path = get_install_folder(actual_version, entry["arch"], entry["language"])
                try:
                    print(f"Updating version for {entry['version']} -> {actual_version}")
                    # Rename the folder to match the new version
                    os.rename(current_install_path, new_install_path)

                    # Update the entry's version to the new one
                    entry["version"] = actual_version
                    entry["install_path"] = new_install_path
                    updated_count += 1
                except OSError as e:
                    print(f"Error renaming folder for {entry['version']}: {e}. Skipping update for this entry.")

            updated_db.append(entry)

        # Save the database if any changes were made
        if removed_count > 0 or updated_count > 0:
            save_db(updated_db)

        # Show a summary message if not in silent mode
        if not silent:
            messages = []
            if removed_count > 0:
                messages.append(f"Removed {removed_count} missing build(s).")
            if updated_count > 0:
                messages.append(f"Updated {updated_count} build(s) to their current version.")

            if messages:
                messagebox.showinfo("Refresh Complete", "\n".join(messages))
            else:
                messagebox.showinfo("Refresh Complete", "All build installations are verified.")

        self.refresh_installed_builds()

    def _remove_entry(self, version, arch, lang):
        folder = get_install_folder(version, arch, lang)
        if os.path.isdir(folder):
            shutil.rmtree(folder)

        # Create a new list excluding the entry to be removed
        db = [e for e in load_db() if not (e["version"] == version and e["arch"] == arch and e["language"] == lang)]
        save_db(db)
        self.refresh_installed_builds()


if __name__ == "__main__":
    app = FirefoxManagerApp()
    app.mainloop()