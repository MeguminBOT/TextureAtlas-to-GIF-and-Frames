import tkinter as tk
from tkinter import ttk
import webbrowser


class ContributorsWindow:
    """
    A window class for displaying project contributors and their social media links.

    This class provides a dedicated window to thank contributors to the project
    and allows users to visit their social media profiles or GitHub pages.

    Methods:
        create_contributors_window():
            Creates and displays the contributors window with contributor information and links.
        open_link(url):
            Opens a URL in the default web browser.
    """

    @staticmethod
    def create_contributors_window():
        """Creates and displays the contributors window."""
        contributors_window = tk.Toplevel()
        contributors_window.geometry("600x500")
        contributors_window.title("Contributors")
        contributors_window.resizable(True, True)

        main_frame = ttk.Frame(contributors_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_frame,
            text="TextureAtlas to GIF and Frames\nContributors",
            font=("Arial", 16, "bold"),
            justify="center",
        )
        title_label.pack(pady=(0, 20))

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        ContributorsWindow._add_section_header(
            scrollable_frame,
            "Project Starter",
            "The person who started this project and laid the foundation for everything that followed.",
        )
        ContributorsWindow._add_contributor_entry(
            scrollable_frame,
            "AutisticLulu",
            "The original creator and main developer of this project.",
            [
                ("GitHub Profile", "https://github.com/MeguminBOT"),
            ],
        )

        ttk.Separator(scrollable_frame, orient="horizontal").pack(fill="x", pady=20)

        ContributorsWindow._add_section_header(
            scrollable_frame,
            "Major Contributors",
            "Contributors who have made significant improvements, added major features, or provided substantial code contributions.",
        )
        ContributorsWindow._add_contributor_entry(
            scrollable_frame,
            "Jsfasdf250",
            "Big contributor to the tool with significant improvements and features.",
            [
                ("GitHub Profile", "https://github.com/Jsfasdf250"),
            ],
        )

        ttk.Separator(scrollable_frame, orient="horizontal").pack(fill="x", pady=20)

        ContributorsWindow._add_section_header(
            scrollable_frame,
            "Special Thanks",
            "People who have contributed in unique ways, provided resources, or helped make this project better.",
        )
        ContributorsWindow._add_contributor_entry(
            scrollable_frame,
            "Julnz",
            "Created the beautiful app icon for the application.",
            [
                ("Website", "https://julnz.com/"),
            ],
        )

        ttk.Separator(scrollable_frame, orient="horizontal").pack(fill="x", pady=20)

        ContributorsWindow._add_info_section(
            scrollable_frame,
            "Additional Contributors",
            "This project welcomes contributions from the community.\nThank you to everyone who has helped improve this tool!",
        )

        github_frame = ttk.Frame(scrollable_frame)
        github_frame.pack(fill="x", pady=10)

        github_label = tk.Label(
            github_frame, text="View all contributors on GitHub:", font=("Arial", 10)
        )
        github_label.pack()

        github_link = tk.Label(
            github_frame,
            text="https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/graphs/contributors",
            font=("Arial", 10),
            fg="blue",
            cursor="hand2",
        )
        github_link.pack(pady=5)
        github_link.bind(
            "<Button-1>",
            lambda e: ContributorsWindow.open_link(
                "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames/graphs/contributors"
            ),
        )

        ttk.Separator(scrollable_frame, orient="horizontal").pack(fill="x", pady=20)

        ContributorsWindow._add_info_section(
            scrollable_frame,
            "Want to Contribute?",
            "We welcome contributions! Whether it's bug fixes, new features, or documentation improvements.\n\n"
            "Check out our GitHub repository to get started:",
        )

        repo_frame = ttk.Frame(scrollable_frame)
        repo_frame.pack(fill="x", pady=10)

        repo_link = tk.Label(
            repo_frame,
            text="https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames",
            font=("Arial", 10),
            fg="blue",
            cursor="hand2",
        )
        repo_link.pack()
        repo_link.bind(
            "<Button-1>",
            lambda e: ContributorsWindow.open_link(
                "https://github.com/MeguminBOT/TextureAtlas-to-GIF-and-Frames"
            ),
        )

        close_frame = ttk.Frame(scrollable_frame)
        close_frame.pack(fill="x", pady=20)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_window_close():
            contributors_window.unbind_all("<MouseWheel>")
            contributors_window.destroy()

        close_button = ttk.Button(close_frame, text="Close", command=_on_window_close)
        close_button.pack()

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        contributors_window.protocol("WM_DELETE_WINDOW", _on_window_close)

        contributors_window.update_idletasks()
        x = (contributors_window.winfo_screenwidth() // 2) - (
            contributors_window.winfo_width() // 2
        )
        y = (contributors_window.winfo_screenheight() // 2) - (
            contributors_window.winfo_height() // 2
        )
        contributors_window.geometry(f"+{x}+{y}")

    @staticmethod
    def _add_section_header(parent, title, description):
        """Adds a section header with title and description."""
        title_label = tk.Label(
            parent, text=title, font=("Arial", 14, "bold"), justify="left"
        )
        title_label.pack(anchor="w", pady=(0, 5))

        desc_label = tk.Label(
            parent,
            text=description,
            font=("Arial", 9, "italic"),
            justify="left",
            wraplength=550,
            fg="gray50",
        )
        desc_label.pack(anchor="w", pady=(0, 10))

    @staticmethod
    def _add_contributor_entry(parent, name, description, links):
        """Adds a single contributor entry within a section."""
        contributor_frame = tk.Frame(parent, relief="solid", bd=1, bg="white")
        contributor_frame.pack(fill="x", pady=5, padx=10)

        inner_frame = tk.Frame(contributor_frame, bg="white")
        inner_frame.pack(fill="x", padx=10, pady=8)

        name_label = tk.Label(
            inner_frame, text=name, font=("Arial", 12, "bold"), bg="white"
        )
        name_label.pack(anchor="w")

        desc_label = tk.Label(
            inner_frame,
            text=description,
            font=("Arial", 10),
            justify="left",
            wraplength=500,
            bg="white",
        )
        desc_label.pack(anchor="w", pady=(3, 8))

        links_frame = tk.Frame(inner_frame, bg="white")
        links_frame.pack(fill="x")

        for link_text, url in links:
            link_label = tk.Label(
                links_frame,
                text=f"🔗 {link_text}",
                font=("Arial", 9),
                fg="blue",
                cursor="hand2",
                bg="white",
            )
            link_label.pack(anchor="w", pady=1)
            link_label.bind(
                "<Button-1>", lambda e, url=url: ContributorsWindow.open_link(url)
            )

    @staticmethod
    def _add_contributor_section(parent, role, name, description, links):
        """Adds a contributor section with role, name, description, and links."""
        contributor_frame = ttk.LabelFrame(parent, text=role, padding="10")
        contributor_frame.pack(fill="x", pady=10)

        name_label = tk.Label(contributor_frame, text=name, font=("Arial", 12, "bold"))
        name_label.pack(anchor="w")

        desc_label = tk.Label(
            contributor_frame,
            text=description,
            font=("Arial", 10),
            justify="left",
            wraplength=500,
        )
        desc_label.pack(anchor="w", pady=(5, 10))

        links_frame = ttk.Frame(contributor_frame)
        links_frame.pack(fill="x")

        for link_text, url in links:
            link_label = tk.Label(
                links_frame,
                text=f"🔗 {link_text}",
                font=("Arial", 10),
                fg="blue",
                cursor="hand2",
            )
            link_label.pack(anchor="w", pady=2)
            link_label.bind(
                "<Button-1>", lambda e, url=url: ContributorsWindow.open_link(url)
            )

    @staticmethod
    def _add_info_section(parent, title, description):
        """Adds an information section with title and description."""
        info_frame = ttk.LabelFrame(parent, text=title, padding="10")
        info_frame.pack(fill="x", pady=10)

        desc_label = tk.Label(
            info_frame,
            text=description,
            font=("Arial", 10),
            justify="left",
            wraplength=500,
        )
        desc_label.pack(anchor="w")

    @staticmethod
    def open_link(url):
        """Opens a URL in the default web browser."""
        webbrowser.open_new(url)
