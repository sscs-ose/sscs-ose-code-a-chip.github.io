import json
import os
import textwrap
import re
import base64
try:
    from .playbook import Playbook
except ImportError:
    from playbook import Playbook

COMMON_CORE_RULES = {
    "respect_testbench": {
        "description": (
            "All tasks must respect the existing testbench and checker. "
            "New rules must NOT suggest skipping simulations, ignoring the "
            "testbench, bypassing checkers, or hardcoding success messages."
        ),
        "negative_patterns": [
            r"ignore the testbench",
            r"bypass the testbench",
            r"skip (all )?simulation",
            r"do not run (the )?simulator",
            r"no need to run (any )?simulation",
            r"just assume the circuit works",
            r"assume it functions correctly without simulation",
            r"disable all checks",
            r"comment out the check code",
            r"remove the assertion",
            r"force the test to pass",
            r"hardcode the check result",
            r"just print ['\"]?The .* functions correctly['\"]?",
            r"always return success",
        ],
    },
    "respect_library_cells": {
        "description": (
            "All tasks must respect provided library cells and subcircuits "
            "(e.g., those indicated in lib_info.tsv or separate Python modules "
            "like opamp.py). New rules must NOT suggest avoiding or removing "
            "these provided building blocks or replacing them with oversimplified "
            "ideal sources when the task relies on them."
        ),
        "negative_patterns": [
            r"avoid using .*subcircuit",
            r"avoid using external subcircuit",
            r"do not use .* from lib_info",
            r"do not use opamp\.py",
            r"replace the provided .* with an ideal source",
        ],
    },
    "no_fake_physics": {
        "description": (
            "New rules must not recommend physically nonsensical connections, "
            "such as shorting Vdd directly to ground as a generic fix."
        ),
        "negative_patterns": [
            r"short.*Vdd.*to.*GND",
            r"connect Vdd directly to ground",
        ],
    },
}

CORE_RULES = {
    "Integrator": {
        "must_use_opamp_py": {
            "description": (
                "For Task 24 (Op-amp Integrator), the design MUST use the "
                "transistor-level Opamp defined in opamp.py, imported as:\n"
                "  from opamp import Opamp\n"
                "  circuit.subcircuit(Opamp())\n"
                "  circuit.X('op', 'Opamp', 'Vref', 'Vinn', 'Vout')\n"
                "  NOTE: The Opamp subcircuit ONLY exposes three external pins "
                "(non-inverting input, inverting input, output). Do NOT pass Vdd "
                "or GND as extra nodes to circuit.X('...', 'Opamp', ...)."
            ),
            "positive_keywords": ["opamp.py", "Opamp", "subcircuit", "from opamp import"],
            "negative_patterns": [
                r"avoid using external subcircuit",
                r"do not use opamp\.py",
                r"avoid importing external files.*opamp",
                r"subcircuit definition must be self-contained within the main PySpice script",
            ],
        },
        "must_keep_required_nodes": {
            "description": (
                "For the integrator testbench, the input node MUST be named 'Vin' "
                "and the output node MUST be named 'Vout'. New rules must not "
                "suggest renaming these nodes arbitrarily."
            ),
            "positive_keywords": ["Vin", "Vout"],
            "negative_patterns": [
                r"rename\s+Vin",
                r"rename\s+Vout",
                r"use any node names you like",
            ],
        },
    },
    "CurrentMirror": {
        "no_ideal_source": {
            "description": (
                "Current mirror tasks must be implemented using MOS transistors, "
                "not by replacing them with an ideal current source element."
            ),
            "negative_patterns": [
                r"use an ideal current source instead of",
                r"replace the mirror with an ideal current source",
            ]
        }
    },
    "Oscillator": {
        "keep_feedback_and_startup": {
            "description": (
                "Oscillator tasks rely on a feedback loop and a startup mechanism "
                "(such as initial conditions or bias). New rules must not suggest "
                "removing the feedback path or removing all initial conditions as "
                "a generic fix."
            ),
            "negative_patterns": [
                r"remove the feedback network",
                r"delete the feedback resistor",
                r"disconnect the feedback path",
                r"remove all initial conditions",
            ],
        },
        "respect_osc_opamp_model": {
            "description": (
                "When a task explicitly specifies an op-amp model (e.g., a VCVS "
                "with gain 1e6 and Rout=100 Ohm for RC phase-shift or Wien Bridge "
                "oscillators), new rules must not suggest replacing it with a "
                "different op-amp model (such as a transistor-level Opamp from "
                "opamp.py) or removing the output resistor."
            ),
            "negative_patterns": [
                r"use opamp\.py instead of the vcvs",
                r"replace the vcvs opamp with the Opamp subcircuit",
                r"remove the 100 ohm output resistor",
            ],
        },
    },
    "Comparator": {
        "use_opamp_py": {
            "description": (
                "Comparator tasks must use the provided transistor-level Opamp "
                "subcircuit from opamp.py instead of replacing it with a purely "
                "behavioral VCVS-only model or a hard-coded digital output.\n"
                "  Example (Task 9):\n"
                "  circuit.subcircuit(Opamp())\n"
                "  circuit.X('cmp', 'Opamp', 'Vin', 'Vref', 'Vout')\n"
                "  # Vin -> non-inverting input, Vref -> inverting input"
            ),
            "negative_patterns": [
                r"avoid using opamp\.py",
                r"do not use opamp",
                r"replace the opamp with a simple vcvs",
                r"use an ideal comparator model instead of the provided opamp",
            ],
        },
        "correct_polarity": {
            "description": (
                "For Task 9, the comparator must drive Vout HIGH when Vin > Vref "
                "and LOW when Vin < Vref. Therefore, Vin must be connected to the "
                "NON-INVERTING input and Vref to the INVERTING input of the Opamp "
                "subcircuit:\n"
                "  circuit.X('cmp', 'Opamp', 'Vin', 'Vref', 'Vout')"
            ),
            "negative_patterns": [
                r"output high when vin < vref",
                r"output low when vin > vref",
                r"swap vin and vref .* so that the output is inverted",
            ],
        },
    },
}

GLOBAL_FORBIDDEN_PATTERNS = [
    r"ignore the testbench",
    r"bypass the testbench",
    r"skip (all )?simulation",
    r"do not run (the )?simulator",
    r"no need to run (any )?simulation",
    r"just assume the circuit works",
    r"assume it functions correctly without simulation",
    r"disable all checks",
    r"comment out the check code",
    r"remove the assertion",
    r"force the test to pass",
    r"hardcode the check result",
    r"just print ['\"]?The .* functions correctly['\"]?",
    r"just print ['\"]?circuit works['\"]?",
    r"always return success",
    r"avoid using .*subcircuit",
    r"avoid using external subcircuit",
    r"do not use .* from lib_info",
    r"replace the provided .* with an ideal source",
    r"do not use opamp\.py",
    r"short.*Vdd.*to.*GND",
    r"connect Vdd directly to ground",
]

class ExperienceCurator:
    def __init__(self, llm_model=None, model_name="gemini-2.5-flash",
                 task_id="general", storage_file="playbook.json"):
        self.llm = llm_model
        self.model_name = model_name
        self.storage_file = storage_file
        self.local_playbook = Playbook(task_id=task_id)
        self.knowledge_base = self._load_knowledge()

        if not os.path.exists(self.storage_file):
            self._save_knowledge()
        self.task_hard_rules = ""

    def reflect_and_learn(self, task_type, code, error_log, iteration, image_path=None):
        self.local_playbook.add_log(code=code, error_msg=error_log, iteration=iteration)

        if not self.llm:
            return

        has_image = False
        base64_image = None
        if image_path and os.path.exists(image_path):
            try:
                print(f"[Auto-Curator] Encoding waveform image: {image_path}")
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
                has_image = True
            except Exception as e:
                print(f"[Auto-Curator] Image encoding failed: {e}")

        clean_log = str(error_log)[-2000:]
        vision_instruction = ""
        if has_image:
            vision_instruction = textwrap.dedent("""
            **VISUAL EVIDENCE (Waveform Image Provided):**
            - Does the waveform look like the expected response (e.g., ramp/triangle/sine)?
            - Is it saturated at supply rails (flat line at top/bottom)?
            - Is there oscillation when it should be DC / ramp, or vice versa?
            - Is the amplitude / slope clearly wrong?
            Use this visual information to help diagnose the failure.
            """)

        prompt = textwrap.dedent(f"""
            You are an expert in Analog Circuit Design and SKY130 SPICE netlist debugging.
            A generated SKY130 SPICE subcircuit netlist has failed or produced incorrect behavior.

            **FAILED NETLIST (TRUNCATED):**
            ```spice
            {code}
            ```

            **ERROR LOG / CHECK OUTPUT (TRUNCATED):**
            ```text
            {clean_log}
            ```

            {vision_instruction}

            **YOUR TASK:**
            1. Analyze the code, the error log, and the waveform image (if provided).
            2. Identify the most likely root cause of failure at a general, reusable level.
            3. Propose ONE concise, general RULE that would help avoid this class of failures.

            **STRICT RESPONSE FORMAT (JSON ONLY):**
            {{
              "rule": "YOUR_GENERAL_RULE_TEXT_HERE"
            }}
        """)

        try:
            print(f"[Auto-Curator] Requesting analysis ({'Multimodal' if has_image else 'Text only'})...")

            if has_image:
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            }
                        ]
                    }
                ]
            else:
                messages = [{"role": "user", "content": prompt}]

            response = self.llm.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=1.0
            )
            
            response_text = response.choices[0].message.content
            rule_data = self._extract_json(response_text)
            new_rule = rule_data.get("rule")

            if new_rule:
                print(f"[Auto-Curator] Candidate new rule: {new_rule}")
                category = str(task_type).strip() or "General"
                self._add_global_rule(category, new_rule)
            else:
                print("[Auto-Curator] AI failed to identify a rule.")

        except Exception as e:
            print(f"[Auto-Curator] Curator reflection failed: {e}")

    def retrieve_guidance(self, task_type):
        guidance = "\n\n--- AUTOMATED EXPERIENCE GUIDELINES ---\n"
        has_info = False

        if self.task_hard_rules:
            guidance = self.task_hard_rules + "\n" + guidance

        general = self.knowledge_base.get("General", [])
        if general:
            guidance += "\n[General PySpice / Syntax Rules]\n"
            for r in general:
                if r:
                    guidance += f"- {r}\n"
            has_info = True

        rules_section = self.knowledge_base.get("Rules", {})
        specific_rules = rules_section.get(task_type, [])

        if not specific_rules:
            for cat, rules in rules_section.items():
                if cat and cat in str(task_type):
                    specific_rules = rules
                    break

        if specific_rules:
            guidance += f"\n[{task_type} Expert Rules]\n"
            for rule in specific_rules:
                if isinstance(rule, dict):
                    desc = rule.get("description") or rule.get("rule")
                    if desc:
                        guidance += f"- {desc}\n"
                else:
                    guidance += f"- {rule}\n"
            has_info = True

        reflexion = self.local_playbook.get_reflexion_prompt()
        if reflexion:
            guidance += "\n[Recent Failure Reflexion]\n"
            guidance += reflexion
            has_info = True

        return guidance if has_info else ""

    def _extract_json(self, text):
        try:
            text = text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            return json.loads(text)
        except Exception:
            return {"rule": None}

    def _load_knowledge(self):
        if os.path.exists(self.storage_file):
            try:
                with open(self.storage_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"General": [], "Rules": {}}

    def _save_knowledge(self):
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.knowledge_base, f, indent=4)
        except Exception as e:
            print(f"[Curator] Save failed: {e}")

    def _add_global_rule(self, category, rule):
        rule = (rule or "").strip()
        if not rule or self._basic_filter_reject(rule):
            return
        
        if self._conflicts_with_core_rules(category, rule):
            return

        if category == "General":
            if "General" not in self.knowledge_base:
                self.knowledge_base["General"] = []
            target_list = self.knowledge_base["General"]
        else:
            if "Rules" not in self.knowledge_base:
                self.knowledge_base["Rules"] = {}
            if category not in self.knowledge_base["Rules"]:
                self.knowledge_base["Rules"][category] = []
            target_list = self.knowledge_base["Rules"][category]

        if rule in target_list:
            return

        target_list.append(rule)
        self._save_knowledge()
        print(f"[Curator] New rule added ({category}): {rule}")

    def _basic_filter_reject(self, rule: str) -> bool:
        if len(rule) < 15:
            return True
        for pat in GLOBAL_FORBIDDEN_PATTERNS:
            if re.search(pat, rule, flags=re.IGNORECASE):
                return True
        return False

    def _conflicts_with_core_rules(self, category: str, rule: str) -> bool:
        rule_lower = rule.lower()
        for key, meta in COMMON_CORE_RULES.items():
            for pat in meta.get("negative_patterns", []):
                if re.search(pat, rule_lower, flags=re.IGNORECASE):
                    return True
        if category not in CORE_RULES:
            return False
        cat_rules = CORE_RULES[category]
        for key, meta in cat_rules.items():
            for pat in meta.get("negative_patterns", []):
                if re.search(pat, rule_lower, flags=re.IGNORECASE):
                    return True
        return False