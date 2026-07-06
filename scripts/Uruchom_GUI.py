from _bootstrap_paths import ROOT  # noqa: F401
import tkinter as tk
from GUI import SymulatorWindyGUI

def main() -> None:
    root = tk.Tk()
    SymulatorWindyGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
