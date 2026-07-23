import logging
import threading

logger = logging.getLogger(__name__)

# Lock global e verdadeiro (nao so o "import threading" morto que estava
# aqui antes). O bug real: cada chamada cria seu proprio HardwareInstance()
# pra evitar disputa no objeto .NET compartilhado - isso funciona - mas o
# driver nativo por baixo (WinRing0/PawnIO, que o LibreHardwareMonitor usa
# pra ler hardware de baixo nivel) nao e thread-safe entre instancias
# DIFERENTES de Computer(). Duas chamadas simultaneas (ex: telemetria
# continua + /api/hardware/all disparado ao mesmo tempo) podem colidir
# dentro do proprio driver, nao so no objeto Python - foi isso que gerou
# o "Referencia de objeto nao definida... CpuGroup.GetProcessorThreads()".
# Serializar TODO acesso ao Computer() com este lock resolve os dois casos.
_hardware_lock = threading.Lock()

# Mapeamento de unidades para o frontend
_SENSOR_UNITS = {
    "Temperature": "°C", "Load": "%", "Clock": "MHz", "Voltage": "V",
    "Fan": "RPM", "Power": "W", "Data": "GB", "SmallData": "MB", 
    "Throughput": "B/s", "Factor": "x"
}

class HardwareInstance:
    """
    Wrapper para isolar instâncias do HardwareMonitor.Computer().
    Cada camada (Telemetria, Discovery, API) cria a sua instância, 
    evitando disputa de concorrência (thread-safety) e garantindo redundância.
    """
    def __init__(self):
        self.computer = None
        self._open()

    def _open(self):
        try:
            import clr
            from HardwareMonitor.Hardware import Computer
            self.computer = Computer()
            self.computer.IsCpuEnabled = True
            self.computer.IsGpuEnabled = True
            self.computer.IsStorageEnabled = True
            self.computer.IsMotherboardEnabled = True
            self.computer.IsMemoryEnabled = True
            self.computer.IsNetworkEnabled = True
            self.computer.IsControllerEnabled = True
            self.computer.Open()
        except ImportError:
            logger.warning("pacote 'pythonnet' ou 'HardwareMonitor' não instalado.")
            self.computer = None
        except Exception as e:
            logger.error(f"falha ao abrir Computer(): {e}")
            self.computer = None

    def close(self):
        if self.computer:
            try:
                self.computer.Close()
            except:
                pass
            self.computer = None

def _collect_sensors(hw) -> list:
    out = []
    for sensor in hw.Sensors:
        if sensor.Value is None: continue
        stype = str(sensor.SensorType)
        try: value = float(sensor.Value)
        except: continue
        out.append({
            "name": sensor.Name or "", 
            "type": stype, 
            "value": value, 
            "unit": _SENSOR_UNITS.get(stype, "")
        })
    return out

def get_all_hardware_sensors() -> list:
    """Varre todos os dispositivos e sensores (usado pelo /api/hardware/all)."""
    with _hardware_lock:
        instance = HardwareInstance()
        if not instance.computer:
            return []

        devices = []
        try:
            for hw in instance.computer.Hardware:
                hw.Update()
                sensors = _collect_sensors(hw)
                if sensors:
                    devices.append({"name": hw.Name, "type": str(hw.HardwareType), "sensors": sensors})

                sub_hw = getattr(hw, "SubHardware", None) or []
                for sub in sub_hw:
                    sub.Update()
                    sub_sensors = _collect_sensors(sub)
                    if sub_sensors:
                        devices.append({"name": f"{hw.Name} / {sub.Name}", "type": str(sub.HardwareType), "sensors": sub_sensors})
        except Exception as e:
            logger.warning(f"erro lendo todos os sensores: {e}")
        finally:
            instance.close()

        return devices

def get_gpu_static_specs() -> list:
    """Specs estáticos de GPU (nome + VRAM total) para o Discovery."""
    with _hardware_lock:
        instance = HardwareInstance()
        if not instance.computer:
            return []

        specs = []
        try:
            for hw in instance.computer.Hardware:
                hw.Update()
                if "Gpu" not in str(hw.HardwareType):
                    continue
                vram_total_mb = 0
                for sensor in hw.Sensors:
                    if str(sensor.SensorType) == "SmallData" and sensor.Name == "GPU Memory Total" and sensor.Value is not None:
                        vram_total_mb = int(float(sensor.Value))
                        break
                specs.append({"model": hw.Name, "vram_mb": vram_total_mb})
        except Exception as e:
            logger.warning(f"erro lendo specs estáticos de GPU: {e}")
        finally:
            instance.close()

        return specs

def get_gpu_sensors() -> dict:
    """Sensores rápidos da GPU (Temp, Load, VRAM usada) para a Telemetria contínua."""
    instance = HardwareInstance()
    if not instance.computer:
        return {"temperature_celsius": None, "load_percent": None, "vram_used_mb": None}
        
    temp = load = vram_used = None
    try:
        for hw in instance.computer.Hardware:
            hw.Update()
            if "Gpu" not in str(hw.HardwareType): continue
            for sensor in hw.Sensors:
                name = sensor.Name or ""
                sensor_type = str(sensor.SensorType)
                value = sensor.Value
                if value is None: continue
                if sensor_type == "Temperature":
                    if temp is None or "Core" in name: temp = float(value)
                elif sensor_type == "Load":
                    if load is None or "Core" in name: load = float(value)
                elif sensor_type == "SmallData" and "Memory" in name and "Used" in name:
                    vram_used = float(value)
    except Exception as e:
        logger.warning(f"erro lendo GPU: {e}")
    finally:
        instance.close()
        
    return {"temperature_celsius": temp, "load_percent": load, "vram_used_mb": vram_used}