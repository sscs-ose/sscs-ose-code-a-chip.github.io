"""Integrated Jupyter controller over the existing CPU, SRAM and views."""

import asyncio
from html import escape
from io import BytesIO

import ipywidgets as widgets
from IPython.display import Image, display

from riscv_memory_visualizer.cpu.parser import InstructionParser
from riscv_memory_visualizer.cpu.processor import Processor
from riscv_memory_visualizer.memory.array import SRAMArray
from riscv_memory_visualizer.memory.sram6t import SRAMCell6T
from riscv_memory_visualizer.memory.sram8t import SRAMCell8T
from riscv_memory_visualizer.simulation.controller import MemoryEventEngine
from riscv_memory_visualizer.simulation.processor_memory import ProcessorEventMemory
from riscv_memory_visualizer.simulation.timeline import EventTimeline
from riscv_memory_visualizer.simulation.signals import SimulationTraceRecorder
from riscv_memory_visualizer.visualization.array_view import SRAMArrayView
from riscv_memory_visualizer.visualization.cell_view import SRAMCell6TView
from riscv_memory_visualizer.visualization.cell8t_view import SRAMCell8TView
from riscv_memory_visualizer.visualization.pipeline_view import PipelineView
from riscv_memory_visualizer.visualization.waveform_view import WaveformView


class RiscVMemoryVisualizerApp:
    """A reusable dashboard. Load/reset clear SRAM and history, retaining objects.

    Run requires the running asyncio loop supplied by Jupyter/IPykernel. In
    scripts, call step() or run() inside an async function. close() cancels
    execution and releases widget comms when replacing an application.
    """

    DEMO_PROGRAM = "addi x2, x0, 0\nlw x5, 8(x2)\nadd x6, x5, x2"
    CELL_TYPES = {"6T": SRAMCell6T, "8T": SRAMCell8T}

    def __init__(self) -> None:
        self.parser = InstructionParser()
        self.array = SRAMArray(4, 4)
        self.timeline = EventTimeline()
        self.trace_recorder = SimulationTraceRecorder(self.timeline)
        self.waveform_view = WaveformView()
        self.engine = MemoryEventEngine(self.array, timeline=self.timeline)
        self.processor = Processor(self.engine)
        self.processor.memory = ProcessorEventMemory(self.engine, self.processor.state)
        self.pipeline_view = PipelineView()
        self.array_view = SRAMArrayView()
        self._cell_views = {"6T": SRAMCell6TView(), "8T": SRAMCell8TView()}
        self.cell_view = self._cell_views["6T"]
        self.running = False
        self._task = None
        self._displayed = False
        self._closed = False
        self.changed_registers = set()
        self.status_message = "Ready — enter instructions and Load Program."
        self.instruction_input = widgets.Textarea(
            value=self.DEMO_PROGRAM, description="Program:",
            layout=widgets.Layout(width="100%", height="110px"))
        self.load_button = widgets.Button(description="Load Program", button_style="primary")
        self.reset_button = widgets.Button(description="Reset")
        self.step_button = widgets.Button(description="Step")
        self.run_button = widgets.Button(description="Run", button_style="success")
        self.pause_button = widgets.Button(description="Pause")
        self.demo_button = widgets.Button(description="Load Demo Data")
        self.speed = widgets.Dropdown(description="Speed:",
                                      options=[("Slow", 1.0), ("Normal", .4), ("Fast", .1)], value=.4)
        self.architecture_selector = widgets.Dropdown(
            description="Cell architecture:", options=[("6T SRAM", "6T"), ("8T SRAM (abstract)", "8T")],
            value="6T", style={"description_width": "initial"})
        self.architecture_note = widgets.HTML()
        self.status = widgets.HTML()
        self.register_panel = widgets.HTML()
        self.help_panel = widgets.HTML()
        self.cell_label = widgets.HTML()
        self.timeline_panel = widgets.HTML(layout=widgets.Layout(
            max_height="300px", overflow="auto"))
        self.pipeline_output = widgets.Output()
        self.array_output = widgets.Output()
        self.cell_output = widgets.Output()
        self.waveform_output = widgets.Output()
        controls = widgets.HBox([self.load_button, self.reset_button, self.step_button,
                                 self.run_button, self.pause_button, self.demo_button],
                                layout=widgets.Layout(flex_flow="row wrap"))
        def panel(title, children):
            return widgets.VBox([widgets.HTML(f"<h3>{title}</h3>"), *children],
                                layout=widgets.Layout(width="50%", min_width="350px"))
        self.widget = widgets.VBox([
            widgets.HTML("<h2>RISC-V Memory Microarchitecture Visualizer</h2>"
                         "<p>4 × 4 = 16 logical single-bit cells, at byte addresses 0, 4, …, 60. "
                         "Stores accept 0 or 1 only. This is educational memory, not 32-bit words.</p>"),
            self.instruction_input, controls, self.speed, self.architecture_selector,
            self.architecture_note, self.status,
            widgets.HBox([panel("1 · Processor pipeline", [self.pipeline_output]),
                          panel("2 · SRAM array", [self.array_output])],
                         layout=widgets.Layout(flex_flow="row wrap")),
            widgets.HBox([panel("3 · Selected SRAM cell", [self.cell_label, self.cell_output]),
                          panel("Processor state / registers", [self.register_panel])],
                         layout=widgets.Layout(flex_flow="row wrap")),
            self.help_panel, widgets.HTML("<h3>4 · Event timeline</h3>"), self.timeline_panel,
            widgets.HTML("<h3>5 · Digital timing / waveform</h3><p>Logical states and event timing, "
                         "not an analog SPICE waveform. Top: last 12 CPU cycles. Bottom: ordered events "
                         "in the latest memory cycle, or setup events with no known CPU cycle. "
                         "CELL identifies the observed cell; changing selection can change the displayed signals. "
                         "Unknown signals show ?; unsupported 8T physical signals show N/A.</p>"),
            self.waveform_output])
        for button, method in ((self.load_button, self.load_program), (self.reset_button, self.reset),
                               (self.step_button, self.step), (self.run_button, self.run),
                               (self.pause_button, self.pause), (self.demo_button, self.load_demo_data)):
            button.on_click(lambda _, action=method: action())
        self.architecture_selector.observe(self._architecture_changed, names="value")
        self.refresh()

    def _architecture_changed(self, change) -> None:
        """Pause and reset execution while preserving CPU, adapter and views."""
        if self._closed:
            return
        self.pause()
        self.array = SRAMArray(self.array.rows, self.array.columns,
                               cell_type=self.CELL_TYPES[change["new"]])
        # Same shape/capacity: only the engine's backing array changes.
        self.engine.memory = self.array
        self.cell_view = self._cell_views[change["new"]]
        self.processor.reset()
        self.timeline.clear()
        self._clear_trace()
        self.changed_registers.clear()
        self._message(f"Architecture: {self.array.architecture_name}. Execution, SRAM and timeline reset; program retained.")
        self.refresh()

    def _clear_trace(self) -> None:
        self.trace_recorder.clear(architecture=self.array.architecture_name,
                                  physical_signals=self.array.uses_word_line)

    def _message(self, text):
        self.status_message = text
        self.status.value = f"<p role='status'><b>{escape(text)}</b></p>"
        self._controls()

    def _controls(self):
        self.step_button.disabled = self.running or self.processor.finished or self._closed
        self.run_button.disabled = self.step_button.disabled
        self.pause_button.disabled = not self.running
        self.demo_button.disabled = self.running or self._closed

    def load_program(self, text: str | None = None) -> bool:
        """Parse all lines before committing; errors retain the previous simulation."""
        self.pause()
        source = self.instruction_input.value if text is None else text
        program = []
        for number, line in enumerate(source.splitlines(), 1):
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            try:
                program.append(self.parser.parse(line))
            except ValueError as error:
                self._message(f"Error: invalid instruction on line {number}: {error}")
                return False
        if not program:
            self._message("Error: program contains no instructions.")
            return False
        self.processor.load_program(program)
        self.array.reset()
        self.timeline.clear()
        self._clear_trace()
        self.changed_registers.clear()
        self.instruction_input.value = source
        self._message(f"Program loaded: {len(program)} instructions. SRAM cleared.")
        self.refresh()
        return True

    def reset(self) -> None:
        """Retain the loaded program; clear CPU, memory, selection and events."""
        self.pause()
        self.processor.reset()
        self.array.reset()
        self.timeline.clear()
        self._clear_trace()
        self.changed_registers.clear()
        self._message("Ready — reset complete. SRAM and timeline cleared.")
        self.refresh()

    def load_demo_data(self) -> None:
        """Explicitly write address 8 = 1 through the engine, recording setup events."""
        self.pause()
        self.engine.write(8, 1)
        self.trace_recorder.record_events()
        self._message("Demo data loaded: address 0x08 = 1. Setup events have no CPU cycle.")
        self.refresh()

    def step(self) -> bool:
        """Advance exactly one processor cycle, or report completion/error."""
        if self._closed:
            return False
        if self.processor.finished:
            self._message("Program complete" if self.processor.instruction_memory else "Load a program first.")
            return False
        before = self.processor.registers.get_all()
        if not self.trace_recorder.cycle_traces["CYCLE"].snapshot():
            self.trace_recorder.record_cycle(self.processor.state.cpu_cycle, self.array, processor=self.processor)
        try:
            self.processor.step()
        except Exception as error:
            self.pause()
            self.trace_recorder.record_events()
            self._message(f"Error: {error}")
            self.refresh()
            return False
        self.changed_registers = {i for i, value in enumerate(before)
                                  if value != self.processor.registers.read(i)}
        state = self.processor.state
        self.trace_recorder.record_cycle(state.cpu_cycle, self.array, processor=self.processor)
        message = "Program complete" if self.processor.finished else f"Cycle {state.cpu_cycle}"
        if state.operation:
            message += (f" · Memory {state.operation.lower()}: address {state.effective_address:#04x}"
                        f" · Selected SRAM cell: ({self.array.selected_row}, {self.array.selected_column})")
        self._message(message)
        self.refresh()
        return True

    def run(self) -> bool:
        """Schedule cooperative execution; duplicate Run clicks create no extra loop."""
        if self.running or self._closed:
            return False
        if self.processor.finished:
            self.step()
            return False
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            self._message("Error: Run requires a running Jupyter event loop; use Step in scripts.")
            return False
        self.running = True
        self._message("Running")
        self._task = loop.create_task(self._run_loop())
        return True

    async def _run_loop(self):
        try:
            while self.running and not self.processor.finished:
                if not self.step():
                    break
                await asyncio.sleep(self.speed.value)
        except asyncio.CancelledError:
            pass
        except Exception as error:
            self._message(f"Error: {error}")
        finally:
            # A cancelled old task must not stop a newly resumed task.
            if self._task is asyncio.current_task():
                self._task = None
                self.running = False
                self._controls()

    def pause(self) -> None:
        """Cancel automatic stepping without changing simulation state."""
        was_running = self.running
        self.running = False
        if self._task is not None:
            self._task.cancel()
            self._task = None
        if was_running:
            self._message("Paused")
        self._controls()

    def refresh(self) -> None:
        """Read models and update existing artists/widgets, without executing anything."""
        self.pipeline_view.update(self.processor)
        self.array_view.update(self.array)
        self.waveform_view.update(self.trace_recorder.snapshot())
        row, column = self.array.selected_row, self.array.selected_column
        selected = row is not None and column is not None
        architecture = self.array.architecture_name
        self.architecture_note.value = (
            f"<p><b>Architecture: {escape(architecture)}</b>. Switching clears execution, SRAM and history.</p>"
            + ("<p>8T is an abstract placeholder. Source material does not specify transistor connectivity. "
               "Q/Q_bar and selection are logical assumptions; no physical read/write paths are claimed.</p>"
               if not self.array.uses_word_line else ""))
        self.cell_label.value = (f"{architecture} SRAM CELL · Selected SRAM cell: ({row}, {column})" if selected
                                 else "No SRAM cell selected")
        if selected:
            self.cell_view.update(self.array.get_cell(row, column))
        state = self.processor.state
        rows = []
        for start in range(0, 32, 4):
            cells = []
            for i in range(start, start + 4):
                style = "background:#fff0b3;font-weight:bold;" if i in self.changed_registers else ""
                changed = " (changed)" if i in self.changed_registers else ""
                cells.append(f'<td style="padding:6px;{style}">x{i}: {self.processor.registers.read(i)}{changed}</td>')
            rows.append("<tr>" + "".join(cells) + "</tr>")
        self.register_panel.value = (f"<p>Cycle: {state.cpu_cycle} · PC: {state.pc:#04x}</p>"
                                     f"<p>Last retired: {escape(state.instruction_text or '—')}</p>"
                                     "<p>Registers marked (changed) updated during the last step.</p><table>" + "".join(rows) + "</table>")
        events = self.timeline.events()
        event_rows = []
        for order, event in enumerate(events, 1):
            values = (order, event.event_type.name, event.cycle,
                      f"{event.address:#04x}" if event.address is not None else None,
                      event.row, event.column, event.value, event.description)
            event_rows.append("<tr>" + "".join(f"<td style='padding:4px'>{escape(str(v)) if v is not None else '—'}</td>"
                                              for v in values) + "</tr>")
        self.timeline_panel.value = ("<table><thead><tr>" + "".join(f"<th>{h}</th>" for h in
            ("Order", "Event", "Cycle", "Address", "Row", "Column", "Value", "Description"))
            + "</tr></thead><tbody>" + "".join(event_rows) + "</tbody></table>"
            if events else "No memory events yet.")
        explanation = []
        for name, text in self.processor.pipeline.snapshot().items():
            if text:
                explanation.append({"IF": "Instruction Fetch: the fetched instruction occupies IF.",
                                    "ID/EX": "ID/EX: operands and ALU/address calculation execute on the next step.",
                                    "MEM/WB": "MEM/WB: memory access and writeback retire on the next step."}[name])
        if state.operation:
            explanation.append(f"Memory {state.operation.lower()}: the effective address selected a row and column in SRAM.")
        if selected:
            explanation.append(f"Selected {architecture} SRAM cell: Q and Q_bar store complementary logical values. Selection remains active after access.")
        self.help_panel.value = "<p>" + escape(" ".join(explanation) or "Load a program, then Step or Run. Load Demo Data explicitly writes address 8 = 1.") + "</p>"
        self._message(self.status_message)
        if self._displayed:
            self._render_output(self.pipeline_output, self.pipeline_view.figure)
            self._render_output(self.array_output, self.array_view.figure)
            self._render_output(self.cell_output, self.cell_view.figure if selected else None)
            self._render_output(self.waveform_output, self.waveform_view.figure, width=1100)

    @staticmethod
    def _render_output(output, figure, *, width=600):
        # Explicit PNGs work with inline and headless backends. Replace, never append history.
        if figure is None:
            output.outputs = ()
            return
        buffer = BytesIO()
        figure.savefig(buffer, format="png", dpi=85)
        output.outputs = ()
        output.append_display_data(Image(data=buffer.getvalue(), width=width))

    def display(self) -> None:
        """Display one coherent dashboard in the current notebook output."""
        if self._closed:
            raise RuntimeError("Application is closed; construct a new instance.")
        self._displayed = True
        self.refresh()
        display(self.widget)

    def close(self) -> None:
        """Stop callbacks and close owned widgets, including their layouts/styles."""
        if self._closed:
            return
        self.pause()
        self._closed = True
        self._displayed = False
        self.architecture_selector.unobserve(self._architecture_changed, names="value")
        seen = set()
        def close_widget(widget):
            if id(widget) in seen:
                return
            seen.add(id(widget))
            for child in getattr(widget, "children", ()):
                close_widget(child)
            for name in ("layout", "style"):
                child = getattr(widget, name, None)
                if isinstance(child, widgets.Widget):
                    close_widget(child)
            widget.close()
        close_widget(self.widget)
