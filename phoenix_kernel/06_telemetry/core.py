import logging

logger = logging.getLogger(__name__)

_computer = None
_diagnostic_logged = False  # garante que o log detalhado sai só 1x no boot, não a cada poll


def _get_computer():
    global _computer
    if _computer is not None:
        return _computer

    # BUG 1 CORRIGIDO: sem isso, "from HardwareMonitor.Hardware import ..."
    # pode falhar com uma exceção que NÃO é ImportError (ex: falha do
    # pythonnet em resolver o runtime .NET), e essa exceção escapava sem
    # log nenhum porque só capturávamos ImportError.
    try:
        import clr  # noqa: F401 — bootstrap do pythonnet, precisa vir ANTES do import abaixo
    except ImportError:
        logger.warning("pacote 'pythonnet' não instalado. Rode: pip install pythonnet")
        return None

    try:
        from HardwareMonitor.Hardware import Computer
    except ImportError:
        logger.warning("pacote 'HardwareMonitor' não instalado. Rode: pip install HardwareMonitor")
        return None
    except Exception as e:
        # Isso é o caso que antes vazava sem log: clr importou ok, mas a
        # resolução da assembly HardwareMonitor.Hardware falhou de verdade.
        logger.error(f"falha ao carregar HardwareMonitor.Hardware via pythonnet: {e}")
        return None

    try:
        computer = Computer()
        computer.IsCpuEnabled = True
        computer.IsGpuEnabled = True
        # BUG 3 CORRIGIDO: só Cpu e Gpu estavam habilitados aqui. O
        # HardwareMonitor/LibreHardwareMonitorLib exige que CADA categoria
        # seja ligada explicitamente antes do Open() — sem isso, SSD/HDD,
        # placa-mãe, memória e rede nunca aparecem em computer.Hardware,
        # não importa o que get_all_hardware_sensors() faça depois. Cada
        # flag é ligada em try/except separado porque builds mais antigos
        # da lib podem não ter todas essas propriedades.
        for flag in (
            "IsMotherboardEnabled",
            "IsMemoryEnabled",
            "IsStorageEnabled",
            "IsNetworkEnabled",
            "IsControllerEnabled",
            "IsPsuEnabled",
            "IsBatteryEnabled",
        ):
            try:
                setattr(computer, flag, True)
            except Exception as e:
                logger.debug(f"HardwareMonitor: propriedade '{flag}' indisponível nessa versão da lib: {e}")
        computer.Open()
        _computer = computer
        return _computer
    except Exception as e:
        logger.warning(
            f"falha ao abrir HardwareMonitor.Computer(): {e}. "
            f"Se a mensagem mencionar acesso negado/permissão, rode o processo como Administrador."
        )
        return None


def _log_diagnostic_once(computer):
    """
    Roda 1x na vida do processo. Lista TUDO que o HardwareMonitor está
    vendo — hardware detectado, tipos, e nome/tipo de cada sensor de GPU —
    pra você conseguir olhar o log e saber exatamente onde está travando
    (0 hardware? GPU sem nenhum sensor? sensor com nome que o filtro não
    reconhece?) em vez de só ver "None" sem explicação.
    """
    global _diagnostic_logged
    if _diagnostic_logged:
        return
    _diagnostic_logged = True

    try:
        hw_list = list(computer.Hardware)
        logger.info(f"[HW DIAGNOSTIC] {len(hw_list)} dispositivo(s) de hardware detectado(s) pelo HardwareMonitor.")
        for hw in hw_list:
            hw.Update()
            htype = str(hw.HardwareType)
            sensors = list(hw.Sensors)
            logger.info(f"[HW DIAGNOSTIC]  - {hw.Name} (tipo={htype}, {len(sensors)} sensor(es))")
            if "Gpu" in htype:
                for s in sensors:
                    logger.info(f"[HW DIAGNOSTIC]      sensor: name='{s.Name}' type={s.SensorType} value={s.Value}")
                if not sensors:
                    logger.warning(
                        "[HW DIAGNOSTIC]      GPU detectada mas SEM NENHUM sensor. "
                        "Causa mais comum: processo não está rodando como Administrador "
                        "(leitura de sensores AMD via ADL exige elevação no Windows)."
                    )
        if not any("Gpu" in str(hw.HardwareType) for hw in hw_list):
            logger.warning(
                "[HW DIAGNOSTIC] Nenhum hardware do tipo GPU foi detectado pelo HardwareMonitor. "
                "Verifique se o driver AMD está instalado corretamente e se o processo tem permissão de Administrador."
            )
    except Exception as e:
        logger.error(f"[HW DIAGNOSTIC] falha ao gerar diagnóstico: {e}")


# Mapa de unidade de exibição por SensorType do HardwareMonitor/LibreHardwareMonitorLib.
# Usado só pro frontend saber o que colar depois do número — não afeta a coleta.
_SENSOR_UNITS = {
    "Temperature": "°C",
    "Load": "%",
    "Clock": " MHz",
    "Voltage": " V",
    "Fan": " RPM",
    "Flow": " L/h",
    "Control": "%",
    "Power": " W",
    "Data": " GB",
    "SmallData": " MB",
    "Throughput": " B/s",
    "Factor": "x",
}


def _collect_sensors(hw) -> list:
    """Lê todos os sensores de um objeto hardware/sub-hardware já atualizado (hw.Update() chamado antes)."""
    out = []
    for sensor in hw.Sensors:
        if sensor.Value is None:
            continue
        stype = str(sensor.SensorType)
        try:
            value = float(sensor.Value)
        except (TypeError, ValueError):
            continue
        out.append({
            "name": sensor.Name or "",
            "type": stype,
            "value": value,
            "unit": _SENSOR_UNITS.get(stype, ""),
        })
    return out


def get_all_hardware_sensors() -> list:
    """
    Retorna TODOS os dispositivos ativos detectados pelo HardwareMonitor
    (CPU, GPU, RAM, placa-mãe/Super I/O, SSD, HDD, rede, bateria etc.)
    junto com todos os sensores de cada um.

    Formato de retorno:
    [
      {"name": "Samsung SSD 970 EVO", "type": "Storage", "sensors": [
          {"name": "Used Space", "type": "Load", "value": 42.3, "unit": "%"}, ...
      ]},
      ...
    ]

    Dispositivos que estejam presentes na placa mas sem NENHUM sensor legível
    (sem driver/permissão) são omitidos daqui — pra achar esses, olhe o
    log "[HW DIAGNOSTIC]" gerado 1x no boot por _log_diagnostic_once().
    """
    computer = _get_computer()
    if computer is None:
        return []

    _log_diagnostic_once(computer)

    devices = []
    try:
        for hw in computer.Hardware:
            hw.Update()
            sensors = _collect_sensors(hw)
            if sensors:
                devices.append({
                    "name": hw.Name,
                    "type": str(hw.HardwareType),
                    "sensors": sensors,
                })

            # Muitos sensores de placa-mãe (fans, temps de VRM, etc.) e às vezes
            # de storage vêm dentro de SubHardware (ex: chip Super I/O), não
            # direto no objeto principal. Sem isso, placa-mãe/SSD aparecem
            # "vazios" mesmo com sensores reais disponíveis.
            sub_hw_list = getattr(hw, "SubHardware", None) or []
            for sub in sub_hw_list:
                try:
                    sub.Update()
                    sub_sensors = _collect_sensors(sub)
                    if sub_sensors:
                        devices.append({
                            "name": f"{hw.Name} / {sub.Name}",
                            "type": str(sub.HardwareType),
                            "sensors": sub_sensors,
                        })
                except Exception as e:
                    logger.debug(f"falha lendo sub-hardware de {hw.Name}: {e}")
    except Exception as e:
        logger.warning(f"erro lendo todos os sensores de hardware: {e}")

    return devices


def get_gpu_sensors() -> dict:
    computer = _get_computer()
    if computer is None:
        return {"temperature_celsius": None, "load_percent": None, "vram_used_mb": None}

    _log_diagnostic_once(computer)

    temp = load = vram_used = None
    try:
        for hw in computer.Hardware:
            hw.Update()
            if "Gpu" not in str(hw.HardwareType):
                continue
            for sensor in hw.Sensors:
                name = sensor.Name or ""
                sensor_type = str(sensor.SensorType)
                value = sensor.Value
                if value is None:
                    continue

                # BUG 2 CORRIGIDO: antes exigia "Core" no nome exato. Agora
                # aceita qualquer sensor do SensorType certo — o primeiro
                # encontrado de cada tipo — já que builds diferentes da
                # LibreHardwareMonitorLib nomeiam os sensores de GPU de
                # formas diferentes (ex: "GPU Core", "GPU Hot Spot", "GPU").
                # Preferência: se existir um sensor com "Core" no nome, usa
                # ele (é o mais específico); senão aceita o primeiro do tipo.
                if sensor_type == "Temperature":
                    if temp is None or "Core" in name:
                        temp = float(value)
                elif sensor_type == "Load":
                    if load is None or "Core" in name:
                        load = float(value)
                elif sensor_type == "SmallData" and "Memory" in name and "Used" in name:
                    vram_used = float(value)
    except Exception as e:
        logger.warning(f"erro lendo sensores de GPU: {e}")

    if temp is None and load is None and vram_used is None:
        logger.debug(
            "get_gpu_sensors() retornou tudo None. Veja o log '[HW DIAGNOSTIC]' "
            "no boot pra saber se é falta de elevação, driver, ou nome de sensor."
        )

    return {"temperature_celsius": temp, "load_percent": load, "vram_used_mb": vram_used}