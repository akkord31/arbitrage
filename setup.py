from cx_Freeze import setup, Executable
import os
import shutil

dll_dir = "C:/Windows/System32"
msvcp = os.path.join(dll_dir, "msvcp140.dll")
vcomp = os.path.join(dll_dir, "vcomp140.dll")
build_exe_options = {
    "packages": ["os", "sqlite3", "http.server", "socketserver", "threading", "time", "json", "webbrowser"],
    "include_files": [
        "templates/",
        "market_data.db"
        # Не включаем DLL сюда — они будут скопированы вручную
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

# 🔽 КОПИРУЕМ DLL ПОСЛЕ СБОРКИ
build_dir = "build"
exe_dir = None

# Ищем подпапку с exe (например, build/exe.win-amd64-3.11)
for name in os.listdir(build_dir):
    full_path = os.path.join(build_dir, name)
    if os.path.isdir(full_path) and name.startswith("exe"):
        exe_dir = full_path
        break

if exe_dir:
    print(f"→ Копируем DLL в: {exe_dir}")
    try:
        shutil.copy(msvcp, os.path.join(exe_dir, "msvcp140.dll"))
        shutil.copy(vcomp, os.path.join(exe_dir, "vcomp140.dll"))
        print("✅ DLL успешно скопированы.")
    except Exception as e:
        print(f"❌ Ошибка при копировании DLL: {e}")
else:
    print("❌ Папка exe не найдена. Проверь, что сборка прошла успешно.")