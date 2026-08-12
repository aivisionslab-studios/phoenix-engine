# phoenix_diagnostic.py
# Phoenix Inspector 2.0 - Rastreamento Dinâmico em Tempo de Execução
# Uso: python phoenix_diagnostic.py

import os
import sys
import json
import asyncio
import sqlite3
import importlib
import traceback
import platform
from pathlib import Path
from datetime import datetime

# Cores para o terminal
class C:
    OK = '\033[92m'
    FAIL = '\033[91m'
    WARN = '\033[93m'
    INFO = '\033[96m'
    FLOW = '\033[95m'
    ENDC = '\033[0m'

def p(status, msg):
    icons = {"OK": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "🔍", "FLOW": "➡️"}
    color = {"OK": C.OK, "FAIL": C.FAIL, "WARN": C.WARN, "INFO": C.INFO, "FLOW": C.FLOW}
    print(f"{color.get(status, C.ENDC)}{icons.get(status, ' ')} {msg}{C.ENDC}")

def trace_async(func_name):
    """Decorator para rastrear a execução de coroutines em tempo real."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            p("FLOW", f"ENTROU -> {func_name}")
            try:
                result = await func(*args, **kwargs)
                p("FLOW", f"SAIU OK -> {func_name}")
                return result
            except Exception as e:
                p("FAIL", f"EXCEÇÃO EM -> {func_name}: {str(e)}")
                raise
        return wrapper
    return decorator

class PhoenixInspector:
    def __init__(self):
        self.root_dir = Path(__file__).parent.resolve()
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "machine": platform.node(),
            "os": platform.system(),
            "python_version": sys.version,
            "steps": [],
            "errors": []
        }
        self.log_file = self.root_dir / "diagnostic.log"
        self.json_report = self.root_dir / "diagnostic_report.json"
        
        import logging
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            filename=self.log_file,
            filemode="w",
            force=True
        )
        self.logger = logging.getLogger("PhoenixInspector")

    def add_step(self, component, status, details=""):
        step = {"component": component, "status": status, "details": details}
        self.report["steps"].append(step)
        if status == "FAIL":
            self.report["errors"].append(f"{component}: {details}")
        self.logger.info(f"{component} - {status} - {details}")

    def check_imports(self):
        p("INFO", "1. Verificando Estrutura e Imports do Projeto...")
        modules = [
            "phoenix_kernel.kernel", 
            "phoenix_kernel.state", 
            "phoenix_kernel.cloud_sync",
            "phoenix_kernel.discovery.engine",
            "phoenix_kernel.telemetry.core"
        ]
        for mod_name in modules:
            try:
                importlib.import_module(mod_name)
                p("OK", f"Módulo importado: {mod_name}")
                self.add_step("Imports", "OK", mod_name)
            except Exception as e:
                p("FAIL", f"Falha ao importar {mod_name}: {str(e)}")
                self.add_step("Imports", "FAIL", f"{mod_name} - {str(e)}")

    def check_database(self):
        p("INFO", "2. Verificando Banco de Dados SQLite (AHDE)...")
        db_patterns = ["*.sqlite", "*.sqlite3", "hardware_engine*.db"]
        db_files = []
        for pattern in db_patterns:
            db_files.extend(self.root_dir.rglob(pattern))
        
        if not db_files:
            p("WARN", "Nenhum arquivo SQLite encontrado. O AHDE ainda pode não ter rodado.")
            self.add_step("Database", "WARN", "Nenhum SQLite encontrado")
            return

        for db_path in db_files:
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                p("OK", f"DB OK: {db_path.name} (Tabelas: {len(tables)})")
                self.add_step("Database", "OK", f"{db_path.name} - {len(tables)} tabelas")
                conn.close()
            except Exception as e:
                p("FAIL", f"Erro ao ler DB {db_path.name}: {str(e)}")
                self.add_step("Database", "FAIL", str(e))

    async def check_hardware_and_state(self):
        p("INFO", "3. Verificando Hardware Discovery e StateEngine (Runtime)...")
        try:
            from phoenix_kernel.discovery.engine import DiscoveryEngine
            discovery = DiscoveryEngine()
            hw_data = await discovery.discover_hardware()
            p("OK", "DiscoveryEngine executado com sucesso.")
            self.add_step("Discovery", "OK", "Hardware descoberto")

            from phoenix_kernel.state import StateEngine
            from phoenix_kernel.budget.engine import BudgetEngine
            from phoenix_kernel.telemetry.engine import TelemetryEngine
            from phoenix_kernel.services.engine import ServicesEngine
            
            budget = BudgetEngine()
            telemetry = TelemetryEngine()
            services = ServicesEngine()
            
            # Mock corrigido e assíncrono
            class MockModels:
                async def get_model_and_rag_status(self):
                    return {"models": [], "rag_docs": 0}
            
            state = StateEngine(budget, telemetry, services, MockModels())
            
            class Profile: pass
            profile = Profile()
            profile.cpu = hw_data.get('cpu', 'Unknown')
            profile.memory = hw_data.get('memory', 0)
            profile.gpus = hw_data.get('gpus', [])
            profile.available_backends = hw_data.get('available_backends', [])
            
            from core.domain.machine import MachineContext
            machine_context = MachineContext(profile=profile)
            
            state.set_context(machine_context, hw_data)
            state_data = await state.get_state()
            
            dump_file = self.root_dir / "state_dump.json"
            with open(dump_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2, default=str)
                
            p("OK", "StateEngine montou o estado. Salvo em state_dump.json")
            self.add_step("StateEngine", "OK", "Estado gerado com sucesso")
            
            return state_data

        except Exception as e:
            err = traceback.format_exc()
            p("FAIL", f"Falha no Discovery/StateEngine: {str(e)}")
            self.logger.error(err)
            self.add_step("StateEngine", "FAIL", str(e))
            return None

    async def check_cloud_sync(self, state_data):
        p("INFO", "4. Verificando Cloud Sync e Firebase (Monkey-Patching)...")
        
        try:
            from phoenix_kernel.cloud_sync import has_consent, CONSENT_FLAG, MACHINE_ID_FILE, FirestoreSync
        except Exception as e:
            p("FAIL", f"Erro ao importar cloud_sync: {str(e)}")
            return

        # 4.1 Consentimento e Machine ID
        if has_consent():
            p("OK", "Consentimento concedido.")
        else:
            p("WARN", "Consentimento NEGADO.")
            
        if MACHINE_ID_FILE.exists():
            p("OK", f"Machine ID encontrado: {MACHINE_ID_FILE.read_text().strip()}")
        else:
            p("WARN", "Machine ID não existe.")

        # 4.2 Instanciação e Monkey-Patching dinâmico
        try:
            sync = FirestoreSync()
            p("OK", "FirestoreSync instanciado.")
            
            # Aplica o tracing na função principal de sync
            original_sync = sync.sync_machine_state
            sync.sync_machine_state = trace_async("sync_machine_state")(original_sync)
            
            if state_data:
                p("FLOW", "Disparando sync_machine_state(state_data)...")
                await sync.sync_machine_state(state_data)
                p("OK", "Sincronização de teste concluída sem exceções.")
                self.add_step("CloudSync:Firebase", "OK", "Documento enviado/tracing concluído")
                
        except Exception as e:
            err = traceback.format_exc()
            p("FAIL", f"Erro na sincronização com Firebase: {str(e)}")
            self.logger.error(err)
            self.add_step("CloudSync:Firebase", "FAIL", str(e))

    def generate_reports(self):
        p("INFO", "5. Gerando Relatórios Finais...")
        
        with open(self.json_report, "w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2, ensure_ascii=False)
        p("OK", f"Relatório JSON salvo em: {self.json_report.name}")
        
        print("\n" + "="*50)
        print(f"{C.INFO}RESUMO DO DIAGNÓSTICO{C.ENDC}")
        print("="*50)
        
        ok_count = sum(1 for s in self.report["steps"] if s["status"] == "OK")
        fail_count = sum(1 for s in self.report["steps"] if s["status"] == "FAIL")
        warn_count = sum(1 for s in self.report["steps"] if s["status"] == "WARN")
        
        print(f"✅ Sucessos: {ok_count}")
        print(f"❌ Falhas:   {fail_count}")
        print(f"⚠️ Avisos:   {warn_count}")
        
        if fail_count > 0:
            print(f"\n{C.FAIL}ERROS CRÍTICOS ENCONTRADOS:{C.ENDC}")
            for err in self.report["errors"]:
                print(f"  - {err}")
            print(f"\nConsulte o log completo: {self.log_file.name}")
        else:
            print(f"\n{C.OK}Nenhum erro crítico encontrado!{C.ENDC}")
        
        print("="*50)

    async def run(self):
        print(f"{C.INFO}==================================")
        print(f"   PHOENIX INSPECTOR 2.0 - RUNTIME TRACING")
        print(f"=================================={C.ENDC}\n")
        
        self.check_imports()
        print()
        self.check_database()
        print()
        state_data = await self.check_hardware_and_state()
        print()
        await self.check_cloud_sync(state_data)
        print()
        self.generate_reports()

if __name__ == "__main__":
    inspector = PhoenixInspector()
    try:
        asyncio.run(inspector.run())
    except KeyboardInterrupt:
        print("\nDiagnóstico interrompido pelo usuário.")
    except Exception as e:
        print(f"\n{C.FAIL}Erro fatal no próprio script de diagnóstico: {str(e)}{C.ENDC}")
        traceback.print_exc()