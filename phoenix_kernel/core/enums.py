from enum import Enum

class MissionAction(str, Enum):
    INSTALL_PACKAGE = "INSTALL_PACKAGE"
    DOWNLOAD_MODEL = "DOWNLOAD_MODEL"
    VALIDATE_ENVIRONMENT = "VALIDATE_ENVIRONMENT"
    VALIDATE = "VALIDATE"
    CONFIGURE = "CONFIGURE"
    EXECUTE = "EXECUTE"
    START_SERVICE = "START_SERVICE"
    STOP_SERVICE = "STOP_SERVICE"
    CLONE_REPOSITORY = "CLONE_REPOSITORY"
    RUN_BENCHMARK = "RUN_BENCHMARK"
    SWITCH_RUNTIME = "SWITCH_RUNTIME"
    GENERATE_IMAGE = "GENERATE_IMAGE"

class MissionStatus(str, Enum):
    CREATED = "created"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"
    PAUSED = "paused"