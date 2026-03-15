# setup_exe.py
import PyInstaller.__main__
import os
import shutil
import sys


def create_exe():
    """Создание EXE файла с правильной конфигурацией"""

    # Очистка предыдущих сборок
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    print("=" * 60)
    print("🔧 СОЗДАНИЕ EXE ФАЙЛА")
    print("=" * 60)
    print("\n📊 Программа анализа успеваемости")
    print("👨‍💻 Разработчик: Даниил Зуев")
    print("=" * 60)

    # Параметры для PyInstaller
    params = [
        'grade_analyzer.py',
        '--name=GradeAnalyzer',
        '--onefile',
        '--windowed',  # Без консоли
        '--icon=NONE',  # Можно добавить иконку позже
        '--add-data=streamlit;streamlit',  # Для Windows
        '--hidden-import=streamlit',
        '--hidden-import=streamlit.web.cli',
        '--hidden-import=streamlit.runtime.scriptrunner',
        '--hidden-import=streamlit.runtime.caching',
        '--hidden-import=pandas',
        '--hidden-import=plotly',
        '--hidden-import=plotly.express',
        '--hidden-import=plotly.graph_objects',
        '--hidden-import=numpy',
        '--hidden-import=datetime',
        '--hidden-import=re',
        '--collect-all=streamlit',
        '--collect-all=pandas',
        '--collect-all=plotly',
    ]

    # Запуск PyInstaller
    PyInstaller.__main__.run(params)

    print("\n" + "=" * 60)
    print("✅ EXE ФАЙЛ СОЗДАН!")
    print("=" * 60)
    print("\n📁 Расположение: dist/GradeAnalyzer.exe")
    print("\n🚀 Для запуска просто откройте GradeAnalyzer.exe")
    print("=" * 60)


if __name__ == "__main__":
    create_exe()# setup_exe.py
import PyInstaller.__main__
import os
import shutil
import sys

def create_exe():
    """Создание EXE файла с правильной конфигурацией"""

    # Очистка предыдущих сборок
    if os.path.exists('dist'):
        shutil.rmtree('dist')
    if os.path.exists('build'):
        shutil.rmtree('build')

    print("="*60)
    print("🔧 СОЗДАНИЕ EXE ФАЙЛА")
    print("="*60)
    print("\n📊 Программа анализа успеваемости")
    print("👨‍💻 Разработчик: Даниил Зуев")
    print("="*60)

    # Параметры для PyInstaller
    params = [
        'grade_analyzer.py',
        '--name=GradeAnalyzer',
        '--onefile',
        '--windowed',  # Без консоли
        '--icon=NONE',  # Можно добавить иконку позже
        '--add-data=streamlit;streamlit',  # Для Windows
        '--hidden-import=streamlit',
        '--hidden-import=streamlit.web.cli',
        '--hidden-import=streamlit.runtime.scriptrunner',
        '--hidden-import=streamlit.runtime.caching',
        '--hidden-import=pandas',
        '--hidden-import=plotly',
        '--hidden-import=plotly.express',
        '--hidden-import=plotly.graph_objects',
        '--hidden-import=numpy',
        '--hidden-import=datetime',
        '--hidden-import=re',
        '--collect-all=streamlit',
        '--collect-all=pandas',
        '--collect-all=plotly',
    ]

    # Запуск PyInstaller
    PyInstaller.__main__.run(params)

    print("\n" + "="*60)
    print("✅ EXE ФАЙЛ СОЗДАН!")
    print("="*60)
    print("\n📁 Расположение: dist/GradeAnalyzer.exe")
    print("\n🚀 Для запуска просто откройте GradeAnalyzer.exe")
    print("="*60)

if __name__ == "__main__":
    create_exe()