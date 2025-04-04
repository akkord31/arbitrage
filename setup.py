from cx_Freeze import setup, Executable


build_exe_options = {
    "packages": ["os", "sqlite3", "http.server", "socketserver", "threading", "time", "json", "webbrowser"],
    "include_files": [
        "templates/",
        "market_data.db",
        "C:/Windows/System32/msvcp140.dll",
        "C:/Windows/System32/vcomp140.dll"
    ],
    "excludes": ["tkinter"],
}


setup(
    name = "server",
    version = "1.0",
    description = "Локальный HTTP сервер",
    options={"build_exe": build_exe_options},
    executables = [Executable("run_server.py", target_name="my_server.exe", base="Console")]
)