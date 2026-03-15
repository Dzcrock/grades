"""
setup.py - файл для сборки программы в exe с помощью PyInstaller
Установка зависимостей: pip install pyinstaller
Запуск сборки: python setup.py
"""

import os
import sys
import shutil
from datetime import datetime


def create_spec_file():
    """Создание spec файла для PyInstaller"""
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['school_analytics.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('README.txt', '.'),
        ('icon.ico', '.'),
    ],
    hiddenimports=[
        'pandas',
        'numpy',
        'matplotlib',
        'matplotlib.backends.backend_tkagg',
        'seaborn',
        'openpyxl',
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SchoolAnalytics',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # False - скрыть консоль, True - показать для отладки
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
    copyright='© {year} Школьная аналитика',
    trademark='School Analytics',
)

# Для создания одной папки с файлами
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SchoolAnalytics'
)
"""
    return spec_content


def create_readme():
    """Создание файла README.txt"""
    readme_content = """ШКОЛЬНАЯ АНАЛИТИКА v1.0
==========================

Программа для анализа успеваемости учеников и результатов ВПР.

УСТАНОВКА:
----------
1. Распакуйте архив в любую папку
2. Запустите SchoolAnalytics.exe

ИСПОЛЬЗОВАНИЕ:
--------------
1. Загрузите файл с данными учеников (Excel или CSV)
2. Переключайтесь между вкладками для просмотра аналитики
3. Используйте кнопки для сохранения отчетов

ФОРМАТ ФАЙЛОВ:
--------------
Основные данные:
- Первая колонка: ФИО ученика
- Последующие колонки: оценки (2-5) или баллы за работы

Данные ВПР:
- Первая колонка: ФИО ученика
- Колонки с баллами за задания
- Последняя колонка: итоговая оценка или сумма баллов

ГОРЯЧИЕ КЛАВИШИ:
----------------
Ctrl+O - открыть файл
Ctrl+S - сохранить отчет
Ctrl+R - обновить аналитику
F1 - справка

ТРЕБОВАНИЯ К СИСТЕМЕ:
--------------------
Windows 7/8/10/11 (64-bit)
MacOS 10.14+ (требуется отдельная сборка)
Linux (требуется отдельная сборка)

© 2024 Школьная аналитика
Версия: 1.0
Дата сборки: {date}
"""
    return readme_content


def create_icon():
    """Создание простой иконки (если нет своей)"""
    from PIL import Image, ImageDraw

    # Создаем изображение 256x256
    img = Image.new('RGBA', (256, 256), color=(41, 128, 185, 255))
    draw = ImageDraw.Draw(img)

    # Рисуем букву "Ш"
    draw.text((70, 50), "Ш", fill=(255, 255, 255, 255), font_size=150)

    # Сохраняем как ICO
    img.save('icon.ico', format='ICO', sizes=[(256, 256)])
    print("✅ Создана иконка icon.ico")


def build_windows():
    """Сборка для Windows"""
    print("🔧 Начинаю сборку для Windows...")

    # Создаем spec файл
    with open('school_analytics.spec', 'w', encoding='utf-8') as f:
        f.write(create_spec_file().format(year=datetime.now().year))

    # Запускаем PyInstaller
    os.system('pyinstaller school_analytics.spec --clean')

    # Копируем дополнительные файлы
    if os.path.exists('dist/SchoolAnalytics'):
        # Создаем папку для документации
        os.makedirs('dist/SchoolAnalytics/docs', exist_ok=True)

        # Копируем README
        with open('dist/SchoolAnalytics/README.txt', 'w', encoding='utf-8') as f:
            f.write(create_readme().format(date=datetime.now().strftime('%Y-%m-%d')))

        print("✅ Сборка для Windows завершена!")
        print("📁 Исполняемый файл находится в папке: dist/SchoolAnalytics/")
    else:
        print("❌ Ошибка сборки!")


def build_mac():
    """Сборка для MacOS"""
    print("🔧 Начинаю сборку для MacOS...")

    # Специальные параметры для MacOS
    mac_spec = create_spec_file().replace(
        "console=False",
        "console=False\n    bundle_identifier='com.school.analytics'"
    )

    with open('school_analytics_mac.spec', 'w', encoding='utf-8') as f:
        f.write(mac_spec.format(year=datetime.now().year))

    # Запускаем PyInstaller с параметрами для Mac
    os.system('pyinstaller school_analytics_mac.spec --clean --target-arch=universal2')

    # Создаем DMG образ (требуется create-dmg)
    if os.path.exists('dist/SchoolAnalytics.app'):
        os.system(
            'hdiutil create -volname "SchoolAnalytics" -srcfolder "dist/SchoolAnalytics.app" -ov -format UDZO "dist/SchoolAnalytics.dmg"')
        print("✅ Сборка для MacOS завершена!")
        print("📁 Приложение находится в папке: dist/SchoolAnalytics.app")
    else:
        print("❌ Ошибка сборки!")


def create_installer_windows():
    """Создание установщика для Windows (Inno Setup)"""
    iss_content = """
[Setup]
AppName=Школьная аналитика
AppVersion=1.0
AppPublisher=School Analytics
AppPublisherURL=https://example.com
DefaultDirName={pf}\\SchoolAnalytics
DefaultGroupName=Школьная аналитика
UninstallDisplayIcon={app}\\SchoolAnalytics.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename=SchoolAnalytics_Setup

[Files]
Source: "dist\\SchoolAnalytics\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\\Школьная аналитика"; Filename: "{app}\\SchoolAnalytics.exe"
Name: "{group}\\{cm:UninstallProgram,Школьная аналитика}"; Filename: "{uninstallexe}"
Name: "{commondesktop}\\Школьная аналитика"; Filename: "{app}\\SchoolAnalytics.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи:"

[Run]
Filename: "{app}\\SchoolAnalytics.exe"; Description: "Запустить программу"; Flags: postinstall nowait skipifsilent
"""

    os.makedirs('installer', exist_ok=True)
    with open('installer/setup.iss', 'w', encoding='utf-8') as f:
        f.write(iss_content)

    print("✅ Файл для Inno Setup создан: installer/setup.iss")
    print("Для создания установщика выполните: iscc installer/setup.iss")


def create_portable_version():
    """Создание портативной версии"""
    import zipfile

    if os.path.exists('dist/SchoolAnalytics'):
        with zipfile.ZipFile('dist/SchoolAnalytics_Portable.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk('dist/SchoolAnalytics'):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, 'dist')
                    zipf.write(file_path, arcname)

        print("✅ Портативная версия создана: dist/SchoolAnalytics_Portable.zip")


def main():
    print("=" * 60)
    print("СБОРЩИК ПРОГРАММЫ ШКОЛЬНАЯ АНАЛИТИКА")
    print("=" * 60)
    print()
    print("Выберите платформу для сборки:")
    print("1. Windows (exe)")
    print("2. Windows (установщик Inno Setup)")
    print("3. MacOS (app)")
    print("4. Все платформы")
    print("5. Только портативная версия")
    print("6. Создать иконку")
    print()

    choice = input("Ваш выбор (1-6): ").strip()

    # Проверка наличия основного файла
    if not os.path.exists('school_analytics.py'):
        print("❌ Ошибка: файл school_analytics.py не найден!")
        return

    # Установка зависимостей
    print("📦 Проверка зависимостей...")
    os.system('pip install pyinstaller pandas numpy matplotlib seaborn openpyxl pillow')

    if choice == '1':
        build_windows()
        create_portable_version()
    elif choice == '2':
        build_windows()
        create_installer_windows()
    elif choice == '3':
        build_mac()
    elif choice == '4':
        build_windows()
        build_mac()
        create_portable_version()
        create_installer_windows()
    elif choice == '5':
        if os.path.exists('dist/SchoolAnalytics'):
            create_portable_version()
        else:
            print("❌ Сначала выполните сборку Windows (пункт 1)")
    elif choice == '6':
        create_icon()
    else:
        print("❌ Неверный выбор!")

    print()
    print("✅ Готово!")


if __name__ == '__main__':
    main()

