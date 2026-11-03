"""Compact, manually navigated Jupyter SRAM lesson."""

from html import escape

import ipywidgets as widgets
from IPython.display import display

from riscv_memory_visualizer.simulation.teaching import SRAMTeachingController
from riscv_memory_visualizer.visualization.schematic_svg import render_scene


class SRAMTeachingApp:
    def __init__(self):
        self.controller = SRAMTeachingController()
        self.operation_selector = widgets.ToggleButtons(
            options=[("Read", "READ"), ("Write", "WRITE")], value="READ",
            description="Access:", style={"description_width": "initial"})
        self.previous_button = widgets.Button(description="◀ Previous")
        self.next_button = widgets.Button(description="Next ▶", button_style="primary")
        self.restart_button = widgets.Button(description="Restart")
        self.step_counter = widgets.HTML()
        self.instruction_view = widgets.HTML()
        self.scene_view = widgets.HTML(layout=widgets.Layout(width="68%", flex="1 1 68%", min_height="0"))
        self.caption_view = widgets.HTML()
        self.explanation_view = widgets.HTML()
        self.explanation_panel = widgets.VBox(
            [self.caption_view, self.explanation_view],
            layout=widgets.Layout(width="30%", flex="1 1 30%", padding="10px 14px",
                                  overflow="hidden", border="1px solid #dce5ee"))
        self.content = widgets.HBox(
            [self.scene_view, self.explanation_panel],
            layout=widgets.Layout(width="100%", flex="1 1 auto", min_height="0",
                                  align_items="stretch", justify_content="space-between"))
        self.details_view = widgets.HTML()
        self.technical_details = widgets.Accordion(children=[self.details_view], selected_index=None)
        self.technical_details.set_title(0, "Technical Details")
        self.toolbar = widgets.HBox(
            [self.operation_selector, self.step_counter],
            layout=widgets.Layout(width="100%", align_items="center", justify_content="space-between",
                                  flex_flow="row wrap", padding="4px 10px"))
        self.toolbar.add_class("sram-toolbar")
        self.controls = widgets.HBox([self.previous_button, self.next_button, self.restart_button],
                                     layout=widgets.Layout(justify_content="center", padding="4px"))
        self.widget = widgets.VBox([
            widgets.HTML('<style>.sram-toolbar{background:#f8fafc}.sram-scene svg{max-height:100%}'
                         '</style><div style="font-family:system-ui"><h2 style="margin:2px;color:#253268;font-size:20px">INSIDE SRAM</h2></div>'),
            self.toolbar, self.instruction_view, self.content, self.controls, self.technical_details,
        ], layout=widgets.Layout(width="min(100%, 1100px)", height="min(84vh, 720px)",
                                 min_height="420px", margin="auto", overflow="hidden"))
        self.previous_button.on_click(lambda _: self.previous())
        self.next_button.on_click(lambda _: self.next())
        self.restart_button.on_click(lambda _: self.restart())
        self.operation_selector.observe(self._change_operation, names="value")
        self.refresh()

    def _change_operation(self, change):
        self.controller.select_operation(change["new"])
        self.refresh()

    def next(self):
        self.controller.next()
        self.refresh()

    def previous(self):
        self.controller.previous()
        self.refresh()

    def restart(self):
        self.controller.restart()
        self.refresh()

    def refresh(self):
        step = self.controller.current_step
        svg = render_scene(step)
        self.scene_view.value = (
            '<div class="sram-scene" style="width:100%;height:100%;min-height:0;overflow:hidden;animation:sram-enter .3s ease">'
            '<style>@keyframes sram-enter{from{opacity:.25;transform:scale(.985)}to{opacity:1;transform:scale(1)}}'
            '@media(prefers-reduced-motion:reduce){*{animation:none!important}}</style>'
            + svg + '</div>')
        self.step_counter.value = (
            f'<strong style="font:600 14px system-ui;color:#253268">'
            f'Step {self.controller.index+1} of {self.controller.total_steps}</strong>')
        self.instruction_view.value = (
            '<div style="font:13px system-ui;color:#52627c;padding:0 8px 4px">'
            f'{escape(step.operation.title())} · <code>{escape(step.instruction)}</code>'
            f' · Address {step.address:#04x}</div>')
        self.caption_view.value = (
            '<div style="font:700 17px system-ui;color:#253268;margin:0 0 8px">'
            f'{escape(step.title)}</div>')
        self.explanation_view.value = (
            '<div style="font:14px/1.45 system-ui;color:#243249">'
            '<strong style="font-size:12px;letter-spacing:.06em;color:#087e89">WHAT IS HAPPENING?</strong>'
            f'<p style="margin:8px 0 12px">{escape(step.explanation)}</p>'
            f'<p style="margin:0;padding:8px;background:#eaf5f6;border-left:3px solid #0f9aa7">'
            f'<strong>Key idea:</strong> {escape(step.key_idea)}</p></div>')
        self.details_view.value = (
            f'<p>Instruction: {escape(step.instruction)} · {step.operation} · Address: {step.address:#04x}'
            f' · Row {step.row}, column {step.column} · Q={step.q}, Q_bar={step.q_bar}</p>'
            '<p>Logical simulation timing, not analog SPICE timing. '
            'The source dashboard remains available as Advanced View.</p>')
        self.previous_button.disabled = self.controller.index == 0
        self.next_button.disabled = self.controller.index == self.controller.total_steps - 1

    def display(self):
        display(self.widget)

    def close(self):
        self.operation_selector.unobserve(self._change_operation, names="value")
        for item in (self.widget, self.operation_selector, self.previous_button,
                     self.next_button, self.restart_button, self.scene_view,
                     self.caption_view, self.details_view, self.technical_details,
                     self.step_counter, self.toolbar, self.instruction_view,
                     self.explanation_view, self.explanation_panel, self.content,
                     self.controls):
            item.close()
