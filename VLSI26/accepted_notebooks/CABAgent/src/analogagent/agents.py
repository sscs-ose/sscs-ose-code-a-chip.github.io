import time
import os
from typing import List, Dict, Optional


class CodeGenerator:
    """
    [Code Generator]
    Maintains conversation history and calls the LLM to generate circuit code.
    """
    def __init__(self, llm_client, model_name):
        self.llm = llm_client
        self.model_name = model_name

    def generate_solution(self,
                          base_template: str,
                          task_description: str = "",
                          curator_guidance: str = "",
                          history_messages: Optional[List[Dict]] = None) -> str:

        messages = history_messages if history_messages is not None else []

        if not messages:
            messages.append({"role": "system", "content": base_template})
            user_content = f"Task Description:\n{task_description}"
            if task_description:
                messages.append({"role": "user", "content": user_content})

        if curator_guidance:
            messages.append({"role": "user", "content": f"Feedback for correction:\n{curator_guidance}"})

        is_fixing = len(messages) > 2
        print(f"[Generator] Generating code... Mode: {'FIX' if is_fixing else 'CREATE'}")

        try:
            resp = self.llm.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=1.0
            )
            content = resp.choices[0].message.content.strip()
        except Exception as e:
            print(f"[Generator] LLM Error: {e}")
            return ""

        return content

class DesignOptimizer:
    """
    [Design Optimizer]
    Reflects on simulation logs to provide topology fixes or parameter
    optimization suggestions.
    """
    def __init__(self, llm_client, model_name):
        self.llm = llm_client
        self.model_name = model_name

    def simulator(self, code_path):
        try:
            from .main_run import run_code
        except ImportError:
            from main_run import run_code
        return run_code(code_path)

    def verify_and_reflect(self, task_id: int, code_path: str, task_type: str,
                           target_specs: Dict = None, image_path: str = None) -> Dict:
        print(f"[Optimizer] Verifying design for Task {task_id}...")

        # Physical Simulation
        exec_err, sim_err, err_info, _ = self.simulator(code_path)
        is_passed = (exec_err == 0 and sim_err == 0)

        result = {
            "is_passed": is_passed,
            "error_info": err_info if not is_passed else "",
            "suggestions": ""
        }

        # Text-based feedback
        if is_passed and target_specs and not result["suggestions"]:
            analysis_prompt = (
                f"As an analog expert, analyze this simulation log and suggest improvements.\n"
                f"Task: {task_type}\n"
                f"Target Specs: {target_specs}\n"
                f"Execution Log: {err_info}\n"
                f"Provide sizing or topology adjustments."
            )
            try:
                reflection = self.llm.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": analysis_prompt}],
                    temperature=0.1
                )
                result["suggestions"] = reflection.choices[0].message.content
            except Exception as e:
                print(f"[Optimizer] Textual Reflection Error: {e}")
                result["suggestions"] = "Optimize device sizing for better performance margin."

        return result
