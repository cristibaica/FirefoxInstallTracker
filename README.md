# Firefox Build Manager

Firefox Build Manager is a desktop utility built with Python and Tkinter that simplifies the process of downloading, installing, and managing multiple versions of Firefox. It is particularly useful for web developers, QA testers, and power users who need to work with specific pre-release ("candidate") builds of Firefox.

## Features

*   **Download Specific Builds:** Easily download any Firefox candidate build by specifying its version (e.g., `128.0b3`), architecture (win64, mac, linux-x86_64), and language.
*   **Automated Installation:** Automatically extracts downloaded archives into a clean, organized folder structure within the `builds/` directory.
*   **Centralized Management:** View all your installed Firefox versions in a clear list, showing their version, architecture, language, and status.
*   **One-Click Launch:** Launch any installed Firefox version directly from the application.
*   **Easy Access:** Quickly open the installation folder for any build in your system's file explorer.
*   **Clean Removal:** Completely remove a build, deleting its files and database record with a single click.
*   **Smart Version Sync:** The "Refresh" feature automatically detects when a Firefox build has updated itself (e.g., from `142.0` to `142.0.1`). It updates the version in the list and **renames the installation folder** to match, keeping everything perfectly synchronized.
*   **Automatic Cleanup:** The application automatically detects and removes entries for builds that have been manually deleted, keeping your list clean and accurate.

## How It Works

The application maintains a simple ecosystem to manage builds:

*   `builds/`: The root directory where all Firefox versions are installed. Each build gets its own subfolder named with its version, architecture, and language (e.g., `builds/128.0b3-candidates-win64-en-US`).
*   `downloads/`: A temporary directory where build archives are downloaded before being extracted.
*   `firefox_db.json`: A simple JSON file that acts as a database, keeping a record of every managed build and its metadata.

## Prerequisites

Before running the application, you need to install the required Python libraries:

```bash
pip install requests beautifulsoup4
```

## How to Run

1.  Ensure you have Python 3 installed.
2.  Install the prerequisites using the command above.
3.  Run the main UI file from your terminal:

    ```bash
    python ui.py
    ```

## Project Files

*   `ui.py`: The main application file containing the Tkinter GUI and user interaction logic. It orchestrates all high-level operations.
*   `downloader.py`: Handles all communication with the Mozilla archive to find the latest build number and download the correct build files.
*   `manager.py`: Contains the backend logic for managing the JSON database, extracting archives, and defining the installation folder structure.
*   `firefox_db.json`: The database file that stores the list of installed builds.
