"""
build_windows.py - Сборка программы для Windows
Запуск: python build_windows.py
"""

import os
import sys
import subprocess
import shutil
import platform
from datetime import datetime


class WindowsBuilder:
    def __init__(self):
        self.app_name = "SchoolAnalytics"
        self.version = "1.0.0"
        self.main_script = "school_analytics.py"

    def print_header(self):
        """Вывод заголовка"""
        print("=" * 60)
        print(f"СБОРКА ДЛЯ WINDOWS: {self.app_name} v{self.version}")
        print("=" * 60)
        print()

    def check_files(self):
        """Проверка наличия необходимых файлов"""
        print("📁 Проверка файлов...")

        # Проверка основного скрипта
        if not os.path.exists(self.main_script):
            print(f"❌ Ошибка: файл {self.main_script} не найден!")
            print("   Убедитесь, что вы находитесь в папке с программой")
            return False

        # Создание README если нет
        if not os.path.exists('README.txt'):
            self.create_readme()
            print("  ✅ Создан файл README.txt")

        # Проверка иконки
        if os.path.exists('icon.ico'):
            print("  ✅ Найдена иконка icon.ico")
        else:
            print("  ⚠️ Иконка не найдена, будет использована стандартная")
            # Создаем простую иконку
            self.create_default_icon()

        print("✅ Все файлы проверены")
        return True

    def create_readme(self):
        """Создание файла README.txt"""
        readme_content = f"""ШКОЛЬНАЯ АНАЛИТИКА v{self.version}
==========================

Программа для анализа успеваемости учеников и результатов ВПР.

УСТАНОВКА:
----------
Просто запустите файл SchoolAnalytics.exe

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

СИСТЕМНЫЕ ТРЕБОВАНИЯ:
--------------------
- Windows 7/8/10/11 (64-bit)
- 100 MB свободного места
- 2 GB RAM

© {datetime.now().year} Школьная аналитика
"""
        with open('README.txt', 'w', encoding='utf-8') as f:
            f.write(readme_content)

    def create_default_icon(self):
        """Создание простой иконки по умолчанию"""
        try:
            from PIL import Image, ImageDraw

            # Создаем изображение 256x256
            img = Image.new('RGBA', (256, 256), color=(41, 128, 185, 255))
            draw = ImageDraw.Draw(img)

            # Рисуем белую букву "Ш"
            try:
                # Пробуем использовать шрифт
                from PIL import ImageFont
                try:
                    font = ImageFont.truetype("arial.ttf", 180)
                except:
                    font = ImageFont.load_default()

                # Получаем размеры текста
                bbox = draw.textbbox((0, 0), "Ш", font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                # Центрируем
                x = (256 - text_width) // 2
                y = (256 - text_height) // 2 - 10

                draw.text((x, y), "Ш", fill=(255, 255, 255, 255), font=font)
            except:
                # Если не получается с текстом, рисуем простую фигуру
                draw.rectangle([50, 50, 206, 206], fill=(255, 255, 255, 255))
                draw.ellipse([103, 103, 153, 153], fill=(41, 128, 185, 255))

            # Сохраняем как ICO
            img.save('icon.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
            print("  ✅ Создана иконка по умолчанию: icon.ico")

        except ImportError:
            print("  ⚠️ Не удалось создать иконку (установите pillow: pip install pillow)")
        except Exception as e:
            print(f"  ⚠️ Ошибка создания иконки: {e}")

    def check_dependencies(self):
        """Проверка зависимостей"""
        print("\n📦 Проверка зависимостей...")

        required_packages = ['pyinstaller', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'openpyxl', 'pillow']
        missing = []

        for package in required_packages:
            try:
                __import__(package)
                print(f"  ✅ {package}")
            except ImportError:
                missing.append(package)
                print(f"  ❌ {package}")

        if missing:
            print("\n⚠️ Отсутствуют зависимости. Установить? (y/n)")
            answer = input().lower()
            if answer == 'y':
                for package in missing:
                    print(f"  Установка {package}...")
                    subprocess.run([sys.executable, '-m', 'pip', 'install', package], check=True)
                print("✅ Зависимости установлены")
            else:
                print("❌ Продолжение без установки зависимостей может привести к ошибкам")
                return False

        return True

    def build_exe(self):
        """Сборка EXE файла"""
        print("\n🔧 Запуск сборки EXE...")

        # Очистка предыдущих сборок
        if os.path.exists('build'):
            shutil.rmtree('build')
        if os.path.exists('dist'):
            shutil.rmtree('dist')

        # Подготовка параметров сборки
        cmd = [
            'pyinstaller',
            '--name', self.app_name,
            '--windowed',  # Без консоли
            '--onefile',  # Один файл
            '--icon', 'icon.ico' if os.path.exists('icon.ico') else '',
            '--add-data', f'README.txt;.' if os.path.exists('README.txt') else '',
            '--hidden-import', 'pandas',
            '--hidden-import', 'numpy',
            '--hidden-import', 'matplotlib',
            '--hidden-import', 'seaborn',
            '--hidden-import', 'openpyxl',
            '--hidden-import', 'tkinter',
            '--hidden-import', 'PIL',
            '--hidden-import', 'PIL._tkinter_finder',
            '--collect-all', 'matplotlib',
            '--collect-all', 'pandas',
            '--collect-all', 'numpy',
            '--collect-all', 'seaborn',
            '--clean',
            '--log-level', 'WARN',
            self.main_script
        ]

        # Убираем пустые аргументы
        cmd = [arg for arg in cmd if arg]

        print("\n🛠️  Команда сборки:")
        print(' '.join(cmd))
        print("\n⏳ Это может занять несколько минут...")
        print()

        try:
            # Запускаем процесс с выводом в реальном времени
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            # Выводим результат построчно
            for line in process.stdout:
                line = line.strip()
                if line:
                    if 'INFO' in line:
                        print(f"  ℹ️ {line}")
                    elif 'WARNING' in line:
                        print(f"  ⚠️ {line}")
                    elif 'ERROR' in line:
                        print(f"  ❌ {line}")
                    else:
                        print(f"  {line}")

            process.wait()

            if process.returncode == 0:
                print("\n✅ Сборка EXE завершена успешно!")
                return True
            else:
                print("\n❌ Ошибка при сборке EXE")
                return False

        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            return False

    def create_portable_version(self):
        """Создание портативной версии (ZIP)"""
        print("\n📦 Создание портативной версии...")

        exe_path = os.path.join('dist', f'{self.app_name}.exe')
        if not os.path.exists(exe_path):
            print("  ❌ EXE файл не найден")
            return False

        import zipfile

        zip_name = f'dist/{self.app_name}_v{self.version}_portable.zip'

        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Добавляем EXE
            zipf.write(exe_path, f'{self.app_name}.exe')

            # Добавляем README
            if os.path.exists('README.txt'):
                zipf.write('README.txt', 'README.txt')

            # Добавляем иконку (опционально)
            if os.path.exists('icon.ico'):
                zipf.write('icon.ico', 'icon.ico')

        print(f"  ✅ Портативная версия создана: {zip_name}")
        return True

    def create_installer(self):
        """Создание установщика с помощью Inno Setup"""
        print("\n📀 Создание установщика...")

        # Проверка наличия Inno Setup
        iscc_path = None
        possible_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\iscc.exe",
            r"C:\Program Files\Inno Setup 6\iscc.exe",
            r"C:\Program Files (x86)\Inno Setup 5\iscc.exe",
            r"C:\Program Files\Inno Setup 5\iscc.exe",
        ]

        for path in possible_paths:
            if os.path.exists(path):
                iscc_path = path
                break

        if not iscc_path:
            print("  ⚠️ Inno Setup не найден. Установщик не будет создан.")
            print("  Скачайте Inno Setup: https://jrsoftware.org/isdl.php")
            return False

        exe_path = os.path.join('dist', f'{self.app_name}.exe')
        if not os.path.exists(exe_path):
            print("  ❌ EXE файл не найден")
            return False

        # Создание скрипта для Inno Setup
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
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

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

        # Создаем папку для установщика
        os.makedirs('installer', exist_ok=True)

        # Сохраняем скрипт
        iss_path = os.path.join('installer', 'setup.iss')
        with open(iss_path, 'w', encoding='utf-8') as f:
            f.write(iss_content)

        # Запускаем Inno Setup
        try:
            subprocess.run([iscc_path, iss_path], check=True)
            print("  ✅ Установщик создан в папке installer/")
            return True
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Ошибка создания установщика: {e}")
            return False

    def show_results(self):
        """Отображение результатов сборки"""
        print("\n" + "=" * 60)
        print("📊 РЕЗУЛЬТАТЫ СБОРКИ")
        print("=" * 60)

        # Проверяем созданные файлы
        dist_files = []
        if os.path.exists('dist'):
            for file in os.listdir('dist'):
                file_path = os.path.join('dist', file)
                if os.path.isfile(file_path):
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    dist_files.append((file, size_mb))

        if dist_files:
            print("\n📁 Папка dist/:")
            for file, size in sorted(dist_files):
                print(f"  • {file} - {size:.2f} MB")

        # Проверяем установщик
        if os.path.exists('installer'):
            print("\n📁 Папка installer/:")
            for file in os.listdir('installer'):
                if file.endswith('.exe'):
                    file_path = os.path.join('installer', file)
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    print(f"  • {file} - {size_mb:.2f} MB")

        print("\n" + "=" * 60)
        print("✅ СБОРКА ЗАВЕРШЕНА!")
        print("=" * 60)

    def clean(self):
        """Очистка временных файлов"""
        print("\n🧹 Очистка временных файлов...")

        dirs_to_remove = ['build', '__pycache__']
        files_to_remove = ['*.spec']

        # Удаление папок
        for dir_name in dirs_to_remove:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
                print(f"  Удалена папка: {dir_name}")

        # Удаление spec файлов
        import glob
        for pattern in files_to_remove:
            for file in glob.glob(pattern):
                os.remove(file)
                print(f"  Удален файл: {file}")

        print("✅ Очистка завершена")

    def run(self):
        """Запуск сборки"""
        self.print_header()

        # Проверка ОС
        if platform.system() != 'Windows':
            print("⚠️ ВНИМАНИЕ: Этот скрипт предназначен для Windows!")
            print(f"   Текущая ОС: {platform.system()}")
            print("   Продолжение может привести к ошибкам.")
            response = input("   Продолжить? (y/n): ").lower()
            if response != 'y':
                print("❌ Сборка отменена")
                return

        # Проверка файлов
        if not self.check_files():
            return

        # Проверка зависимостей
        if not self.check_dependencies():
            return

        # Очистка перед сборкой
        self.clean()

        # Сборка EXE
        if not self.build_exe():
            return

        # Создание портативной версии
        self.create_portable_version()

        # Создание установщика
        self.create_installer()

        # Показ результатов
        self.show_results()

        print("\n🚀 Программа готова к распространению!")


def main():
    # Создаем экземпляр сборщика и запускаем
    builder = WindowsBuilder()

    try:
        builder.run()
    except KeyboardInterrupt:
        print("\n\n⚠️ Сборка прервана пользователем")
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}")
        import traceback
        traceback.print_exc()

    input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    main()