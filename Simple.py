import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter import scrolledtext
import seaborn as sns
from datetime import datetime
import os
import warnings
import re
import pickle
import json

warnings.filterwarnings('ignore', category=DeprecationWarning)


class UniversalParser:
    """Универсальный парсер для любых форматов школьных журналов"""

    @staticmethod
    def parse_file(df, log_func=None):
        """Парсинг файла любой структуры"""
        students = []

        def log(msg):
            if log_func:
                log_func(msg)

        log("🔍 Начинаю универсальный парсинг...")

        # Определяем все возможные колонки с ФИО
        name_columns = UniversalParser.find_name_columns(df)
        log(f"   Найдено потенциальных колонок с ФИО: {name_columns}")

        # Ищем все классы в файле
        classes = UniversalParser.find_classes(df)
        log(f"   Найдено классов: {len(classes)}")

        # Для каждого класса обрабатываем учеников
        for class_name, class_range in classes.items():
            log(f"   Обрабатываю класс {class_name} (строки {class_range['start']}-{class_range['end']})")

            # Получаем данные только для этого класса
            class_df = df.iloc[class_range['start']:class_range['end'] + 1]

            # Находим колонку с ФИО в этом классе
            name_col = UniversalParser.find_name_column_in_range(class_df)

            if name_col:
                # Обрабатываем учеников класса
                class_students = UniversalParser.process_class(
                    class_df, name_col, class_name, log
                )
                students.extend(class_students)
                log(f"      Найдено учеников: {len(class_students)}")

        return students

    @staticmethod
    def find_name_columns(df):
        """Поиск всех колонок, которые могут содержать ФИО"""
        name_columns = []

        for col in df.columns:
            # Проверяем первые 10 строк в колонке
            sample = df[col].head(10).astype(str).tolist()

            # Считаем, сколько строк похожи на ФИО
            name_count = 0
            for val in sample:
                if UniversalParser.looks_like_name(val):
                    name_count += 1

            # Если больше 30% строк похожи на ФИО
            if name_count >= 3:
                name_columns.append(col)

        return name_columns

    @staticmethod
    def find_name_column_in_range(df):
        """Поиск колонки с ФИО в указанном диапазоне"""
        best_col = None
        best_score = 0

        for col in df.columns:
            score = 0
            sample = df[col].head(20).astype(str).tolist()

            for val in sample:
                if UniversalParser.looks_like_name(val):
                    score += 1
                elif UniversalParser.is_number(val):
                    score -= 0.5  # Штраф за числа

            if score > best_score:
                best_score = score
                best_col = col

        return best_col if best_score > 3 else None

    @staticmethod
    def find_classes(df):
        """Поиск всех классов в файле"""
        classes = {}
        current_class = None
        start_row = None

        for idx, row in df.iterrows():
            # Проверяем все колонки на наличие класса
            class_name = None
            for col in df.columns[:5]:  # Проверяем первые 5 колонок
                val = str(row[col]) if pd.notna(row[col]) else ""
                found = UniversalParser.extract_class(val)
                if found:
                    class_name = found
                    break

            if class_name:
                # Если нашли новый класс
                if current_class and start_row is not None:
                    classes[current_class] = {
                        'start': start_row,
                        'end': idx - 1
                    }

                current_class = class_name
                start_row = idx + 1

        # Добавляем последний класс
        if current_class and start_row is not None:
            classes[current_class] = {
                'start': start_row,
                'end': len(df) - 1
            }

        return classes

    @staticmethod
    def extract_class(text):
        """Извлечение названия класса из текста"""
        if not isinstance(text, str):
            return None

        text = text.strip()

        # Паттерны для классов: 5А, 5-А, 5 А, 5а класс и т.д.
        patterns = [
            r'(\d+)\s*[-\s]?\s*([А-Я])',  # 5А, 5-А, 5 А
            r'(\d+)\s*класс',  # 5 класс
            r'класс\s*(\d+)\s*([А-Я])?',  # класс 5 А
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                if len(groups) == 2 and groups[1]:
                    return f"{groups[0]}{groups[1].upper()}"
                elif groups[0]:
                    return groups[0]

        return None

    @staticmethod
    def looks_like_name(text):
        """Проверка, похоже ли текст на ФИО"""
        if not isinstance(text, str):
            return False

        text = text.strip()

        # Слишком короткие строки
        if len(text) < 5 or len(text) > 50:
            return False

        # Игнорируем служебные слова
        skip_words = ['класс', 'итого', 'средний', 'учитель', 'директор',
                      'заместитель', 'копия', 'дата', 'тема', 'обучающийся',
                      'биология', 'география', 'химия', 'физика', 'история',
                      'мониторинг', 'проверочная', 'контрольная', 'домашнее',
                      'аттестация', 'ведомость', 'муниципальное', 'автономное',
                      'гимназия', 'директор', 'учебный', 'год', 'класс',
                      'алгебра', 'геометрия', 'русский', 'литература',
                      'английский', 'информатика', 'обществознание']

        text_lower = text.lower()
        for word in skip_words:
            if word in text_lower:
                return False

        # Проверка на наличие пробелов (ФИО обычно содержит пробелы)
        if ' ' not in text:
            return False

        # Проверка на наличие букв
        if not any(c.isalpha() for c in text):
            return False

        # Проверка на наличие кириллицы (русские буквы)
        if not re.search('[а-яА-Я]', text):
            return False

        # Разбиваем на слова
        words = text.split()

        # Должно быть минимум 2 слова (фамилия и имя)
        if len(words) < 2:
            return False

        # Проверка, что слова выглядят как части ФИО
        valid_words = 0
        for word in words:
            # Слово должно содержать буквы и быть разумной длины
            if len(word) >= 2 and any(c.isalpha() for c in word):
                valid_words += 1

        return valid_words >= 2

    @staticmethod
    def is_number(text):
        """Проверка, является ли текст числом"""
        if not isinstance(text, str):
            return False

        text = text.strip()
        try:
            float(text)
            return True
        except:
            return False

    @staticmethod
    def process_class(df, name_col, class_name, log):
        """Обработка одного класса"""
        students = []

        for idx, row in df.iterrows():
            # Получаем ФИО
            name_val = row[name_col] if pd.notna(row[name_col]) else ""
            name = str(name_val).strip()

            # Проверяем, похоже ли на ФИО
            if not UniversalParser.looks_like_name(name):
                continue

            # Собираем оценки
            grades = []

            # Проходим по всем колонкам, кроме колонки с ФИО
            for col in df.columns:
                if col == name_col:
                    continue

                val = row[col]

                # Пытаемся извлечь оценку
                grade = UniversalParser.extract_grade(val)
                if grade is not None:
                    grades.append(grade)
                else:
                    # Если не оценка и не пусто - возможно это конец данных
                    if UniversalParser.is_metadata(val):
                        break
                    grades.append(None)

            # Если есть хотя бы одна оценка
            valid_grades = [g for g in grades if g not in [None, "н"]]
            if valid_grades:
                # Создаем ученика
                student = Student(name, grades, class_name)
                students.append(student)

        return students

    @staticmethod
    def extract_grade(val):
        """Извлечение оценки из значения"""
        if pd.isna(val):
            return None

        # Если это число
        if isinstance(val, (int, float)):
            if 1 <= val <= 5:
                return val
            elif 1 <= val <= 100:  # Баллы
                return val
            return None

        # Если это строка
        if isinstance(val, str):
            val_str = val.strip()

            # Пропуск
            if val_str.lower() in ['н', '-', '—', 'б', 'н/а']:
                return "н"

            # Пустая строка
            if not val_str:
                return None

            # Пытаемся преобразовать в число
            try:
                num_val = float(val_str.replace(',', '.'))
                if 1 <= num_val <= 5 or 1 <= num_val <= 100:
                    return num_val
            except:
                pass

        return None

    @staticmethod
    def is_metadata(val):
        """Проверка на метаданные"""
        if pd.isna(val):
            return False

        if isinstance(val, str):
            val_str = val.lower().strip()

            # Ключевые слова метаданных
            metadata_words = [
                'дата', 'тема', 'урок', 'задание', 'домашнее',
                'параграф', 'практическая', 'контрольная', 'проверочная',
                'повторяем', 'готовимся', 'читаем', 'выполняем',
                'презентация', 'тетрадь', 'учебник', 'страница'
            ]

            # Проверка на дату
            if re.match(r'^\d{1,2}[./-]\d{1,2}', val_str):
                return True

            # Проверка на ключевые слова
            for word in metadata_words:
                if word in val_str:
                    return True

            # Длинный текст (больше 20 символов) - скорее всего метаданные
            if len(val_str) > 20 and any(c.isalpha() for c in val_str):
                return True

        return False


class JournalParser:
    """Упрощенный парсер для электронных журналов"""

    @staticmethod
    def parse_journal(df, log_func=None):
        """Очень простой парсинг журнала с учетом номера в первой колонке"""
        students = []
        current_class = None

        def log(msg):
            if log_func:
                log_func(msg)

        log("🔍 Начинаю упрощенный парсинг...")

        # Определяем, где находятся ФИО (может быть в первой или второй колонке)
        first_col = df.columns[0]
        second_col = df.columns[1] if len(df.columns) > 1 else None

        # Проверяем, содержит ли первая колонка номера
        first_col_sample = df[first_col].head(10).astype(str).tolist()
        has_numbers = all(val.strip().isdigit() for val in first_col_sample if val.strip())

        if has_numbers and second_col:
            log(f"   В первой колонке обнаружены номера, используем вторую колонку для ФИО")
            name_col = second_col
        else:
            log(f"   Используем первую колонку для ФИО")
            name_col = first_col

        # Ищем класс в любом месте
        for idx, row in df.iterrows():
            row_str = ' '.join([str(x) for x in row if pd.notna(x)])
            if '5А' in row_str:
                current_class = '5А'
                log(f"   Найден класс: {current_class}")
                break

        # Проходим по всем строкам
        for idx, row in df.iterrows():
            # Получаем ФИО из нужной колонки
            name_val = row[name_col] if pd.notna(row[name_col]) else ""
            name = str(name_val).strip()

            # Пропускаем пустые строки
            if not name or name.lower() in ['nan', 'none', '']:
                continue

            # Пропускаем слишком короткие строки
            if len(name) < 5:
                continue

            # Пропускаем строки с ключевыми словами
            skip_words = ['класс', 'итого', 'средний', 'учитель', 'директор',
                          'заместитель', 'копия', 'дата', 'тема', 'обучающийся',
                          'сен', 'окт', 'ноя', 'дек', 'янв', 'фев', 'мар',
                          'география', 'группа', 'резервный', 'урок', 'домашнее']

            skip = False
            name_lower = name.lower()
            for word in skip_words:
                if word in name_lower:
                    skip = True
                    break

            if skip:
                continue

            # Проверяем, что это похоже на ФИО (есть пробелы и буквы)
            if ' ' in name and any(c.isalpha() for c in name):
                # Собираем оценки
                grades = []

                # Проходим по всем колонкам, начиная с той, где могут быть оценки
                start_col_idx = df.columns.get_loc(name_col) + 1

                for col_idx in range(start_col_idx, min(start_col_idx + 30, len(df.columns))):
                    col = df.columns[col_idx]
                    val = row[col]

                    # Пытаемся получить оценку
                    grade = JournalParser.get_simple_grade(val)

                    # Если получили None и это не первая колонка с оценками,
                    # и мы уже собрали несколько оценок - возможно, это конец
                    if grade is None and len(grades) > 5:
                        # Проверяем, не является ли значение датой или текстом
                        if JournalParser.is_text_stop_value(val):
                            break
                        else:
                            grades.append(None)
                    else:
                        grades.append(grade)

                # Если есть хотя бы одна оценка
                valid_grades = [g for g in grades if g not in [None, "н"]]
                if valid_grades:
                    student = Student(name, grades, current_class)
                    students.append(student)
                    log(f"   ✅ {name}: {len(valid_grades)} оценок")

        log(f"   Всего найдено учеников: {len(students)}")
        return students

    @staticmethod
    def get_simple_grade(val):
        """Очень простое получение оценки"""
        if pd.isna(val):
            return None

        # Если это число
        if isinstance(val, (int, float)):
            if 1 <= val <= 5:
                return val
            return None

        # Если это строка
        if isinstance(val, str):
            val_str = val.strip()

            # Пропуск
            if val_str.lower() == 'н':
                return "н"

            # Пустая строка
            if not val_str or val_str == '':
                return None

            # Пытаемся преобразовать в число
            try:
                num_val = int(val_str)
                if 1 <= num_val <= 5:
                    return num_val
            except:
                pass

        return None

    @staticmethod
    def is_text_stop_value(val):
        """Проверка, является ли значение признаком конца оценок"""
        if pd.isna(val):
            return False

        if isinstance(val, str):
            val_str = val.strip().lower()

            # Проверка на дату
            if re.match(r'^\d{1,2}[./-]\d{1,2}', val_str):
                return True

            # Проверка на тему урока
            text_words = ['тема', 'урок', 'задание', 'домашнее', 'параграф',
                          'практическая', 'контрольная', 'повторяем', 'готовимся']

            if any(word in val_str for word in text_words):
                return True

            # Если строка длинная (больше 5 символов) и содержит буквы
            if len(val_str) > 5 and any(c.isalpha() for c in val_str):
                return True

        return False

class GradeModeDialog:
    """Диалог для выбора режима оценок"""
    def __init__(self, parent):
        self.parent = parent
        self.result = None

    def show(self):
        """Отображение диалога"""
        dialog = tk.Toplevel(self.parent.root)
        dialog.title("Выберите режим оценивания")
        dialog.geometry("450x350")
        dialog.transient(self.parent.root)
        dialog.grab_set()

        # Центрируем окно
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        # Заголовок
        title_frame = ttk.Frame(dialog, padding="15")
        title_frame.pack(fill=tk.X)

        ttk.Label(title_frame, text="Выберите тип данных в файле",
                  style='Title.TLabel').pack()

        # Основное содержание
        content_frame = ttk.Frame(dialog, padding="15")
        content_frame.pack(fill=tk.BOTH, expand=True)

        self.mode_var = tk.StringVar(value="auto")

        # Автоматическое определение
        auto_frame = ttk.LabelFrame(content_frame, text="🤖 Автоматически", padding="10")
        auto_frame.pack(fill=tk.X, pady=5)

        auto_rb = ttk.Radiobutton(auto_frame, variable=self.mode_var, value="auto")
        auto_rb.pack(side=tk.LEFT)
        ttk.Label(auto_frame, text="Автоматическое определение (рекомендуется)",
                  font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(auto_frame, text="Программа сама определит тип данных",
                  foreground='gray', font=('Arial', 8)).pack(anchor=tk.W, padx=25)

        # Оценки 2-5
        grades_frame = ttk.LabelFrame(content_frame, text="📊 Оценки 2-5", padding="10")
        grades_frame.pack(fill=tk.X, pady=5)

        grades_rb = ttk.Radiobutton(grades_frame, variable=self.mode_var, value="grades")
        grades_rb.pack(side=tk.LEFT)
        ttk.Label(grades_frame, text="Школьные оценки (2, 3, 4, 5)",
                  font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(grades_frame, text="Для оценок за четверти, контрольные",
                  foreground='gray', font=('Arial', 8)).pack(anchor=tk.W, padx=25)

        # Баллы
        points_frame = ttk.LabelFrame(content_frame, text="🎯 Баллы", padding="10")
        points_frame.pack(fill=tk.X, pady=5)

        points_rb = ttk.Radiobutton(points_frame, variable=self.mode_var, value="points")
        points_rb.pack(side=tk.LEFT)
        ttk.Label(points_frame, text="Баллы (например, 0-100)",
                  font=('Arial', 10)).pack(side=tk.LEFT, padx=5)
        ttk.Label(points_frame, text="Для ЕГЭ, ВПР, олимпиад",
                  foreground='gray', font=('Arial', 8)).pack(anchor=tk.W, padx=25)

        # Кнопки
        button_frame = ttk.Frame(dialog, padding="15")
        button_frame.pack(fill=tk.X)

        def on_ok():
            self.result = self.mode_var.get()
            dialog.destroy()

        ttk.Button(button_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side=tk.RIGHT)

        # Подпись автора
        ttk.Label(dialog, text="Daniil Zuev © 2024",
                  font=('Arial', 7), foreground='gray').pack(side=tk.BOTTOM, pady=2)

        self.parent.root.wait_window(dialog)
        return self.result


class DataManager:
    """Класс для управления сохранением и загрузкой данных"""
    def __init__(self):
        self.data_dir = "saved_data"
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Создание директории для сохранения данных"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save_students(self, students, filename=None):
        """Сохранение данных учеников"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"students_data_{timestamp}.pkl"

        filepath = os.path.join(self.data_dir, filename)

        # Подготавливаем данные для сохранения
        data = {
            'students': [],
            'timestamp': datetime.now().isoformat(),
            'version': '1.0'
        }

        for student in students:
            student_data = {
                'name': student.name,
                'original_names': student.original_names,
                'grades': student.grades,
                'student_class': student.student_class
            }
            data['students'].append(student_data)

        with open(filepath, 'wb') as f:
            pickle.dump(data, f)

        return filename

    def load_students(self, filename):
        """Загрузка данных учеников"""
        filepath = os.path.join(self.data_dir, filename)

        with open(filepath, 'rb') as f:
            data = pickle.load(f)

        students = []
        for student_data in data['students']:
            student = Student(
                student_data['name'],
                student_data['grades'],
                student_data['student_class']
            )
            student.original_names = student_data.get('original_names', [student_data['name']])
            students.append(student)

        return students

    def get_saved_files(self):
        """Получение списка сохраненных файлов"""
        if not os.path.exists(self.data_dir):
            return []

        files = []
        for f in os.listdir(self.data_dir):
            if f.endswith('.pkl'):
                filepath = os.path.join(self.data_dir, f)
                mtime = os.path.getmtime(filepath)
                files.append({
                    'name': f,
                    'path': filepath,
                    'modified': datetime.fromtimestamp(mtime)
                })

        return sorted(files, key=lambda x: x['modified'], reverse=True)

    def export_to_json(self, students, filename=None):
        """Экспорт данных в JSON для удобного просмотра"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"students_export_{timestamp}.json"

        filepath = os.path.join(self.data_dir, filename)

        data = []
        for student in students:
            student_data = {
                'name': student.name,
                'class': student.student_class,
                'statistics': student.statistics,
                'grades': student.grades
            }
            data.append(student_data)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename


class DataMergeDialog:
    """Диалог для выбора режима объединения данных"""
    def __init__(self, parent, existing_students):
        self.parent = parent
        self.existing_students = existing_students
        self.result = None

    def show(self):
        """Отображение диалога"""
        dialog = tk.Toplevel(self.parent.root)
        dialog.title("Выберите режим загрузки")
        dialog.geometry("500x450")
        dialog.transient(self.parent.root)
        dialog.grab_set()

        # Центрируем окно
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f'+{x}+{y}')

        # Заголовок
        title_frame = ttk.Frame(dialog, padding="10")
        title_frame.pack(fill=tk.X)

        ttk.Label(title_frame, text="Выберите режим загрузки данных",
                  style='Title.TLabel').pack()

        if self.existing_students:
            ttk.Label(title_frame,
                      text=f"В программе уже загружено {len(self.existing_students)} учеников",
                      foreground="blue").pack(pady=5)

        # Основное содержание
        content_frame = ttk.Frame(dialog, padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True)

        self.mode_var = tk.StringVar(value="new")

        modes = [
            ("new", "🆕 Новая четверть/полугодие",
             "Очистить текущие данные и загрузить новые"),
            ("append", "➕ Добавить к существующим",
             "Добавить новые данные к уже загруженным (объединит учеников)"),
            ("replace_class", "🔄 Заменить данные для класса",
             "Заменить данные только для указанного класса"),
            ("merge", "🔀 Объединить с существующими",
             "Объединить данные, сохраняя всю историю"),
            ("keep", "💾 Оставить текущие данные",
             "Не загружать новые данные, оставить существующие")
        ]

        for mode, label, desc in modes:
            frame = ttk.Frame(content_frame)
            frame.pack(fill=tk.X, pady=5)

            rb = ttk.Radiobutton(frame, variable=self.mode_var, value=mode)
            rb.pack(side=tk.LEFT)

            text_frame = ttk.Frame(frame)
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

            ttk.Label(text_frame, text=label, font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            ttk.Label(text_frame, text=desc, foreground="gray").pack(anchor=tk.W)

        # Дополнительные опции
        options_frame = ttk.LabelFrame(content_frame, text="Дополнительные опции", padding="5")
        options_frame.pack(fill=tk.X, pady=10)

        self.merge_similar_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Объединять похожие имена",
                        variable=self.merge_similar_var).pack(anchor=tk.W)

        self.keep_history_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Сохранять историю изменений",
                        variable=self.keep_history_var).pack(anchor=tk.W)

        # Кнопки
        button_frame = ttk.Frame(dialog, padding="10")
        button_frame.pack(fill=tk.X)

        def on_ok():
            self.result = {
                'mode': self.mode_var.get(),
                'merge_similar': self.merge_similar_var.get(),
                'keep_history': self.keep_history_var.get()
            }
            dialog.destroy()

        ttk.Button(button_frame, text="ОК",
                   command=on_ok).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Отмена",
                   command=dialog.destroy).pack(side=tk.RIGHT)

        # Подпись автора
        ttk.Label(dialog, text="Daniil Zuev © 2024",
                  font=('Arial', 7), foreground='gray').pack(side=tk.BOTTOM, pady=2)

        self.parent.root.wait_window(dialog)
        return self.result


class ClassParser:
    """Класс для парсинга и определения класса ученика"""
    CLASS_PATTERNS = [
        r'(\d+)[-\s]*?([А-Яа-я])',  # 5А, 5-А, 5 А
        r'([А-Яа-я])[-\s]*?(\d+)',  # А5, А-5
        r'(\d+)\s*?класс\s*?([А-Яа-я])',  # 5 класс А
        r'([А-Яа-я])\s*?класс\s*?(\d+)',  # А класс 5
        r'класс\s*?(\d+)\s*?([А-Яа-я])',  # класс 5 А
        r'(\d+)\s*?([А-Яа-я])\s*?класс',  # 5 А класс
    ]

    CLASS_COLUMN_PATTERNS = [
        r'класс', r'class', r'клас', r'параллель',
        r'кл\.?', r'cl\.?', r'классный', r'класса'
    ]

    @staticmethod
    def extract_class_from_string(text):
        """Извлечение класса из строки"""
        if pd.isna(text) or not isinstance(text, str):
            return None

        text = str(text).strip().lower()

        # Проверяем по всем паттернам
        for pattern in ClassParser.CLASS_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Определяем где цифра, где буква
                digit = None
                letter = None

                for g in groups:
                    if g.isdigit():
                        digit = g
                    elif g.isalpha() and len(g) == 1:
                        letter = g.upper()

                if digit and letter:
                    return f"{digit}{letter}"
                elif digit:
                    return digit
                elif letter:
                    return letter

        # Проверяем простые случаи
        if re.match(r'^\d+[а-я]?$', text, re.IGNORECASE):
            return text.upper()

        return None

    @staticmethod
    def is_class_column(column_name):
        """Проверка, является ли колонка колонкой с классом"""
        if pd.isna(column_name) or not isinstance(column_name, str):
            return False

        col_lower = str(column_name).lower()

        for pattern in ClassParser.CLASS_COLUMN_PATTERNS:
            if re.search(pattern, col_lower, re.IGNORECASE):
                return True

        return False

    @staticmethod
    def find_class_in_header(header_row):
        """Поиск класса в строке заголовка"""
        if not isinstance(header_row, str):
            return None

        return ClassParser.extract_class_from_string(header_row)

    @staticmethod
    def normalize_class_name(class_name):
        """Нормализация названия класса"""
        if not class_name:
            return None

        class_name = str(class_name).strip().upper()

        # Убираем лишние символы
        class_name = re.sub(r'[^\w\d]', '', class_name)

        # Приводим к формату "5А"
        match = re.match(r'(\d+)([А-ЯA-Z])', class_name, re.IGNORECASE)
        if match:
            return f"{match.group(1)}{match.group(2).upper()}"

        return class_name

    @staticmethod
    def find_classes_in_header_rows(df):
        """Поиск классов в отдельных строках заголовка"""
        classes = {}
        current_class = None

        # Проверяем первые несколько строк на наличие классов
        for idx in range(min(5, len(df))):
            row = df.iloc[idx]
            first_cell = str(row[0]) if len(row) > 0 else ""

            # Проверяем, является ли строка заголовком класса
            class_name = ClassParser.extract_class_from_string(first_cell)

            if class_name:
                # Это строка с классом
                current_class = class_name
                classes[current_class] = {
                    'start_row': idx,
                    'students': []
                }
                continue

            # Если есть текущий класс и это не заголовок, добавляем ученика
            if current_class and idx > 0 and pd.notna(first_cell):
                student_name = str(first_cell).strip()
                if student_name and student_name.lower() not in ['nan', 'none', '']:
                    # Проверяем, что это не заголовок таблицы
                    if not any(keyword in student_name.lower() for keyword in ['фио', 'фамилия', 'имя', 'ученик']):
                        classes[current_class]['students'].append({
                            'row_idx': idx,
                            'name': student_name,
                            'data': row[1:].tolist()
                        })

        return classes if classes else None

    @staticmethod
    def detect_class_boundaries(df):
        """Определение границ классов в файле"""
        class_boundaries = []
        current_class = None
        start_row = None

        for idx in range(len(df)):
            row = df.iloc[idx]
            first_cell = str(row[0]) if len(row) > 0 else ""

            # Проверяем, является ли строка заголовком класса
            class_name = ClassParser.extract_class_from_string(first_cell)

            if class_name:
                # Если был предыдущий класс, сохраняем его границы
                if current_class and start_row is not None:
                    class_boundaries.append({
                        'class': current_class,
                        'start': start_row,
                        'end': idx - 1,
                        'count': idx - start_row
                    })

                # Начинаем новый класс
                current_class = class_name
                start_row = idx + 1  # Следующая строка после заголовка
                continue

            # Проверяем, не конец ли класса (пустая строка или новый заголовок)
            if current_class and (pd.isna(first_cell) or first_cell.strip() == ''):
                class_boundaries.append({
                    'class': current_class,
                    'start': start_row,
                    'end': idx - 1,
                    'count': idx - start_row if start_row else 0
                })
                current_class = None
                start_row = None

        # Добавляем последний класс
        if current_class and start_row is not None:
            class_boundaries.append({
                'class': current_class,
                'start': start_row,
                'end': len(df) - 1,
                'count': len(df) - start_row
            })

        return class_boundaries if class_boundaries else None


class Student:
    """Класс для хранения информации о конкретном ученике"""
    _instances = {}  # Словарь для хранения всех экземпляров

    def __new__(cls, name, grades, student_class=None):
        # Нормализуем имя для поиска
        norm_name = cls.normalize_name(name)

        # Если ученик уже существует, возвращаем существующий экземпляр
        if norm_name in cls._instances:
            instance = cls._instances[norm_name]
            # Обновляем существующий экземпляр
            instance.merge_with(name, grades, student_class)
            return instance
        else:
            # Создаем новый экземпляр
            instance = super().__new__(cls)
            # Сразу инициализируем базовые атрибуты
            instance.original_name = name
            instance.name = name
            instance.original_names = [name]
            instance.all_names = [name]
            instance.student_class = student_class
            instance.update_history = []
            # ВАЖНО: инициализируем statistics ДО обработки grades
            instance.statistics = {}
            # Теперь обрабатываем оценки
            instance.grades = instance._process_grades(grades)
            # Вычисляем статистику
            instance.statistics = instance._calculate_statistics()
            # Сохраняем в кэш
            cls._instances[norm_name] = instance
            return instance

    def __init__(self, name, grades, student_class=None):
        # Этот метод может вызываться несколько раз из-за __new__
        # Но мы уже все инициализировали в __new__, поэтому просто возвращаемся
        pass

    @staticmethod
    def normalize_name(name):
        """Нормализация имени для сравнения"""
        if not name:
            return ""

        # Приводим к нижнему регистру
        name = name.lower().strip()

        # Убираем лишние пробелы
        name = ' '.join(name.split())

        # Убираем инициалы и отчества для сравнения
        # Оставляем фамилию и первое слово имени
        parts = name.split()
        if len(parts) >= 2:
            # Берем фамилию и первую букву имени
            return f"{parts[0]} {parts[1][0] if parts[1] else ''}"

        return name

    def merge_with(self, new_name, new_grades, new_class=None):
        """Объединение с другой записью того же ученика"""
        # Добавляем новое имя в список
        if new_name not in self.all_names:
            self.all_names.append(new_name)
        if new_name not in self.original_names:
            self.original_names.append(new_name)

        # Обновляем имя на самое короткое
        if len(new_name) < len(self.name):
            self.name = new_name

        # Обрабатываем новые оценки
        processed_new_grades = self._process_grades(new_grades)

        # Объединяем оценки
        max_len = max(len(self.grades), len(processed_new_grades))
        merged_grades = []

        for i in range(max_len):
            grade1 = self.grades[i] if i < len(self.grades) else None
            grade2 = processed_new_grades[i] if i < len(processed_new_grades) else None

            if grade1 is not None and grade2 is not None:
                # Если обе оценки есть, берем среднее
                merged_grades.append((grade1 + grade2) / 2)
                self.update_history.append(f"Работа {i + 1}: {grade1} + {grade2} → {(grade1 + grade2) / 2:.1f}")
            elif grade1 is not None:
                merged_grades.append(grade1)
            elif grade2 is not None:
                merged_grades.append(grade2)
            else:
                merged_grades.append(None)

        self.grades = merged_grades

        # Обновляем класс, если новый указан
        if new_class and not self.student_class:
            self.student_class = new_class
        elif new_class and self.student_class and new_class != self.student_class:
            self.update_history.append(f"Класс: {self.student_class} → {new_class}")
            self.student_class = new_class

        # Пересчитываем статистику
        self.statistics = self._calculate_statistics()

    def _process_grades(self, grades):
        """Обработка оценок, замена 'н' на None"""
        processed = []
        for grade in grades:
            if pd.isna(grade) or str(grade).strip().lower() in ['н', 'н/а', 'null', 'none', '']:
                processed.append(None)
            else:
                try:
                    val = float(str(grade).replace(',', '.').strip())
                    processed.append(val)
                except:
                    processed.append(None)
        return processed

    def _calculate_statistics(self):
        """Расчет статистики по ученику"""
        # Убеждаемся, что grades существует
        if not hasattr(self, 'grades'):
            self.grades = []

        valid_grades = [g for g in self.grades if g is not None]

        if not valid_grades:
            return {
                'mean': 0,
                'median': 0,
                'min': 0,
                'max': 0,
                'count': 0,
                'trend': 'Нет данных',
                'grade_distribution': {},
                'passed_count': 0,
                'failed_count': 0,
                'first_grade': None,
                'last_grade': None,
                'merge_count': len(self.all_names) if hasattr(self, 'all_names') else 1
            }

        stats = {
            'mean': float(np.mean(valid_grades)),
            'median': float(np.median(valid_grades)),
            'min': float(np.min(valid_grades)),
            'max': float(np.max(valid_grades)),
            'count': len(valid_grades),
            'grade_distribution': self._get_grade_distribution(valid_grades),
            'first_grade': valid_grades[0] if valid_grades else None,
            'last_grade': valid_grades[-1] if valid_grades else None,
            'merge_count': len(self.all_names) if hasattr(self, 'all_names') else 1
        }

        # Определяем режим (оценки или баллы)
        if valid_grades:
            is_grades_mode = max(valid_grades) <= 5 and all(
                g is not None and (isinstance(g, (int, float)) and float(g).is_integer())
                for g in valid_grades
            )
        else:
            is_grades_mode = False

        if is_grades_mode:
            stats['passed_count'] = len([g for g in valid_grades if g >= 3])
            stats['failed_count'] = len([g for g in valid_grades if g < 3])
        else:
            stats['passed_count'] = len(valid_grades)
            stats['failed_count'] = 0

        # Расчет динамики (тренда)
        if len(valid_grades) >= 3:
            x = np.arange(len(valid_grades))
            try:
                z = np.polyfit(x, valid_grades, 1)
                trend = float(z[0])
                if trend > 0.1:
                    stats['trend'] = 'Положительная'
                elif trend < -0.1:
                    stats['trend'] = 'Отрицательная'
                else:
                    stats['trend'] = 'Стабильная'
            except:
                stats['trend'] = 'Ошибка расчета'
        else:
            stats['trend'] = 'Недостаточно данных'

        return stats

    def _get_grade_distribution(self, grades):
        """Получение распределения оценок"""
        distribution = {}

        # Проверяем, являются ли оценки целыми числами в диапазоне 2-5
        is_standard_grades = all(
            g is not None and
            isinstance(g, (int, float)) and
            float(g).is_integer() and
            2 <= float(g) <= 5
            for g in grades
        )

        if is_standard_grades:
            distribution = {2: 0, 3: 0, 4: 0, 5: 0}
            for g in grades:
                if g is not None:
                    distribution[int(g)] += 1
        else:
            for g in grades:
                if g is not None:
                    # Округляем до 2 знаков для группировки
                    key = round(g, 2)
                    distribution[key] = distribution.get(key, 0) + 1

        return distribution

    def get_info(self):
        """Получение информации об ученике"""
        # Убеждаемся, что statistics существует
        if not hasattr(self, 'statistics') or not self.statistics:
            self.statistics = self._calculate_statistics()

        return {
            'name': self.name,
            'all_names': self.all_names if hasattr(self, 'all_names') else [self.name],
            'grades': self.grades if hasattr(self, 'grades') else [],
            'update_history': self.update_history if hasattr(self, 'update_history') else [],
            **self.statistics
        }

    @classmethod
    def clear_cache(cls):
        """Очистка кэша экземпляров"""
        cls._instances = {}

    def __repr__(self):
        return f"Student(name={self.name}, class={self.student_class})"


class StudentRegistry:
    """Класс для управления учениками с возможностью объединения записей"""
    def __init__(self):
        self.students = []
        self.name_index = {}  # Индекс для быстрого поиска по имени

    def normalize_name(self, name):
        """Нормализация имени для сравнения"""
        if not name:
            return ""

        # Приводим к нижнему регистру и убираем лишние пробелы
        name = name.lower().strip()

        # Убираем инициалы и отчества для сравнения
        # Оставляем только фамилию и имя
        parts = name.split()
        if len(parts) >= 2:
            # Берем фамилию и первую букву имени
            return f"{parts[0]} {parts[1][0] if parts[1] else ''}"

        return name

    def find_similar_student(self, name, threshold=0.8):
        """Поиск похожего ученика"""
        from difflib import SequenceMatcher

        norm_name = self.normalize_name(name)

        for student in self.students:
            for orig_name in student.original_names:
                similarity = SequenceMatcher(None, norm_name, self.normalize_name(orig_name)).ratio()
                if similarity > threshold:
                    return student
        return None

    def add_student(self, student):
        """Добавление ученика с проверкой на дубликаты"""
        existing = self.find_similar_student(student.name)

        if existing:
            # Объединяем с существующим
            existing.merge_with(student)
            return existing
        else:
            # Добавляем нового
            self.students.append(student)
            return student

    def get_all_students(self):
        """Получение всех учеников"""
        return self.students

    def clear(self):
        """Очистка реестра"""
        self.students = []
        self.name_index = {}


class DataFilter:
    """Класс для фильтрации лишних данных"""
    SERVICE_KEYWORDS = [
        'итого', 'всего', 'средний', 'среднее', 'сумма', 'итог',
        'классный руководитель', 'учитель', 'директор', 'завуч',
        'подпись', 'дата', 'отчет', 'таблица', 'список',
        'класс', 'параллель', 'школа', 'гимназия', 'лицей'
    ]

    NUMBER_PATTERN = r'^\d+$'
    DATE_PATTERN = r'\d{1,2}[./-]\d{1,2}[./-]\d{2,4}'

    @staticmethod
    def is_service_row(row_values):
        """Проверка, является ли строка служебной"""
        if not row_values or len(row_values) == 0:
            return True

        first_cell = str(row_values[0]).lower().strip() if len(row_values) > 0 else ""

        # Проверка на пустую строку
        if not first_cell or first_cell in ['nan', 'none', '']:
            return True

        # Проверка на ключевые слова
        for keyword in DataFilter.SERVICE_KEYWORDS:
            if keyword in first_cell:
                return True

        # Проверка на даты
        if re.search(DataFilter.DATE_PATTERN, first_cell):
            return True

        # Проверка на подписи и примечания
        if any(symbol in first_cell for symbol in ['подпись', 'примечание', 'сноска']):
            return True

        return False

    @staticmethod
    def clean_cell_value(value):
        """Очистка значения ячейки от лишних символов"""
        if pd.isna(value):
            return None

        value = str(value).strip()

        # Убираем лишние пробелы и спецсимволы
        value = re.sub(r'\s+', ' ', value)

        # Если после очистки осталась пустая строка
        if not value or value.lower() in ['nan', 'none', 'null']:
            return None

        return value

    @staticmethod
    def extract_valid_grades(row_values, start_idx=1):
        """Извлечение валидных оценок из строки"""
        valid_grades = []

        for i in range(start_idx, len(row_values)):
            val = DataFilter.clean_cell_value(row_values[i])

            if val is None:
                valid_grades.append(None)
            else:
                # Проверяем, является ли значение оценкой
                try:
                    num_val = float(val.replace(',', '.'))

                    # Проверяем разумные пределы
                    if 0 <= num_val <= 100:  # Баллы до 100
                        valid_grades.append(num_val)
                    else:
                        valid_grades.append(None)
                except:
                    # Если не число, но это может быть 'н' или прочерк
                    if val.lower() in ['н', '-', '—', 'пропуск']:
                        valid_grades.append(None)
                    else:
                        # Игнорируем другие текстовые значения
                        valid_grades.append(None)

        return valid_grades

    @staticmethod
    def is_grade_column(column_values):
        """Проверка, является ли колонка колонкой с оценками"""
        if len(column_values) == 0:
            return False

        # Проверяем первые несколько значений
        grade_count = 0
        total_count = 0

        for val in column_values[:20]:  # Проверяем первые 20 строк
            if pd.isna(val):
                continue

            val_str = str(val).strip()
            if val_str.lower() in ['н', '-', '—']:
                grade_count += 1
                total_count += 1
                continue

            try:
                num_val = float(val_str.replace(',', '.'))
                if 0 <= num_val <= 100:  # Разумный диапазон для оценок/баллов
                    grade_count += 1
                total_count += 1
            except:
                pass

        # Если больше 50% значений - потенциальные оценки
        return total_count > 0 and (grade_count / total_count) > 0.5


class BatchClassEditor:
    """Класс для пакетного редактирования классов"""
    def __init__(self, parent_app):
        self.parent = parent_app
        self.selected_students = []
        self.student_listbox = None
        self.student_items = []
        self.info_label = None

    def show_editor(self):
        """Отображение редактора для пакетного назначения классов"""
        if not self.parent.students:
            messagebox.showwarning("Предупреждение", "Нет учеников для редактирования")
            return

        # Создаем новое окно
        editor_window = tk.Toplevel(self.parent.root)
        editor_window.title("Пакетное назначение классов")
        editor_window.geometry("800x650")

        # Верхняя панель
        top_frame = ttk.Frame(editor_window, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Пакетное редактирование классов",
                  style='Title.TLabel').pack()

        # Панель фильтрации
        filter_frame = ttk.LabelFrame(editor_window, text="Фильтр", padding="10")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(filter_frame, text="Поиск:").pack(side=tk.LEFT)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="Класс:").pack(side=tk.LEFT, padx=(20, 5))
        class_filter_var = tk.StringVar()

        # Получаем список классов
        class_list = ['Все']
        if hasattr(self.parent, 'classes') and self.parent.classes:
            class_list.extend(sorted([c for c in self.parent.classes.keys() if c]))

        class_filter_combo = ttk.Combobox(filter_frame, textvariable=class_filter_var, width=15)
        class_filter_combo['values'] = class_list
        class_filter_combo.set('Все')
        class_filter_combo.pack(side=tk.LEFT)

        # Основная область с двумя панелями
        main_frame = ttk.Frame(editor_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Левая панель - список учеников
        left_frame = ttk.LabelFrame(main_frame, text="Список учеников", padding="5")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Список с множественным выбором
        list_frame = ttk.Frame(left_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.student_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                          selectmode=tk.EXTENDED, height=20)
        self.student_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.student_listbox.yview)

        # Правая панель - управление
        right_frame = ttk.LabelFrame(main_frame, text="Управление", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5)

        # Назначение класса
        ttk.Label(right_frame, text="Назначить класс:",
                  style='Heading.TLabel').pack(pady=10)

        class_var = tk.StringVar()
        class_entry = ttk.Entry(right_frame, textvariable=class_var, width=20)
        class_entry.pack(pady=5)

        ttk.Button(right_frame, text="Применить к выбранным",
                   command=lambda: self.apply_class_to_selected(class_var.get())).pack(pady=5)

        ttk.Button(right_frame, text="Применить ко всем",
                   command=lambda: self.apply_class_to_all(class_var.get())).pack(pady=5)

        ttk.Separator(right_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Очистка класса
        ttk.Label(right_frame, text="Очистить класс:",
                  style='Heading.TLabel').pack(pady=10)

        ttk.Button(right_frame, text="Очистить у выбранных",
                   command=self.clear_class_from_selected).pack(pady=5)

        ttk.Button(right_frame, text="Очистить у всех",
                   command=self.clear_class_from_all).pack(pady=5)

        ttk.Separator(right_frame, orient='horizontal').pack(fill=tk.X, pady=10)

        # Информация
        self.info_label = ttk.Label(right_frame, text="", foreground="blue")
        self.info_label.pack(pady=10)

        # Обновление списка при изменении фильтра
        def update_list(*args):
            self.update_student_list(search_var.get(), class_filter_var.get())

        search_var.trace('w', update_list)
        class_filter_var.trace('w', update_list)

        # Заполняем список
        self.update_student_list()

        # Кнопка закрытия
        ttk.Button(editor_window, text="Закрыть",
                   command=editor_window.destroy).pack(pady=10)

        # Подпись автора
        ttk.Label(editor_window, text="Daniil Zuev © 2024",
                  font=('Arial', 7), foreground='gray').pack(side=tk.BOTTOM, pady=2)

    def update_students_list(self):
        """Обновление списка учеников в интерфейсе"""
        try:
            self.students_listbox.delete(0, tk.END)

            if not self.students:
                self.log("⚠️ Список учеников пуст")
                return

            # Проверяем, есть ли у учеников информация о классах
            has_classes = any(student.student_class for student in self.students)

            if has_classes:
                # Есть информация о классах - группируем по классам
                self.log("📚 Обнаружена информация о классах, группирую...")

                # Сортируем учеников по классу и имени
                sorted_students = sorted(self.students, key=lambda x: (x.student_class or 'ZZZ', x.name))

                current_class = None

                for student in sorted_students:
                    # Определяем класс для отображения
                    display_class = student.student_class if student.student_class else "Без класса"

                    # Добавляем разделитель для нового класса
                    if display_class != current_class:
                        current_class = display_class
                        display_text = f"📚 КЛАСС {display_class}"
                        self.students_listbox.insert(tk.END, display_text)
                        self.students_listbox.itemconfig(tk.END, fg='blue', font=('Arial', 10, 'bold'))

                    # Добавляем ученика
                    self._insert_student_item(student)
            else:
                # Нет информации о классах - показываем всех учеников подряд
                self.log("📋 Информация о классах отсутствует, показываю всех учеников")

                # Добавляем заголовок
                self.students_listbox.insert(tk.END, "📋 ВСЕ УЧЕНИКИ")
                self.students_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 10, 'bold'))

                # Сортируем учеников по имени
                for student in sorted(self.students, key=lambda x: x.name):
                    self._insert_student_item(student)

            # Добавляем информацию о количестве учеников
            self.students_listbox.insert(tk.END, "")
            self.students_listbox.insert(tk.END, f"📊 Всего учеников: {len(self.students)}")
            self.students_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 9, 'italic'))

            self.log(f"✅ Список учеников обновлен: {len(self.students)} учеников")

        except Exception as e:
            self.log(f"⚠️ Ошибка обновления списка учеников: {e}")
            import traceback
            traceback.print_exc()

    def _insert_student_item(self, student):
        """Вспомогательный метод для вставки ученика в список"""
        try:
            # Определяем префикс в зависимости от успеваемости
            prefix = ""

            if hasattr(student, 'statistics') and student.statistics:
                mean = student.statistics.get('mean', 0)
                trend = student.statistics.get('trend', '')

                if mean < 3:
                    prefix = "⚠️ "
                elif trend == 'Отрицательная':
                    prefix = "📉 "

            # Формируем отображаемое имя
            display_name = student.name
            if len(display_name) > 45:
                display_name = display_name[:42] + "..."

            self.students_listbox.insert(tk.END, f"   {prefix}{display_name}")

        except Exception as e:
            self.log(f"⚠️ Ошибка вставки ученика: {e}")

    def update_classes_list(self):
        """Обновление списка классов"""
        try:
            self.class_listbox.delete(0, tk.END)

            # Проверяем наличие классов
            if not hasattr(self, 'classes') or not self.classes:
                self.class_listbox.insert(tk.END, "📭 Нет данных о классах")
                return

            # Проверяем, есть ли реальные классы (не пустые)
            non_empty_classes = {k: v for k, v in self.classes.items() if v}

            if not non_empty_classes:
                self.class_listbox.insert(tk.END, "📭 Нет данных о классах")
                return

            self.log(f"📚 Классы для отображения: {list(non_empty_classes.keys())}")

            stats = self.get_class_statistics()
            sort_by = self.class_sort_var.get()

            # Получаем список непустых классов
            all_classes = list(non_empty_classes.keys())

            if sort_by == 'name':
                items = sorted(all_classes)
            elif sort_by == 'avg':
                items = sorted(all_classes,
                               key=lambda x: stats.get(x, {}).get('avg_class_mean', 0),
                               reverse=True)
            elif sort_by == 'count':
                items = sorted(all_classes,
                               key=lambda x: len(non_empty_classes[x]),
                               reverse=True)

            for class_name in items:
                students = non_empty_classes[class_name]
                class_stats = stats.get(class_name, {})
                avg = class_stats.get('avg_class_mean', 0)
                count = len(students)

                # Определяем цвет и иконку
                if avg >= 4.5:
                    prefix = "🏆 "
                    color = 'green'
                elif avg >= 4:
                    prefix = "📚 "
                    color = 'dark green'
                elif avg >= 3:
                    prefix = "📖 "
                    color = 'blue'
                else:
                    prefix = "⚠️ "
                    color = 'red'

                display = f"{prefix}{class_name}  |  {count} уч.  |  ср.{avg:.2f}"

                # Добавляем информацию о распределении
                dist = class_stats.get('distribution', {})
                if dist:
                    excellent = dist.get('excellent', 0)
                    good = dist.get('good', 0)
                    poor = dist.get('poor', 0)
                    if excellent > 0 or good > 0 or poor > 0:
                        display += f"  [👍{excellent} 👎{poor}]"

                idx = self.class_listbox.insert(tk.END, display)
                self.class_listbox.itemconfig(idx, fg=color, font=('Arial', 10, 'bold'))

            # Добавляем информацию о количестве
            self.class_listbox.insert(tk.END, "")
            self.class_listbox.insert(tk.END, f"📊 Всего классов: {len(non_empty_classes)}")
            self.class_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 9, 'italic'))

        except Exception as e:
            self.log(f"⚠️ Ошибка обновления списка классов: {e}")
            import traceback
            traceback.print_exc()

    def filter_students(self, *args):
        """Фильтрация списка учеников по поиску"""
        try:
            search_term = self.search_var.get().lower()
            self.students_listbox.delete(0, tk.END)

            if not self.students:
                return

            # Фильтруем учеников по поисковому запросу
            filtered_students = []
            for student in self.students:
                if search_term in student.name.lower():
                    filtered_students.append(student)
                elif student.student_class and search_term in student.student_class.lower():
                    filtered_students.append(student)

            # Если ничего не найдено
            if not filtered_students and search_term:
                self.students_listbox.insert(tk.END, f"🔍 Ничего не найдено по запросу '{search_term}'")
                self.students_listbox.itemconfig(tk.END, fg='gray')
                return
            elif not filtered_students:
                filtered_students = self.students

            # Проверяем наличие классов у отфильтрованных учеников
            has_classes = any(s.student_class for s in filtered_students)

            if has_classes:
                # Есть классы - группируем
                sorted_students = sorted(filtered_students, key=lambda x: (x.student_class or 'ZZZ', x.name))

                current_class = None
                for student in sorted_students:
                    display_class = student.student_class if student.student_class else "Без класса"

                    if display_class != current_class:
                        current_class = display_class
                        display_text = f"📚 КЛАСС {display_class}"
                        self.students_listbox.insert(tk.END, display_text)
                        self.students_listbox.itemconfig(tk.END, fg='blue', font=('Arial', 10, 'bold'))

                    self._insert_student_item(student)
            else:
                # Нет классов - простой список
                self.students_listbox.insert(tk.END, "📋 РЕЗУЛЬТАТЫ ПОИСКА")
                self.students_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 10, 'bold'))

                for student in sorted(filtered_students, key=lambda x: x.name):
                    self._insert_student_item(student)

            # Информация о количестве
            self.students_listbox.insert(tk.END, "")
            self.students_listbox.insert(tk.END,
                                         f"📊 Показано: {len(filtered_students)} из {len(self.students)} учеников")
            self.students_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 9, 'italic'))

        except Exception as e:
            self.log(f"⚠️ Ошибка фильтрации: {e}")

    def apply_class_to_selected(self, new_class):
        """Применение класса к выбранным ученикам"""
        if not new_class:
            messagebox.showwarning("Предупреждение", "Введите название класса")
            return

        if not self.student_listbox:
            return

        selected_indices = self.student_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Предупреждение", "Выберите учеников")
            return

        count = 0
        for idx in selected_indices:
            if idx < len(self.student_items):
                student = self.student_items[idx]
                old_class = student.student_class
                student.student_class = new_class

                # Обновляем словарь классов
                if old_class and old_class in self.parent.classes:
                    if student in self.parent.classes[old_class]:
                        self.parent.classes[old_class].remove(student)
                    if not self.parent.classes[old_class]:
                        del self.parent.classes[old_class]

                if new_class not in self.parent.classes:
                    self.parent.classes[new_class] = []
                if student not in self.parent.classes[new_class]:
                    self.parent.classes[new_class].append(student)

                count += 1

        if self.info_label:
            self.info_label.config(text=f"✅ Класс назначен {count} ученикам")
        self.parent.update_students_list()
        self.parent.update_classes_list()
        self.update_student_list()

    def apply_class_to_all(self, new_class):
        """Применение класса ко всем ученикам"""
        if not new_class:
            messagebox.showwarning("Предупреждение", "Введите название класса")
            return

        result = messagebox.askyesno("Подтверждение",
                                     f"Назначить класс '{new_class}' всем {len(self.parent.students)} ученикам?")
        if not result:
            return

        self.parent.classes = {new_class: []}

        for student in self.parent.students:
            student.student_class = new_class
            if student not in self.parent.classes[new_class]:
                self.parent.classes[new_class].append(student)

        if self.info_label:
            self.info_label.config(text=f"✅ Класс назначен всем {len(self.parent.students)} ученикам")
        self.parent.update_students_list()
        self.parent.update_classes_list()
        self.update_student_list()

    def clear_class_from_selected(self):
        """Очистка класса у выбранных учеников"""
        if not self.student_listbox:
            return

        selected_indices = self.student_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Предупреждение", "Выберите учеников")
            return

        count = 0
        for idx in selected_indices:
            if idx < len(self.student_items):
                student = self.student_items[idx]
                if student.student_class:
                    old_class = student.student_class
                    student.student_class = None

                    if old_class in self.parent.classes:
                        if student in self.parent.classes[old_class]:
                            self.parent.classes[old_class].remove(student)
                        if not self.parent.classes[old_class]:
                            del self.parent.classes[old_class]

                    count += 1

        if self.info_label:
            self.info_label.config(text=f"✅ Класс очищен у {count} учеников")
        self.parent.update_students_list()
        self.parent.update_classes_list()
        self.update_student_list()

    def clear_class_from_all(self):
        """Очистка класса у всех учеников"""
        result = messagebox.askyesno("Подтверждение",
                                     "Очистить класс у всех учеников?")
        if not result:
            return

        for student in self.parent.students:
            student.student_class = None

        self.parent.classes = {}

        if self.info_label:
            self.info_label.config(text=f"✅ Класс очищен у всех учеников")
        self.parent.update_students_list()
        self.parent.update_classes_list()
        self.update_student_list()


class SchoolAnalyticsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Школьная аналитика - Анализ успеваемости")
        self.root.geometry("1400x800")

        # Добавьте подпись в нижнюю панель
        self.author_label = ttk.Label(root, text="© 2024 Daniil Zuev",
                                      font=('Arial', 8), foreground='gray')
        self.author_label.pack(side=tk.BOTTOM, pady=2)

        # Переменные
        self.students = []
        self.data = None
        self.current_student = None
        self.is_grades_mode = True  # True - оценки 2-5, False - баллы
        self.classes = {}

        # Настройка стилей
        self.setup_styles()

        # Создание интерфейса
        self.create_widgets()

    def update_charts(self):
        """Обновление дополнительных графиков"""
        if not self.students:
            return

        self.chart1_figure.clear()
        self.chart2_figure.clear()

        # График 1: Средние баллы учеников
        ax1 = self.chart1_figure.add_subplot(111)

        # Берем всех учеников для полной картины
        names = []
        means = []
        colors = []

        for student in sorted(self.students, key=lambda x: x.statistics['mean']):
            name_parts = student.name.split()
            short_name = name_parts[0] if name_parts else student.name
            if len(short_name) > 15:
                short_name = short_name[:12] + "..."
            names.append(short_name)
            mean_val = student.statistics['mean']
            means.append(mean_val)

            if mean_val < 3:
                colors.append('#ff6b6b')  # красный
            elif mean_val < 4:
                colors.append('#ffd93d')  # желтый
            else:
                colors.append('#6bcb77')  # зеленый

        bars = ax1.barh(names, means, color=colors, edgecolor='black', linewidth=1)
        ax1.set_xlabel('Средний балл', fontsize=11)
        ax1.set_title('Распределение средних баллов', fontsize=12, fontweight='bold')

        # Вертикальная линия общего среднего
        overall_mean = np.mean([s.statistics['mean'] for s in self.students])
        ax1.axvline(x=overall_mean, color='red', linestyle='--', linewidth=2,
                    label=f'Общее среднее: {overall_mean:.2f}')
        ax1.legend()

        # Добавление значений
        for i, (bar, val) in enumerate(zip(bars, means)):
            ax1.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
                     f'{val:.2f}', va='center', fontsize=8)

        # График 2: Динамика успеваемости
        ax2 = self.chart2_figure.add_subplot(111)

        trends = {'Положительная': 0, 'Стабильная': 0, 'Отрицательная': 0, 'Недостаточно данных': 0}
        for student in self.students:
            trends[student.statistics['trend']] += 1

        colors_trend = {
            'Положительная': '#6bcb77',
            'Стабильная': '#4d96ff',
            'Отрицательная': '#ff6b6b',
            'Недостаточно данных': '#95a5a6'
        }

        # Убираем нулевые значения
        labels = []
        sizes = []
        colors_list = []

        for key, value in trends.items():
            if value > 0:
                labels.append(key)
                sizes.append(value)
                colors_list.append(colors_trend[key])

        if sizes:
            wedges, texts, autotexts = ax2.pie(
                sizes,
                labels=labels,
                colors=colors_list,
                autopct='%1.1f%%',
                startangle=90,
                textprops={'fontsize': 10}
            )

            # Настройка текста процентов
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

        ax2.set_title('Распределение динамики успеваемости', fontsize=12, fontweight='bold')

        self.chart1_figure.tight_layout()
        self.chart2_figure.tight_layout()
        self.chart1_canvas.draw()
        self.chart2_canvas.draw()

    def update_general_stats(self):
        """Обновление общей статистики"""
        # Очистка предыдущей статистики
        for widget in [self.stats_frame_left, self.stats_frame_right]:
            for child in widget.winfo_children():
                child.destroy()

        if not self.students:
            return

        # Сбор общей статистики
        all_grades = []
        student_means = []

        for student in self.students:
            valid_grades = [g for g in student.grades if g is not None]
            all_grades.extend(valid_grades)
            if valid_grades:
                student_means.append(student.statistics['mean'])

        if not all_grades:
            ttk.Label(self.stats_frame_left, text="❌ Нет данных для отображения").pack()
            return

        # Левая колонка - основная статистика
        ttk.Label(self.stats_frame_left, text="📊 Основные показатели",
                  style='Heading.TLabel').pack(anchor=tk.W, pady=5)

        stats_items = [
            ("👥 Всего учеников:", f"{len(self.students)}"),
            ("📝 Всего работ:", f"{len(all_grades)}"),
            ("📊 Общий средний балл:", f"{np.mean(all_grades):.2f}"),
            ("📈 Медиана:", f"{np.median(all_grades):.2f}"),
            ("📉 Минимум:", f"{np.min(all_grades)}"),
            ("📈 Максимум:", f"{np.max(all_grades)}"),
            ("📊 Среднее по ученикам:", f"{np.mean(student_means):.2f}"),
        ]

        for label, value in stats_items:
            frame = ttk.Frame(self.stats_frame_left)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label, width=25, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=value, font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        if self.is_grades_mode:
            passed = len([g for g in all_grades if g >= 3])
            failed = len([g for g in all_grades if g < 3])

            ttk.Separator(self.stats_frame_left, orient='horizontal').pack(fill=tk.X, pady=10)
            ttk.Label(self.stats_frame_left, text="✅ Качество знаний",
                      style='Heading.TLabel').pack(anchor=tk.W, pady=5)

            quality_items = [
                ("Успешных работ:", f"{passed} ({passed / len(all_grades) * 100:.1f}%)"),
                ("Неуд. работ:", f"{failed} ({failed / len(all_grades) * 100:.1f}%)"),
                ("Качество знаний:", f"{(passed - failed) / len(all_grades) * 100:.1f}%"),
            ]

            for label, value in quality_items:
                frame = ttk.Frame(self.stats_frame_left)
                frame.pack(fill=tk.X, pady=2)
                ttk.Label(frame, text=label, width=25, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(frame, text=value, font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        # Правая колонка - распределение
        ttk.Label(self.stats_frame_right, text="📊 Распределение по уровням",
                  style='Heading.TLabel').pack(anchor=tk.W, pady=5)

        # Категории учеников
        high_achievers = len([s for s in self.students if s.statistics['mean'] >= 4.5])
        good_achievers = len([s for s in self.students if 4 <= s.statistics['mean'] < 4.5])
        average = len([s for s in self.students if 3 <= s.statistics['mean'] < 4])
        low_achievers = len([s for s in self.students if s.statistics['mean'] < 3])

        categories = [
            ("🏆 Отличники (>4.5):", high_achievers, "green"),
            ("📚 Хорошисты (4-4.5):", good_achievers, "blue"),
            ("📖 Троечники (3-4):", average, "orange"),
            ("⚠️ Неуспевающие (<3):", low_achievers, "red"),
        ]

        for label, count, color in categories:
            frame = ttk.Frame(self.stats_frame_right)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label, width=20, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=str(count), foreground=color,
                      font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        # Динамика
        ttk.Separator(self.stats_frame_right, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(self.stats_frame_right, text="📈 Динамика",
                  style='Heading.TLabel').pack(anchor=tk.W, pady=5)

        trends = {}
        for student in self.students:
            trends[student.statistics['trend']] = trends.get(student.statistics['trend'], 0) + 1

        for trend, count in trends.items():
            color = "green" if trend == "Положительная" else "orange" if trend == "Стабильная" else "red"
            frame = ttk.Frame(self.stats_frame_right)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{trend}:", width=20, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=str(count), foreground=color,
                      font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        # Общий график
        self.plot_general_stats(all_grades)

    def plot_general_stats(self, all_grades):
        """Улучшенное построение общего графика с читаемыми именами"""
        self.general_figure.clear()

        if not all_grades:
            return

        # Создаем 2x2 сетку графиков
        gs = self.general_figure.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # График 1: Распределение оценок/баллов
        ax1 = self.general_figure.add_subplot(gs[0, 0])

        if self.is_grades_mode and max(all_grades) <= 5:
            # Для оценок 2-5
            grades_count = {2: 0, 3: 0, 4: 0, 5: 0}
            for g in all_grades:
                if int(g) in grades_count:
                    grades_count[int(g)] += 1

            grades = list(grades_count.keys())
            counts = list(grades_count.values())
            colors = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff']
            bars = ax1.bar(grades, counts, color=colors, edgecolor='black', linewidth=1.5)

            # Добавление значений на столбцы
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width() / 2., height,
                         f'{int(height)}', ha='center', va='bottom', fontsize=10)

            ax1.set_xlabel('Оценка', fontsize=11)
            ax1.set_ylabel('Количество', fontsize=11)
            ax1.set_title('Распределение оценок', fontsize=12, fontweight='bold')
            ax1.set_xticks(grades)
        else:
            # Для баллов
            n, bins, patches = ax1.hist(all_grades, bins=15, edgecolor='black',
                                        alpha=0.7, color='#4d96ff', linewidth=1.5)
            ax1.set_xlabel('Баллы', fontsize=11)
            ax1.set_ylabel('Частота', fontsize=11)
            ax1.set_title('Распределение баллов', fontsize=12, fontweight='bold')

        ax1.grid(True, alpha=0.3)

        # График 2: Средние баллы учеников (с прокруткой если много)
        ax2 = self.general_figure.add_subplot(gs[0, 1])

        # Сортируем учеников по среднему баллу
        sorted_students = sorted(self.students, key=lambda x: x.statistics['mean'], reverse=True)

        # Если учеников много, показываем только топ и дно
        if len(sorted_students) > 20:
            # Берем топ-10 и дно-10
            top_students = sorted_students[:10]
            bottom_students = sorted_students[-10:]
            display_students = top_students + bottom_students
            title = f'Топ-10 и последние 10 учеников (всего: {len(sorted_students)})'
        else:
            display_students = sorted_students
            title = 'Средние баллы учеников'

        names = []
        means = []
        colors = []

        for student in display_students:
            # Сокращаем имя для читаемости
            name_parts = student.name.split()
            if len(name_parts) >= 2:
                short_name = f"{name_parts[0]} {name_parts[1][0]}."
            else:
                short_name = student.name[:15] + "..." if len(student.name) > 15 else student.name

            names.append(short_name)
            mean_val = student.statistics['mean']
            means.append(mean_val)

            if mean_val < 3:
                colors.append('#ff6b6b')
            elif mean_val < 4:
                colors.append('#ffd93d')
            else:
                colors.append('#6bcb77')

        # Используем горизонтальные бары для лучшей читаемости имен
        y_pos = np.arange(len(names))
        bars = ax2.barh(y_pos, means, color=colors, edgecolor='black', linewidth=1)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(names, fontsize=9)
        ax2.set_xlabel('Средний балл', fontsize=11)
        ax2.set_title(title, fontsize=12, fontweight='bold')

        # Добавляем значения
        for i, (bar, val) in enumerate(zip(bars, means)):
            ax2.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                     f'{val:.2f}', va='center', fontsize=8)

        ax2.grid(True, alpha=0.3, axis='x')

        # График 3: Ящик с усами
        ax3 = self.general_figure.add_subplot(gs[1, 0])

        # Группируем по классам если есть
        if self.classes and len(self.classes) <= 10:
            # Показываем по классам
            class_data = []
            class_names = []

            for class_name, students in sorted(self.classes.items()):
                class_grades = []
                for student in students:
                    class_grades.extend([g for g in student.grades if g is not None])
                if class_grades:
                    class_data.append(class_grades)
                    class_names.append(str(class_name))

            if class_data:
                bp = ax3.boxplot(class_data, labels=class_names, patch_artist=True)
                for box in bp['boxes']:
                    box.set_facecolor('#4d96ff')
                    box.set_alpha(0.7)
                ax3.set_xlabel('Класс', fontsize=11)
                ax3.set_title('Распределение по классам', fontsize=12, fontweight='bold')
        else:
            # Показываем по ученикам (первые 15)
            student_grades = []
            student_names = []

            for student in sorted(self.students, key=lambda x: x.statistics['mean'], reverse=True)[:15]:
                valid = [g for g in student.grades if g is not None]
                if valid:
                    student_grades.append(valid)
                    # Сокращаем имя
                    name_parts = student.name.split()
                    short_name = name_parts[0] if name_parts else student.name
                    if len(short_name) > 10:
                        short_name = short_name[:8] + "."
                    student_names.append(short_name)

            if student_grades:
                bp = ax3.boxplot(student_grades, labels=student_names, patch_artist=True)
                for box in bp['boxes']:
                    box.set_facecolor('#4d96ff')
                    box.set_alpha(0.7)
                ax3.set_xlabel('Ученики', fontsize=11)
                ax3.set_title('Топ-15 учеников (разброс)', fontsize=12, fontweight='bold')
                ax3.tick_params(axis='x', rotation=45)

        ax3.set_ylabel('Оценки/Баллы', fontsize=11)
        ax3.grid(True, alpha=0.3, axis='y')

        # График 4: Динамика успеваемости
        ax4 = self.general_figure.add_subplot(gs[1, 1])

        trends = {'Положительная': 0, 'Стабильная': 0, 'Отрицательная': 0, 'Недостаточно данных': 0}
        for student in self.students:
            trends[student.statistics['trend']] += 1

        colors_trend = {
            'Положительная': '#6bcb77',
            'Стабильная': '#4d96ff',
            'Отрицательная': '#ff6b6b',
            'Недостаточно данных': '#95a5a6'
        }

        # Убираем нулевые значения
        labels = []
        sizes = []
        colors_list = []

        for key, value in trends.items():
            if value > 0:
                labels.append(key)
                sizes.append(value)
                colors_list.append(colors_trend[key])

        if sizes:
            wedges, texts, autotexts = ax4.pie(
                sizes,
                labels=labels,
                colors=colors_list,
                autopct='%1.1f%%',
                startangle=90,
                textprops={'fontsize': 10}
            )

            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

        ax4.set_title('Динамика успеваемости', fontsize=12, fontweight='bold')

        self.general_figure.tight_layout()
        self.general_canvas.draw()

    def setup_styles(self):
        """Настройка стилей для виджетов"""
        style = ttk.Style()
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Info.TLabel', font=('Arial', 10))

        # Настройка цветов для проблемных учеников
        style.configure('Problem.TLabel', foreground='red', font=('Arial', 10, 'bold'))
        style.configure('Warning.TLabel', foreground='orange', font=('Arial', 10))
        style.configure('Success.TLabel', foreground='green', font=('Arial', 10))

    def create_widgets(self):
        """Создание элементов интерфейса"""
        # Верхняя панель с кнопками
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        # Первая строка кнопок
        button_frame1 = ttk.Frame(top_frame)
        button_frame1.pack(fill=tk.X, pady=2)

        ttk.Button(button_frame1, text="📂 Загрузить файл",
                   command=self.load_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame1, text="💾 Сохранить данные",
                   command=self.save_current_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame1, text="📂 Загрузить сохраненные",
                   command=self.load_saved_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame1, text="🗑️ Очистить все",
                   command=self.clear_all_data).pack(side=tk.LEFT, padx=2)

        # Вторая строка кнопок
        button_frame2 = ttk.Frame(top_frame)
        button_frame2.pack(fill=tk.X, pady=2)

        ttk.Button(button_frame2, text="🔄 Обновить аналитику",
                   command=self.update_analytics).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame2, text="📊 Пример данных",
                   command=self.load_sample_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame2, text="✏️ Редактировать классы",
                   command=self.open_batch_editor).pack(side=tk.LEFT, padx=2)

        # Информация о файле
        info_frame = ttk.Frame(top_frame)
        info_frame.pack(fill=tk.X, pady=5)

        self.file_label = ttk.Label(info_frame, text="Файл не загружен", foreground="gray")
        self.file_label.pack(side=tk.LEFT, padx=5)

        self.mode_label = ttk.Label(info_frame, text="", foreground="blue")
        self.mode_label.pack(side=tk.LEFT, padx=20)

        self.stats_label = ttk.Label(info_frame, text="", foreground="green")
        self.stats_label.pack(side=tk.RIGHT, padx=5)

        # Основная область с вкладками
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Вкладки
        self.general_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.general_frame, text="📊 Общая аналитика")
        self.create_general_tab()

        self.students_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.students_frame, text="👥 По ученикам")
        self.create_students_tab()

        self.charts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.charts_frame, text="📈 Визуализация")
        self.create_charts_tab()

        self.problems_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.problems_frame, text="⚠️ Проблемные ученики")
        self.create_problems_tab()

        self.classes_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.classes_frame, text="🏫 По классам")
        self.create_classes_tab()

        # Нижняя панель с логами
        bottom_frame = ttk.Frame(self.root, padding="5")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.log_text = scrolledtext.ScrolledText(bottom_frame, height=5, width=100,
                                                  font=('Consolas', 9), bg='#f0f0f0')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log("✅ Программа запущена. Загрузите файл с данными.")

    def open_batch_editor(self):
        """Открытие редактора для пакетного назначения классов"""
        if not self.students:
            messagebox.showwarning("Предупреждение", "Нет данных для редактирования")
            return

        editor = BatchClassEditor(self)
        editor.show_editor()

    def create_classes_tab(self):
        """Создание вкладки аналитики по классам"""
        # Верхняя панель с информацией
        info_frame = ttk.Frame(self.classes_frame)
        info_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(info_frame, text="Аналитика по классам", style='Title.TLabel').pack()

        # Панель управления
        control_frame = ttk.Frame(self.classes_frame)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(control_frame, text="Сортировка:").pack(side=tk.LEFT)
        self.class_sort_var = tk.StringVar(value="name")
        ttk.Radiobutton(control_frame, text="По имени", variable=self.class_sort_var,
                        value="name", command=self.update_classes_list).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(control_frame, text="По среднему баллу", variable=self.class_sort_var,
                        value="avg", command=self.update_classes_list).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(control_frame, text="По количеству учеников", variable=self.class_sort_var,
                        value="count", command=self.update_classes_list).pack(side=tk.LEFT, padx=5)

        # Основная область с прокруткой
        main_container = ttk.Frame(self.classes_frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель - список классов
        left_frame = ttk.Frame(main_container, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        left_frame.pack_propagate(False)

        ttk.Label(left_frame, text="Список классов", style='Heading.TLabel').pack(anchor=tk.W)

        # Список классов с прокруткой
        list_container = ttk.Frame(left_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.class_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar.set,
                                        height=20, font=('Arial', 11))
        self.class_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.class_listbox.yview)
        self.class_listbox.bind('<<ListboxSelect>>', self.on_class_select)

        # Правая панель с информацией
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        # Notebook для правой панели
        class_notebook = ttk.Notebook(right_frame)
        class_notebook.pack(fill=tk.BOTH, expand=True)

        # Вкладка с общей информацией
        info_tab = ttk.Frame(class_notebook)
        class_notebook.add(info_tab, text="📊 Общая информация")

        # Текстовая информация о классе с прокруткой
        text_frame = ttk.Frame(info_tab)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.class_info_text = scrolledtext.ScrolledText(text_frame, height=15,
                                                         font=('Consolas', 11), wrap=tk.WORD)
        self.class_info_text.pack(fill=tk.BOTH, expand=True)

        # Вкладка с графиками
        charts_tab = ttk.Frame(class_notebook)
        class_notebook.add(charts_tab, text="📈 Графики")

        # Создаем место для нескольких графиков
        self.class_figure = plt.Figure(figsize=(12, 8), dpi=100)
        self.class_canvas = FigureCanvasTkAgg(self.class_figure, charts_tab)
        self.class_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Вкладка со списком учеников
        students_tab = ttk.Frame(class_notebook)
        class_notebook.add(students_tab, text="👥 Ученики класса")

        self.class_students_text = scrolledtext.ScrolledText(students_tab, height=20,
                                                             font=('Consolas', 11), wrap=tk.WORD)
        self.class_students_text.pack(fill=tk.BOTH, expand=True)

        # Вкладка с динамикой
        dynamics_tab = ttk.Frame(class_notebook)
        class_notebook.add(dynamics_tab, text="📉 Динамика")

        self.class_dynamics_text = scrolledtext.ScrolledText(dynamics_tab, height=20,
                                                             font=('Consolas', 11), wrap=tk.WORD)
        self.class_dynamics_text.pack(fill=tk.BOTH, expand=True)

    def update_students_list(self):
        """Обновление списка учеников в интерфейсе"""
        try:
            self.students_listbox.delete(0, tk.END)

            if not self.students:
                self.log("⚠️ Список учеников пуст")
                return

            # ОТЛАДКА: выводим информацию о всех учениках
            self.log(f"📊 Всего учеников: {len(self.students)}")
            class_set = set()
            for student in self.students:
                class_name = student.student_class if student.student_class else "Без класса"
                class_set.add(class_name)
            self.log(f"📚 Найдено классов: {len(class_set)}: {sorted(class_set)}")

            # Сортируем учеников по классу и имени
            sorted_students = sorted(self.students, key=lambda x: (x.student_class or 'ZZZ', x.name))

            current_class = None

            for student in sorted_students:
                # Определяем класс для отображения
                display_class = student.student_class if student.student_class else "Без класса"

                # Добавляем разделитель для нового класса
                if display_class != current_class:
                    current_class = display_class
                    display_text = f"📚 КЛАСС {display_class}"
                    self.students_listbox.insert(tk.END, display_text)
                    self.students_listbox.itemconfig(tk.END, fg='blue', font=('Arial', 10, 'bold'))

                # Добавляем ученика с индикатором проблемы
                prefix = ""

                try:
                    # Безопасное получение статистики
                    if hasattr(student, 'statistics') and student.statistics:
                        mean = student.statistics.get('mean', 0)
                        trend = student.statistics.get('trend', '')
                    else:
                        mean = 0
                        trend = ''

                    if mean < 3:
                        prefix = "⚠️ "
                    elif trend == 'Отрицательная':
                        prefix = "📉 "
                except:
                    prefix = "❓ "

                # Формируем отображаемое имя
                display_name = student.name
                if len(display_name) > 45:
                    display_name = display_name[:42] + "..."

                self.students_listbox.insert(tk.END, f"   {prefix}{display_name}")

            # Добавляем информацию о количестве учеников
            self.students_listbox.insert(tk.END, "")
            self.students_listbox.insert(tk.END, f"📊 Всего учеников: {len(self.students)}")
            self.students_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 9, 'italic'))

            self.log(f"✅ Список учеников обновлен: {len(self.students)} учеников")

        except Exception as e:
            self.log(f"⚠️ Ошибка обновления списка учеников: {e}")
            import traceback
            traceback.print_exc()

    def update_classes_list(self):
        """Обновление списка классов с сортировкой"""
        try:
            if not hasattr(self, 'classes') or not self.classes:
                self.class_listbox.delete(0, tk.END)
                self.class_listbox.insert(tk.END, "📭 Нет данных о классах")
                return

            self.class_listbox.delete(0, tk.END)

            # ОТЛАДКА: выводим информацию о классах
            self.log(f"📚 Классы в словаре classes: {list(self.classes.keys())}")

            stats = self.get_class_statistics()
            sort_by = self.class_sort_var.get()

            # Получаем список всех классов
            all_classes = list(self.classes.keys())

            if sort_by == 'name':
                items = sorted(all_classes)
            elif sort_by == 'avg':
                items = sorted(all_classes,
                               key=lambda x: stats.get(x, {}).get('avg_class_mean', 0),
                               reverse=True)
            elif sort_by == 'count':
                items = sorted(all_classes,
                               key=lambda x: len(self.classes[x]),
                               reverse=True)

            for class_name in items:
                students = self.classes[class_name]
                class_stats = stats.get(class_name, {})
                avg = class_stats.get('avg_class_mean', 0)
                count = len(students)

                # Определяем цвет и иконку
                if avg >= 4.5:
                    prefix = "🏆 "
                    color = 'green'
                elif avg >= 4:
                    prefix = "📚 "
                    color = 'dark green'
                elif avg >= 3:
                    prefix = "📖 "
                    color = 'blue'
                else:
                    prefix = "⚠️ "
                    color = 'red'

                display = f"{prefix}{class_name}  |  {count} уч.  |  ср.{avg:.2f}"

                # Добавляем информацию о распределении
                dist = class_stats.get('distribution', {})
                if dist:
                    excellent = dist.get('excellent', 0)
                    good = dist.get('good', 0)
                    poor = dist.get('poor', 0)
                    if excellent > 0 or good > 0 or poor > 0:
                        display += f"  [👍{excellent} 👎{poor}]"

                idx = self.class_listbox.insert(tk.END, display)
                self.class_listbox.itemconfig(idx, fg=color, font=('Arial', 10, 'bold'))

            # Добавляем информацию о количестве
            self.class_listbox.insert(tk.END, "")
            self.class_listbox.insert(tk.END, f"📊 Всего классов: {len(self.classes)}")
            self.class_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 9, 'italic'))

            self.log(f"✅ Список классов обновлен: {len(self.classes)} классов")

        except Exception as e:
            self.log(f"⚠️ Ошибка обновления списка классов: {e}")
            import traceback
            traceback.print_exc()

    def on_student_select(self, event):
        """Обработка выбора ученика из списка"""
        try:
            selection = self.students_listbox.curselection()
            if not selection:
                return

            index = selection[0]
            item_text = self.students_listbox.get(index)

            # Пропускаем заголовки классов
            if item_text.startswith("📚") or item_text.startswith("📊"):
                return

            # Очищаем имя от префиксов и отступов
            clean_name = item_text
            # Убираем префиксы
            for prefix in ["⚠️ ", "📉 ", "❓ ", "   "]:
                clean_name = clean_name.replace(prefix, "")
            clean_name = clean_name.strip()

            self.log(f"🔍 Ищем ученика: '{clean_name}'")

            # Поиск ученика по имени
            found_student = None
            for student in self.students:
                if student.name == clean_name:
                    found_student = student
                    break
                # Проверяем, начинается ли имя ученика с искомого (для сокращенных имен)
                if clean_name in student.name and len(clean_name) > 10:
                    found_student = student
                    break

            if found_student:
                self.log(f"✅ Найден ученик: {found_student.name}")
                self.show_student_info(found_student)
            else:
                self.log(f"❌ Ученик не найден: {clean_name}")

        except Exception as e:
            self.log(f"⚠️ Ошибка выбора ученика: {e}")
            import traceback
            traceback.print_exc()

    def on_class_select(self, event):
        """Обработка выбора класса"""
        try:
            selection = self.class_listbox.curselection()
            if not selection:
                return

            index = selection[0]
            item_text = self.class_listbox.get(index)

            # Пропускаем информационные строки
            if item_text.startswith("📊"):
                return

            # Извлекаем название класса из строки
            # Формат: "🏆 5А  |  30 уч.  |  ср.4.52"
            parts = item_text.split('|')
            if len(parts) > 0:
                # Убираем иконку и пробелы
                class_part = parts[0].strip()
                # Убираем эмодзи в начале
                class_name = class_part.split(' ', 1)[-1] if ' ' in class_part else class_part
                class_name = class_name.strip()

                self.log(f"🔍 Выбран класс: '{class_name}'")

                if class_name in self.classes:
                    self.show_class_info(class_name)
                else:
                    self.log(f"❌ Класс '{class_name}' не найден в словаре classes")

        except Exception as e:
            self.log(f"⚠️ Ошибка выбора класса: {e}")
            import traceback
            traceback.print_exc()

    def filter_students(self, *args):
        """Фильтрация списка учеников по поиску"""
        try:
            search_term = self.search_var.get().lower()
            self.students_listbox.delete(0, tk.END)

            if not self.students:
                return

            # Фильтруем учеников по поисковому запросу
            filtered_students = []
            for student in self.students:
                if search_term in student.name.lower():
                    filtered_students.append(student)
                elif student.student_class and search_term in student.student_class.lower():
                    filtered_students.append(student)

            # Если ничего не найдено, показываем всех
            if not filtered_students and search_term:
                self.students_listbox.insert(tk.END, f"🔍 Ничего не найдено по запросу '{search_term}'")
                self.students_listbox.itemconfig(tk.END, fg='gray')
                return
            elif not filtered_students:
                filtered_students = self.students

            # Сортируем по классу и имени
            sorted_students = sorted(filtered_students, key=lambda x: (x.student_class or 'ZZZ', x.name))

            current_class = None

            for student in sorted_students:
                display_class = student.student_class if student.student_class else "Без класса"

                if display_class != current_class:
                    current_class = display_class
                    display_text = f"📚 КЛАСС {display_class}"
                    self.students_listbox.insert(tk.END, display_text)
                    self.students_listbox.itemconfig(tk.END, fg='blue', font=('Arial', 10, 'bold'))

                # Добавляем ученика
                prefix = ""
                try:
                    if hasattr(student, 'statistics') and student.statistics:
                        mean = student.statistics.get('mean', 0)
                        if mean < 3:
                            prefix = "⚠️ "
                except:
                    pass

                display_name = student.name
                if len(display_name) > 45:
                    display_name = display_name[:42] + "..."

                self.students_listbox.insert(tk.END, f"   {prefix}{display_name}")

            # Информация о количестве
            self.students_listbox.insert(tk.END, "")
            self.students_listbox.insert(tk.END,
                                         f"📊 Показано: {len(filtered_students)} из {len(self.students)} учеников")
            self.students_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 9, 'italic'))

        except Exception as e:
            self.log(f"⚠️ Ошибка фильтрации: {e}")

    def on_student_select(self, event):
        """Обработка выбора ученика из списка"""
        try:
            selection = self.students_listbox.curselection()
            if not selection:
                return

            index = selection[0]
            item_text = self.students_listbox.get(index)

            # Пропускаем заголовки классов и информационные строки
            if item_text.startswith("📚") or item_text.startswith("📊"):
                return

            # Убираем префиксы и отступы
            student_name = item_text.replace("⚠️ ", "").replace("📉 ", "").replace("❓ ", "").strip()
            if student_name.startswith("   "):
                student_name = student_name[3:]  # Убираем отступы

            # Поиск ученика по имени
            found_student = None
            for student in self.students:
                if student.name == student_name:
                    found_student = student
                    break
                # Также проверяем по сокращенному имени
                if len(student_name) < len(student.name) and student.name.startswith(student_name):
                    found_student = student
                    break

            if found_student:
                self.show_student_info(found_student)
        except Exception as e:
            self.log(f"⚠️ Ошибка выбора ученика: {e}")

    def update_charts(self):
        """Обновление дополнительных графиков с масштабированием"""
        if not self.students:
            return

        self.chart1_figure.clear()
        self.chart2_figure.clear()

        # График 1: Средние баллы учеников (с масштабированием)
        ax1 = self.chart1_figure.add_subplot(111)

        # Определяем количество учеников для отображения
        num_students = len(self.students)

        # Динамически определяем размер графика
        if num_students <= 10:
            # Мало учеников - показываем всех
            display_students = self.students
            fig_height = 5
            font_size = 10
        elif num_students <= 20:
            # Среднее количество - показываем всех, но с уменьшенным шрифтом
            display_students = self.students
            fig_height = 6
            font_size = 9
        elif num_students <= 30:
            # Много учеников - показываем топ-15 и последние 15
            sorted_students = sorted(self.students, key=lambda x: x.statistics['mean'])
            top_15 = sorted_students[-15:]
            bottom_15 = sorted_students[:15]
            display_students = top_15 + bottom_15
            fig_height = 7
            font_size = 8
            ax1.set_title(f'Топ-15 и последние 15 учеников (всего: {num_students})', fontsize=12, fontweight='bold')
        else:
            # Очень много учеников - показываем только топ-20 и последние 20
            sorted_students = sorted(self.students, key=lambda x: x.statistics['mean'])
            top_20 = sorted_students[-20:]
            bottom_20 = sorted_students[:20]
            display_students = top_20 + bottom_20
            fig_height = 8
            font_size = 7
            ax1.set_title(f'Топ-20 и последние 20 учеников (всего: {num_students})', fontsize=12, fontweight='bold')

        names = []
        means = []
        colors = []

        for student in display_students:
            # Сокращаем имя для читаемости
            name_parts = student.name.split()
            if len(name_parts) >= 2:
                short_name = f"{name_parts[0]} {name_parts[1][0]}."
            else:
                short_name = student.name[:12] + "..." if len(student.name) > 12 else student.name

            names.append(short_name)
            mean_val = student.statistics['mean']
            means.append(mean_val)

            if mean_val < 3:
                colors.append('#ff6b6b')  # красный
            elif mean_val < 4:
                colors.append('#ffd93d')  # желтый
            else:
                colors.append('#6bcb77')  # зеленый

        # Используем горизонтальные бары для лучшей читаемости
        y_pos = np.arange(len(names))
        bars = ax1.barh(y_pos, means, color=colors, edgecolor='black', linewidth=1)
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(names, fontsize=font_size)
        ax1.set_xlabel('Средний балл', fontsize=11)

        if 'title' not in ax1.get_title():
            ax1.set_title('Распределение средних баллов', fontsize=12, fontweight='bold')

        # Вертикальная линия общего среднего
        overall_mean = np.mean([s.statistics['mean'] for s in self.students])
        ax1.axvline(x=overall_mean, color='red', linestyle='--', linewidth=2,
                    label=f'Общее среднее: {overall_mean:.2f}')
        ax1.legend(fontsize=9)

        # Добавление значений (только если не слишком много)
        if len(means) <= 30:
            for i, (bar, val) in enumerate(zip(bars, means)):
                ax1.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
                         f'{val:.2f}', va='center', fontsize=font_size - 1)

        # График 2: Динамика успеваемости
        ax2 = self.chart2_figure.add_subplot(111)

        trends = {'Положительная': 0, 'Стабильная': 0, 'Отрицательная': 0, 'Недостаточно данных': 0}
        for student in self.students:
            trends[student.statistics['trend']] += 1

        colors_trend = {
            'Положительная': '#6bcb77',
            'Стабильная': '#4d96ff',
            'Отрицательная': '#ff6b6b',
            'Недостаточно данных': '#95a5a6'
        }

        # Убираем нулевые значения
        labels = []
        sizes = []
        colors_list = []

        for key, value in trends.items():
            if value > 0:
                labels.append(key)
                sizes.append(value)
                colors_list.append(colors_trend[key])

        if sizes:
            wedges, texts, autotexts = ax2.pie(
                sizes,
                labels=labels,
                colors=colors_list,
                autopct='%1.1f%%',
                startangle=90,
                textprops={'fontsize': 10}
            )

            # Настройка текста процентов
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

        ax2.set_title('Распределение динамики успеваемости', fontsize=12, fontweight='bold')

        # Настраиваем размер фигур в зависимости от количества данных
        self.chart1_figure.set_figheight(fig_height)
        self.chart1_figure.set_figwidth(8)
        self.chart2_figure.set_figheight(5)
        self.chart2_figure.set_figwidth(8)

        self.chart1_figure.tight_layout()
        self.chart2_figure.tight_layout()
        self.chart1_canvas.draw()
        self.chart2_canvas.draw()

    def plot_general_stats(self, all_grades):
        """Улучшенное построение общего графика с масштабированием"""
        self.general_figure.clear()

        if not all_grades:
            return

        # Определяем количество учеников для масштабирования
        num_students = len(self.students)

        # Создаем сетку графиков с динамическими размерами
        if num_students <= 20:
            # Мало учеников - стандартные графики
            gs = self.general_figure.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
            fig_height = 6
        else:
            # Много учеников - увеличиваем высоту для лучшей читаемости
            gs = self.general_figure.add_gridspec(2, 2, hspace=0.4, wspace=0.3)
            fig_height = 8

        self.general_figure.set_figheight(fig_height)
        self.general_figure.set_figwidth(12)

        # График 1: Распределение оценок/баллов
        ax1 = self.general_figure.add_subplot(gs[0, 0])

        if self.is_grades_mode and max(all_grades) <= 5:
            # Для оценок 2-5
            grades_count = {2: 0, 3: 0, 4: 0, 5: 0}
            for g in all_grades:
                if int(g) in grades_count:
                    grades_count[int(g)] += 1

            grades = list(grades_count.keys())
            counts = list(grades_count.values())
            colors = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff']
            bars = ax1.bar(grades, counts, color=colors, edgecolor='black', linewidth=1.5)

            # Добавление значений на столбцы
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width() / 2., height,
                         f'{int(height)}', ha='center', va='bottom', fontsize=10)

            ax1.set_xlabel('Оценка', fontsize=11)
            ax1.set_ylabel('Количество', fontsize=11)
            ax1.set_title('Распределение оценок', fontsize=12, fontweight='bold')
            ax1.set_xticks(grades)
        else:
            # Для баллов
            n, bins, patches = ax1.hist(all_grades, bins=min(15, len(set(all_grades))),
                                        edgecolor='black', alpha=0.7, color='#4d96ff', linewidth=1.5)
            ax1.set_xlabel('Баллы', fontsize=11)
            ax1.set_ylabel('Частота', fontsize=11)
            ax1.set_title('Распределение баллов', fontsize=12, fontweight='bold')

        ax1.grid(True, alpha=0.3)

        # График 2: Средние баллы учеников (с масштабированием)
        ax2 = self.general_figure.add_subplot(gs[0, 1])

        # Сортируем учеников по среднему баллу
        sorted_students = sorted(self.students, key=lambda x: x.statistics['mean'], reverse=True)

        # Динамически определяем, сколько учеников показывать
        if num_students <= 15:
            display_students = sorted_students
            title = 'Средние баллы учеников'
            font_size = 9
        elif num_students <= 30:
            # Берем топ-10 и дно-10
            top_students = sorted_students[:10]
            bottom_students = sorted_students[-10:]
            display_students = top_students + bottom_students
            title = f'Топ-10 и последние 10 учеников (всего: {num_students})'
            font_size = 8
        else:
            # Берем топ-15 и дно-15
            top_students = sorted_students[:15]
            bottom_students = sorted_students[-15:]
            display_students = top_students + bottom_students
            title = f'Топ-15 и последние 15 учеников (всего: {num_students})'
            font_size = 7

        names = []
        means = []
        colors = []

        for student in display_students:
            # Сокращаем имя для читаемости
            name_parts = student.name.split()
            if len(name_parts) >= 2:
                short_name = f"{name_parts[0]} {name_parts[1][0]}."
            else:
                short_name = student.name[:10] + "..." if len(student.name) > 10 else student.name

            names.append(short_name)
            mean_val = student.statistics['mean']
            means.append(mean_val)

            if mean_val < 3:
                colors.append('#ff6b6b')
            elif mean_val < 4:
                colors.append('#ffd93d')
            else:
                colors.append('#6bcb77')

        # Используем горизонтальные бары
        y_pos = np.arange(len(names))
        bars = ax2.barh(y_pos, means, color=colors, edgecolor='black', linewidth=1)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(names, fontsize=font_size)
        ax2.set_xlabel('Средний балл', fontsize=11)
        ax2.set_title(title, fontsize=12, fontweight='bold')

        # Добавляем значения (если не слишком много)
        if len(means) <= 30:
            for i, (bar, val) in enumerate(zip(bars, means)):
                ax2.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                         f'{val:.2f}', va='center', fontsize=font_size - 1)

        ax2.grid(True, alpha=0.3, axis='x')

        # Остальные графики остаются без изменений
        # График 3: Ящик с усами
        ax3 = self.general_figure.add_subplot(gs[1, 0])

        # Группируем по классам если есть
        if self.classes and len(self.classes) <= 10:
            # Показываем по классам
            class_data = []
            class_names = []

            for class_name, students in sorted(self.classes.items()):
                class_grades = []
                for student in students:
                    class_grades.extend([g for g in student.grades if g not in [None, "н"]])
                if class_grades:
                    class_data.append(class_grades)
                    class_names.append(str(class_name))

            if class_data:
                bp = ax3.boxplot(class_data, labels=class_names, patch_artist=True)
                for box in bp['boxes']:
                    box.set_facecolor('#4d96ff')
                    box.set_alpha(0.7)
                ax3.set_xlabel('Класс', fontsize=11)
                ax3.set_title('Распределение по классам', fontsize=12, fontweight='bold')
                ax3.tick_params(axis='x', rotation=45)
        else:
            # Показываем по ученикам (топ-10)
            student_grades = []
            student_names = []

            for student in sorted(self.students, key=lambda x: x.statistics['mean'], reverse=True)[:10]:
                valid = [g for g in student.grades if g not in [None, "н"]]
                if valid:
                    student_grades.append(valid)
                    # Сокращаем имя
                    name_parts = student.name.split()
                    short_name = name_parts[0] if name_parts else student.name
                    if len(short_name) > 8:
                        short_name = short_name[:6] + "."
                    student_names.append(short_name)

            if student_grades:
                bp = ax3.boxplot(student_grades, labels=student_names, patch_artist=True)
                for box in bp['boxes']:
                    box.set_facecolor('#4d96ff')
                    box.set_alpha(0.7)
                ax3.set_xlabel('Топ-10 учеников', fontsize=11)
                ax3.set_title('Разброс оценок (топ-10)', fontsize=12, fontweight='bold')
                ax3.tick_params(axis='x', rotation=45)

        ax3.set_ylabel('Оценки/Баллы', fontsize=11)
        ax3.grid(True, alpha=0.3, axis='y')

        # График 4: Динамика успеваемости
        ax4 = self.general_figure.add_subplot(gs[1, 1])

        trends = {'Положительная': 0, 'Стабильная': 0, 'Отрицательная': 0, 'Недостаточно данных': 0}
        for student in self.students:
            trends[student.statistics['trend']] += 1

        colors_trend = {
            'Положительная': '#6bcb77',
            'Стабильная': '#4d96ff',
            'Отрицательная': '#ff6b6b',
            'Недостаточно данных': '#95a5a6'
        }

        # Убираем нулевые значения
        labels = []
        sizes = []
        colors_list = []

        for key, value in trends.items():
            if value > 0:
                labels.append(key)
                sizes.append(value)
                colors_list.append(colors_trend[key])

        if sizes:
            wedges, texts, autotexts = ax4.pie(
                sizes,
                labels=labels,
                colors=colors_list,
                autopct='%1.1f%%',
                startangle=90,
                textprops={'fontsize': 10}
            )

            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

        ax4.set_title('Динамика успеваемости', fontsize=12, fontweight='bold')

        self.general_figure.tight_layout()
        self.general_canvas.draw()

    def show_class_general_info(self, class_name, students, stats):
        """Отображение общей информации о классе"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"📚 КЛАСС {class_name}")
        lines.append("=" * 70)
        lines.append(f"👥 Всего учеников: {stats.get('count', 0)}")
        lines.append(f"📊 Средний балл класса: {stats.get('avg_class_mean', 0):.2f}")
        lines.append(f"📈 Лучший средний балл: {stats.get('max_mean', 0):.2f}")
        lines.append(f"📉 Худший средний балл: {stats.get('min_mean', 0):.2f}")

        if 'avg_grade' in stats:
            lines.append(f"📝 Средняя оценка: {stats['avg_grade']:.2f}")

        lines.append("\n📊 Распределение по успеваемости:")
        dist = stats.get('distribution', {})
        total = stats.get('count', 1)

        excellent = dist.get('excellent', 0)
        good = dist.get('good', 0)
        satisfactory = dist.get('satisfactory', 0)
        poor = dist.get('poor', 0)

        lines.append(f"  🏆 Отличники (≥4.5): {excellent} ({excellent / total * 100:.1f}%)")
        lines.append(f"  📚 Хорошисты (4-4.5): {good} ({good / total * 100:.1f}%)")
        lines.append(f"  📖 Троечники (3-4): {satisfactory} ({satisfactory / total * 100:.1f}%)")
        lines.append(f"  ⚠️ Неуспевающие (<3): {poor} ({poor / total * 100:.1f}%)")

        # Качество знаний
        quality = (excellent + good) / total * 100
        lines.append(f"\n📈 Качество знаний: {quality:.1f}%")

        # Успеваемость
        success = (excellent + good + satisfactory) / total * 100
        lines.append(f"📊 Успеваемость: {success:.1f}%")

        self.class_info_text.delete(1.0, tk.END)
        self.class_info_text.insert(1.0, "\n".join(lines))

    def plot_class_charts(self, class_name, students, stats):
        """Построение графиков для класса"""
        self.class_figure.clear()

        if len(students) <= 10:
            # Если учеников мало - один большой график
            self.plot_small_class_charts(students, class_name)
        else:
            # Если учеников много - несколько графиков
            self.plot_large_class_charts(students, class_name, stats)

    def plot_small_class_charts(self, students, class_name):
        """Графики для маленького класса (до 10 учеников)"""
        # График 1: Средние баллы учеников
        ax1 = self.class_figure.add_subplot(221)

        names = []
        means = []
        colors = []

        for student in sorted(students, key=lambda x: x.statistics['mean'], reverse=True):
            short_name = student.name.split()[0] if student.name else "Ученик"
            names.append(short_name)
            mean_val = student.statistics['mean']
            means.append(mean_val)

            if mean_val < 3:
                colors.append('#ff6b6b')
            elif mean_val < 4:
                colors.append('#ffd93d')
            else:
                colors.append('#6bcb77')

        bars = ax1.bar(range(len(names)), means, color=colors, edgecolor='black')
        ax1.set_xticks(range(len(names)))
        ax1.set_xticklabels(names, rotation=45, ha='right')
        ax1.set_ylabel('Средний балл')
        ax1.set_title(f'Успеваемость класса {class_name}')
        ax1.axhline(y=np.mean(means), color='red', linestyle='--',
                    label=f'Среднее: {np.mean(means):.2f}')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')

        # Добавление значений
        for bar, val in zip(bars, means):
            ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                     f'{val:.2f}', ha='center', va='bottom', fontsize=8)

        # График 2: Распределение оценок в классе
        ax2 = self.class_figure.add_subplot(222)

        all_grades = []
        for student in students:
            all_grades.extend([g for g in student.grades if g is not None])

        if all_grades:
            if max(all_grades) <= 5 and all(g.is_integer() for g in all_grades):
                grades_count = {2: 0, 3: 0, 4: 0, 5: 0}
                for g in all_grades:
                    if int(g) in grades_count:
                        grades_count[int(g)] += 1

                grades = list(grades_count.keys())
                counts = list(grades_count.values())
                colors_map = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff']
                ax2.bar(grades, counts, color=colors_map, edgecolor='black')
                ax2.set_xlabel('Оценка')
            else:
                ax2.hist(all_grades, bins=10, edgecolor='black', alpha=0.7, color='#4d96ff')
                ax2.set_xlabel('Баллы')

            ax2.set_ylabel('Количество')
            ax2.set_title('Распределение оценок')
            ax2.grid(True, alpha=0.3)

        # График 3: Динамика по работам
        ax3 = self.class_figure.add_subplot(223)

        # Собираем средние баллы по каждой работе
        work_avgs = []
        work_numbers = []

        if students and students[0].grades:
            num_works = len(students[0].grades)
            for work_idx in range(num_works):
                work_grades = []
                for student in students:
                    if work_idx < len(student.grades) and student.grades[work_idx] is not None:
                        work_grades.append(student.grades[work_idx])
                if work_grades:
                    work_avgs.append(np.mean(work_grades))
                    work_numbers.append(work_idx + 1)

        if work_avgs:
            ax3.plot(work_numbers, work_avgs, 'bo-', linewidth=2, markersize=8)
            ax3.set_xlabel('Номер работы')
            ax3.set_ylabel('Средний балл')
            ax3.set_title('Динамика класса')
            ax3.grid(True, alpha=0.3)

        # График 4: Сравнение с параллелью (если есть другие классы)
        ax4 = self.class_figure.add_subplot(224)

        if len(self.classes) > 1:
            class_names = []
            class_avgs = []
            colors_map = []

            for other_class, other_students in self.classes.items():
                other_means = [s.statistics['mean'] for s in other_students]
                class_names.append(str(other_class))
                class_avgs.append(np.mean(other_means))

                if other_class == class_name:
                    colors_map.append('#ff6b6b')
                else:
                    colors_map.append('#4d96ff')

            bars = ax4.bar(class_names, class_avgs, color=colors_map, edgecolor='black')
            ax4.set_xlabel('Класс')
            ax4.set_ylabel('Средний балл')
            ax4.set_title('Сравнение классов')
            ax4.grid(True, alpha=0.3, axis='y')

            # Выделяем текущий класс
            for i, (bar, is_current) in enumerate(zip(bars, [c == class_name for c in class_names])):
                if is_current:
                    bar.set_edgecolor('red')
                    bar.set_linewidth(3)

        self.class_figure.tight_layout()
        self.class_canvas.draw()

    def plot_large_class_charts(self, students, class_name, stats):
        """Графики для большого класса (более 10 учеников)"""
        # График 1: Гистограмма распределения средних баллов
        ax1 = self.class_figure.add_subplot(331)

        means = [s.statistics['mean'] for s in students]
        ax1.hist(means, bins=10, edgecolor='black', alpha=0.7, color='#4d96ff')
        ax1.axvline(x=stats.get('avg_class_mean', 0), color='red', linestyle='--',
                    linewidth=2, label=f'Среднее: {stats.get("avg_class_mean", 0):.2f}')
        ax1.set_xlabel('Средний балл')
        ax1.set_ylabel('Количество учеников')
        ax1.set_title('Распределение средних баллов')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # График 2: Ящик с усами
        ax2 = self.class_figure.add_subplot(332)

        all_grades = []
        for student in students:
            valid_grades = [g for g in student.grades if g is not None]
            if valid_grades:
                all_grades.append(valid_grades)

        if all_grades:
            bp = ax2.boxplot(all_grades, patch_artist=True)
            for box in bp['boxes']:
                box.set_facecolor('#4d96ff')
                box.set_alpha(0.7)
            ax2.set_xlabel('Ученики')
            ax2.set_ylabel('Оценки')
            ax2.set_title('Разброс оценок')
            ax2.grid(True, alpha=0.3, axis='y')

        # График 3: Круговая диаграмма успеваемости
        ax3 = self.class_figure.add_subplot(333)

        dist = stats.get('distribution', {})
        labels = ['Отличники', 'Хорошисты', 'Троечники', 'Неуспевающие']
        sizes = [
            dist.get('excellent', 0),
            dist.get('good', 0),
            dist.get('satisfactory', 0),
            dist.get('poor', 0)
        ]
        colors = ['#6bcb77', '#4d96ff', '#ffd93d', '#ff6b6b']
        explode = (0.1, 0, 0, 0.1)

        # Фильтруем нулевые значения
        filtered_labels = [l for l, s in zip(labels, sizes) if s > 0]
        filtered_sizes = [s for s in sizes if s > 0]
        filtered_colors = [c for c, s in zip(colors, sizes) if s > 0]
        filtered_explode = [e for e, s in zip(explode, sizes) if s > 0]

        if filtered_sizes:
            wedges, texts, autotexts = ax3.pie(
                filtered_sizes,
                labels=filtered_labels,
                colors=filtered_colors,
                autopct='%1.1f%%',
                startangle=90,
                explode=filtered_explode
            )
            ax3.set_title('Успеваемость')

        # График 4: Топ учеников
        ax4 = self.class_figure.add_subplot(334)

        top_students = sorted(students, key=lambda x: x.statistics['mean'], reverse=True)[:5]
        names = [s.name.split()[0] for s in top_students]
        top_means = [s.statistics['mean'] for s in top_students]

        ax4.barh(names, top_means, color='#6bcb77', edgecolor='black')
        ax4.set_xlabel('Средний балл')
        ax4.set_title('Топ-5 учеников')
        ax4.grid(True, alpha=0.3, axis='x')

        # График 5: Аутсайдеры
        ax5 = self.class_figure.add_subplot(335)

        bottom_students = sorted(students, key=lambda x: x.statistics['mean'])[:5]
        names = [s.name.split()[0] for s in bottom_students]
        bottom_means = [s.statistics['mean'] for s in bottom_students]

        ax5.barh(names, bottom_means, color='#ff6b6b', edgecolor='black')
        ax5.set_xlabel('Средний балл')
        ax5.set_title('Нуждаются во внимании')
        ax5.grid(True, alpha=0.3, axis='x')

        # График 6: Динамика по работам
        ax6 = self.class_figure.add_subplot(336)

        if students and students[0].grades:
            num_works = len(students[0].grades)
            work_avgs = []
            work_numbers = []

            for work_idx in range(num_works):
                work_grades = []
                for student in students:
                    if work_idx < len(student.grades) and student.grades[work_idx] is not None:
                        work_grades.append(student.grades[work_idx])
                if work_grades:
                    work_avgs.append(np.mean(work_grades))
                    work_numbers.append(work_idx + 1)

            if work_avgs:
                ax6.plot(work_numbers, work_avgs, 'bo-', linewidth=2, markersize=8)
                ax6.set_xlabel('Номер работы')
                ax6.set_ylabel('Средний балл')
                ax6.set_title('Динамика класса')
                ax6.grid(True, alpha=0.3)

                # Линия тренда
                if len(work_avgs) >= 3:
                    z = np.polyfit(work_numbers, work_avgs, 1)
                    p = np.poly1d(z)
                    ax6.plot(work_numbers, p(work_numbers), "r--", alpha=0.7,
                             label=f'Тренд: {z[0]:+.3f}')
                    ax6.legend()

        # График 7: Сравнение с другими классами
        if len(self.classes) > 1:
            ax7 = self.class_figure.add_subplot(337)

            comparison_data = []
            class_labels = []
            colors_map = []

            for other_class, other_students in self.classes.items():
                other_means = [s.statistics['mean'] for s in other_students]
                comparison_data.append(other_means)
                class_labels.append(str(other_class))

                if other_class == class_name:
                    colors_map.append('#ff6b6b')
                else:
                    colors_map.append('#4d96ff')

            bp = ax7.boxplot(comparison_data, labels=class_labels, patch_artist=True)
            for box, color in zip(bp['boxes'], colors_map):
                box.set_facecolor(color)
                box.set_alpha(0.7)

            ax7.set_ylabel('Средний балл')
            ax7.set_title('Сравнение классов')
            ax7.tick_params(axis='x', rotation=45)
            ax7.grid(True, alpha=0.3, axis='y')

        # График 8: Тепловая карта успеваемости
        if len(students) <= 20:  # Только для небольших классов
            ax8 = self.class_figure.add_subplot(338)

            # Создаем матрицу оценок
            grade_matrix = []
            student_names = []

            for student in students[:10]:  # Ограничиваем для читаемости
                grades = [g if g is not None else 0 for g in student.grades[:10]]
                grade_matrix.append(grades)
                student_names.append(student.name.split()[0])

            if grade_matrix:
                im = ax8.imshow(grade_matrix, cmap='RdYlGn', aspect='auto',
                                vmin=2, vmax=5 if self.is_grades_mode else max([max(row) for row in grade_matrix]))
                ax8.set_yticks(range(len(student_names)))
                ax8.set_yticklabels(student_names)
                ax8.set_xlabel('Работы')
                ax8.set_title('Тепловая карта успеваемости')
                plt.colorbar(im, ax=ax8)

        # График 9: Статистика
        ax9 = self.class_figure.add_subplot(339)
        ax9.axis('off')

        stats_text = f"Статистика класса:\n\n"
        stats_text += f"Учеников: {stats.get('count', 0)}\n"
        stats_text += f"Средний балл: {stats.get('avg_class_mean', 0):.2f}\n"
        stats_text += f"Качество знаний: {(dist.get('excellent', 0) + dist.get('good', 0)) / stats.get('count', 1) * 100:.1f}%\n"
        stats_text += f"Успеваемость: {(dist.get('excellent', 0) + dist.get('good', 0) + dist.get('satisfactory', 0)) / stats.get('count', 1) * 100:.1f}%\n\n"

        if 'avg_grade' in stats:
            stats_text += f"Ср. оценка: {stats['avg_grade']:.2f}\n"

        ax9.text(0.1, 0.5, stats_text, transform=ax9.transAxes, fontsize=11,
                 verticalalignment='center', fontfamily='monospace')

        self.class_figure.tight_layout()
        self.class_canvas.draw()

    def show_class_students_list(self, students):
        """Отображение списка учеников класса"""
        lines = []
        lines.append("=" * 70)
        lines.append("👥 СПИСОК УЧЕНИКОВ КЛАССА")
        lines.append("=" * 70)
        lines.append(f"{'№':<4} {'ФИО':<40} {'Ср.балл':<8} {'Динамика':<12} {'Статус':<10}")
        lines.append("-" * 70)

        for i, student in enumerate(sorted(students, key=lambda x: x.statistics['mean'], reverse=True), 1):
            mean = student.statistics['mean']
            trend = student.statistics['trend']

            if mean >= 4.5:
                status = "🏆 Отличник"
            elif mean >= 4:
                status = "📚 Хорошист"
            elif mean >= 3:
                status = "📖 Троечник"
            else:
                status = "⚠️ Отстающий"

            trend_symbol = "📈" if trend == "Положительная" else "📉" if trend == "Отрицательная" else "➡️"

            name_display = student.name[:38] + "..." if len(student.name) > 38 else student.name
            lines.append(f"{i:<4} {name_display:<40} {mean:<8.2f} {trend_symbol} {trend:<10} {status}")

        self.class_students_text.delete(1.0, tk.END)
        self.class_students_text.insert(1.0, "\n".join(lines))

    def show_class_dynamics(self, students):
        """Отображение динамики класса"""
        lines = []
        lines.append("=" * 70)
        lines.append("📊 ДИНАМИКА КЛАССА")
        lines.append("=" * 70)

        # Анализ динамики по работам
        if students and students[0].grades:
            num_works = len(students[0].grades)
            work_stats = []

            for work_idx in range(num_works):
                work_grades = []
                for student in students:
                    if work_idx < len(student.grades) and student.grades[work_idx] is not None:
                        work_grades.append(student.grades[work_idx])

                if work_grades:
                    work_stats.append({
                        'work': work_idx + 1,
                        'avg': np.mean(work_grades),
                        'median': np.median(work_grades),
                        'min': np.min(work_grades),
                        'max': np.max(work_grades),
                        'count': len(work_grades)
                    })

            if work_stats:
                lines.append("\n📈 Статистика по работам:")
                lines.append("-" * 70)
                lines.append(f"{'Работа':<8} {'Средний':<10} {'Медиана':<10} {'Мин':<6} {'Макс':<6} {'Выполнили':<10}")
                lines.append("-" * 70)

                for stat in work_stats:
                    lines.append(f"{stat['work']:<8} {stat['avg']:<10.2f} {stat['median']:<10.2f} "
                                 f"{stat['min']:<6.0f} {stat['max']:<6.0f} {stat['count']:<10}")

                # Тренд
                avgs = [s['avg'] for s in work_stats]
                if len(avgs) >= 3:
                    first_avg = avgs[0]
                    last_avg = avgs[-1]
                    change = last_avg - first_avg

                    lines.append("\n📊 Общая динамика:")
                    if change > 0.5:
                        lines.append(f"  📈 Значительный рост: +{change:.2f}")
                    elif change > 0.1:
                        lines.append(f"  📈 Небольшой рост: +{change:.2f}")
                    elif change > -0.1:
                        lines.append(f"  ➡️ Стабильно: {change:+.2f}")
                    elif change > -0.5:
                        lines.append(f"  📉 Небольшой спад: {change:.2f}")
                    else:
                        lines.append(f"  📉 Значительный спад: {change:.2f}")

        # Распределение динамики по ученикам
        lines.append("\n📊 Распределение динамики:")
        trends = {'Положительная': 0, 'Стабильная': 0, 'Отрицательная': 0, 'Недостаточно данных': 0}

        for student in students:
            trends[student.statistics['trend']] += 1

        for trend, count in trends.items():
            if count > 0:
                percent = count / len(students) * 100
                symbol = "📈" if trend == "Положительная" else "📉" if trend == "Отрицательная" else "➡️"
                lines.append(f"  {symbol} {trend}: {count} чел. ({percent:.1f}%)")

        self.class_dynamics_text.delete(1.0, tk.END)
        self.class_dynamics_text.insert(1.0, "\n".join(lines))

    def create_general_tab(self):
        """Создание вкладки общей аналитики"""
        # Панель с общей статистикой
        stats_panel = ttk.Frame(self.general_frame)
        stats_panel.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(stats_panel, text="Общая статистика", style='Title.TLabel').pack(anchor=tk.W, pady=5)

        # Фрейм для статистики в две колонки
        stats_container = ttk.Frame(stats_panel)
        stats_container.pack(fill=tk.X)

        self.stats_frame_left = ttk.Frame(stats_container)
        self.stats_frame_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.stats_frame_right = ttk.Frame(stats_container)
        self.stats_frame_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Графики
        self.general_figure = plt.Figure(figsize=(12, 5), dpi=100)
        self.general_canvas = FigureCanvasTkAgg(self.general_figure, self.general_frame)
        self.general_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_students_tab(self):
        """Создание вкладки аналитики по ученикам"""
        # Левая панель со списком учеников
        left_panel = ttk.Frame(self.students_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)

        ttk.Label(left_panel, text="Список учеников", style='Heading.TLabel').pack(anchor=tk.W, pady=5)

        # Поиск ученика
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=tk.X, pady=5)

        ttk.Label(search_frame, text="🔍 Поиск:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        # Используем trace_add вместо trace
        self.search_var.trace_add('write', self.filter_students)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Список учеников с прокруткой
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.students_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                           height=20, font=('Arial', 10))
        self.students_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.students_listbox.yview)
        self.students_listbox.bind('<<ListboxSelect>>', self.on_student_select)

        # Правая панель с информацией об ученике
        right_panel = ttk.Frame(self.students_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Информация об ученике
        info_frame = ttk.LabelFrame(right_panel, text="Информация об ученике", padding="5")
        info_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.student_info = scrolledtext.ScrolledText(info_frame, height=12, width=50,
                                                      font=('Consolas', 10), wrap=tk.WORD)
        self.student_info.pack(fill=tk.BOTH, expand=True)

        # График ученика
        chart_frame = ttk.LabelFrame(right_panel, text="Динамика успеваемости", padding="5")
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.student_figure = plt.Figure(figsize=(6, 4), dpi=100)
        self.student_canvas = FigureCanvasTkAgg(self.student_figure, chart_frame)
        self.student_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_charts_tab(self):
        """Создание вкладки с диаграммами"""
        # Верхний график
        top_frame = ttk.LabelFrame(self.charts_frame, text="Распределение успеваемости", padding="5")
        top_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.chart1_figure = plt.Figure(figsize=(7, 3.5), dpi=100)
        self.chart1_canvas = FigureCanvasTkAgg(self.chart1_figure, top_frame)
        self.chart1_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Нижний график
        bottom_frame = ttk.LabelFrame(self.charts_frame, text="Сравнительный анализ", padding="5")
        bottom_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.chart2_figure = plt.Figure(figsize=(7, 3.5), dpi=100)
        self.chart2_canvas = FigureCanvasTkAgg(self.chart2_figure, bottom_frame)
        self.chart2_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def create_problems_tab(self):
        """Создание вкладки с проблемными учениками"""
        # Верхняя панель с кнопками фильтрации
        filter_frame = ttk.Frame(self.problems_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(filter_frame, text="Показать:", style='Heading.TLabel').pack(side=tk.LEFT, padx=5)

        self.problem_filter = tk.StringVar(value="all")
        ttk.Radiobutton(filter_frame, text="Все проблемы", variable=self.problem_filter,
                        value="all", command=self.show_problems).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="Низкая успеваемость", variable=self.problem_filter,
                        value="low", command=self.show_problems).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="Отрицательная динамика", variable=self.problem_filter,
                        value="negative", command=self.show_problems).pack(side=tk.LEFT, padx=5)

        # Текстовая область для отображения проблемных учеников
        self.problems_text = scrolledtext.ScrolledText(self.problems_frame, height=15,
                                                       font=('Consolas', 11), wrap=tk.WORD)
        self.problems_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def diagnose_file(self, file_path):
        """Диагностика файла перед загрузкой"""
        self.log("🔍 Начинаю диагностику файла...")

        # Проверка существования файла
        if not os.path.exists(file_path):
            self.log("❌ Файл не существует")
            return False

        file_size = os.path.getsize(file_path)
        self.log(f"📁 Размер файла: {file_size} байт")

        if file_size == 0:
            self.log("❌ Файл пустой")
            return False

        # Определение типа файла
        if file_path.endswith('.csv'):
            self.log("📄 Тип файла: CSV")
            # Пробуем прочитать первые несколько строк
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_lines = [next(f) for _ in range(3)]
                    self.log("📋 Первые строки файла:")
                    for i, line in enumerate(first_lines):
                        self.log(f"   Строка {i + 1}: {line.strip()[:100]}")
            except Exception as e:
                self.log(f"⚠️ Не удалось прочитать файл как текст: {e}")

        elif file_path.endswith(('.xlsx', '.xls')):
            self.log("📗 Тип файла: Excel")

        return True

    def load_file(self):
        """Загрузка файла Excel или CSV с подробной диагностикой"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл",
            filetypes=[
                ("Все поддерживаемые", "*.xlsx *.xls *.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        # Диагностика файла
        if not self.diagnose_file(file_path):
            messagebox.showerror("Ошибка", "Файл поврежден или имеет неподдерживаемый формат")
            return

        try:
            # Сначала спрашиваем режим оценок
            mode_dialog = GradeModeDialog(self)
            selected_mode = mode_dialog.show()

            if selected_mode is None:
                self.log("❌ Загрузка отменена пользователем")
                return

            # Если есть существующие данные, спрашиваем режим загрузки
            merge_mode = None
            if self.students:
                dialog = DataMergeDialog(self, self.students)
                merge_mode = dialog.show()

                if merge_mode is None:
                    self.log("❌ Загрузка отменена пользователем")
                    return

                if merge_mode['mode'] == 'keep':
                    self.log("💿 Текущие данные сохранены")
                    return

            # Сброс предыдущих данных если нужно
            if merge_mode and merge_mode['mode'] == 'new':
                self.log("🧹 Очистка предыдущих данных...")
                self.students = []
                self.classes = {}
                Student.clear_cache()

            # Загрузка файла в зависимости от типа
            self.log(f"📂 Загрузка файла: {os.path.basename(file_path)}")

            if file_path.endswith('.csv'):
                self.data = self.load_csv_file(file_path)
            else:
                self.data = self.load_excel_file(file_path)

            if self.data is None:
                raise Exception("Не удалось загрузить данные из файла")

            self.log(f"✅ Данные загружены: {len(self.data)} строк, {len(self.data.columns)} колонок")

            # Устанавливаем режим оценок
            if selected_mode == 'grades':
                self.is_grades_mode = True
                self.log("📊 Выбран режим: оценки (2-5)")
            elif selected_mode == 'points':
                self.is_grades_mode = False
                self.log("🎯 Выбран режим: баллы")
            else:
                # Автоматическое определение
                self.is_grades_mode = self.detect_grades_mode()
                self.log(f"🔍 Режим определен автоматически: {'оценки' if self.is_grades_mode else 'баллы'}")

            # Обработка данных
            self.process_data()

            # Проверяем, что ученики загружены
            if not self.students:
                raise Exception("Не удалось найти учеников в файле. Проверьте формат данных.")

            # Обновление отображения
            self.file_label.config(text=f"Файл: {os.path.basename(file_path)}")
            mode_text = "Режим: оценки (2-5)" if self.is_grades_mode else "Режим: баллы"
            self.mode_label.config(text=mode_text)

            self.log(f"✅ Файл успешно загружен!")
            self.log(f"📊 Найдено учеников: {len(self.students)}")

            # Информация об объединенных записях
            merged_count = sum(1 for s in self.students if hasattr(s, 'all_names') and len(s.all_names) > 1)
            if merged_count > 0:
                self.log(f"🔄 Объединено записей: {merged_count}")

            self.update_analytics()
            messagebox.showinfo("Успех", f"Загружено {len(self.students)} учеников")

        except Exception as e:
            error_message = str(e)
            self.log(f"❌ Ошибка загрузки: {error_message}")

            # Подробная диагностика ошибки
            import traceback
            traceback.print_exc()

            # Показываем пользователю понятное сообщение
            if "No engine" in error_message or "install" in error_message:
                messagebox.showerror("Ошибка",
                                     "Не удалось загрузить файл. Возможно, требуется установка дополнительных компонентов.\n\n"
                                     "Выполните в терминале:\n"
                                     "pip install openpyxl xlrd")
            elif "empty" in error_message.lower():
                messagebox.showerror("Ошибка", "Файл пуст или не содержит данных")
            elif "find" in error_message.lower() and "students" in error_message.lower():
                messagebox.showerror("Ошибка",
                                     "Не удалось найти учеников в файле.\n\n"
                                     "Проверьте:\n"
                                     "1. Первая колонка должна содержать ФИО учеников\n"
                                     "2. В следующих колонках должны быть оценки\n"
                                     "3. В файле должны быть данные, а не только заголовки")
            else:
                messagebox.showerror("Ошибка",
                                     f"Не удалось загрузить файл:\n{error_message}\n\n"
                                     "Проверьте логи для детальной информации")

    def load_csv_file(self, file_path):
        """Загрузка CSV файла с пробованием разных кодировок"""
        encodings = ['utf-8', 'cp1251', 'windows-1251', 'koi8-r', 'latin1']

        for enc in encodings:
            try:
                self.log(f"  Пробую кодировку: {enc}")
                df = pd.read_csv(file_path, encoding=enc)
                self.log(f"  ✅ Успешно с кодировкой {enc}")
                return df
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self.log(f"  ⚠️ Ошибка с кодировкой {enc}: {e}")
                continue

        # Последняя попытка с автоопределением
        try:
            self.log("  Пробую автоопределение...")
            df = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
            self.log("  ✅ Загружено с игнорированием ошибок")
            return df
        except Exception as e:
            self.log(f"  ❌ Не удалось загрузить CSV: {e}")
            return None

    def load_excel_file(self, file_path):
        """Загрузка Excel файла"""
        try:
            # Пробуем разные движки
            engines = ['openpyxl', 'xlrd']

            for engine in engines:
                try:
                    self.log(f"  Пробую движок: {engine}")
                    df = pd.read_excel(file_path, engine=engine)
                    self.log(f"  ✅ Успешно с движком {engine}")
                    return df
                except Exception as e:
                    self.log(f"  ⚠️ Ошибка с движком {engine}: {e}")
                    continue

            # Последняя попытка без указания движка
            df = pd.read_excel(file_path)
            return df

        except Exception as e:
            self.log(f"  ❌ Не удалось загрузить Excel: {e}")
            return None

    def process_data(self):
        """Обработка загруженных данных"""
        if self.data is None or self.data.empty:
            self.log("❌ Данные отсутствуют")
            return

        try:
            # Очищаем кэш
            Student.clear_cache()

            # Используем универсальный парсер
            self.log("🔍 Запускаю универсальный парсер...")

            students = UniversalParser.parse_file(self.data, self.log)

            if students:
                self.students = students
                self.log(f"✅ Успешно загружено: {len(self.students)} учеников")

                # Формируем словарь классов
                self.classes = {}
                for student in self.students:
                    if student.student_class:
                        if student.student_class not in self.classes:
                            self.classes[student.student_class] = []
                        self.classes[student.student_class].append(student)

                # ОТЛАДКА: подробная информация о каждом ученике
                self.log("=" * 50)
                self.log("📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ УЧЕНИКАХ:")
                for i, student in enumerate(self.students[:10]):  # Первые 10 для примера
                    class_info = student.student_class if student.student_class else "Нет класса"
                    grades_count = len([g for g in student.grades if g not in [None, "н"]])
                    self.log(f"   {i + 1}. {student.name} | Класс: '{class_info}' | Оценок: {grades_count}")

                if len(self.students) > 10:
                    self.log(f"   ... и еще {len(self.students) - 10} учеников")

                self.log("📚 ИНФОРМАЦИЯ О КЛАССАХ:")
                if self.classes:
                    for class_name, students_list in self.classes.items():
                        self.log(f"   • КЛАСС '{class_name}': {len(students_list)} учеников")
                        # Показываем первых 3 учеников в каждом классе
                        for j, student in enumerate(students_list[:3]):
                            self.log(f"        - {student.name}")
                        if len(students_list) > 3:
                            self.log(f"        ... и еще {len(students_list) - 3} учеников")
                else:
                    self.log("   ❌ Классы не найдены!")

                self.log("=" * 50)

                # Сортировка учеников
                self.students.sort(key=lambda x: (x.student_class or '', x.name))

                # Обновление списков
                self.update_students_list()
                self.update_classes_list()

                # Статистика
                total_grades = sum(len([g for g in s.grades if g not in [None, "н"]])
                                   for s in self.students)
                self.log(f"📊 Всего оценок: {total_grades}")

                return

            self.log("❌ Универсальный парсер не нашел учеников")

        except Exception as e:
            self.log(f"❌ Ошибка: {str(e)}")
            import traceback
            traceback.print_exc()

    def detect_grades_mode(self):
        """Определение режима (оценки или баллы)"""
        try:
            # Пробуем сначала журнальный парсер
            journal_students = JournalParser.parse_journal(self.data)
            if journal_students:
                # Собираем все оценки
                all_grades = []
                for student in journal_students:
                    for g in student['grades']:
                        try:
                            if g not in ['н', None] and pd.notna(g):
                                num_val = float(str(g).replace(',', '.').strip())
                                all_grades.append(num_val)
                        except:
                            pass

                if all_grades:
                    max_val = max(all_grades)
                    # Если все значения <= 5 и целые числа - это оценки
                    if max_val <= 5 and all(v.is_integer() for v in all_grades):
                        return True
                    else:
                        return False

            # Стандартная проверка
            sample_data = []
            for i in range(min(5, len(self.data))):
                row = self.data.iloc[i]
                for val in row[1:]:
                    if pd.notna(val) and str(val).strip().lower() not in ['н', 'н/а', '']:
                        try:
                            num = float(str(val).replace(',', '.').strip())
                            sample_data.append(num)
                        except:
                            pass

            if sample_data:
                max_val = max(sample_data)
                # Если все значения <= 5 и целые числа - это оценки
                if max_val <= 5 and all(v.is_integer() for v in sample_data):
                    return True
                else:
                    return False
            return True  # По умолчанию оценки
        except:
            return True

    def update_students_list(self):
        """Обновление списка учеников в интерфейсе"""
        try:
            self.students_listbox.delete(0, tk.END)

            if not self.students:
                self.log("⚠️ Список учеников пуст")
                return

            # Сортируем учеников по классу и имени
            sorted_students = sorted(self.students, key=lambda x: (x.student_class or '', x.name))

            current_class = None
            student_count = 0

            for student in sorted_students:
                # Добавляем разделитель для нового класса
                if student.student_class != current_class:
                    current_class = student.student_class
                    if current_class:
                        display_text = f"📚 КЛАСС {current_class}"
                        self.students_listbox.insert(tk.END, display_text)
                        self.students_listbox.itemconfig(tk.END, fg='blue', font=('Arial', 10, 'bold'))
                        student_count = 0
                    else:
                        display_text = "📚 БЕЗ КЛАССА"
                        self.students_listbox.insert(tk.END, display_text)
                        self.students_listbox.itemconfig(tk.END, fg='gray', font=('Arial', 10, 'bold'))

                # Добавляем ученика с индикатором проблемы
                prefix = ""

                # Безопасное получение статистики
                try:
                    if hasattr(student, 'statistics') and student.statistics:
                        mean = student.statistics.get('mean', 0)
                        trend = student.statistics.get('trend', '')
                    else:
                        # Пытаемся вычислить статистику
                        if hasattr(student, '_calculate_statistics'):
                            student.statistics = student._calculate_statistics()
                            mean = student.statistics.get('mean', 0)
                            trend = student.statistics.get('trend', '')
                        else:
                            mean = 0
                            trend = ''

                    if mean < 3:
                        prefix = "⚠️ "
                    elif trend == 'Отрицательная':
                        prefix = "📉 "
                except:
                    prefix = "❓ "

                # Сокращаем имя для отображения
                display_name = student.name
                if len(display_name) > 40:
                    display_name = display_name[:37] + "..."

                self.students_listbox.insert(tk.END, f"   {prefix}{display_name}")
                student_count += 1

            # Добавляем информацию о количестве учеников
            self.students_listbox.insert(tk.END, "")
            self.students_listbox.insert(tk.END, f"📊 Всего учеников: {len(self.students)}")
            self.students_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 9, 'italic'))

        except Exception as e:
            self.log(f"⚠️ Ошибка обновления списка учеников: {e}")
            import traceback
            traceback.print_exc()

    def update_classes_list(self):
        """Обновление списка классов с сортировкой"""
        try:
            if not hasattr(self, 'classes') or not self.classes:
                self.class_listbox.delete(0, tk.END)
                self.class_listbox.insert(tk.END, "📭 Нет данных о классах")
                return

            self.class_listbox.delete(0, tk.END)

            stats = self.get_class_statistics()
            sort_by = self.class_sort_var.get()

            # Получаем список всех классов
            all_classes = list(self.classes.keys())

            if sort_by == 'name':
                items = sorted(all_classes)
            elif sort_by == 'avg':
                items = sorted(all_classes,
                               key=lambda x: stats.get(x, {}).get('avg_class_mean', 0),
                               reverse=True)
            elif sort_by == 'count':
                items = sorted(all_classes,
                               key=lambda x: len(self.classes[x]),
                               reverse=True)

            for class_name in items:
                students = self.classes[class_name]
                class_stats = stats.get(class_name, {})
                avg = class_stats.get('avg_class_mean', 0)
                count = len(students)

                # Определяем цвет и иконку в зависимости от успеваемости
                if avg >= 4.5:
                    prefix = "🏆 "
                    color = 'green'
                elif avg >= 4:
                    prefix = "📚 "
                    color = 'dark green'
                elif avg >= 3:
                    prefix = "📖 "
                    color = 'blue'
                else:
                    prefix = "⚠️ "
                    color = 'red'

                display = f"{prefix}{class_name}  |  {count} уч.  |  ср.{avg:.2f}"

                # Добавляем информацию о распределении
                dist = class_stats.get('distribution', {})
                if dist:
                    excellent = dist.get('excellent', 0)
                    good = dist.get('good', 0)
                    poor = dist.get('poor', 0)
                    if excellent > 0 or good > 0 or poor > 0:
                        display += f"  [👍{excellent} 👎{poor}]"

                self.class_listbox.insert(tk.END, display)

                # Раскрашиваем строки
                self.class_listbox.itemconfig(tk.END, fg=color, font=('Arial', 10, 'bold'))

            # Добавляем информацию о количестве
            self.class_listbox.insert(tk.END, "")
            self.class_listbox.insert(tk.END, f"📊 Всего классов: {len(self.classes)}")
            self.class_listbox.itemconfig(tk.END, fg='purple', font=('Arial', 9, 'italic'))

        except Exception as e:
            self.log(f"⚠️ Ошибка обновления списка классов: {e}")
            import traceback
            traceback.print_exc()

    def on_class_select(self, event):
        """Обработка выбора класса"""
        try:
            selection = self.class_listbox.curselection()
            if selection and hasattr(self, 'classes') and self.classes:
                index = selection[0]

                # Получаем список классов в том же порядке, что и в отображении
                all_classes = list(self.classes.keys())

                if index < len(all_classes):
                    class_name = all_classes[index]
                    self.show_class_info(class_name)
        except Exception as e:
            self.log(f"⚠️ Ошибка выбора класса: {e}")

    def get_class_statistics(self):
        """Получение статистики по классам"""
        try:
            if not hasattr(self, 'classes') or not self.classes:
                return {}

            stats = {}
            for class_name, students in self.classes.items():
                if not students:
                    continue

                # Собираем все средние баллы учеников
                student_means = []
                for student in students:
                    try:
                        if hasattr(student, 'statistics') and student.statistics:
                            student_means.append(student.statistics.get('mean', 0))
                        else:
                            student_means.append(0)
                    except:
                        student_means.append(0)

                class_stats = {
                    'count': len(students),
                    'avg_class_mean': np.mean(student_means) if student_means else 0,
                    'max_mean': max(student_means) if student_means else 0,
                    'min_mean': min(student_means) if student_means else 0,
                    'distribution': {
                        'excellent': len([s for s in students if s.statistics.get('mean', 0) >= 4.5]),
                        'good': len([s for s in students if 4 <= s.statistics.get('mean', 0) < 4.5]),
                        'satisfactory': len([s for s in students if 3 <= s.statistics.get('mean', 0) < 4]),
                        'poor': len([s for s in students if s.statistics.get('mean', 0) < 3])
                    }
                }

                # Средняя оценка, если это режим оценок
                all_grades = []
                for student in students:
                    if hasattr(student, 'grades'):
                        all_grades.extend([g for g in student.grades if g not in [None, "н"]])
                if all_grades and max(all_grades) <= 5:
                    class_stats['avg_grade'] = np.mean(all_grades)

                stats[class_name] = class_stats

            return stats
        except Exception as e:
            self.log(f"⚠️ Ошибка получения статистики классов: {e}")
            return {}

    def filter_students(self, *args):
        """Фильтрация списка учеников"""
        try:
            search_term = self.search_var.get().lower()
            self.students_listbox.delete(0, tk.END)

            if not self.students:
                return

            current_class = None
            for student in self.students:
                # Проверяем совпадение с именем или классом
                name_match = search_term in student.name.lower()
                class_match = student.student_class and search_term in student.student_class.lower()

                if name_match or class_match or search_term == '':
                    # Добавляем разделитель для нового класса
                    if student.student_class != current_class:
                        current_class = student.student_class
                        if current_class:
                            display_text = f"📚 КЛАСС {current_class}"
                            self.students_listbox.insert(tk.END, display_text)
                            self.students_listbox.itemconfig(tk.END, fg='blue', font=('Arial', 10, 'bold'))

                    prefix = ""
                    if hasattr(student, 'statistics') and student.statistics:
                        if student.statistics.get('mean', 0) < 3:
                            prefix = "⚠️ "
                        elif student.statistics.get('trend') == 'Отрицательная':
                            prefix = "📉 "

                    display_name = f"   {prefix}{student.name}"
                    self.students_listbox.insert(tk.END, display_name)

        except Exception as e:
            self.log(f"⚠️ Ошибка фильтрации: {e}")

    def on_student_select(self, event):
        """Обработка выбора ученика из списка"""
        try:
            selection = self.students_listbox.curselection()
            if not selection:
                return

            index = selection[0]
            item_text = self.students_listbox.get(index)

            # Пропускаем заголовки классов
            if item_text.startswith("📚"):
                return

            # Убираем префиксы
            student_name = item_text.replace("⚠️ ", "").replace("📉 ", "").strip()
            if student_name.startswith("   "):
                student_name = student_name[3:]  # Убираем отступы

            # Поиск ученика
            for student in self.students:
                if student.name == student_name:
                    self.show_student_info(student)
                    break
        except Exception as e:
            self.log(f"⚠️ Ошибка выбора ученика: {e}")

    def show_student_info(self, student):
        """Отображение информации о конкретном ученике"""
        try:
            # Убеждаемся, что статистика существует
            if not hasattr(student, 'statistics') or not student.statistics:
                if hasattr(student, '_calculate_statistics'):
                    student.statistics = student._calculate_statistics()
                else:
                    student.statistics = {}

            info = student.get_info()

            lines = []
            lines.append("═" * 50)
            if student.student_class:
                lines.append(f"📚 Класс: {student.student_class}")
            lines.append(f"👤 {info['name']}")
            lines.append("═" * 50)
            lines.append(f"📊 Средний балл: {info.get('mean', 0):.2f}")
            lines.append(f"📈 Медиана: {info.get('median', 0):.2f}")
            lines.append(f"📉 Минимум: {info.get('min', 0)}")
            lines.append(f"📈 Максимум: {info.get('max', 0)}")
            lines.append(f"📝 Количество работ: {info.get('count', 0)}")
            lines.append(f"📊 Динамика: {info.get('trend', 'Нет данных')}")

            if self.is_grades_mode:
                lines.append(f"✅ Положительных оценок: {info.get('passed_count', 0)}")
                lines.append(f"❌ Неудовлетворительных: {info.get('failed_count', 0)}")

            if info.get('first_grade') is not None and info.get('last_grade') is not None:
                change = info['last_grade'] - info['first_grade']
                change_symbol = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                lines.append(f"{change_symbol} Изменение: {change:+.2f}")

            if info.get('merge_count', 1) > 1:
                lines.append(f"🔄 Объединено записей: {info['merge_count']}")

            lines.append("\n📊 Распределение оценок:")
            for grade, count in sorted(info.get('grade_distribution', {}).items()):
                bar = "█" * count
                lines.append(f"  {grade}: {count} {bar}")

            lines.append("\n📝 Оценки по порядку:")
            grade_line = ""
            for i, grade in enumerate(info['grades'], 1):
                if grade is not None:
                    grade_line += f"{grade:4.0f}" if grade.is_integer() else f"{grade:5.1f}"
                else:
                    grade_line += "  н "
                if i % 10 == 0:
                    lines.append(grade_line)
                    grade_line = ""
            if grade_line:
                lines.append(grade_line)

            self.student_info.delete(1.0, tk.END)
            self.student_info.insert(1.0, "\n".join(lines))

            # График
            self.plot_student_grades(student)

        except Exception as e:
            self.log(f"⚠️ Ошибка отображения информации об ученике: {e}")
            self.student_info.delete(1.0, tk.END)
            self.student_info.insert(1.0, f"❌ Ошибка загрузки данных ученика\n\n{str(e)}")

    def plot_student_grades(self, student):
        """Построение графика для конкретного ученика"""
        self.student_figure.clear()

        grades = student.grades
        valid_indices = [i + 1 for i, g in enumerate(grades) if g is not None]  # 1-индексация для наглядности
        valid_grades = [g for g in grades if g is not None]

        if valid_grades:
            ax = self.student_figure.add_subplot(111)

            # Линия оценок
            ax.plot(valid_indices, valid_grades, 'bo-', label='Оценки', linewidth=2, markersize=8)

            # Добавление линии среднего
            ax.axhline(y=student.statistics['mean'], color='r', linestyle='--',
                       linewidth=2, label=f"Среднее: {student.statistics['mean']:.2f}")

            # Добавление линии тренда
            if len(valid_grades) >= 2:
                z = np.polyfit(valid_indices, valid_grades, 1)
                p = np.poly1d(z)
                ax.plot(valid_indices, p(valid_indices), "g--", alpha=0.7,
                        label=f"Тренд: {z[0]:+.3f}")

            ax.set_xlabel('Номер работы', fontsize=10)
            ax.set_ylabel('Оценка/Балл', fontsize=10)
            ax.set_title(f'Динамика успеваемости: {student.name}', fontsize=12, fontweight='bold')
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)
            ax.set_xlim(0, max(valid_indices) + 1)

            if self.is_grades_mode:
                ax.set_ylim(1.5, 5.5)
                ax.set_yticks([2, 3, 4, 5])

            # Добавление значений над точками
            for i, (x, y) in enumerate(zip(valid_indices, valid_grades)):
                ax.annotate(f'{y:.0f}' if y.is_integer() else f'{y:.1f}',
                            (x, y), textcoords="offset points",
                            xytext=(0, 10), ha='center', fontsize=8)
        else:
            ax = self.student_figure.add_subplot(111)
            ax.text(0.5, 0.5, '❌ Нет данных для отображения',
                    ha='center', va='center', transform=ax.transAxes, fontsize=14)

        self.student_figure.tight_layout()
        self.student_canvas.draw()

    def update_analytics(self):
        """Обновление всей аналитики"""
        if not self.students:
            self.stats_label.config(text="Нет данных")
            messagebox.showwarning("Предупреждение", "Нет данных для анализа. Возможные причины:\n"
                                                     "1. Файл не содержит данных в правильном формате\n"
                                                     "2. Первая колонка должна содержать ФИО учеников\n"
                                                     "3. Проверьте логи для детальной информации")
            return

        self.update_general_stats()
        self.update_charts()
        self.show_problems()

        # Обновление списка классов
        if hasattr(self, 'classes') and self.classes:
            self.update_classes_list()

        # Обновление статистики в заголовке
        total_students = len(self.students)
        total_classes = len(self.classes) if hasattr(self, 'classes') else 0
        self.stats_label.config(text=f"👥 {total_students} уч. | 🏫 {total_classes} кл.")

        self.log("🔄 Аналитика обновлена")

    def update_general_stats(self):
        """Обновление общей статистики"""
        # Очистка предыдущей статистики
        for widget in [self.stats_frame_left, self.stats_frame_right]:
            for child in widget.winfo_children():
                child.destroy()

        if not self.students:
            return

        # Сбор общей статистики
        all_grades = []
        student_means = []

        for student in self.students:
            valid_grades = [g for g in student.grades if g is not None]
            all_grades.extend(valid_grades)
            if valid_grades:
                student_means.append(student.statistics['mean'])

        if not all_grades:
            ttk.Label(self.stats_frame_left, text="❌ Нет данных для отображения").pack()
            return

        # Левая колонка - основная статистика
        ttk.Label(self.stats_frame_left, text="📊 Основные показатели",
                  style='Heading.TLabel').pack(anchor=tk.W, pady=5)

        stats_items = [
            ("👥 Всего учеников:", f"{len(self.students)}"),
            ("📝 Всего работ:", f"{len(all_grades)}"),
            ("📊 Общий средний балл:", f"{np.mean(all_grades):.2f}"),
            ("📈 Медиана:", f"{np.median(all_grades):.2f}"),
            ("📉 Минимум:", f"{np.min(all_grades)}"),
            ("📈 Максимум:", f"{np.max(all_grades)}"),
            ("📊 Среднее по ученикам:", f"{np.mean(student_means):.2f}"),
        ]

        for label, value in stats_items:
            frame = ttk.Frame(self.stats_frame_left)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label, width=25, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=value, font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        if self.is_grades_mode:
            passed = len([g for g in all_grades if g >= 3])
            failed = len([g for g in all_grades if g < 3])

            ttk.Separator(self.stats_frame_left, orient='horizontal').pack(fill=tk.X, pady=10)
            ttk.Label(self.stats_frame_left, text="✅ Качество знаний",
                      style='Heading.TLabel').pack(anchor=tk.W, pady=5)

            quality_items = [
                ("Успешных работ:", f"{passed} ({passed / len(all_grades) * 100:.1f}%)"),
                ("Неуд. работ:", f"{failed} ({failed / len(all_grades) * 100:.1f}%)"),
                ("Качество знаний:", f"{(passed - failed) / len(all_grades) * 100:.1f}%"),
            ]

            for label, value in quality_items:
                frame = ttk.Frame(self.stats_frame_left)
                frame.pack(fill=tk.X, pady=2)
                ttk.Label(frame, text=label, width=25, anchor=tk.W).pack(side=tk.LEFT)
                ttk.Label(frame, text=value, font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        # Правая колонка - распределение
        ttk.Label(self.stats_frame_right, text="📊 Распределение по уровням",
                  style='Heading.TLabel').pack(anchor=tk.W, pady=5)

        # Категории учеников
        high_achievers = len([s for s in self.students if s.statistics['mean'] >= 4.5])
        good_achievers = len([s for s in self.students if 4 <= s.statistics['mean'] < 4.5])
        average = len([s for s in self.students if 3 <= s.statistics['mean'] < 4])
        low_achievers = len([s for s in self.students if s.statistics['mean'] < 3])

        categories = [
            ("🏆 Отличники (>4.5):", high_achievers, "green"),
            ("📚 Хорошисты (4-4.5):", good_achievers, "blue"),
            ("📖 Троечники (3-4):", average, "orange"),
            ("⚠️ Неуспевающие (<3):", low_achievers, "red"),
        ]

        for label, count, color in categories:
            frame = ttk.Frame(self.stats_frame_right)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=label, width=20, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=str(count), foreground=color,
                      font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        # Динамика
        ttk.Separator(self.stats_frame_right, orient='horizontal').pack(fill=tk.X, pady=10)
        ttk.Label(self.stats_frame_right, text="📈 Динамика",
                  style='Heading.TLabel').pack(anchor=tk.W, pady=5)

        trends = {}
        for student in self.students:
            trends[student.statistics['trend']] = trends.get(student.statistics['trend'], 0) + 1

        for trend, count in trends.items():
            color = "green" if trend == "Положительная" else "orange" if trend == "Стабильная" else "red"
            frame = ttk.Frame(self.stats_frame_right)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{trend}:", width=20, anchor=tk.W).pack(side=tk.LEFT)
            ttk.Label(frame, text=str(count), foreground=color,
                      font=('Arial', 10, 'bold')).pack(side=tk.LEFT)

        # Общий график
        self.plot_general_stats(all_grades)

    def plot_general_stats(self, all_grades):
        """Улучшенное построение общего графика с читаемыми именами"""
        self.general_figure.clear()

        if not all_grades:
            return

        # Создаем 2x2 сетку графиков
        gs = self.general_figure.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # График 1: Распределение оценок/баллов
        ax1 = self.general_figure.add_subplot(gs[0, 0])

        if max(all_grades) <= 5 and all(g.is_integer() for g in all_grades):
            # Для оценок 2-5
            grades_count = {2: 0, 3: 0, 4: 0, 5: 0}
            for g in all_grades:
                if int(g) in grades_count:
                    grades_count[int(g)] += 1

            grades = list(grades_count.keys())
            counts = list(grades_count.values())
            colors = ['#ff6b6b', '#ffd93d', '#6bcb77', '#4d96ff']
            bars = ax1.bar(grades, counts, color=colors, edgecolor='black', linewidth=1.5)

            # Добавление значений на столбцы
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width() / 2., height,
                         f'{int(height)}', ha='center', va='bottom', fontsize=10)

            ax1.set_xlabel('Оценка', fontsize=11)
            ax1.set_ylabel('Количество', fontsize=11)
            ax1.set_title('Распределение оценок', fontsize=12, fontweight='bold')
            ax1.set_xticks(grades)
        else:
            # Для баллов
            n, bins, patches = ax1.hist(all_grades, bins=15, edgecolor='black',
                                        alpha=0.7, color='#4d96ff', linewidth=1.5)
            ax1.set_xlabel('Баллы', fontsize=11)
            ax1.set_ylabel('Частота', fontsize=11)
            ax1.set_title('Распределение баллов', fontsize=12, fontweight='bold')

        ax1.grid(True, alpha=0.3)

        # График 2: Средние баллы учеников (с прокруткой если много)
        ax2 = self.general_figure.add_subplot(gs[0, 1])

        # Сортируем учеников по среднему баллу
        sorted_students = sorted(self.students, key=lambda x: x.statistics['mean'], reverse=True)

        # Если учеников много, показываем только топ и дно
        if len(sorted_students) > 20:
            # Берем топ-10 и дно-10
            top_students = sorted_students[:10]
            bottom_students = sorted_students[-10:]
            display_students = top_students + bottom_students
            title = f'Топ-10 и последние 10 учеников (всего: {len(sorted_students)})'
        else:
            display_students = sorted_students
            title = 'Средние баллы учеников'

        names = []
        means = []
        colors = []

        for student in display_students:
            # Сокращаем имя для читаемости
            name_parts = student.name.split()
            if len(name_parts) >= 2:
                short_name = f"{name_parts[0]} {name_parts[1][0]}."
            else:
                short_name = student.name[:15] + "..." if len(student.name) > 15 else student.name

            names.append(short_name)
            mean_val = student.statistics['mean']
            means.append(mean_val)

            if mean_val < 3:
                colors.append('#ff6b6b')
            elif mean_val < 4:
                colors.append('#ffd93d')
            else:
                colors.append('#6bcb77')

        # Используем горизонтальные бары для лучшей читаемости имен
        y_pos = np.arange(len(names))
        bars = ax2.barh(y_pos, means, color=colors, edgecolor='black', linewidth=1)
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(names, fontsize=9)
        ax2.set_xlabel('Средний балл', fontsize=11)
        ax2.set_title(title, fontsize=12, fontweight='bold')

        # Добавляем значения
        for i, (bar, val) in enumerate(zip(bars, means)):
            ax2.text(val + 0.05, bar.get_y() + bar.get_height() / 2,
                     f'{val:.2f}', va='center', fontsize=8)

        ax2.grid(True, alpha=0.3, axis='x')

        # График 3: Ящик с усами
        ax3 = self.general_figure.add_subplot(gs[1, 0])

        # Группируем по классам если есть
        if self.classes and len(self.classes) <= 10:
            # Показываем по классам
            class_data = []
            class_names = []

            for class_name, students in sorted(self.classes.items()):
                class_grades = []
                for student in students:
                    class_grades.extend([g for g in student.grades if g is not None])
                if class_grades:
                    class_data.append(class_grades)
                    class_names.append(str(class_name))

            if class_data:
                bp = ax3.boxplot(class_data, labels=class_names, patch_artist=True)
                for box in bp['boxes']:
                    box.set_facecolor('#4d96ff')
                    box.set_alpha(0.7)
                ax3.set_xlabel('Класс', fontsize=11)
                ax3.set_title('Распределение по классам', fontsize=12, fontweight='bold')
        else:
            # Показываем по ученикам (первые 15)
            student_grades = []
            student_names = []

            for student in sorted(self.students, key=lambda x: x.statistics['mean'], reverse=True)[:15]:
                valid = [g for g in student.grades if g is not None]
                if valid:
                    student_grades.append(valid)
                    # Сокращаем имя
                    name_parts = student.name.split()
                    short_name = name_parts[0] if name_parts else student.name
                    if len(short_name) > 10:
                        short_name = short_name[:8] + "."
                    student_names.append(short_name)

            if student_grades:
                bp = ax3.boxplot(student_grades, labels=student_names, patch_artist=True)
                for box in bp['boxes']:
                    box.set_facecolor('#4d96ff')
                    box.set_alpha(0.7)
                ax3.set_xlabel('Ученики', fontsize=11)
                ax3.set_title('Топ-15 учеников (разброс)', fontsize=12, fontweight='bold')
                ax3.tick_params(axis='x', rotation=45)

        ax3.set_ylabel('Оценки/Баллы', fontsize=11)
        ax3.grid(True, alpha=0.3, axis='y')

        # График 4: Динамика успеваемости
        ax4 = self.general_figure.add_subplot(gs[1, 1])

        trends = {'Положительная': 0, 'Стабильная': 0, 'Отрицательная': 0, 'Недостаточно данных': 0}
        for student in self.students:
            trends[student.statistics['trend']] += 1

        colors_trend = {
            'Положительная': '#6bcb77',
            'Стабильная': '#4d96ff',
            'Отрицательная': '#ff6b6b',
            'Недостаточно данных': '#95a5a6'
        }

        # Убираем нулевые значения
        labels = []
        sizes = []
        colors_list = []

        for key, value in trends.items():
            if value > 0:
                labels.append(key)
                sizes.append(value)
                colors_list.append(colors_trend[key])

        if sizes:
            wedges, texts, autotexts = ax4.pie(
                sizes,
                labels=labels,
                colors=colors_list,
                autopct='%1.1f%%',
                startangle=90,
                textprops={'fontsize': 10}
            )

            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')

        ax4.set_title('Динамика успеваемости', fontsize=12, fontweight='bold')

        self.general_figure.tight_layout()
        self.general_canvas.draw()

    def save_current_data(self):
        """Сохранение текущих данных"""
        if not self.students:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return

        # Создаем диалог сохранения
        dialog = tk.Toplevel(self.root)
        dialog.title("Сохранить данные")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Заголовок
        ttk.Label(dialog, text="Сохранение данных",
                  style='Title.TLabel').pack(pady=10)

        # Имя файла
        frame = ttk.Frame(dialog, padding="10")
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Имя файла:").pack(anchor=tk.W)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_var = tk.StringVar(value=f"students_{timestamp}")

        name_entry = ttk.Entry(frame, textvariable=filename_var, width=30)
        name_entry.pack(fill=tk.X, pady=5)

        # Опции
        options_frame = ttk.LabelFrame(dialog, text="Опции", padding="10")
        options_frame.pack(fill=tk.X, padx=10, pady=10)

        save_history_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Сохранить историю изменений",
                        variable=save_history_var).pack(anchor=tk.W)

        export_json_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Дополнительно экспортировать в JSON",
                        variable=export_json_var).pack(anchor=tk.W)

        # Кнопки
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)

        def do_save():
            filename = filename_var.get().strip()
            if not filename:
                filename = f"students_{timestamp}"

            if not filename.endswith('.pkl'):
                filename += '.pkl'

            # Сохраняем данные
            data_manager = DataManager()
            saved_file = data_manager.save_students(self.students, filename)

            if export_json_var.get():
                json_file = filename.replace('.pkl', '.json')
                data_manager.export_to_json(self.students, json_file)
                self.log(f"📄 Данные экспортированы в JSON: {json_file}")

            self.log(f"💾 Данные сохранены: {saved_file}")
            messagebox.showinfo("Успех", f"Данные сохранены в файл:\n{saved_file}")
            dialog.destroy()

        ttk.Button(button_frame, text="Сохранить", command=do_save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side=tk.RIGHT)

        dialog.wait_window()

    def load_saved_data(self):
        """Загрузка сохраненных данных"""
        data_manager = DataManager()
        saved_files = data_manager.get_saved_files()

        if not saved_files:
            messagebox.showinfo("Информация", "Нет сохраненных файлов")
            return

        # Создаем диалог выбора файла
        dialog = tk.Toplevel(self.root)
        dialog.title("Загрузить данные")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Заголовок
        ttk.Label(dialog, text="Выберите файл для загрузки",
                  style='Title.TLabel').pack(pady=10)

        # Список файлов
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        file_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=15)
        file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=file_listbox.yview)

        # Заполняем список
        file_items = []
        for f in saved_files:
            display = f"{f['name']} ({f['modified'].strftime('%Y-%m-%d %H:%M')})"
            file_listbox.insert(tk.END, display)
            file_items.append(f)

        # Опции загрузки
        options_frame = ttk.LabelFrame(dialog, text="Опции загрузки", padding="10")
        options_frame.pack(fill=tk.X, padx=10, pady=10)

        clear_current_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Очистить текущие данные перед загрузкой",
                        variable=clear_current_var).pack(anchor=tk.W)

        # Кнопки
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, pady=10)

        def do_load():
            selection = file_listbox.curselection()
            if not selection:
                messagebox.showwarning("Предупреждение", "Выберите файл")
                return

            idx = selection[0]
            selected_file = file_items[idx]['name']

            try:
                # Загружаем данные
                loaded_students = data_manager.load_students(selected_file)

                if clear_current_var.get():
                    self.students = loaded_students
                    self.log(f"📂 Загружены новые данные: {len(self.students)} учеников")
                else:
                    # Объединяем с существующими
                    registry = StudentRegistry()
                    for s in self.students:
                        registry.add_student(s)
                    for s in loaded_students:
                        registry.add_student(s)
                    self.students = registry.get_all_students()
                    self.log(f"📂 Данные объединены. Всего: {len(self.students)} учеников")

                # Восстанавливаем словарь классов
                self.classes = {}
                for student in self.students:
                    if student.student_class:
                        if student.student_class not in self.classes:
                            self.classes[student.student_class] = []
                        self.classes[student.student_class].append(student)

                self.update_students_list()
                self.update_analytics()

                messagebox.showinfo("Успех", f"Загружено {len(self.students)} учеников")
                dialog.destroy()

            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {str(e)}")

        ttk.Button(button_frame, text="Загрузить", command=do_load).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Отмена", command=dialog.destroy).pack(side=tk.RIGHT)

        dialog.wait_window()

    def clear_all_data(self):
        """Очистка всех данных"""
        if not self.students:
            messagebox.showinfo("Информация", "Нет данных для очистки")
            return

        result = messagebox.askyesno("Подтверждение",
                                     f"Очистить все данные ({len(self.students)} учеников)?\n"
                                     "Это действие нельзя отменить!")

        if result:
            self.students = []
            self.classes = {}
            self.data = None
            Student.clear_cache()
            self.update_students_list()
            self.update_analytics()
            self.file_label.config(text="Файл не загружен")
            self.log("🗑️ Все данные очищены")

    def filter_raw_data(self, df):
        """Фильтрация сырых данных от служебной информации"""
        if df is None or df.empty:
            return df

        # Удаляем полностью пустые строки
        df = df.dropna(how='all')

        # Удаляем строки, где первая колонка содержит служебные слова
        first_col = df.columns[0]
        mask = ~df[first_col].astype(str).str.lower().str.contains(
            '|'.join(DataFilter.SERVICE_KEYWORDS), na=False, regex=True
        )
        df = df[mask]

        # Удаляем строки с датами
        mask = ~df[first_col].astype(str).str.contains(DataFilter.DATE_PATTERN, na=False, regex=True)
        df = df[mask]

        # Удаляем строки, где первая колонка пустая или состоит из пробелов
        df = df[df[first_col].notna()]
        df = df[df[first_col].astype(str).str.strip() != '']

        # Сброс индекса
        df = df.reset_index(drop=True)

        return df

    def get_class_statistics(self):
        """Получение статистики по классам"""
        if not hasattr(self, 'classes') or not self.classes:
            return {}

        stats = {}
        for class_name, students in self.classes.items():
            if not students:
                continue

            class_stats = {
                'count': len(students),
                'avg_class_mean': np.mean([s.statistics['mean'] for s in students]),
                'max_mean': max([s.statistics['mean'] for s in students]),
                'min_mean': min([s.statistics['mean'] for s in students]),
                'distribution': {
                    'excellent': len([s for s in students if s.statistics['mean'] >= 4.5]),
                    'good': len([s for s in students if 4 <= s.statistics['mean'] < 4.5]),
                    'satisfactory': len([s for s in students if 3 <= s.statistics['mean'] < 4]),
                    'poor': len([s for s in students if s.statistics['mean'] < 3])
                }
            }

            # Средняя оценка, если это режим оценок
            all_grades = []
            for student in students:
                all_grades.extend([g for g in student.grades if g is not None])
            if all_grades and max(all_grades) <= 5:
                class_stats['avg_grade'] = np.mean(all_grades)

            stats[class_name] = class_stats

        return stats

    def show_problems(self):
        """Отображение проблемных учеников"""
        self.problems_text.delete(1.0, tk.END)

        if not self.students:
            self.problems_text.insert(1.0, "❌ Нет данных для анализа")
            return

        filter_type = self.problem_filter.get()

        lines = []
        lines.append("=" * 70)
        lines.append("⚠️  АНАЛИЗ ПРОБЛЕМНЫХ УЧЕНИКОВ")
        lines.append("=" * 70)

        if filter_type in ['all', 'low']:
            # Ученики с низкой успеваемостью
            low_achievers = [s for s in self.students if s.statistics['mean'] < 3]
            if low_achievers:
                lines.append("\n📉 УЧЕНИКИ С НИЗКОЙ УСПЕВАЕМОСТЬЮ (средний балл < 3):")
                lines.append("-" * 50)
                for student in sorted(low_achievers, key=lambda x: x.statistics['mean']):
                    mean = student.statistics['mean']
                    failed = student.statistics['failed_count']
                    total = student.statistics['count']
                    lines.append(f"  • {student.name}:")
                    lines.append(f"    Средний балл: {mean:.2f}")
                    lines.append(f"    Неудовлетворительных: {failed} из {total} ({failed / total * 100:.0f}%)")
                    lines.append(f"    Динамика: {student.statistics['trend']}")
            elif filter_type == 'low':
                lines.append("\n✅ Нет учеников с низкой успеваемостью")

        if filter_type in ['all', 'negative']:
            # Ученики с отрицательной динамикой
            negative_trend = [s for s in self.students
                              if s.statistics['trend'] == 'Отрицательная'
                              and s.statistics['mean'] >= 3]  # Исключаем уже попавших в низкую успеваемость

            if negative_trend:
                lines.append("\n📉 УЧЕНИКИ С ОТРИЦАТЕЛЬНОЙ ДИНАМИКОЙ:")
                lines.append("-" * 50)
                for student in sorted(negative_trend, key=lambda x: x.statistics['mean']):
                    first = student.statistics['first_grade']
                    last = student.statistics['last_grade']
                    change = last - first if first and last else 0
                    lines.append(f"  • {student.name}:")
                    lines.append(f"    Средний балл: {student.statistics['mean']:.2f}")
                    lines.append(f"    Изменение: {first:.1f} → {last:.1f} ({change:+.1f})")
            elif filter_type == 'negative':
                lines.append("\n✅ Нет учеников с отрицательной динамикой")

        if filter_type == 'all' and not low_achievers and not negative_trend:
            lines.append("\n✅ Проблемных учеников не обнаружено!")

        lines.append("\n" + "=" * 70)
        lines.append("🏁 Конец отчета")

        self.problems_text.insert(1.0, "\n".join(lines))

    def save_report(self):
        """Сохранение отчета"""
        if not self.students:
            messagebox.showwarning("Предупреждение", "Нет данных для сохранения")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("ШКОЛЬНАЯ АНАЛИТИКА - ОТЧЕТ УСПЕВАЕМОСТИ\n")
                f.write("=" * 80 + "\n")
                f.write(f"Дата отчета: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
                f.write(f"Режим: {'оценки (2-5)' if self.is_grades_mode else 'баллы'}\n\n")

                # Общая статистика
                f.write("ОБЩАЯ СТАТИСТИКА\n")
                f.write("-" * 40 + "\n")

                all_grades = []
                for student in self.students:
                    valid_grades = [g for g in student.grades if g is not None]
                    all_grades.extend(valid_grades)

                if all_grades:
                    f.write(f"Всего учеников: {len(self.students)}\n")
                    f.write(f"Всего оценок: {len(all_grades)}\n")
                    f.write(f"Общий средний балл: {np.mean(all_grades):.2f}\n")
                    f.write(f"Медиана: {np.median(all_grades):.2f}\n")
                    f.write(f"Минимум: {np.min(all_grades)}\n")
                    f.write(f"Максимум: {np.max(all_grades)}\n\n")

                    if self.is_grades_mode:
                        passed = len([g for g in all_grades if g >= 3])
                        failed = len([g for g in all_grades if g < 3])
                        f.write(f"Успешных работ: {passed} ({passed / len(all_grades) * 100:.1f}%)\n")
                        f.write(f"Неудовлетворительных: {failed} ({failed / len(all_grades) * 100:.1f}%)\n\n")

                # Проблемные ученики
                f.write("\nПРОБЛЕМНЫЕ УЧЕНИКИ\n")
                f.write("=" * 40 + "\n")

                low_achievers = [s for s in self.students if s.statistics['mean'] < 3]
                if low_achievers:
                    f.write("\nУченики с низкой успеваемостью (средний балл < 3):\n")
                    for student in sorted(low_achievers, key=lambda x: x.statistics['mean']):
                        f.write(f"  • {student.name}: {student.statistics['mean']:.2f}\n")
                else:
                    f.write("\nНет учеников с низкой успеваемостью\n")

                negative_trend = [s for s in self.students if s.statistics['trend'] == 'Отрицательная']
                if negative_trend:
                    f.write("\nУченики с отрицательной динамикой:\n")
                    for student in negative_trend:
                        f.write(f"  • {student.name}\n")
                else:
                    f.write("\nНет учеников с отрицательной динамикой\n")

                # Детальная информация по ученикам
                f.write("\n\n" + "=" * 80 + "\n")
                f.write("ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ПО КАЖДОМУ УЧЕНИКУ\n")
                f.write("=" * 80 + "\n\n")

                for student in sorted(self.students, key=lambda x: x.name):
                    info = student.get_info()
                    f.write(f"Ученик: {info['name']}\n")
                    f.write(f"  Средний балл: {info['mean']:.2f}\n")
                    f.write(f"  Медиана: {info['median']:.2f}\n")
                    f.write(f"  Минимум: {info['min']}\n")
                    f.write(f"  Максимум: {info['max']}\n")
                    f.write(f"  Динамика: {info['trend']}\n")

                    valid_grades = [g for g in info['grades'] if g is not None]
                    grade_str = []
                    for g in valid_grades:
                        if g.is_integer():
                            grade_str.append(f"{int(g)}")
                        else:
                            grade_str.append(f"{g:.1f}")

                    f.write(f"  Оценки: {', '.join(grade_str)}\n")
                    f.write("-" * 40 + "\n")

            self.log(f"✅ Отчет сохранен: {file_path}")
            messagebox.showinfo("Успех", "Отчет успешно сохранен")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить отчет: {str(e)}")
            self.log(f"❌ Ошибка сохранения: {str(e)}")

    def log(self, message):
        """Добавление сообщения в лог"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.update()

    def load_sample_data(self):
        """Загрузка тестовых данных для демонстрации"""
        import random

        result = messagebox.askyesno("Тестовые данные",
                                     "Загрузить пример данных для тестирования?\n\n"
                                     "Текущие данные будут очищены.")

        if not result:
            return

        # Очищаем кэш
        Student.clear_cache()
        self.students = []
        self.classes = {}

        # Создание тестовых данных
        names = [
            "Иванов Иван Иванович", "Петров Петр Петрович", "Сидорова Анна Сергеевна",
            "Смирнова Елена Владимировна", "Козлов Дмитрий Александрович",
            "Морозова Ольга Николаевна", "Волков Андрей Викторович",
            "Соколова Мария Дмитриевна", "Федоров Алексей Игоревич",
            "Новикова Татьяна Павловна", "Кузнецов Михаил Андреевич",
            "Попова Екатерина Романовна", "Васильев Артем Сергеевич",
            "Павлова Наталья Олеговна", "Семенов Денис Владимирович"
        ]

        # Добавляем дубликаты для проверки объединения
        names.append("Иванов И.И.")
        names.append("Петров П.П.")

        # Определяем режим случайно
        self.is_grades_mode = random.choice([True, False])

        # Создаем учеников
        for name in names:
            # Генерируем оценки
            grades = []
            for _ in range(10):  # 10 работ
                if random.random() < 0.1:  # 10% пропусков
                    grades.append("н")
                else:
                    if self.is_grades_mode:
                        grades.append(random.choices([2, 3, 4, 5], weights=[1, 3, 4, 2])[0])
                    else:
                        grades.append(random.randint(0, 30))

            # Случайный класс
            class_name = random.choice(["5А", "5Б", "6А", "6Б", "7А", None])

            # Создаем ученика (автоматически объединится при совпадении)
            Student(name, grades, class_name)

        # Получаем всех учеников
        self.students = list(Student._instances.values())

        # Формируем словарь классов
        self.classes = {}
        for student in self.students:
            if student.student_class:
                if student.student_class not in self.classes:
                    self.classes[student.student_class] = []
                self.classes[student.student_class].append(student)

        mode_text = "Режим: оценки (2-5)" if self.is_grades_mode else "Режим: баллы"
        self.file_label.config(text="Файл: тестовые данные")
        self.mode_label.config(text=mode_text)

        self.log("📊 Загружены тестовые данные")
        self.log(f"👥 Учеников: {len(self.students)}")

        merged_count = sum(1 for s in self.students if len(s.all_names) > 1)
        if merged_count > 0:
            self.log(f"🔄 Объединено записей: {merged_count}")

        self.log(f"🔢 {mode_text}")

        self.update_analytics()

    def find_class_column(self, df):
        """Поиск колонки с классом в DataFrame"""
        try:
            # Сначала проверяем отдельные строки с классами
            class_boundaries = ClassParser.detect_class_boundaries(df)
            if class_boundaries:
                return None, 'separate_rows', class_boundaries

            classes_in_header = ClassParser.find_classes_in_header_rows(df)
            if classes_in_header:
                return None, 'header_rows', classes_in_header

            # Проверяем первую строку (возможно там класс)
            first_row = df.iloc[0] if len(df) > 0 else None

            # Проверяем все колонки на наличие классов
            for idx, col in enumerate(df.columns):
                if ClassParser.is_class_column(col):
                    return idx, 'column', None

                # Проверяем значения в колонке
                if idx > 0:  # Пропускаем первую колонку (ФИО)
                    sample_values = df[col].dropna().astype(str).head(10)
                    class_count = 0
                    for val in sample_values:
                        if ClassParser.extract_class_from_string(val):
                            class_count += 1
                    if class_count >= 3:  # Если нашли классы в нескольких строках
                        return idx, 'column', None

            # Проверяем первую колонку на наличие классов в ФИО
            first_col = df.columns[0]
            first_col_values = df[first_col].astype(str).tolist()

            for val in first_col_values[:20]:
                class_name = ClassParser.extract_class_from_string(val)
                if class_name:
                    # Проверяем, что после удаления класса осталось осмысленное имя
                    clean_name = re.sub(r'\s*[,\(\)]?\s*' + re.escape(class_name) + r'\s*[,\(\)]?', '', val,
                                        flags=re.IGNORECASE).strip()
                    if clean_name and len(clean_name) > 2 and not clean_name.isdigit():
                        return 0, 'name_with_class', None

            # Поиск класса в заголовке файла
            if first_row is not None:
                for val in first_row.astype(str):
                    class_name = ClassParser.find_class_in_header(val)
                    if class_name:
                        return None, 'header', class_name

        except Exception as e:
            self.log(f"⚠️ Ошибка в find_class_column: {e}")

        return None, None, None

    def process_classes_in_rows(self, class_boundaries, original_data, name_col_idx=0):
        """Обработка файла с классами в отдельных строках"""
        first_col = original_data.columns[name_col_idx]

        for boundary in class_boundaries:
            class_name = boundary['class']
            start_row = boundary['start']
            end_row = boundary['end']

            for idx in range(start_row, end_row + 1):
                if idx >= len(original_data):
                    continue

                row = original_data.iloc[idx]
                name = str(row[first_col]).strip()

                if name and name.lower() not in ['nan', 'none', '']:
                    # Проверяем, что это не служебная строка
                    if not any(keyword in name.lower() for keyword in ['итого', 'средний', 'всего', 'класс']):
                        grades = []
                        for i, val in enumerate(row):
                            if i != name_col_idx:  # Пропускаем колонку с именем
                                grades.append(val)
                        student = Student(name, grades, class_name)
                        self.students.append(student)

                        # Добавляем в словарь классов
                        if class_name not in self.classes:
                            self.classes[class_name] = []
                        self.classes[class_name].append(student)

    def process_classes_in_headers(self, classes_data, original_data, name_col_idx=0):
        """Обработка файла с классами в заголовках"""
        first_col = original_data.columns[name_col_idx]

        for class_name, class_info in classes_data.items():
            for student_info in class_info['students']:
                name = student_info['name']
                grades = student_info['data']
                student = Student(name, grades, class_name)
                self.students.append(student)

                if class_name not in self.classes:
                    self.classes[class_name] = []
                self.classes[class_name].append(student)

    def process_standard_format(self, class_col_idx, class_location, class_data, name_col_idx=0):
        """Обработка стандартного формата (класс в колонке или в ФИО)"""
        first_col = self.data.columns[name_col_idx]
        class_info = class_data if class_location == 'header' else None

        for idx, row in self.data.iterrows():
            try:
                name = str(row[first_col]).strip()

                if not name or name.lower() in ['nan', 'none', '']:
                    continue

                # Пропускаем служебные строки
                if any(keyword in name.lower() for keyword in ['итого', 'средний', 'всего', 'класс']):
                    continue

                # Определяем класс ученика
                student_class = class_info

                if class_location == 'column' and class_col_idx is not None:
                    # Корректируем индекс колонки с классом с учетом смещения
                    adjusted_class_idx = class_col_idx
                    if name_col_idx > 0 and class_col_idx >= name_col_idx:
                        adjusted_class_idx = class_col_idx + 1

                    if adjusted_class_idx < len(row):
                        class_val = row.iloc[adjusted_class_idx]
                        student_class = ClassParser.extract_class_from_string(class_val)

                        grades = []
                        for i, val in enumerate(row):
                            # Пропускаем колонку с именем и колонку с классом
                            if i != name_col_idx and i != adjusted_class_idx:
                                grades.append(val)
                    else:
                        grades = []
                        for i, val in enumerate(row):
                            if i != name_col_idx:
                                grades.append(val)

                elif class_location == 'name_with_class':
                    class_val = ClassParser.extract_class_from_string(name)
                    if class_val:
                        student_class = class_val
                        name = re.sub(r'\s*[,\(\)]?\s*' + re.escape(class_val) + r'\s*[,\(\)]?', '', name,
                                      flags=re.IGNORECASE).strip()
                    grades = []
                    for i, val in enumerate(row):
                        if i != name_col_idx:
                            grades.append(val)
                else:
                    grades = []
                    for i, val in enumerate(row):
                        if i != name_col_idx:
                            grades.append(val)

                # Проверяем, что есть хотя бы одна оценка
                valid_grades = [g for g in grades if pd.notna(g) and str(g).strip() not in ['', 'н', 'н/а']]
                if valid_grades or True:  # Создаем ученика даже без оценок
                    student = Student(name, grades, student_class)
                    self.students.append(student)

                    if student_class:
                        if student_class not in self.classes:
                            self.classes[student_class] = []
                        self.classes[student_class].append(student)

            except Exception as e:
                self.log(f"⚠️ Ошибка обработки строки {idx}: {e}")
                continue

    def process_simple_format(self, name_col_idx=0):
        """Простая обработка данных без поиска классов"""
        try:
            first_col = self.data.columns[name_col_idx]

            for idx, row in self.data.iterrows():
                try:
                    name = str(row[first_col]).strip()

                    # Пропускаем пустые и служебные строки
                    if not name or name.lower() in ['nan', 'none', '']:
                        continue

                    if any(keyword in name.lower() for keyword in ['класс', 'итого', 'средний', 'всего']):
                        continue

                    # Берем все остальные колонки как оценки
                    grades = []
                    for i, val in enumerate(row):
                        if i != name_col_idx:  # Пропускаем колонку с именем
                            grades.append(val)

                    student = Student(name, grades)
                    self.students.append(student)

                except Exception as e:
                    continue

            self.log(f"✅ Альтернативный метод: загружено {len(self.students)} учеников")

        except Exception as e:
            self.log(f"❌ Ошибка в process_simple_format: {e}")


def main():
    # Отключаем предупреждения
    import warnings
    warnings.filterwarnings('ignore')

    root = tk.Tk()

    # Установка иконки (если есть)
    try:
        root.iconbitmap(default='school.ico')
    except:
        pass

    app = SchoolAnalyticsApp(root)

    # Центрирование окна
    root.update()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()