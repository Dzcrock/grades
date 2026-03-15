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

warnings.filterwarnings('ignore', category=DeprecationWarning)

class ClassParser:
    """Класс для парсинга и определения класса ученика"""

    # Паттерны для поиска класса
    CLASS_PATTERNS = [
        r'(\d+)[-\s]*?([А-Яа-я])',  # 5А, 5-А, 5 А
        r'([А-Яа-я])[-\s]*?(\d+)',  # А5, А-5
        r'(\d+)\s*?класс\s*?([А-Яа-я])',  # 5 класс А
        r'([А-Яа-я])\s*?класс\s*?(\d+)',  # А класс 5
        r'класс\s*?(\d+)\s*?([А-Яа-я])',  # класс 5 А
        r'(\d+)\s*?([А-Яа-я])\s*?класс',  # 5 А класс
    ]

    # Паттерны для заголовков колонок с классом
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



class VPRResult:
    """Класс для хранения результатов ВПР одного ученика"""

    def __init__(self, name, task_scores, total_score=None, grade=None):
        self.name = name
        self.task_scores = self._process_scores(task_scores)
        self.total_score = total_score if total_score is not None else sum(self.task_scores)
        self.grade = grade
        self.statistics = self._calculate_statistics()

    def _process_scores(self, scores):
        """Обработка баллов за задания"""
        processed = []
        for score in scores:
            if pd.isna(score) or str(score).strip().lower() in ['н', 'н/а', '']:
                processed.append(0)
            else:
                try:
                    processed.append(float(str(score).replace(',', '.').strip()))
                except:
                    processed.append(0)
        return processed

    def _calculate_statistics(self):
        """Расчет статистики по ВПР"""
        valid_scores = [s for s in self.task_scores if s > 0]

        stats = {
            'total': self.total_score,
            'grade': self.grade,
            'task_count': len(self.task_scores),
            'completed_tasks': len(valid_scores),
            'max_task_score': max(self.task_scores) if self.task_scores else 0,
            'min_task_score': min([s for s in self.task_scores if s > 0]) if valid_scores else 0,
            'avg_task_score': np.mean(valid_scores) if valid_scores else 0,
            'zero_tasks': len([s for s in self.task_scores if s == 0]),
            'completion_percent': (len(valid_scores) / len(self.task_scores) * 100) if self.task_scores else 0
        }

        # Определение уровня (если есть оценка)
        if self.grade is not None:
            if self.grade >= 4.5:
                stats['level'] = 'Высокий'
            elif self.grade >= 3.5:
                stats['level'] = 'Повышенный'
            elif self.grade >= 2.5:
                stats['level'] = 'Базовый'
            else:
                stats['level'] = 'Низкий'
        else:
            # По сумме баллов (перцентили)
            stats['level'] = 'Не определен'

        return stats

    def get_info(self):
        """Получение информации о результате ВПР"""
        return {
            'name': self.name,
            'task_scores': self.task_scores,
            **self.statistics
        }


class VPRAnalytics:
    """Класс для анализа результатов ВПР по всем ученикам"""

    def __init__(self):
        self.results = []
        self.data = None
        self.has_grades = False  # Флаг: есть ли итоговая оценка

    def load_file(self, file_path):
        """Загрузка файла с результатами ВПР"""
        try:
            # Загрузка файла
            if file_path.endswith('.csv'):
                encodings = ['utf-8', 'cp1251', 'windows-1251', 'koi8-r']
                for enc in encodings:
                    try:
                        self.data = pd.read_csv(file_path, encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    self.data = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
            else:
                self.data = pd.read_excel(file_path)

            # Обработка данных
            self._process_data()
            return True, f"Загружено {len(self.results)} результатов ВПР"

        except Exception as e:
            return False, str(e)

    def _process_data(self):
        """Обработка загруженных данных ВПР"""
        if self.data is None or self.data.empty:
            return

        # Очистка данных
        self.data = self.data.dropna(how='all')
        self.results = []

        # Первая колонка - ФИО
        first_col = self.data.columns[0]

        # Анализ структуры файла
        last_col = self.data.columns[-1]
        last_col_data = self.data[last_col].dropna()

        # Проверяем, является ли последняя колонка оценкой (2-5)
        self.has_grades = False
        if len(last_col_data) > 0:
            try:
                sample_values = pd.to_numeric(last_col_data.head(), errors='coerce')
                if not sample_values.isna().all():
                    max_val = sample_values.max()
                    if max_val <= 5 and all(v.is_integer() for v in sample_values if not pd.isna(v)):
                        self.has_grades = True
            except:
                pass

        # Обработка каждого ученика
        for idx, row in self.data.iterrows():
            name = str(row[first_col]).strip()
            if name and name.lower() not in ['nan', 'none', '']:
                # Баллы за задания (все колонки кроме первой и последней)
                task_scores = row[1:-1].tolist() if len(self.data.columns) > 2 else []

                # Итог (последняя колонка)
                total = row[last_col]
                grade = None

                if self.has_grades:
                    # Последняя колонка - оценка
                    try:
                        grade = float(total) if pd.notna(total) else None
                        total = sum(task_scores)  # Сумма баллов за задания
                    except:
                        grade = None
                        total = None
                else:
                    # Последняя колонка - сумма баллов
                    try:
                        total = float(total) if pd.notna(total) else sum(task_scores)
                    except:
                        total = sum(task_scores)

                result = VPRResult(name, task_scores, total, grade)
                self.results.append(result)

        # Сортировка по ФИО
        self.results.sort(key=lambda x: x.name)

    def get_general_stats(self):
        """Получение общей статистики по ВПР"""
        if not self.results:
            return {}

        all_totals = [r.total_score for r in self.results]
        all_grades = [r.grade for r in self.results if r.grade is not None]
        all_completion = [r.statistics['completion_percent'] for r in self.results]

        stats = {
            'total_students': len(self.results),
            'avg_total': np.mean(all_totals),
            'median_total': np.median(all_totals),
            'min_total': np.min(all_totals),
            'max_total': np.max(all_totals),
            'std_total': np.std(all_totals),
            'avg_completion': np.mean(all_completion),
            'total_with_grades': len(all_grades)
        }

        if all_grades:
            stats.update({
                'avg_grade': np.mean(all_grades),
                'grade_distribution': {
                    '5': len([g for g in all_grades if g >= 4.5]),
                    '4': len([g for g in all_grades if 3.5 <= g < 4.5]),
                    '3': len([g for g in all_grades if 2.5 <= g < 3.5]),
                    '2': len([g for g in all_grades if g < 2.5])
                }
            })

        # Распределение по уровням
        levels = {'Высокий': 0, 'Повышенный': 0, 'Базовый': 0, 'Низкий': 0, 'Не определен': 0}
        for r in self.results:
            levels[r.statistics['level']] += 1
        stats['level_distribution'] = levels

        return stats

    def get_task_analysis(self):
        """Анализ выполнения отдельных заданий"""
        if not self.results:
            return {}

        task_count = len(self.results[0].task_scores)
        task_stats = []

        for task_idx in range(task_count):
            task_scores = [r.task_scores[task_idx] for r in self.results]
            valid_scores = [s for s in task_scores if s > 0]

            stats = {
                'task_num': task_idx + 1,
                'avg_score': np.mean(task_scores),
                'median_score': np.median(task_scores),
                'max_score': np.max(task_scores),
                'min_score': np.min([s for s in task_scores if s > 0]) if valid_scores else 0,
                'zero_count': len([s for s in task_scores if s == 0]),
                'completed_count': len(valid_scores),
                'completion_percent': len(valid_scores) / len(self.results) * 100
            }
            task_stats.append(stats)

        return task_stats

    def get_problem_students(self):
        """Выявление проблемных учеников"""
        if not self.results:
            return []

        problem_students = []

        for result in self.results:
            problems = []

            # Низкий общий балл
            if result.total_score < np.mean([r.total_score for r in self.results]) - np.std(
                    [r.total_score for r in self.results]):
                problems.append("низкий общий балл")

            # Низкий процент выполнения
            if result.statistics['completion_percent'] < 50:
                problems.append(f"выполнено только {result.statistics['completion_percent']:.0f}% заданий")

            # Много пропусков/нулей
            if result.statistics['zero_tasks'] > len(result.task_scores) * 0.3:
                problems.append(f"много пропусков ({result.statistics['zero_tasks']} заданий)")

            # Низкая оценка (если есть)
            if result.grade is not None and result.grade < 3:
                problems.append(f"оценка {result.grade}")

            if problems:
                problem_students.append({
                    'name': result.name,
                    'total': result.total_score,
                    'grade': result.grade,
                    'problems': problems,
                    'completion': result.statistics['completion_percent']
                })

        return sorted(problem_students, key=lambda x: x['total'])

    def generate_report(self):
        """Генерация текстового отчета"""
        if not self.results:
            return "Нет данных для анализа"

        stats = self.get_general_stats()
        task_stats = self.get_task_analysis()
        problem_students = self.get_problem_students()

        lines = []
        lines.append("=" * 70)
        lines.append("📊 АНАЛИЗ РЕЗУЛЬТАТОВ ВПР")
        lines.append("=" * 70)
        lines.append(f"Всего участников: {stats['total_students']}")
        lines.append(f"Средний балл: {stats['avg_total']:.2f}")
        lines.append(f"Медиана: {stats['median_total']:.2f}")
        lines.append(f"Минимум: {stats['min_total']}")
        lines.append(f"Максимум: {stats['max_total']}")
        lines.append(f"Стандартное отклонение: {stats['std_total']:.2f}")
        lines.append(f"Средний процент выполнения: {stats['avg_completion']:.1f}%")

        if self.has_grades:
            lines.append("\n📈 РАСПРЕДЕЛЕНИЕ ОЦЕНОК:")
            lines.append("-" * 40)
            for grade, count in stats['grade_distribution'].items():
                percent = count / stats['total_with_grades'] * 100 if stats['total_with_grades'] > 0 else 0
                bar = "█" * int(percent / 5)
                lines.append(f"  Оценка {grade}: {count} чел. ({percent:.1f}%) {bar}")

        lines.append("\n📊 РАСПРЕДЕЛЕНИЕ ПО УРОВНЯМ:")
        lines.append("-" * 40)
        for level, count in stats['level_distribution'].items():
            if count > 0:
                percent = count / stats['total_students'] * 100
                bar = "█" * int(percent / 5)
                lines.append(f"  {level}: {count} чел. ({percent:.1f}%) {bar}")

        lines.append("\n📝 АНАЛИЗ ВЫПОЛНЕНИЯ ЗАДАНИЙ:")
        lines.append("-" * 40)
        for task in task_stats:
            lines.append(f"  Задание {task['task_num']}:")
            lines.append(f"    Средний балл: {task['avg_score']:.2f}")
            lines.append(f"    Выполнили: {task['completed_count']} чел. ({task['completion_percent']:.1f}%)")
            lines.append(f"    Не приступили: {task['zero_count']} чел.")

        if problem_students:
            lines.append("\n⚠️ ПРОБЛЕМНЫЕ УЧАЩИЕСЯ:")
            lines.append("-" * 40)
            for student in problem_students[:10]:  # Топ-10 проблемных
                lines.append(f"  • {student['name']}")
                lines.append(f"    Балл: {student['total']:.1f}, Выполнение: {student['completion']:.1f}%")
                for problem in student['problems']:
                    lines.append(f"    - {problem}")

        return "\n".join(lines)


class Student:
    """Класс для хранения информации о конкретном ученике"""

    def __init__(self, name, grades, student_class=None):
        self.name = name
        self.grades = self._process_grades(grades)
        self.student_class = student_class  # Добавляем поле для класса
        self.statistics = self._calculate_statistics()

    def _process_grades(self, grades):
        """Обработка оценок, замена 'н' на None"""
        processed = []
        for grade in grades:
            if pd.isna(grade) or str(grade).strip().lower() in ['н', 'н/а', 'null', 'none', '']:
                processed.append(None)
            else:
                try:
                    # Пробуем преобразовать в число
                    val = float(str(grade).replace(',', '.').strip())
                    processed.append(val)
                except:
                    processed.append(None)
        return processed

    def _calculate_statistics(self):
        """Расчет статистики по ученику"""
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
                'last_grade': None
            }

        # Основная статистика
        stats = {
            'mean': float(np.mean(valid_grades)),
            'median': float(np.median(valid_grades)),
            'min': float(np.min(valid_grades)),
            'max': float(np.max(valid_grades)),
            'count': len(valid_grades),
            'grade_distribution': self._get_grade_distribution(valid_grades),
            'first_grade': valid_grades[0] if valid_grades else None,
            'last_grade': valid_grades[-1] if valid_grades else None
        }

        # Определяем режим (оценки или баллы)
        is_grades_mode = max(valid_grades) <= 5 and all(g.is_integer() for g in valid_grades if g is not None)

        if is_grades_mode:
            stats['passed_count'] = len([g for g in valid_grades if g >= 3])
            stats['failed_count'] = len([g for g in valid_grades if g < 3])
        else:
            stats['passed_count'] = len(valid_grades)
            stats['failed_count'] = 0

        # Расчет динамики (тренда)
        if len(valid_grades) >= 3:
            x = np.arange(len(valid_grades))
            z = np.polyfit(x, valid_grades, 1)
            trend = float(z[0])
            if trend > 0.1:
                stats['trend'] = 'Положительная'
            elif trend < -0.1:
                stats['trend'] = 'Отрицательная'
            else:
                stats['trend'] = 'Стабильная'
        else:
            stats['trend'] = 'Недостаточно данных'

        return stats

    def _get_grade_distribution(self, grades):
        """Получение распределения оценок"""
        distribution = {}

        # Проверяем, являются ли оценки целыми числами в диапазоне 2-5
        is_standard_grades = all(
            g is not None and
            float(g).is_integer() and
            2 <= float(g) <= 5
            for g in grades
        )

        if is_standard_grades:
            # Для целочисленных оценок 2-5
            distribution = {2: 0, 3: 0, 4: 0, 5: 0}
            for g in grades:
                if g is not None:
                    distribution[int(g)] += 1
        else:
            # Для баллов или нестандартных оценок
            for g in grades:
                if g is not None:
                    # Округляем до 2 знаков для группировки
                    key = round(g, 2)
                    distribution[key] = distribution.get(key, 0) + 1

        return distribution

    def get_info(self):
        """Получение информации об ученике"""
        return {
            'name': self.name,
            'grades': self.grades,
            **self.statistics
        }


class SchoolAnalyticsApp:
    def add_vpr_tab_to_app(self):
        """Функция для добавления вкладки ВПР в основное приложение"""

        # Создание вкладки ВПР
        self.vpr_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.vpr_frame, text="📋 ВПР Аналитика")

        # Инициализация анализатора ВПР
        self.vpr_analyzer = VPRAnalytics()

        # Верхняя панель с кнопками
        top_frame = ttk.Frame(self.vpr_frame, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Button(top_frame, text="📂 Загрузить файл ВПР",
                   command=self.load_vpr_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="📊 Обновить аналитику ВПР",
                   command=self.update_vpr_analytics).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="💾 Сохранить отчет ВПР",
                   command=self.save_vpr_report).pack(side=tk.LEFT, padx=5)

        self.vpr_file_label = ttk.Label(top_frame, text="Файл ВПР не загружен", foreground="gray")
        self.vpr_file_label.pack(side=tk.LEFT, padx=20)

        # Панель с аналитикой ВПР
        content_frame = ttk.Frame(self.vpr_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель - общая статистика
        left_panel = ttk.LabelFrame(content_frame, text="Общая статистика", padding="5")
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        self.vpr_stats_text = scrolledtext.ScrolledText(left_panel, height=20,
                                                        font=('Consolas', 10), wrap=tk.WORD)
        self.vpr_stats_text.pack(fill=tk.BOTH, expand=True)

        # Правая панель - графики
        right_panel = ttk.LabelFrame(content_frame, text="Визуализация", padding="5")
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)

        self.vpr_figure = plt.Figure(figsize=(8, 6), dpi=100)
        self.vpr_canvas = FigureCanvasTkAgg(self.vpr_figure, right_panel)
        self.vpr_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def load_vpr_file(self):
        """Загрузка файла с результатами ВПР"""
        file_path = filedialog.askopenfilename(
            title="Выберите файл с результатами ВПР",
            filetypes=[
                ("Все поддерживаемые", "*.xlsx *.xls *.csv"),
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All files", "*.*")
            ]
        )

        if not file_path:
            return

        success, message = self.vpr_analyzer.load_file(file_path)

        if success:
            self.vpr_file_label.config(text=f"Файл: {os.path.basename(file_path)}")
            self.log(f"✅ Файл ВПР загружен: {file_path}")
            self.log(f"📊 {message}")
            self.update_vpr_analytics()
        else:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {message}")
            self.log(f"❌ Ошибка загрузки ВПР: {message}")

    def update_vpr_analytics(self):
        """Обновление аналитики ВПР"""
        if not self.vpr_analyzer.results:
            messagebox.showwarning("Предупреждение", "Нет данных ВПР для анализа")
            return

        # Отображение статистики
        report = self.vpr_analyzer.generate_report()
        self.vpr_stats_text.delete(1.0, tk.END)
        self.vpr_stats_text.insert(1.0, report)

        # Построение графиков
        self.plot_vpr_charts()

        self.log("🔄 Аналитика ВПР обновлена")

    def plot_vpr_charts(self):
        """Построение графиков по результатам ВПР"""
        self.vpr_figure.clear()

        if not self.vpr_analyzer.results:
            return

        stats = self.vpr_analyzer.get_general_stats()
        task_stats = self.vpr_analyzer.get_task_analysis()

        # График 1: Распределение итоговых баллов
        ax1 = self.vpr_figure.add_subplot(221)

        totals = [r.total_score for r in self.vpr_analyzer.results]
        ax1.hist(totals, bins=15, edgecolor='black', alpha=0.7, color='#4d96ff')
        ax1.axvline(x=stats['avg_total'], color='red', linestyle='--',
                    linewidth=2, label=f"Среднее: {stats['avg_total']:.1f}")
        ax1.set_xlabel('Итоговый балл')
        ax1.set_ylabel('Количество учеников')
        ax1.set_title('Распределение итоговых баллов')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # График 2: Распределение по уровням
        ax2 = self.vpr_figure.add_subplot(222)

        levels = stats['level_distribution']
        if any(levels.values()):
            colors = {'Высокий': '#6bcb77', 'Повышенный': '#4d96ff',
                      'Базовый': '#ffd93d', 'Низкий': '#ff6b6b', 'Не определен': '#95a5a6'}
            wedges, texts, autotexts = ax2.pie(
                levels.values(),
                labels=levels.keys(),
                colors=[colors[k] for k in levels.keys()],
                autopct='%1.1f%%',
                startangle=90
            )
            ax2.set_title('Распределение по уровням')

        # График 3: Выполнение заданий
        ax3 = self.vpr_figure.add_subplot(223)

        if task_stats:
            tasks = [t['task_num'] for t in task_stats]
            completion = [t['completion_percent'] for t in task_stats]
            avg_scores = [t['avg_score'] for t in task_stats]

            ax3.bar(tasks, completion, color='#6bcb77', alpha=0.7, edgecolor='black')
            ax3.set_xlabel('Номер задания')
            ax3.set_ylabel('Процент выполнения')
            ax3.set_title('Выполнение заданий')
            ax3.set_ylim(0, 105)
            ax3.grid(True, alpha=0.3, axis='y')

            # Добавление значений
            for i, (task, comp) in enumerate(zip(tasks, completion)):
                ax3.text(task, comp + 1, f'{comp:.0f}%', ha='center', va='bottom', fontsize=8)

        # График 4: Топ проблемных заданий
        ax4 = self.vpr_figure.add_subplot(224)

        if task_stats:
            # Сортируем по проценту выполнения
            problem_tasks = sorted(task_stats, key=lambda x: x['completion_percent'])[:5]
            tasks = [f"Зад.{t['task_num']}" for t in problem_tasks]
            zero_counts = [t['zero_count'] for t in problem_tasks]

            bars = ax4.barh(tasks, zero_counts, color='#ff6b6b', alpha=0.7, edgecolor='black')
            ax4.set_xlabel('Количество не приступивших')
            ax4.set_title('Самые проблемные задания')

            # Добавление значений
            for bar, count in zip(bars, zero_counts):
                ax4.text(count + 0.1, bar.get_y() + bar.get_height() / 2,
                         str(count), va='center')

        self.vpr_figure.tight_layout()
        self.vpr_canvas.draw()

    def save_vpr_report(self):
        """Сохранение отчета по ВПР"""
        if not self.vpr_analyzer.results:
            messagebox.showwarning("Предупреждение", "Нет данных ВПР для сохранения")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not file_path:
            return

        try:
            report = self.vpr_analyzer.generate_report()

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(report)

                # Добавляем детальную информацию по каждому ученику
                f.write("\n\n" + "=" * 70 + "\n")
                f.write("ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ПО УЧЕНИКАМ\n")
                f.write("=" * 70 + "\n\n")

                for result in sorted(self.vpr_analyzer.results, key=lambda x: x.total_score, reverse=True):
                    info = result.get_info()
                    f.write(f"Ученик: {info['name']}\n")
                    f.write(f"  Итоговый балл: {info['total']:.1f}\n")
                    if info['grade']:
                        f.write(f"  Оценка: {info['grade']}\n")
                    f.write(f"  Уровень: {info['level']}\n")
                    f.write(
                        f"  Выполнено заданий: {info['completed_tasks']} из {info['task_count']} ({info['completion_percent']:.1f}%)\n")

                    # Баллы по заданиям
                    task_scores_str = [f"{s:.0f}" if s.is_integer() else f"{s:.1f}" for s in info['task_scores']]
                    f.write(f"  Баллы по заданиям: {', '.join(task_scores_str)}\n")
                    f.write("-" * 40 + "\n")

            self.log(f"✅ Отчет ВПР сохранен: {file_path}")
            messagebox.showinfo("Успех", "Отчет ВПР успешно сохранен")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить отчет: {str(e)}")
            self.log(f"❌ Ошибка сохранения отчета ВПР: {str(e)}")

    def __init__(self, root):
        self.root = root
        self.root.title("Школьная аналитика - Анализ успеваемости")
        self.root.geometry("1400x800")

        # Переменные
        self.students = []
        self.data = None
        self.current_student = None
        self.is_grades_mode = True  # True - оценки 2-5, False - баллы

        # Настройка стилей
        self.setup_styles()

        # Создание интерфейса
        self.create_widgets()

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

        # Кнопки
        ttk.Button(top_frame, text="📂 Загрузить файл", command=self.load_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="🔄 Обновить аналитику", command=self.update_analytics).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="💾 Сохранить отчет", command=self.save_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="📊 Пример данных", command=self.load_sample_data).pack(side=tk.LEFT, padx=5)

        # Информация о файле
        self.file_label = ttk.Label(top_frame, text="Файл не загружен", foreground="gray")
        self.file_label.pack(side=tk.LEFT, padx=20)

        # Индикатор режима
        self.mode_label = ttk.Label(top_frame, text="", foreground="blue")
        self.mode_label.pack(side=tk.LEFT, padx=10)

        # Основная область с вкладками
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Вкладка общей аналитики
        self.general_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.general_frame, text="📊 Общая аналитика")
        self.create_general_tab()

        # Вкладка по ученикам
        self.students_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.students_frame, text="👥 По ученикам")
        self.create_students_tab()

        # Вкладка с диаграммами
        self.charts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.charts_frame, text="📈 Визуализация")
        self.create_charts_tab()

        # Вкладка с проблемными учениками
        self.problems_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.problems_frame, text="⚠️ Проблемные ученики")
        self.create_problems_tab()

        # Нижняя панель с логами
        bottom_frame = ttk.Frame(self.root, padding="5")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM)

        # Лог
        self.log_text = scrolledtext.ScrolledText(bottom_frame, height=5, width=100,
                                                  font=('Consolas', 9), bg='#f0f0f0')
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log("✅ Программа запущена. Загрузите файл с данными.")
        # Вкладка с классами
        self.classes_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.classes_frame, text="🏫 По классам")
        self.create_classes_tab()
        self.add_vpr_tab_to_app()

        # ... остальной код ...

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

    def update_classes_list(self):
        """Обновление списка классов с сортировкой"""
        if not hasattr(self, 'classes') or not self.classes:
            return

        self.class_listbox.delete(0, tk.END)

        stats = self.get_class_statistics()
        sort_by = self.class_sort_var.get()

        if sort_by == 'name':
            items = sorted(self.classes.keys())
        elif sort_by == 'avg':
            items = sorted(self.classes.keys(),
                           key=lambda x: stats.get(x, {}).get('avg_class_mean', 0),
                           reverse=True)
        elif sort_by == 'count':
            items = sorted(self.classes.keys(),
                           key=lambda x: len(self.classes[x]),
                           reverse=True)

        for class_name in items:
            students = self.classes[class_name]
            class_stats = stats.get(class_name, {})
            avg = class_stats.get('avg_class_mean', 0)

            # Определяем цвет в зависимости от успеваемости
            if avg >= 4:
                prefix = "🏆 "
            elif avg >= 3:
                prefix = "📚 "
            else:
                prefix = "⚠️ "

            display = f"{prefix}{class_name} ({len(students)} уч., ср.{avg:.2f})"
            self.class_listbox.insert(tk.END, display)

            # Раскрашиваем строки
            if avg >= 4:
                self.class_listbox.itemconfig(tk.END, fg='green')
            elif avg >= 3:
                self.class_listbox.itemconfig(tk.END, fg='blue')
            else:
                self.class_listbox.itemconfig(tk.END, fg='red')

    def on_class_select(self, event):
        """Обработка выбора класса"""
        selection = self.class_listbox.curselection()
        if selection and hasattr(self, 'classes'):
            index = selection[0]
            class_name = list(sorted(self.classes.keys()))[index]
            self.show_class_info(class_name)

    def show_class_info(self, class_name):
        """Отображение информации о классе"""
        if not hasattr(self, 'classes') or class_name not in self.classes:
            return

        students = self.classes[class_name]
        stats = self.get_class_statistics().get(class_name, {})

        # Общая информация
        self.show_class_general_info(class_name, students, stats)

        # Графики
        self.plot_class_charts(class_name, students, stats)

        # Список учеников
        self.show_class_students_list(students)

        # Динамика класса
        self.show_class_dynamics(students)

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
        """Построение нескольких графиков для класса"""
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
            if self.is_grades_mode and max(all_grades) <= 5:
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

        wedges, texts, autotexts = ax3.pie(
            [s for s in sizes if s > 0],
            labels=[l for l, s in zip(labels, sizes) if s > 0],
            colors=[c for c, s in zip(colors, sizes) if s > 0],
            autopct='%1.1f%%',
            startangle=90,
            explode=[e for e, s in zip(explode, sizes) if s > 0]
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

    def update_analytics(self):
        """Обновление всей аналитики"""
        if not self.students:
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

        self.log("🔄 Аналитика обновлена")

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

    def debug_print_first_rows(self, num_rows=5):
        """Отладка - вывод первых строк данных"""
        if self.data is None:
            self.log("❌ Нет данных для отладки")
            return

        self.log("📋 Первые строки данных:")
        for i in range(min(num_rows, len(self.data))):
            row = self.data.iloc[i]
            row_str = " | ".join([f"{col}: {val}" for col, val in zip(self.data.columns, row)])
            self.log(f"  Строка {i + 1}: {row_str[:100]}...")

    def load_file(self):
        """Загрузка файла Excel или CSV"""
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

        try:
            # Сброс предыдущих данных
            self.students = []
            self.classes = {}

            # Определение типа файла и загрузка
            if file_path.endswith('.csv'):
                # Пробуем разные кодировки для CSV
                encodings = ['utf-8', 'cp1251', 'windows-1251', 'koi8-r']
                loaded = False
                for enc in encodings:
                    try:
                        self.data = pd.read_csv(file_path, encoding=enc)
                        self.log(f"CSV загружен с кодировкой {enc}")
                        loaded = True
                        break
                    except UnicodeDecodeError:
                        continue
                if not loaded:
                    self.data = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
            else:
                self.data = pd.read_excel(file_path)

            # Проверка, что данные загружены
            if self.data is None or self.data.empty:
                messagebox.showerror("Ошибка", "Файл пуст или не содержит данных")
                return

            # Отладка - показываем первые строки
            self.debug_print_first_rows()

            # Обработка данных
            self.process_data()

            # Обновление отображения
            self.file_label.config(text=f"Файл: {os.path.basename(file_path)}")
            mode_text = "Режим: оценки (2-5)" if self.is_grades_mode else "Режим: баллы"
            self.mode_label.config(text=mode_text)

            self.log(f"✅ Файл загружен: {file_path}")
            self.log(f"📊 Найдено учеников: {len(self.students)}")

            if self.data is not None:
                self.log(f"📝 Количество колонок: {len(self.data.columns)}")

            self.log(f"🔢 {mode_text}")

            self.update_analytics()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {str(e)}")
            self.log(f"❌ Ошибка загрузки: {str(e)}")
            import traceback
            traceback.print_exc()
    def process_data(self):
        """Обработка загруженных данных"""
        if self.data is None or self.data.empty:
            self.log("❌ Данные отсутствуют")
            return

        try:
            # Удаляем полностью пустые строки
            self.data = self.data.dropna(how='all')

            if len(self.data) == 0:
                self.log("❌ Нет данных после удаления пустых строк")
                return

            # Определяем, является ли первая колонка нумерацией
            first_col = self.data.columns[0]
            first_col_data = self.data[first_col].astype(str).tolist()

            # Проверяем, содержит ли первая колонка только цифры (номера)
            is_numbering = True
            name_col_idx = 0

            for val in first_col_data[:20]:  # Проверяем первые 20 строк
                val = val.strip()
                if val and val.lower() not in ['nan', 'none', '']:
                    # Если значение не является числом или содержит буквы - это ФИО
                    if not val.isdigit() and any(c.isalpha() for c in val):
                        is_numbering = False
                        break

            if is_numbering:
                # Первая колонка - нумерация, используем вторую колонку для ФИО
                self.log("📌 Обнаружена нумерация в первой колонке, используем вторую колонку для ФИО")
                name_col_idx = 1
                first_col = self.data.columns[1]

            # Сохраняем оригинальные данные
            original_data = self.data.copy()

            # Поиск колонки с классом
            class_col_idx, class_location, class_data = self.find_class_column(self.data)

            # Определяем режим (оценки или баллы)
            self.is_grades_mode = self.detect_grades_mode()

            # Создание объектов учеников
            self.students = []
            self.classes = {}

            # Обработка в зависимости от расположения классов
            if class_location == 'separate_rows' and class_data:
                # Классы в отдельных строках
                self.process_classes_in_rows(class_data, original_data, name_col_idx)
            elif class_location == 'header_rows' and class_data:
                # Классы в заголовках
                self.process_classes_in_headers(class_data, original_data, name_col_idx)
            else:
                # Стандартная обработка
                self.process_standard_format(class_col_idx, class_location, class_data, name_col_idx)

            if not self.students:
                self.log("❌ Не удалось создать ни одного ученика")
                # Попробуем альтернативный метод - просто взять все строки
                self.log("🔄 Пробуем альтернативный метод обработки...")
                self.process_simple_format(name_col_idx)

            if self.students:
                # Сортировка учеников по классу и имени
                self.students.sort(key=lambda x: (x.student_class or '', x.name))

                # Обновление списка учеников
                self.update_students_list()

                # Логирование информации о классах
                self.log(f"✅ Загружено учеников: {len(self.students)}")
                if self.classes:
                    self.log(f"📚 Найдено классов: {len(self.classes)}")
                    for class_name, students in sorted(self.classes.items()):
                        self.log(f"   Класс {class_name}: {len(students)} учеников")
                else:
                    self.log("📚 Информация о классах не найдена")
            else:
                self.log("❌ Не удалось загрузить ни одного ученика")

        except Exception as e:
            self.log(f"❌ Ошибка в process_data: {str(e)}")
            import traceback
            traceback.print_exc()

    def detect_grades_mode(self):
        """Определение режима (оценки или баллы)"""
        try:
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
                return

            # Группировка по классам
            current_class = None
            for student in self.students:
                # Добавляем разделитель для нового класса
                if student.student_class != current_class:
                    current_class = student.student_class
                    if current_class:
                        display_text = f"📚 КЛАСС {current_class}"
                        self.students_listbox.insert(tk.END, display_text)
                        self.students_listbox.itemconfig(tk.END, fg='blue', font=('Arial', 10, 'bold'))

                # Добавляем ученика с индикатором проблемы
                prefix = ""
                if student.statistics and student.statistics.get('mean', 0) < 3:
                    prefix = "⚠️ "
                elif student.statistics and student.statistics.get('trend') == 'Отрицательная':
                    prefix = "📉 "

                display_name = f"   {prefix}{student.name}"
                self.students_listbox.insert(tk.END, display_name)
        except Exception as e:
            self.log(f"⚠️ Ошибка обновления списка: {e}")

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
                    if student.statistics and student.statistics.get('mean', 0) < 3:
                        prefix = "⚠️ "
                    elif student.statistics and student.statistics.get('trend') == 'Отрицательная':
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
        info = student.get_info()

        lines = []
        lines.append("═" * 50)
        if student.student_class:
            lines.append(f"📚 Класс: {student.student_class}")
        lines.append(f"👤 {info['name']}")
        lines.append("═" * 50)

        # Текстовая информация
        lines = []
        lines.append("═" * 50)
        lines.append(f"👤 {info['name']}")
        lines.append("═" * 50)
        lines.append(f"📊 Средний балл: {info['mean']:.2f}")
        lines.append(f"📈 Медиана: {info['median']:.2f}")
        lines.append(f"📉 Минимум: {info['min']}")
        lines.append(f"📈 Максимум: {info['max']}")
        lines.append(f"📝 Количество работ: {info['count']}")
        lines.append(f"📊 Динамика: {info['trend']}")

        if self.is_grades_mode:
            lines.append(f"✅ Положительных оценок: {info['passed_count']}")
            lines.append(f"❌ Неудовлетворительных: {info['failed_count']}")

        if info['first_grade'] is not None and info['last_grade'] is not None:
            change = info['last_grade'] - info['first_grade']
            change_symbol = "📈" if change > 0 else "📉" if change < 0 else "➡️"
            lines.append(f"{change_symbol} Изменение: {change:+.2f}")

        lines.append("\n📊 Распределение оценок:")
        for grade, count in sorted(info['grade_distribution'].items()):
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
            messagebox.showwarning("Предупреждение", "Нет данных для анализа")
            return

        self.update_general_stats()
        self.update_charts()
        self.show_problems()
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
        """Построение общего графика статистики"""
        self.general_figure.clear()

        if not all_grades:
            return

        # Гистограмма распределения
        ax1 = self.general_figure.add_subplot(121)

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

            # Добавление значений
            for i in range(len(patches)):
                if n[i] > 0:
                    ax1.text(patches[i].get_x() + patches[i].get_width() / 2,
                             patches[i].get_height(), f'{int(n[i])}',
                             ha='center', va='bottom', fontsize=8)

        ax1.grid(True, alpha=0.3)

        # Ящик с усами
        ax2 = self.general_figure.add_subplot(122)

        # Подготовка данных по ученикам (первые 10)
        student_grades = []
        student_names = []

        for student in sorted(self.students, key=lambda x: x.statistics['mean'], reverse=True)[:10]:
            valid = [g for g in student.grades if g is not None]
            if valid:
                student_grades.append(valid)
                name = student.name.split()[0] if len(student.name.split()) > 0 else student.name
                if len(name) > 15:
                    name = name[:12] + "..."
                student_names.append(name)

        if student_grades:
            bp = ax2.boxplot(student_grades, labels=student_names, patch_artist=True,
                             showmeans=True, meanline=True)

            # Настройка цветов
            for patch, color in zip(bp['boxes'], plt.cm.viridis(np.linspace(0.2, 0.8, len(student_grades)))):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            for median in bp['medians']:
                median.set_color('red')
                median.set_linewidth(2)

            for mean in bp['means']:
                mean.set_color('blue')
                mean.set_linewidth(1)
                mean.set_linestyle('--')

            ax2.set_ylabel('Оценки/Баллы', fontsize=11)
            ax2.set_title('Сравнение учеников (топ-10)', fontsize=12, fontweight='bold')
            ax2.tick_params(axis='x', rotation=45)
            ax2.grid(True, alpha=0.3, axis='y')

        self.general_figure.tight_layout()
        self.general_canvas.draw()

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

        wedges, texts, autotexts = ax2.pie(
            trends.values(),
            labels=trends.keys(),
            colors=[colors_trend[k] for k in trends.keys()],
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

        data = {"ФИО": names}

        # Определяем режим случайно
        self.is_grades_mode = random.choice([True, False])

        # Добавление 10 контрольных работ
        for i in range(1, 11):
            grades = []
            for _ in names:
                if random.random() < 0.1:  # 10% пропусков
                    grades.append("н")
                else:
                    if self.is_grades_mode:
                        # Оценки 2-5 с разной вероятностью
                        grades.append(random.choices([2, 3, 4, 5], weights=[1, 3, 4, 2])[0])
                    else:
                        # Баллы от 0 до 30
                        grades.append(random.randint(0, 30))
            data[f"Работа {i}"] = grades

        self.data = pd.DataFrame(data)
        self.process_data()

        mode_text = "Режим: оценки (2-5)" if self.is_grades_mode else "Режим: баллы"
        self.file_label.config(text="Файл: тестовые данные")
        self.mode_label.config(text=mode_text)

        self.log("📊 Загружены тестовые данные")
        self.log(f"👥 Учеников: {len(self.students)}")
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