#!/usr/bin/env python3
"""
build_all.py - Автоматическая сборка программы под все платформы
Запуск: python build_all.py
"""

# !/usr/bin/env python3
"""
build_all.py - Автоматическая сборка программы под все платформы
Запуск: python build_all.py
"""

import os
import sys
import platform
import subprocess
import shutil
from datetime import datetime


class ApplicationBuilder:
    def __init__(self):
        self.app_name = "SchoolAnalytics"
        self.version = "1.0.0"
        self.main_script = "school_analytics.py"

    def check_requirements(self):
        """Проверка наличия необходимых инструментов"""
        print("🔍 Проверка инструментов сборки...")

        requirements = {
            'pyinstaller': 'pyinstaller',
        }

        if platform.system() == 'Windows':
            requirements['iscc'] = 'Inno Setup Compiler'

        missing = []
        for cmd, name in requirements.items():
            if not shutil.which(cmd):
                missing.append(name)

        if missing:
            print(f"❌ Отсутствуют: {', '.join(missing)}")
            print("Установите недостающие компоненты:")
            print("  pip install pyinstaller")
            if 'Inno Setup Compiler' in missing:
                print("  Скачайте Inno Setup: https://jrsoftware.org/isdl.php")
            return False

        print("✅ Все инструменты найдены")
        return True

    def prepare_environment(self):
        """Подготовка окружения для сборки"""
        print("📁 Подготовка окружения...")

        # Создание необходимых папок
        os.makedirs('build_temp', exist_ok=True)
        os.makedirs('dist', exist_ok=True)

        # Копирование основного файла
        if not os.path.exists(self.main_script):
            print(f"❌ Файл {self.main_script} не найден!")
            return False

        # Создание файла README если его нет
        if not os.path.exists('README.txt'):
            self.create_readme()

        print("✅ Окружение готово")
        return True

    def create_readme(self):
        """Создание файла README.txt"""
        readme_content = f"""ШКОЛЬНАЯ АНАЛИТИКА v{self.version}
==========================

Программа для анализа успеваемости учеников и результатов ВПР.

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

© {datetime.now().year} Школьная аналитика
Версия: {self.version}
"""
        with open('README.txt', 'w', encoding='utf-8') as f:
            f.write(readme_content)

    def build_windows(self):
        """Сборка для Windows"""
        print("\n🔧 Сборка для Windows...")

        # Проверяем наличие иконки
        icon_param = []
        if os.path.exists('icon.ico'):
            icon_param = ['--icon', 'icon.ico']

        # Параметры для Windows (используем правильный формат --add-data)
        cmd = [
            'pyinstaller',
            '--name', self.app_name,
            '--windowed',
            '--onefile',
            *icon_param,
            '--add-data', f'README.txt{";" if platform.system() == "Windows" else ":"}.',
            '--hidden-import', 'pandas',
            '--hidden-import', 'numpy',
            '--hidden-import', 'matplotlib',
            '--hidden-import', 'seaborn',
            '--hidden-import', 'openpyxl',
            '--hidden-import', 'tkinter',
            '--hidden-import', 'PIL',
            '--collect-all', 'matplotlib',
            '--collect-all', 'pandas',
            '--collect-all', 'numpy',
            '--workpath', 'build_temp',
            '--distpath', 'dist/windows',
            '--clean',
            self.main_script
        ]

        print(f"🛠️  Команда: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ Сборка для Windows завершена")

            # Переименовываем файл
            exe_path = os.path.join('dist/windows', f'{self.app_name}.exe')
            if os.path.exists(exe_path):
                new_name = f'{self.app_name}_v{self.version}_windows.exe'
                new_path = os.path.join('dist', new_name)
                shutil.copy2(exe_path, new_path)
                print(f"📦 Файл сохранен: {new_path}")

            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка сборки Windows:")
            print(e.stderr)
            return False

    def build_macos(self):
        """Сборка для MacOS"""
        print("\n🔧 Сборка для MacOS...")

        if platform.system() != 'Darwin':
            print("⚠️ Сборка для MacOS возможна только на Mac")
            print("   Пропускаем сборку для MacOS")
            return False

        # Проверяем наличие иконки для Mac
        icon_param = []
        if os.path.exists('icon.icns'):
            icon_param = ['--icon', 'icon.icns']
        elif os.path.exists('icon.png'):
            # Конвертируем PNG в ICNS если есть возможность
            self.convert_png_to_icns('icon.png')
            if os.path.exists('icon.icns'):
                icon_param = ['--icon', 'icon.icns']

        cmd = [
            'pyinstaller',
            '--name', self.app_name,
            '--windowed',
            '--onefile',
            *icon_param,
            '--add-data', 'README.txt:.',
            '--hidden-import', 'pandas',
            '--hidden-import', 'numpy',
            '--hidden-import', 'matplotlib',
            '--hidden-import', 'seaborn',
            '--hidden-import', 'openpyxl',
            '--hidden-import', 'tkinter',
            '--hidden-import', 'PIL',
            '--collect-all', 'matplotlib',
            '--collect-all', 'pandas',
            '--collect-all', 'numpy',
            '--target-architecture', 'universal2',
            '--workpath', 'build_temp',
            '--distpath', 'dist/macos',
            '--clean',
            self.main_script
        ]

        print(f"🛠️  Команда: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ Сборка для MacOS завершена")

            # Копируем в основную папку
            app_path = os.path.join('dist/macos', f'{self.app_name}.app')
            if os.path.exists(app_path):
                new_name = f'{self.app_name}_v{self.version}_macos.app'
                new_path = os.path.join('dist', new_name)
                shutil.copytree(app_path, new_path, dirs_exist_ok=True)
                print(f"📦 Файл сохранен: {new_path}")

            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка сборки MacOS:")
            print(e.stderr)
            return False

    def convert_png_to_icns(self, png_path):
        """Конвертация PNG в ICNS для MacOS"""
        try:
            from PIL import Image
            import tempfile
            import subprocess

            # Создаем временную папку для iconset
            iconset_dir = 'icon.iconset'
            os.makedirs(iconset_dir, exist_ok=True)

            # Размеры для MacOS иконок
            sizes = [16, 32, 64, 128, 256, 512, 1024]

            img = Image.open(png_path)

            for size in sizes:
                # Обычная версия
                resized = img.resize((size, size), Image.Resampling.LANCZOS)
                resized.save(os.path.join(iconset_dir, f'icon_{size}x{size}.png'))

                # Retina версия (2x)
                if size * 2 <= 1024:
                    resized_2x = img.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
                    resized_2x.save(os.path.join(iconset_dir, f'icon_{size}x{size}@2x.png'))

            # Конвертируем в icns
            subprocess.run(['iconutil', '-c', 'icns', iconset_dir], check=True)
            shutil.rmtree(iconset_dir)

            print("✅ Иконка для MacOS создана")

        except Exception as e:
            print(f"⚠️ Не удалось создать иконку для MacOS: {e}")

    def build_linux(self):
        """Сборка для Linux"""
        print("\n🔧 Сборка для Linux...")

        if platform.system() != 'Linux':
            print("⚠️ Сборка для Linux возможна только на Linux")
            print("   Пропускаем сборку для Linux")
            return False

        cmd = [
            'pyinstaller',
            '--name', self.app_name,
            '--windowed',
            '--onefile',
            '--add-data', 'README.txt:.',
            '--hidden-import', 'pandas',
            '--hidden-import', 'numpy',
            '--hidden-import', 'matplotlib',
            '--hidden-import', 'seaborn',
            '--hidden-import', 'openpyxl',
            '--hidden-import', 'tkinter',
            '--hidden-import', 'PIL',
            '--collect-all', 'matplotlib',
            '--collect-all', 'pandas',
            '--collect-all', 'numpy',
            '--workpath', 'build_temp',
            '--distpath', 'dist/linux',
            '--clean',
            self.main_script
        ]

        # Добавляем иконку если есть
        if os.path.exists('icon.png'):
            cmd.extend(['--icon', 'icon.png'])

        print(f"🛠️  Команда: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("✅ Сборка для Linux завершена")

            # Копируем в основную папку
            binary_path = os.path.join('dist/linux', self.app_name)
            if os.path.exists(binary_path):
                new_name = f'{self.app_name}_v{self.version}_linux'
                new_path = os.path.join('dist', new_name)
                shutil.copy2(binary_path, new_path)
                print(f"📦 Файл сохранен: {new_path}")

            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка сборки Linux:")
            print(e.stderr)
            return False

    def create_portable_version(self):
        """Создание портативной версии"""
        print("\n📦 Создание портативных версий...")

        import zipfile
        import tarfile

        # Windows portable
        windows_exe = os.path.join('dist', f'{self.app_name}_v{self.version}_windows.exe')
        if os.path.exists(windows_exe):
            with zipfile.ZipFile(f'dist/{self.app_name}_v{self.version}_windows_portable.zip', 'w',
                                 zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(windows_exe, os.path.basename(windows_exe))
                if os.path.exists('README.txt'):
                    zipf.write('README.txt', 'README.txt')
            print("  ✅ Windows portable создан")

        # MacOS portable (если есть)
        mac_app = os.path.join('dist', f'{self.app_name}_v{self.version}_macos.app')
        if os.path.exists(mac_app):
            with tarfile.open(f'dist/{self.app_name}_v{self.version}_macos_portable.tar.gz', 'w:gz') as tar:
                tar.add(mac_app, arcname=os.path.basename(mac_app))
            print("  ✅ MacOS portable создан")

        # Linux portable
        linux_bin = os.path.join('dist', f'{self.app_name}_v{self.version}_linux')
        if os.path.exists(linux_bin):
            with tarfile.open(f'dist/{self.app_name}_v{self.version}_linux_portable.tar.gz', 'w:gz') as tar:
                tar.add(linux_bin, arcname=os.path.basename(linux_bin))
                if os.path.exists('README.txt'):
                    tar.add('README.txt', 'README.txt')
            print("  ✅ Linux portable создан")

    def create_installer_windows(self):
        """Создание установщика для Windows"""
        print("\n📀 Создание установщика для Windows...")

        if not shutil.which('iscc'):
            print("⚠️ Inno Setup не найден, пропускаем создание установщика")
            return

        exe_path = os.path.join('dist', f'{self.app_name}_v{self.version}_windows.exe')
        if not os.path.exists(exe_path):
            print("⚠️ EXE файл не найден, пропускаем создание установщика")
            return

        # Создаем скрипт для Inno Setup
        iss_content = f"""
[Setup]
AppName=Школьная аналитика
AppVersion={self.version}
AppPublisher=School Analytics
AppPublisherURL=https://example.com
AppSupportURL=https://example.com
AppUpdatesURL=https://example.com
DefaultDirName={{pf}}\\SchoolAnalytics
DefaultGroupName=Школьная аналитика
UninstallDisplayIcon={{app}}\\SchoolAnalytics.exe
Compression=lzma2
SolidCompression=yes
OutputDir=installer
OutputBaseFilename=SchoolAnalytics_Setup_v{self.version}
SetupIconFile=icon.ico
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Files]
Source: "{exe_path}"; DestDir: "{{app}}"; DestName: "SchoolAnalytics.exe"
Source: "README.txt"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\Школьная аналитика"; Filename: "{{app}}\\SchoolAnalytics.exe"
Name: "{{group}}\\{{cm:UninstallProgram,Школьная аналитика}}"; Filename: "{{uninstallexe}}"
Name: "{{commondesktop}}\\Школьная аналитика"; Filename: "{{app}}\\SchoolAnalytics.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительные задачи:"

[Run]
Filename: "{{app}}\\SchoolAnalytics.exe"; Description: "Запустить программу"; Flags: postinstall nowait skipifsilent
"""

        os.makedirs('installer', exist_ok=True)
        iss_path = 'installer/setup.iss'

        with open(iss_path, 'w', encoding='utf-8') as f:
            f.write(iss_content)

        try:
            subprocess.run(['iscc', iss_path], check=True)
            print("  ✅ Установщик для Windows создан")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Ошибка создания установщика: {e}")

    def build_current_platform(self):
        """Сборка для текущей платформы"""
        system = platform.system()

        if system == 'Windows':
            return self.build_windows()
        elif system == 'Darwin':
            return self.build_macos()
        elif system == 'Linux':
            return self.build_linux()
        else:
            print(f"❌ Неподдерживаемая платформа: {system}")
            return False

    def build_all(self):
        """Запуск полной сборки"""
        print("=" * 60)
        print(f"🚀 СБОРКА {self.app_name} v{self.version}")
        print("=" * 60)
        print()
        print(f"Платформа: {platform.system()} {platform.release()}")
        print(f"Python: {sys.version}")
        print()

        if not self.check_requirements():
            return

        if not self.prepare_environment():
            return

        # Сборка для текущей платформы
        success = self.build_current_platform()

        if success:
            # Создание портативных версий
            self.create_portable_version()

            # Создание установщика для Windows (только на Windows)
            if platform.system() == 'Windows':
                self.create_installer_windows()

        # Очистка временных файлов
        if os.path.exists('build_temp'):
            shutil.rmtree('build_temp')

        print("\n" + "=" * 60)
        if success:
            print("✅ СБОРКА ЗАВЕРШЕНА УСПЕШНО!")
            print("📁 Результаты в папке: dist/")
        else:
            print("❌ СБОРКА ЗАВЕРШЕНА С ОШИБКАМИ")
        print("=" * 60)

        # Показываем размеры файлов
        self.show_file_sizes()

    def show_file_sizes(self):
        """Показ размеров собранных файлов"""
        print("\n📊 Размеры файлов:")

        if os.path.exists('dist'):
            for file in os.listdir('dist'):
                file_path = os.path.join('dist', file)
                if os.path.isfile(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"  • {file}: {size_mb:.2f} MB")


def create_icons():
    """Создание иконок для разных платформ"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        print("🎨 Создание иконок...")

        # Создаем изображение 512x512
        img = Image.new('RGBA', (512, 512), color=(41, 128, 185, 255))
        draw = ImageDraw.Draw(img)

        # Рисуем букву "Ш"
        try:
            # Пробуем загрузить шрифт
            font_size = 300
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                font = ImageFont.load_default()

            # Получаем размеры текста
            bbox = draw.textbbox((0, 0), "Ш", font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # Центрируем
            x = (512 - text_width) // 2
            y = (512 - text_height) // 2 - 20

            draw.text((x, y), "Ш", fill=(255, 255, 255, 255), font=font)

        except:
            # Если не получается с текстом, рисуем простую иконку
            draw.rectangle([100, 100, 412, 412], fill=(255, 255, 255, 255))
            draw.ellipse([206, 206, 306, 306], fill=(41, 128, 185, 255))

        # Сохраняем PNG
        img.save('icon.png')

        # Создаем ICO для Windows
        img.save('icon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

        print("✅ Иконки созданы: icon.png, icon.ico")

    except ImportError:
        print("❌ Для создания иконок установите PIL: pip install pillow")
    except Exception as e:
        print(f"❌ Ошибка создания иконок: {e}")


def main():
    print("=" * 60)
    print("СБОРЩИК ПРОГРАММЫ ШКОЛЬНАЯ АНАЛИТИКА")
    print("=" * 60)
    print()
    print("Выберите действие:")
    print("1. Собрать для текущей платформы")
    print("2. Создать иконки")
    print("3. Очистить временные файлы")
    print()

    choice = input("Ваш выбор (1-3): ").strip()

    if choice == '1':
        builder = ApplicationBuilder()
        builder.build_all()
    elif choice == '2':
        create_icons()
    elif choice == '3':
        print("🧹 Очистка...")
        dirs_to_remove = ['build', 'build_temp', 'dist', '__pycache__']
        for dir_name in dirs_to_remove:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
                print(f"  Удалено: {dir_name}")
        print("✅ Очистка завершена")
    else:
        print("❌ Неверный выбор!")


if __name__ == '__main__':
    main()