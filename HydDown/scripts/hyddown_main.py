# HydDown hydrogen/other gas depressurisation
# Copyright (c) 2021 Anders Andreasen
# Published under an MIT license

import yaml
import sys

try:
    from hyddown import HydDown
except:
    import sys
    import os
    hyddown_path = os.path.join(os.path.abspath(os.path.dirname(__file__)),"..","src")
    sys.path.append(os.path.abspath(hyddown_path))

    from hyddown import HydDown


if __name__ == "__main__":
    import os
    if len(sys.argv) > 1:
        input_filename = sys.argv[1]
    else:
        input_filename = "input.yml"

    if not os.path.exists(input_filename):
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            input_filename = filedialog.askopenfilename(
                title="Select HydDown Input File (YAML)",
                filetypes=[("YAML Files", "*.yml *.yaml"), ("All Files", "*.*")]
            )
            if not input_filename:
                sys.exit()
        except:
            sys.exit()

    with open(input_filename) as infile:
        input = yaml.load(infile, Loader=yaml.FullLoader)

    hdown=HydDown(input)
    
    hdown.run(disable_pbar=False)
    hdown.plot()