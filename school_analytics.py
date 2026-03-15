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

warnings.filterwarnings('ignore', category=DeprecationWarning)


class VPRResult:
    """Класс для хранения результатов ВПР одного ученика"""

    def __init__(self, name, task_scores, total_score=None, grade=None):
        self.name = name
        self.task_scores = self._process_scores(task_scores)
        self.total_score = total_score if total_score is not None else sum(self.task_scores)
        self.grade = grade
        self.statistics = self._calculate_statistics()
        self.create_widgets()
        self.add_vpr_tab_to_app()

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

    def __init__(self, name, grades):
        self.name = name
        self.grades = self._process_grades(grades)
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
            # Определение типа файла и загрузка
            if file_path.endswith('.csv'):
                # Пробуем разные кодировки для CSV
                encodings = ['utf-8', 'cp1251', 'windows-1251', 'koi8-r']
                for enc in encodings:
                    try:
                        self.data = pd.read_csv(file_path, encoding=enc)
                        self.log(f"CSV загружен с кодировкой {enc}")
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    self.data = pd.read_csv(file_path, encoding='utf-8', errors='ignore')
            else:
                self.data = pd.read_excel(file_path)

            # Обработка данных
            self.process_data()

            # Обновление отображения
            self.file_label.config(text=f"Файл: {os.path.basename(file_path)}")
            mode_text = "Режим: оценки (2-5)" if self.is_grades_mode else "Режим: баллы"
            self.mode_label.config(text=mode_text)

            self.log(f"✅ Файл загружен: {file_path}")
            self.log(f"📊 Найдено учеников: {len(self.students)}")
            self.log(f"📝 Количество работ: {len(self.data.columns) - 1}")
            self.log(f"🔢 {mode_text}")

            self.update_analytics()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {str(e)}")
            self.log(f"❌ Ошибка загрузки: {str(e)}")

    def process_data(self):
        """Обработка загруженных данных"""
        if self.data is None or self.data.empty:
            return

        # Очистка данных
        self.data = self.data.dropna(how='all')  # Удаляем полностью пустые строки

        # Предполагаем, что первая колонка - ФИО
        first_col = self.data.columns[0]

        # Определяем режим (оценки или баллы)
        sample_data = self.data.iloc[0:5, 1:].values.flatten()  # Берем первые 5 строк для анализа
        numeric_values = []

        for val in sample_data:
            if pd.notna(val) and str(val).strip().lower() not in ['н', 'н/а', '']:
                try:
                    num = float(str(val).replace(',', '.').strip())
                    numeric_values.append(num)
                except:
                    pass

        if numeric_values:
            max_val = max(numeric_values)
            # Если все значения <= 5 и целые числа - это оценки
            if max_val <= 5 and all(v.is_integer() for v in numeric_values):
                self.is_grades_mode = True
            else:
                self.is_grades_mode = False
        else:
            self.is_grades_mode = True  # По умолчанию

        # Создание объектов учеников
        self.students = []
        for idx, row in self.data.iterrows():
            name = str(row[first_col]).strip()
            if name and name.lower() not in ['nan', 'none', '']:
                grades = row[1:].tolist()
                student = Student(name, grades)
                self.students.append(student)

        # Сортировка учеников по имени
        self.students.sort(key=lambda x: x.name)

        # Обновление списка учеников
        self.update_students_list()

    def update_students_list(self):
        """Обновление списка учеников в интерфейсе"""
        self.students_listbox.delete(0, tk.END)
        for student in self.students:
            # Добавляем индикатор проблемы
            prefix = ""
            if student.statistics['mean'] < 3:
                prefix = "⚠️ "
            elif student.statistics['trend'] == 'Отрицательная':
                prefix = "📉 "
            self.students_listbox.insert(tk.END, f"{prefix}{student.name}")

    def filter_students(self, *args):
        """Фильтрация списка учеников"""
        search_term = self.search_var.get().lower()
        self.students_listbox.delete(0, tk.END)

        for student in self.students:
            if search_term in student.name.lower():
                prefix = ""
                if student.statistics['mean'] < 3:
                    prefix = "⚠️ "
                elif student.statistics['trend'] == 'Отрицательная':
                    prefix = "📉 "
                self.students_listbox.insert(tk.END, f"{prefix}{student.name}")

    def on_student_select(self, event):
        """Обработка выбора ученика из списка"""
        selection = self.students_listbox.curselection()
        if selection:
            index = selection[0]
            item_text = self.students_listbox.get(index)
            # Убираем возможные префиксы
            student_name = item_text.replace("⚠️ ", "").replace("📉 ", "")

            # Поиск ученика
            for student in self.students:
                if student.name == student_name:
                    self.show_student_info(student)
                    break

    def show_student_info(self, student):
        """Отображение информации о конкретном ученике"""
        info = student.get_info()

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