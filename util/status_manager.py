from enum import Enum
import logging
import threading


class WorkStatus(Enum):
    STOPPED = "STOPPED"
    RUNNING = "RUNNING"
    ERROR = "ERROR"
    PAUSED = "PAUSED"
    INITED = "INITED"
    INITING = "INITING"
    READY = "READY"
    STOPPING = "STOPPING"


class InvalidStateTransitionError(Exception):
    """當狀態轉移不合法時拋出"""
    def __init__(self, current_state, target_state):
        # 把狀態存起來，方便外層 Log 或邏輯判斷
        self.current_state = current_state
        self.target_state = target_state
        
        # 組合標準錯誤訊息傳給父類別
        message = f"Invalid transition: Cannot switch from '{current_state}' to '{target_state}'"
        super().__init__(message)

class StatusManager:
    """
    狀態管理器，初始化狀態預設為 STOPPED
    """
    def __init__(self, work_name: str, initial_state=WorkStatus.INITED):
        self.work_name = work_name
        self._status = initial_state
        self._lock = threading.RLock() # 使用 RLock 允許同一執行緒重入檢查
        self.logger = logging.getLogger(__name__)

        # 狀態流轉規則表 (State Transition Table)
        # {
        #    當前狀態 :  {允許轉換到的狀態},
        #}
        self.TRANSITION_RULES = {
            WorkStatus.INITED: {WorkStatus.INITING, WorkStatus.ERROR},

            WorkStatus.STOPPED:  {WorkStatus.INITING},
            
            WorkStatus.INITING:  {WorkStatus.READY, WorkStatus.ERROR},
            
            WorkStatus.READY:    {WorkStatus.RUNNING, WorkStatus.STOPPING, WorkStatus.ERROR, WorkStatus.STOPPED},
            
            WorkStatus.RUNNING:  {WorkStatus.PAUSED, WorkStatus.STOPPING, WorkStatus.ERROR, WorkStatus.STOPPED},
            
            WorkStatus.PAUSED:   {WorkStatus.RUNNING, WorkStatus.STOPPING, WorkStatus.ERROR},
            
            WorkStatus.STOPPING: {WorkStatus.STOPPED, WorkStatus.ERROR},
            
            WorkStatus.ERROR:    {WorkStatus.STOPPING}
        }

    @property
    def current(self):
        """讀取當前狀態 (Thread-Safe)"""
        with self._lock:
            return self._status

    def is_state(self, *states):
        """檢查是否屬於某些狀態之一"""
        with self._lock:
            return self._status in states

    def transition_to(self, target_state: WorkStatus):
        """
        嘗試切換狀態
        :param target_state: 目標狀態
        :return: 是否成功
        """
        with self._lock:
            if self._status == target_state:
                return

            # 2. 檢查規則 (核心保護)
            allowed_next_states = self.TRANSITION_RULES.get(self._status, None)

            if allowed_next_states is None:
                raise InvalidStateTransitionError(self._status, target_state)

            if target_state not in allowed_next_states:
                raise InvalidStateTransitionError(self._status, target_state)

            # 3. 執行切換
            old_state = self._status
            self._status = target_state
            self.logger.info(f"{self.work_name} 狀態變更: [{old_state.name}] -> [{target_state.name}]")