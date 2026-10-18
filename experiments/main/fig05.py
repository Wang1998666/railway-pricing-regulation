from pathlib import Path
import subprocess
subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','case_fig05.tex'],cwd=Path(__file__).resolve().parent.parent/'fig',check=True)
