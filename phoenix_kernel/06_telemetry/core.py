import glob
import json
import logging
import os
import platform
import re
import subprocess
import threading

logger = logging.getLogger(__name__)

# No Linux nao existe pythonnet/HardwareMonitor (sao Windows/.NET) - tudo
# aqui embaixo com prefixo _linux usa sysfs/DRM (mesma base do self-test
# do install/linux.ps1) + lm-sensors, que ja e' instalado via apt no
# install/linux.ps1. Zero dependencia do Computer()/HardwareInstance abaixo.
IS_LINUX = platform.system() == "Linux"

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

def _amd_gpu_cards():
    """Gera os paths /sys/class/drm/cardN/device de GPUs AMD (vendor 0x1002).
    Mesmo criterio usado no self-test embutido em install/linux.ps1."""
    for card in sorted(glob.glob("/sys/class/drm/card[0-9]*/device")):
        vendor_path = os.path.join(card, "vendor")
        if not os.path.exists(vendor_path):
            continue
        try:
            with open(vendor_path) as f:
                vendor = f.read().strip()
        except OSError:
            continue
        if vendor == "0x1002":
            yield card


def _read_sysfs_int(path):
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _gpu_name_linux() -> str:
    """Nome comercial da GPU AMD via lspci - sysfs so' expoe vendor:device id."""
    try:
        out = subprocess.run(["lspci", "-d", "1002:"], capture_output=True, text=True, timeout=5)
        for line in out.stdout.splitlines():
            if "VGA" in line or "Display" in line or "3D controller" in line:
                # Ex: "03:00.0 VGA compatible controller: Advanced Micro Devices... Polaris 20 XL [Radeon RX 580 2048SP]"
                return line.split(": ", 1)[-1].strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "GPU AMD"


_LMSENSORS_TYPE_MAP = {"temp": "Temperature", "fan": "Fan", "in": "Voltage"}


def _lmsensors_devices() -> list:
    """Roda 'sensors -j' (lm-sensors, ja instalado via apt no linux.ps1) e
    converte cada chip (CPU, placa-mae/Super I/O, etc) num "dispositivo" no
    mesmo formato {name, type, sensors} que o frontend ja espera do Windows."""
    try:
        out = subprocess.run(["sensors", "-j"], capture_output=True, text=True, timeout=5)
        data = json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        logger.warning(f"erro lendo lm-sensors: {e}")
        return []

    devices = []
    for chip_name, chip_data in data.items():
        if not isinstance(chip_data, dict):
            continue
        sensors = []
        for feature_name, readings in chip_data.items():
            if not isinstance(readings, dict):
                continue
            for key, value in readings.items():
                if not key.endswith("_input") or not isinstance(value, (int, float)):
                    continue
                prefix = re.match(r"([a-z]+)", key)
                stype = _LMSENSORS_TYPE_MAP.get(prefix.group(1), None) if prefix else None
                if not stype:
                    continue
                sensors.append({
                    "name": feature_name,
                    "type": stype,
                    "value": float(value),
                    "unit": _SENSOR_UNITS.get(stype, ""),
                })
        if sensors:
            devices.append({"name": chip_name, "type": "Motherboard", "sensors": sensors})
    return devices


def _parse_lsblk_size_gb(size_str):
    """Converte o 'SIZE' do lsblk (ex: '238.5G', '1.8T') pra GB numerico."""
    if not size_str:
        return None
    m = re.match(r"([\d.]+)\s*([KMGT])", size_str.strip(), re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1))
    factor = {"K": 1 / 1024 / 1024, "M": 1 / 1024, "G": 1, "T": 1024}.get(m.group(2).upper(), 1)
    return round(value * factor, 1)


def _disk_temps_by_device() -> dict:
    """Mapeia nome de bloco (ex: 'sda', 'nvme0n1') -> temperatura via hwmon,
    quando o kernel expoe (modulo drivetemp p/ SATA/SAS, nativo pra NVMe).
    Nem toda maquina tem isso carregado - se nao tiver, o disco ainda
    aparece na lista, so' sem sensor de temperatura."""
    result = {}
    for hwmon in glob.glob("/sys/class/hwmon/hwmon*"):
        try:
            with open(os.path.join(hwmon, "name")) as f:
                chip = f.read().strip()
        except OSError:
            continue
        if chip not in ("drivetemp", "nvme"):
            continue

        temp = _read_sysfs_int(os.path.join(hwmon, "temp1_input"))
        if temp is None:
            continue

        block_name = None
        device_path = os.path.join(hwmon, "device")
        block_glob = glob.glob(os.path.join(device_path, "block", "*"))
        if block_glob:
            block_name = os.path.basename(block_glob[0])
        else:
            # NVMe: o "device" do hwmon costuma ser o controlador nvmeX,
            # a namespace de bloco de fato e' nvmeXn1.
            try:
                target = os.path.basename(os.path.realpath(device_path))
            except OSError:
                target = ""
            if target.startswith("nvme"):
                ns_glob = glob.glob(f"/sys/class/nvme/{target}/nvme*n1")
                if ns_glob:
                    block_name = os.path.basename(ns_glob[0])

        if block_name:
            result[block_name] = temp / 1000.0
    return result


def _storage_devices_linux() -> list:
    """Lista discos (SSD/HDD/NVMe) via lsblk, com temperatura quando o
    kernel expoe via hwmon. Dispositivo sem NENHUM sensor legivel (nem
    capacidade) e' omitido, igual ao comportamento do path Windows."""
    try:
        out = subprocess.run(
            ["lsblk", "-d", "-J", "-o", "NAME,MODEL,SIZE,ROTA,TYPE"],
            capture_output=True, text=True, timeout=5,
        )
        data = json.loads(out.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as e:
        logger.warning(f"erro lendo lsblk: {e}")
        return []

    temps_by_dev = _disk_temps_by_device()
    devices = []
    for blk in data.get("blockdevices", []):
        if blk.get("type") != "disk":
            continue
        name = blk.get("name", "")
        if not name:
            continue

        if name.startswith("nvme"):
            kind = "NVMe"
        elif blk.get("rota") in (True, "1", 1):
            kind = "HDD"
        else:
            kind = "SSD"

        sensors = []
        size_gb = _parse_lsblk_size_gb(blk.get("size"))
        if size_gb is not None:
            sensors.append({"name": "Capacity", "type": "Data", "value": size_gb, "unit": "GB"})

        temp = temps_by_dev.get(name)
        if temp is not None:
            sensors.append({"name": "Temperature", "type": "Temperature", "value": temp, "unit": "°C"})

        if sensors:
            label = (blk.get("model") or "").strip() or name
            devices.append({"name": f"{label} ({kind}, /dev/{name})", "type": kind, "sensors": sensors})

    return devices


def _get_all_hardware_sensors_linux() -> list:
    """Equivalente Linux do get_all_hardware_sensors(): GPU via sysfs/DRM +
    CPU/placa-mae/fans via lm-sensors + discos via lsblk."""
    devices = []
    for card in _amd_gpu_cards():
        sensors = []
        busy = _read_sysfs_int(os.path.join(card, "gpu_busy_percent"))
        if busy is not None:
            sensors.append({"name": "GPU Load", "type": "Load", "value": float(busy), "unit": _SENSOR_UNITS["Load"]})

        vram_used = _read_sysfs_int(os.path.join(card, "mem_info_vram_used"))
        if vram_used is not None:
            sensors.append({"name": "GPU Memory Used", "type": "SmallData", "value": vram_used / (1024 * 1024), "unit": _SENSOR_UNITS["SmallData"]})

        vram_total = _read_sysfs_int(os.path.join(card, "mem_info_vram_total"))
        if vram_total is not None:
            sensors.append({"name": "GPU Memory Total", "type": "SmallData", "value": vram_total / (1024 * 1024), "unit": _SENSOR_UNITS["SmallData"]})

        for hwmon_path in glob.glob(os.path.join(card, "hwmon", "hwmon*", "temp1_input")):
            milli_c = _read_sysfs_int(hwmon_path)
            if milli_c is not None:
                sensors.append({"name": "GPU Core", "type": "Temperature", "value": milli_c / 1000.0, "unit": _SENSOR_UNITS["Temperature"]})

        if sensors:
            devices.append({"name": _gpu_name_linux(), "type": "GpuAmd", "sensors": sensors})

    devices.extend(_lmsensors_devices())
    devices.extend(_storage_devices_linux())
    return devices


def _get_gpu_static_specs_linux() -> list:
    specs = []
    for card in _amd_gpu_cards():
        vram_total = _read_sysfs_int(os.path.join(card, "mem_info_vram_total"))
        specs.append({
            "model": _gpu_name_linux(),
            "vram_mb": int(vram_total / (1024 * 1024)) if vram_total else 0,
        })
    return specs


def _get_gpu_sensors_linux() -> dict:
    for card in _amd_gpu_cards():
        temp = load = vram_used = None
        busy = _read_sysfs_int(os.path.join(card, "gpu_busy_percent"))
        if busy is not None:
            load = float(busy)
        vram = _read_sysfs_int(os.path.join(card, "mem_info_vram_used"))
        if vram is not None:
            vram_used = vram / (1024 * 1024)
        for hwmon_path in glob.glob(os.path.join(card, "hwmon", "hwmon*", "temp1_input")):
            milli_c = _read_sysfs_int(hwmon_path)
            if milli_c is not None:
                temp = milli_c / 1000.0
                break
        return {"temperature_celsius": temp, "load_percent": load, "vram_used_mb": vram_used}
    return {"temperature_celsius": None, "load_percent": None, "vram_used_mb": None}


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
    if IS_LINUX:
        return _get_all_hardware_sensors_linux()

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
    if IS_LINUX:
        return _get_gpu_static_specs_linux()

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
    if IS_LINUX:
        return _get_gpu_sensors_linux()

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