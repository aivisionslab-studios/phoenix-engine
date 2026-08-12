from typing import List
from .base_builder import ICommandBuilder
from phoenix_kernel.runtime.contracts.model_contracts import ModelDescriptor, GenerationProfile

class SD15Builder(ICommandBuilder):
    def build(self, exe_path: str, desc: ModelDescriptor, profile: GenerationProfile, prompt: str, output_file: str) -> List[str]:
        # Comandos auditados para SD 1.5
        return [
            exe_path,
            "-m", str(desc.model_path),
            "-p", prompt,
            "-o", output_file,
            "-H", str(profile.height),
            "-W", str(profile.width),
            "--steps", str(profile.steps) # README: -s é seed, --steps é o correto
        ]