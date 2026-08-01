import subprocess
import urllib.request
import logging

logger = logging.getLogger(__name__)

class WingetConnector:
    def install(self, name: str, info: dict) -> str:
        winget_id = info.get("winget_id")
        if not winget_id: return "ERRO: Sem winget_id"
        cmd = ["winget", "install", winget_id, "--accept-package-agreements", "--accept-source-agreements", "-h"]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if proc.returncode == 0: return "OK"
            return f"Skip (Code {proc.returncode})"
        except Exception as e: return f"ERRO: {str(e)}"

class DockerConnector:
    def _is_docker_running(self) -> bool:
        try:
            subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
            return True
        except: return False

    def install(self, name: str, info: dict) -> str:
        if not self._is_docker_running(): return "ERRO: Docker offline"
        
        image = info.get("image")
        cmd = ["docker", "run", "-d", f"--name={name}", f"--restart={info.get('restart', 'unless-stopped')}"]
        for p in info.get("ports", []): cmd.extend(["-p", p])
        for v in info.get("volumes", []): cmd.extend(["-v", v])
        for k, v in info.get("environment", {}).items(): cmd.extend(["-e", f"{k}={v}"])
        cmd.append(image)
        
        try:
            subprocess.run(["docker", "start", name], capture_output=True, text=True)
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return "OK"
        except Exception as e: return f"ERRO: {str(e)}"

class GitConnector:
    def install(self, name: str, info: dict, apps_path: str) -> str:
        url = info.get("url")
        if not url: return "ERRO: Sem URL"
        target_dir = f"{apps_path}\\{name}"
        cmd = ["git", "clone", url, target_dir]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if proc.returncode == 0: return "OK"
            if "already exists" in proc.stderr: return "OK (Already exists)"
            return f"ERRO: {proc.stderr}"
        except Exception as e: return f"ERRO: {str(e)}"
