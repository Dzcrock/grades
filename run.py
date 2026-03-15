# run.py
import subprocess
import sys
import os


def main():
    """Запуск Streamlit приложения"""
    script_path = os.path.join(os.path.dirname(__file__), "NEW2.py")

    print("=" * 60)
    print("🚀 ЗАПУСК ПРИЛОЖЕНИЯ ДЛЯ АНАЛИЗА УСПЕВАЕМОСТИ")
    print("=" * 60)
    print("\n📊 Разработчик: Даниил Зуев")
    print("📅 Версия: 2.0.0")
    print("=" * 60)

    try:
        # Запускаем streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", script_path])
    except KeyboardInterrupt:
        print("\n👋 Программа завершена")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        print("\nУбедитесь, что streamlit установлен:")
        print("pip install streamlit pandas numpy plotly openpyxl")


if __name__ == "__main__":
    main()