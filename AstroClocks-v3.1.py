import tkinter as tk
from tkinter.font import Font

from astroclocks.utils import resource_path


def apply_loading_icon(window, default=False):
    icon_path = resource_path("AppIcon.ico")
    try:
        if default:
            window.iconbitmap(default=icon_path)
        window.iconbitmap(icon_path)
    except (tk.TclError, TypeError):
        pass


def create_loading_window():
    root = tk.Tk()
    root.withdraw()
    apply_loading_icon(root, default=True)

    window = tk.Toplevel(root)
    window.title("AstroClocks")
    apply_loading_icon(window)
    window.configure(bg="#101419")
    window.resizable(False, False)

    width = 440
    height = 170
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max(0, (screen_width - width) // 2)
    y = max(0, (screen_height - height) // 2)
    window.geometry(f"{width}x{height}+{x}+{y}")

    tk.Label(
        window,
        text="AstroClocks v3.1",
        bg="#101419",
        fg="#f6c451",
        font=Font(family="Segoe UI", size=22, weight="bold"),
    ).pack(pady=(26, 8))

    status_var = tk.StringVar(value="Chargement des modules astronomiques...")
    tk.Label(
        window,
        textvariable=status_var,
        bg="#101419",
        fg="#edf3f8",
        font=Font(family="Segoe UI", size=11),
    ).pack(pady=(4, 18))

    tk.Label(
        window,
        text="Veuillez patienter",
        bg="#101419",
        fg="#93a6b7",
        font=Font(family="Segoe UI", size=9),
    ).pack()

    window.update()
    return root, window, status_var


if __name__ == "__main__":
    loading_root, loading_window, loading_status_var = create_loading_window()
    from astroclocks.app import main

    main(
        root=loading_root,
        loading_window=loading_window,
        loading_status_var=loading_status_var,
    )
