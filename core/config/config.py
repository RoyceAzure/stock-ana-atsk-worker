from dotenv import dotenv_values, load_dotenv
import os


def _project_root() -> str:
    """core/config/config.py -> 專案根目錄。"""
    current_file = os.path.abspath(__file__)
    return os.path.dirname(os.path.dirname(os.path.dirname(current_file)))


class Config:
    """
    用唯一類屬性包含實體。
    載入順序：.env 先讀入，再以系統環境變數覆蓋（環境變數優先）。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        root_dir = _project_root()
        env_file_path = os.path.join(root_dir, ".env")

        # 將 .env 注入 os.environ（不覆蓋已存在的環境變數）
        if os.path.exists(env_file_path):
            load_dotenv(env_file_path, override=False)

        env_config: dict[str, str] = {}
        if os.path.exists(env_file_path):
            env_file_config = dotenv_values(env_file_path)
            env_config.update(
                {key: value for key, value in env_file_config.items() if value is not None}
            )

        # 環境變數覆蓋 .env（與 ensure_env_loaded / os.getenv 行為一致）
        env_config.update(os.environ)

        for key, value in env_config.items():
            setattr(self, key, value)

        setattr(self, "ROOT", root_dir)
        setattr(self, "LIB_PATH", os.path.join(root_dir, "lib"))
        dbdriverfile = env_config.get("DBDRIVERFILE", "")
        setattr(self, "DRIVER_PATH", os.path.join(root_dir, "lib", dbdriverfile))

    def print_config(self, hide_sensitive: bool = True):
        """打印當前加載的所有配置屬性及其值。"""
        print("--- Config Contents ---")
        for key, value in sorted(vars(self).items()):
            if key == "_instance":
                continue

            display_value = value
            if hide_sensitive and isinstance(value, str) and (
                "PASSWORD" in key.upper()
                or "SECRET" in key.upper()
                or "KEY" in key.upper()
            ):
                display_value = "********"

            print(f"{key}: {display_value}")
        print("-----------------------")

    def __getattr__(self, name):
        raise AttributeError(f"Config has no attribute '{name}'")
