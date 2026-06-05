from dotenv import dotenv_values
import os

class Config:
    """
    用唯一類屬性包含實體
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """
            stock-ana-python/
            |
            |- config/
                |- config.py
        """
        # 先設定基本路徑
        current_file = os.path.abspath(__file__)
        root_dir = os.path.dirname(os.path.dirname(current_file))
        
        # 初始化配置字典
        env_config = {}
        
        # 優先讀取 .env 檔案（如果存在）
        env_file_path = os.path.join(root_dir, ".env")
        print(f"env_file_path: {env_file_path}")
        if os.path.exists(env_file_path):
            print("讀取env檔案")
            env_file_config = dotenv_values(env_file_path)
            # 先將 .env 的值載入配置
            env_config.update(env_file_config)
        
        # 再讀取系統環境變數，覆蓋 .env 中的值（環境變數優先）
        # 這樣環境變數會覆蓋 .env 中相同的 key，同時引入 .env 中沒有的環境變數
        env_config.update(os.environ)
        
        # 設定屬性
        for key, value in env_config.items():
            setattr(self, key, value)
        
        # 設定固定路徑
        setattr(self, "ROOT", root_dir)
        setattr(self, "LIB_PATH", os.path.join(root_dir, "lib"))
        setattr(self, "DRIVER_PATH", os.path.join(self.LIB_PATH, self.DBDRIVERFILE))
        
    def print_config(self, hide_sensitive: bool = True):
        """打印當前加載的所有配置屬性及其值。
        
        Args:
            hide_sensitive (bool): 是否嘗試隱藏包含 'PASSWORD', 'SECRET' 或 'KEY' 的敏感屬性值。
                                    默認為 True。
        """
        print("--- Config Contents ---")
        # 使用 vars(self) 或 self.__dict__ 獲取實例的屬性字典
        for key, value in sorted(vars(self).items()):
            # 跳過內部屬性 _instance
            if key == "_instance":
                continue
            
            display_value = value
            # 檢查 key 是否包含敏感關鍵字 (不區分大小寫)
            if hide_sensitive and isinstance(value, str) and \
               ('PASSWORD' in key.upper() or 'SECRET' in key.upper() or 'KEY' in key.upper()):
                display_value = "********"
                
            print(f"{key}: {display_value}")
        print("-----------------------")

    def __getattr__(self, name):
        # 如果嘗試訪問不存在的屬性，返回 None 或拋出異常
        # return None  # 如果你想在屬性不存在時返回 None
        raise AttributeError(f"Config has no attribute '{name}'")