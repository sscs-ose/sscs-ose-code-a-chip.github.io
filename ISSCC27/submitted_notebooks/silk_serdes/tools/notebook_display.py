"""Notebook display formatting only; simulation and measurements stay in Silk."""
from html import escape
from pathlib import Path
from IPython.display import HTML, Markdown, display
from matplotlib.ticker import FuncFormatter


def table(rows):
    """Display a small list of result dictionaries as a Markdown table."""
    if not rows:
        return
    keys = list(rows[0])
    display(Markdown("| " + " | ".join(keys) + " |\n|" + "|".join(["---"]*len(keys)) + "|\n" +
                     "\n".join("| " + " | ".join(str(row.get(k,"")) for k in keys) + " |" for row in rows)))


def show_viewer(path):
    """Embed an already-generated Silk viewer without changing its contents."""
    path = Path(path)
    iframe = '<iframe title="silk waveform explorer" style="width:100%;height:640px;border:1px solid #ccc" srcdoc="' + escape(path.read_text(), quote=True) + '"></iframe>'
    display(HTML(iframe))
    (path.parent / "viewer_embed.html").write_text('<!doctype html><html><body>'+iframe+'</body></html>')


def draw_eye(ax, eye, ui, title):
    """Format traces from a Silk eye result; no measurements are calculated here."""
    # Silk Signal.plot draws each trace; the remaining code labels the axes.
    for trace in eye.traces:
        trace.plot(ax=ax, color="#285f9e", alpha=.12, lw=.6)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda seconds, _: f"{seconds/ui:g}"))
    ax.axvline(.5*ui, color="#b55c28", ls="--", lw=.8)
    ax.axhline(0, color="gray", lw=.6)
    ax.set(xlim=(0, ui), xlabel="Phase (UI)", ylabel="RXP − RXN (V)",
           title=f"{title}: {eye.height*1e3:.1f} mV, {eye.width/ui:.3f} UI")

def show_file(path):
    """Offer a Colab download button or a local Jupyter file link."""
    import sys
    path = Path(path)
    if "google.colab" in sys.modules:
        from google.colab import files
        from ipywidgets import Button
        button = Button(description=f"Download {path.name}", layout={"width": "auto"})
        button.on_click(lambda _: files.download(str(path)))
        display(button)
    else:
        from IPython.display import FileLink
        display(FileLink(str(path)))
