import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import re
import warnings
import openpyxl
import xlrd

warnings.filterwarnings('ignore')
from sklearn.linear_model import LinearRegression

# Проверка наличия plotly
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    PLOTLY_AVAILABLE = True
except ImportError as e:
    st.warning(f"Plotly не установлен: {e}. Некоторые визуализации будут недоступны.")
    PLOTLY_AVAILABLE = False


    class DummyPlotly:
        def __init__(self):
            pass


    px = DummyPlotly()
    go = DummyPlotly()
    make_subplots = None

# Проверка наличия sklearn
try:
    from sklearn.linear_model import LinearRegression

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    st.warning("scikit-learn не установлен. Некоторые функции анализа будут недоступны.")

__author__ = "Даниил Зуев"
__version__ = "2.0.0"
__year__ = "2026"

st.set_page_config(
    page_title="Анализ успеваемости учеников",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Инициализация сессионных переменных
if 'attendance_data' not in st.session_state:
    st.session_state.attendance_data = {}
if 'exam_data' not in st.session_state:
    st.session_state.exam_data = {}
if 'classes_data' not in st.session_state:
    st.session_state.classes_data = {}
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Анализ текущей успеваемости"
if 'student_profiles' not in st.session_state:
    st.session_state.student_profiles = {}
if 'selected_student_attendance' not in st.session_state:
    st.session_state.selected_student_attendance = None
if 'selected_student_exam' not in st.session_state:
    st.session_state.selected_student_exam = None
if 'attendance_analysis_complete' not in st.session_state:
    st.session_state.attendance_analysis_complete = False
if 'exam_analysis_complete' not in st.session_state:
    st.session_state.exam_analysis_complete = False
if 'individual_analysis_data' not in st.session_state:
    st.session_state.individual_analysis_data = {
        'attendance': {'student': None, 'data': None},
        'exam': {'student': None, 'data': None}
    }

# Информация о разработчике в сайдбаре
st.sidebar.markdown("""
---
### 👨‍💻 О программе
**Разработчик:** Даниил Зуев  
**Версия:** 2.0.0  
**Год:** 2026  

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white)](https://github.com/)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/)
""")

# Боковое меню
with st.sidebar:
    st.title("📚 Навигация")
    page = st.radio(
        "Выберите раздел",
        ["Анализ текущей успеваемости", "Анализ экзаменов", "Сравнение экзаменов", "Статистика по классам"]
    )
    st.session_state.current_page = page


def preview_cleaned_data(df, name_column):
    """Предпросмотр очищенных данных"""
    st.subheader("📊 Очищенные данные")

    # Показываем первые строки
    st.write("**Первые 5 строк после очистки:**")
    st.dataframe(df.head(), use_container_width=True)

    # Информация о структуре
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Всего строк:** {len(df)}")
        st.write(f"**Всего колонок:** {len(df.columns)}")
    with col2:
        st.write(f"**Определена колонка ФИО:** {name_column}")
        if name_column in df.columns:
            non_empty = df[name_column].notna().sum()
            st.write(f"**Непустых ФИО:** {non_empty}")

    # Показываем список найденных учеников
    if name_column in df.columns:
        with st.expander("📋 Список найденных учеников"):
            students = df[name_column].dropna().tolist()[:20]
            students_df = pd.DataFrame({
                '№': range(1, len(students) + 1),
                'ФИО': students
            })
            st.dataframe(students_df, use_container_width=True)


def filter_exam_outliers(grades_df, max_reasonable_score=100):
    """Фильтрация выбросов в экзаменационных данных"""
    filtered_df = grades_df.copy()

    for col in filtered_df.columns:
        # Пропускаем колонку с суммой баллов
        if col == 'Сумма баллов':
            continue

        # Заменяем значения больше max_reasonable_score на NaN
        filtered_df[col] = filtered_df[col].apply(
            lambda x: x if pd.isna(x) or x <= max_reasonable_score else np.nan
        )

    return filtered_df


def find_name_column(df):
    """Автоматический поиск колонки с ФИО"""
    for col in df.columns:
        # Проверяем название колонки
        col_lower = str(col).lower()
        name_keywords = ['фио', 'ф.и.о.', 'фамилия', 'имя', 'ученик', 'студент', 'name', 'full name']
        if any(keyword in col_lower for keyword in name_keywords):
            return col

        # Проверяем содержимое колонки
        sample = df[col].dropna().head(10)
        if len(sample) > 0:
            # Проверяем, что значения похожи на имена (содержат буквы и пробелы)
            name_count = 0
            for val in sample:
                val_str = str(val).strip()
                # Имя обычно содержит буквы и может содержать пробелы
                if any(c.isalpha() for c in val_str) and not val_str.replace(' ', '').isdigit():
                    # Проверяем, что это не служебное слово
                    if not any(keyword in val_str.lower() for keyword in ['итого', 'средний', 'всего']):
                        name_count += 1
            if name_count >= len(sample) * 0.7:  # Более 70% значений похожи на имена
                return col

    return None

def configure_max_scores(exam_grades_df):
    """Настройка максимальных баллов для каждого вопроса"""
    st.subheader("⚙️ Настройка максимальных баллов для вопросов")

    # Определяем вопросы (колонки с баллами)
    question_columns = [col for col in exam_grades_df.columns if col != 'Сумма баллов']

    if not question_columns:
        st.warning("Не найдены колонки с вопросами")
        return exam_grades_df, {}

    # Инициализируем максимальные баллы
    max_scores = {}

    # Автоматическое определение максимальных баллов
    for col in question_columns:
        # Пытаемся определить максимальный балл из данных
        max_value = exam_grades_df[col].max()
        if pd.notna(max_value) and max_value > 0:
            max_scores[col] = float(max_value)
        else:
            max_scores[col] = 1.0  # По умолчанию 1 балл

    st.info("💡 Вы можете настроить максимальные баллы для каждого вопроса")

    # Создаем интерфейс для настройки
    cols = st.columns(4)
    for i, col in enumerate(question_columns[:20]):  # Ограничиваем 20 вопросами
        with cols[i % 4]:
            new_max = st.number_input(
                f"Вопрос {col}",
                min_value=0.0,
                max_value=100.0,
                value=float(max_scores[col]),
                step=0.5,
                key=f"max_score_{col}"
            )
            max_scores[col] = new_max

    # Применяем нормализацию баллов
    st.subheader("📊 Результаты после нормализации")

    normalized_grades = exam_grades_df.copy()
    for col in question_columns:
        if col in max_scores and max_scores[col] > 0:
            # Нормализуем баллы к 5-балльной шкале
            normalized_grades[col] = (exam_grades_df[col] / max_scores[col]) * 5
            normalized_grades[col] = normalized_grades[col].clip(0, 5).round(1)

    # Показываем пример нормализации
    st.write("**Пример нормализации (первые 5 учеников):**")
    sample_df = pd.DataFrame({
        'Ученик': normalized_grades.index[:5],
        'Вопросы (оригинал)': [str(list(exam_grades_df.loc[idx, question_columns[:3]].values)) for idx in
                               normalized_grades.index[:5]],
        'Вопросы (нормализовано)': [str(list(normalized_grades.loc[idx, question_columns[:3]].values)) for idx in
                                    normalized_grades.index[:5]]
    })
    st.dataframe(sample_df, use_container_width=True)

    # Статистика после нормализации
    col1, col2 = st.columns(2)
    with col1:
        avg_before = exam_grades_df[question_columns].mean().mean()
        avg_after = normalized_grades[question_columns].mean().mean()
        st.metric("Средний балл (до нормализации)", f"{avg_before:.2f}")
        st.metric("Средний балл (после нормализации)", f"{avg_after:.2f}")

    return normalized_grades, max_scores


def configure_scoring_system():
    """Настройка общей системы оценивания экзамена"""
    st.subheader("⚙️ НАСТРОЙКА СИСТЕМЫ ОЦЕНИВАНИЯ")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Максимальный балл за экзамен**")
        total_max_score = st.number_input(
            "Максимальный балл",
            min_value=1,
            max_value=1000,
            value=100,
            step=5,
            help="Общая сумма баллов, которую можно получить за экзамен"
        )

    with col2:
        st.write("**Шкала перевода баллов в оценки**")
        st.info("Настройте пороговые значения в процентах от максимального балла")

        col2a, col2b = st.columns(2)
        with col2a:
            score_3_percent = st.number_input(
                "Минимальный % для оценки '3'",
                min_value=0,
                max_value=100,
                value=50,
                step=5,
                help="Процент от максимального балла для получения '3'"
            )
            score_4_percent = st.number_input(
                "Минимальный % для оценки '4'",
                min_value=0,
                max_value=100,
                value=70,
                step=5,
                help="Процент от максимального балла для получения '4'"
            )
        with col2b:
            score_5_percent = st.number_input(
                "Минимальный % для оценки '5'",
                min_value=0,
                max_value=100,
                value=85,
                step=5,
                help="Процент от максимального балла для получения '5'"
            )

    # Проверка корректности шкалы
    if score_3_percent >= score_4_percent or score_4_percent >= score_5_percent:
        st.error("❌ Ошибка: Пороги должны увеличиваться: 3 < 4 < 5")

    # Предварительный просмотр шкалы
    st.divider()
    st.write("**📊 Предварительный просмотр шкалы оценивания:**")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Оценка 2", f"0-{score_3_percent - 1}%")
    with col2:
        st.metric("Оценка 3", f"{score_3_percent}-{score_4_percent - 1}%")
    with col3:
        st.metric("Оценка 4", f"{score_4_percent}-{score_5_percent - 1}%")
    with col4:
        st.metric("Оценка 5", f"{score_5_percent}-100%")

    scoring_system = {
        'total_max_score': total_max_score,
        'score_3_percent': score_3_percent,
        'score_4_percent': score_4_percent,
        'score_5_percent': score_5_percent
    }

    return scoring_system


def calculate_grade(total_score, scoring_system):
    """Вычисление оценки на основе общей суммы баллов"""
    if pd.isna(total_score) or total_score == 0:
        return 2

    total_max = scoring_system['total_max_score']
    if total_max == 0:
        return 2

    score_percent = (total_score / total_max) * 100

    if score_percent >= scoring_system['score_5_percent']:
        return 5
    elif score_percent >= scoring_system['score_4_percent']:
        return 4
    elif score_percent >= scoring_system['score_3_percent']:
        return 3
    else:
        return 2


def calculate_percentage(total_score, scoring_system):
    """Вычисление процента от максимального балла"""
    if pd.isna(total_score):
        return 0
    return (total_score / scoring_system['total_max_score']) * 100


def convert_score_to_grade(score, scoring_system, max_score):
    """Преобразование балла в оценку по заданной шкале"""
    if pd.isna(score):
        return np.nan

    # Нормализуем к 100-балльной шкале, если максимальный балл отличается
    if max_score > 0 and max_score != 100:
        score_percent = (score / max_score) * 100
    else:
        score_percent = score

    # Определяем оценку
    if score_percent >= scoring_system['score_5']:
        return 5
    elif score_percent >= scoring_system['score_4']:
        return 4
    elif score_percent >= scoring_system['score_3']:
        return 3
    else:
        return 2


def apply_normalization_and_grading(numeric_grades, question_columns, max_scores, scoring_system):
    """Применение нормализации баллов и выставление оценок"""
    normalized_grades = numeric_grades.copy()

    # Нормализуем баллы по каждому вопросу
    for col in question_columns:
        if col in max_scores and max_scores[col] > 0:
            normalized_grades[col] = (numeric_grades[col] / max_scores[col]) * 100
            normalized_grades[col] = normalized_grades[col].round(1)

    # Вычисляем общий процент
    total_max = sum(max_scores.values())
    if total_max > 0:
        normalized_grades['Процент'] = (normalized_grades[question_columns].sum(axis=1) / total_max) * 100
        normalized_grades['Процент'] = normalized_grades['Процент'].round(1)

        # Выставляем оценку
        normalized_grades['Оценка'] = normalized_grades['Процент'].apply(
            lambda x: convert_score_to_grade(x, scoring_system, 100)
        )

    return normalized_grades


def display_exam_comprehensive_analysis(numeric_grades, detailed_stats, class_info, scoring_system=None):
    """Отображение расширенного комплексного анализа для экзаменов"""
    if numeric_grades is None or numeric_grades.empty or detailed_stats is None or detailed_stats.empty:
        st.warning("Недостаточно данных для анализа")
        return

    # Определяем колонки с вопросами
    question_cols = [c for c in numeric_grades.columns if c != 'Сумма баллов' and c != 'Процент' and c != 'Оценка']

    # ==================== ОСНОВНАЯ СТАТИСТИКА ====================
    st.header("📊 ОСНОВНАЯ СТАТИСТИКА")

    # Метрики в 4 колонках
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_score = detailed_stats['Средний балл'].mean() if not detailed_stats.empty else 0
        st.metric("📈 Средний балл", f"{avg_score:.2f}", delta=None)

        median_score = detailed_stats['Медиана'].mean() if not detailed_stats.empty else 0
        st.metric("📊 Медианный балл", f"{median_score:.2f}")

    with col2:
        max_score = detailed_stats['Максимум'].max() if not detailed_stats.empty else 0
        st.metric("🏆 Максимальный балл", f"{max_score:.0f}")

        min_score = detailed_stats['Минимум'].min() if not detailed_stats.empty else 0
        st.metric("⚠️ Минимальный балл", f"{min_score:.0f}")

    with col3:
        std_dev = detailed_stats['Станд. отклонение'].mean() if not detailed_stats.empty else 0
        st.metric("📊 Стандартное отклонение", f"{std_dev:.2f}")

        total_students = len(detailed_stats)
        st.metric("👥 Всего учеников", total_students)

    with col4:
        total_questions = len(question_cols)
        st.metric("📝 Всего заданий", total_questions)

        total_points = detailed_stats['Сумма баллов'].sum() if not detailed_stats.empty else 0
        st.metric("🎯 Общая сумма баллов", f"{total_points:.0f}")

    # Отображение шкалы оценивания, если она передана
    if scoring_system:
        with st.expander("📏 Шкала оценивания"):
            # Проверяем наличие всех необходимых ключей
            required_keys = ['score_3_percent', 'score_4_percent', 'score_5_percent']
            missing_keys = [k for k in required_keys if k not in scoring_system]

            if missing_keys:
                st.warning(f"Отсутствуют ключи в scoring_system: {missing_keys}")
                st.write("Доступные ключи:", list(scoring_system.keys()))
            else:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Оценка 2", f"0-{scoring_system['score_3_percent'] - 1}%")
                with col2:
                    st.metric("Оценка 3",
                              f"{scoring_system['score_3_percent']}-{scoring_system['score_4_percent'] - 1}%")
                with col3:
                    st.metric("Оценка 4",
                              f"{scoring_system['score_4_percent']}-{scoring_system['score_5_percent'] - 1}%")
                with col4:
                    st.metric("Оценка 5", f"≥ {scoring_system['score_5_percent']}%")

            # Распределение оценок - добавляем уникальный ключ
            if 'Оценка' in numeric_grades.columns:
                grade_counts = numeric_grades['Оценка'].value_counts().sort_index()
                fig = px.bar(
                    x=grade_counts.index,
                    y=grade_counts.values,
                    title="Распределение итоговых оценок",
                    labels={'x': 'Оценка', 'y': 'Количество учеников'},
                    color=grade_counts.index,
                    color_discrete_sequence=['#D32F2F', '#ED6C02', '#1976D2', '#2E7D32']
                )
                st.plotly_chart(fig, use_container_width=True, key="grade_distribution_chart")

    # ==================== РАСПРЕДЕЛЕНИЯ ====================
    st.header("📊 РАСПРЕДЕЛЕНИЯ")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Распределение баллов",
        "🏆 Рейтинги",
        "📊 Анализ заданий",
        "🔗 Корреляции",
        "🏫 По классам",
        "🎯 Индивидуальный анализ"
    ])

    # Вкладка "Распределение баллов" - добавьте ключи
    with tab1:
        st.subheader("Распределение средних баллов учеников")

        col1, col2 = st.columns(2)

        with col1:
            fig = px.histogram(
                detailed_stats, x='Средний балл', nbins=20,
                title='Гистограмма распределения средних баллов',
                color_discrete_sequence=['#636EFA'],
                labels={'Средний балл': 'Средний балл', 'count': 'Количество учеников'}
            )
            fig.add_vline(x=3.0, line_dash="dash", line_color="red", annotation_text="Порог 3.0")
            fig.add_vline(x=4.0, line_dash="dash", line_color="green", annotation_text="Порог 4.0")
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True, key="histogram_chart")

        with col2:
            fig = go.Figure()
            fig.add_trace(go.Box(
                y=detailed_stats['Средний балл'],
                name='Средние баллы',
                boxmean='sd',
                marker_color='#636EFA'
            ))
            fig.update_layout(title='Распределение средних баллов (Box Plot)', height=450)
            st.plotly_chart(fig, use_container_width=True, key="box_plot_chart")

        fig = go.Figure()
        fig.add_trace(go.Violin(
            y=detailed_stats['Средний балл'],
            box_visible=True,
            line_color='black',
            meanline_visible=True,
            fillcolor='lightseagreen',
            opacity=0.6,
            name='Распределение'
        ))
        fig.update_layout(title='Распределение средних баллов (Violin Plot)', height=400)
        st.plotly_chart(fig, use_container_width=True, key="violin_plot_chart")

        # Распределение по уровням
        st.subheader("Распределение по уровням успеваемости")

        levels = {
            'Отлично (≥4.5)': (detailed_stats['Средний балл'] >= 4.5).sum(),
            'Хорошо (4.0-4.49)': (
                        (detailed_stats['Средний балл'] >= 4.0) & (detailed_stats['Средний балл'] < 4.5)).sum(),
            'Удовлетворительно (3.0-3.99)': (
                        (detailed_stats['Средний балл'] >= 3.0) & (detailed_stats['Средний балл'] < 4.0)).sum(),
            'Неудовлетворительно (<3.0)': (detailed_stats['Средний балл'] < 3.0).sum()
        }

        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(
                values=list(levels.values()), names=list(levels.keys()),
                title='Распределение по уровням успеваемости',
                color_discrete_sequence=['#2E7D32', '#1976D2', '#ED6C02', '#D32F2F']
            )
            st.plotly_chart(fig, use_container_width=True, key="levels_pie_chart")

        # Violin plot
        fig = go.Figure()
        fig.add_trace(go.Violin(
            y=detailed_stats['Средний балл'],
            box_visible=True,
            line_color='black',
            meanline_visible=True,
            fillcolor='lightseagreen',
            opacity=0.6,
            name='Распределение'
        ))
        fig.update_layout(title='Распределение средних баллов (Violin Plot)', height=400)
        st.plotly_chart(fig, use_container_width=True)

        # Распределение по уровням
        st.subheader("Распределение по уровням успеваемости")

        levels = {
            'Отлично (≥4.5)': (detailed_stats['Средний балл'] >= 4.5).sum(),
            'Хорошо (4.0-4.49)': (
                        (detailed_stats['Средний балл'] >= 4.0) & (detailed_stats['Средний балл'] < 4.5)).sum(),
            'Удовлетворительно (3.0-3.99)': (
                        (detailed_stats['Средний балл'] >= 3.0) & (detailed_stats['Средний балл'] < 4.0)).sum(),
            'Неудовлетворительно (<3.0)': (detailed_stats['Средний балл'] < 3.0).sum()
        }

        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(
                values=list(levels.values()), names=list(levels.keys()),
                title='Распределение по уровням успеваемости',
                color_discrete_sequence=['#2E7D32', '#1976D2', '#ED6C02', '#D32F2F']
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Сводная таблица
            levels_df = pd.DataFrame(list(levels.items()), columns=['Уровень', 'Количество'])
            levels_df['Процент'] = (levels_df['Количество'] / total_students * 100).round(1)
            st.dataframe(levels_df, use_container_width=True, hide_index=True)

    with tab2:
        st.subheader("🏆 Рейтинги учеников")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Топ-10 лучших учеников**")
            top_10 = detailed_stats.nlargest(10, 'Средний балл')[
                ['ФИО', 'Класс', 'Средний балл', 'Сумма баллов', 'Кол-во заданий']
            ].round(2)
            st.dataframe(top_10, use_container_width=True)

            fig = px.bar(
                top_10, x='Средний балл', y='ФИО', orientation='h',
                title='Топ-10 лучших учеников',
                color='Средний балл',
                color_continuous_scale='Greens',
                text='Средний балл'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.write("**Топ-10 учеников с проблемами**")
            bottom_10 = detailed_stats.nsmallest(10, 'Средний балл')[
                ['ФИО', 'Класс', 'Средний балл', 'Сумма баллов', 'Кол-во заданий']
            ].round(2)
            st.dataframe(bottom_10, use_container_width=True)

            fig = px.bar(
                bottom_10, x='Средний балл', y='ФИО', orientation='h',
                title='Топ-10 учеников с проблемами',
                color='Средний балл',
                color_continuous_scale='Reds',
                text='Средний балл'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(yaxis={'categoryorder': 'total descending'}, height=400)
            st.plotly_chart(fig, use_container_width=True)

        # Радар сравнения лучших учеников
        if len(question_cols) >= 3:
            st.subheader("🕸️ Сравнение профилей лучших учеников")

            top_n_radar = st.slider("Количество учеников для сравнения", 3, 8, 5, key="exam_radar_n")
            top_students_radar = detailed_stats.nlargest(top_n_radar, 'Средний балл')['ФИО'].tolist()

            # Берем первые 6-8 вопросов для радара
            radar_questions = question_cols[:min(8, len(question_cols))]
            radar_labels = [f"{q}" for q in radar_questions]

            fig = go.Figure()
            for student in top_students_radar:
                if student in numeric_grades.index:
                    student_scores = numeric_grades.loc[student][radar_questions].values
                    fig.add_trace(go.Scatterpolar(
                        r=student_scores,
                        theta=radar_labels,
                        fill='toself',
                        name=student[:15] if len(student) > 15 else student
                    ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                title=f"Сравнение профилей топ-{top_n_radar} учеников",
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("📊 Анализ выполнения заданий")

        # Статистика по каждому заданию
        task_stats = pd.DataFrame({
            'Задание': question_cols,
            'Средний балл': numeric_grades[question_cols].mean().values,
            'Медиана': numeric_grades[question_cols].median().values,
            'Максимум': numeric_grades[question_cols].max().values,
            'Минимум': numeric_grades[question_cols].min().values,
            'Станд. отклонение': numeric_grades[question_cols].std().values,
            '% выполнения': (numeric_grades[question_cols] > 0).mean().values * 100,
            'Пропуски (%)': (numeric_grades[question_cols].isna().sum() / len(numeric_grades) * 100).values
        }).round(2)

        st.dataframe(task_stats, use_container_width=True)

        # Графики по заданиям
        col1, col2 = st.columns(2)

        with col1:
            # Самые легкие задания
            easiest = task_stats.nlargest(10, 'Средний балл')[['Задание', 'Средний балл', '% выполнения']]
            fig = px.bar(
                easiest, x='Задание', y='Средний балл',
                title='Топ-10 самых легких заданий',
                color='Средний балл',
                color_continuous_scale='Greens',
                text='Средний балл'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True, key="easiest_tasks_chart")

        with col2:
            # Самые сложные задания
            hardest = task_stats.nsmallest(10, 'Средний балл')[['Задание', 'Средний балл', '% выполнения']]
            fig = px.bar(
                hardest, x='Задание', y='Средний балл',
                title='Топ-10 самых сложных заданий',
                color='Средний балл',
                color_continuous_scale='Reds',
                text='Средний балл'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True, key="hardest_tasks_chart")

        with col2:
            # Самые сложные задания
            hardest = task_stats.nsmallest(10, 'Средний балл')[['Задание', 'Средний балл', '% выполнения']]
            fig = px.bar(
                hardest, x='Задание', y='Средний балл',
                title='Топ-10 самых сложных заданий',
                color='Средний балл',
                color_continuous_scale='Reds',
                text='Средний балл'
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)

        # Тепловая карта
        st.subheader("🌡️ Тепловая карта успеваемости по заданиям")

        # Берем топ-20 учеников
        students_avg = detailed_stats.nlargest(20, 'Средний балл')['ФИО'].tolist()
        heatmap_data = numeric_grades.loc[students_avg, question_cols[:20]] if len(question_cols) > 20 else \
        numeric_grades.loc[students_avg, question_cols]

        fig = px.imshow(
            heatmap_data,
            labels=dict(x="Задания", y="Ученики", color="Баллы"),
            title="Тепловая карта успеваемости (топ-20 учеников)",
            color_continuous_scale='RdYlGn',
            aspect="auto"
        )
        fig.update_layout(height=600)
        st.plotly_chart(fig, use_container_width=True)

        # Матрица корреляций заданий
        if len(question_cols) > 1:
            st.subheader("🔗 Матрица корреляций заданий")

            corr_data = numeric_grades[question_cols].dropna()
            if len(corr_data) > 5:
                corr_matrix = corr_data.corr()

                fig = px.imshow(
                    corr_matrix,
                    labels=dict(color="Корреляция"),
                    x=corr_matrix.columns,
                    y=corr_matrix.columns,
                    color_continuous_scale='RdBu_r',
                    zmin=-1, zmax=1,
                    title="Корреляционная матрица заданий"
                )
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("🔗 Корреляционный анализ")

        col1, col2 = st.columns(2)

        with col1:
            # Влияние пропусков на успеваемость
            fig = px.scatter(
                detailed_stats, x='% пропусков', y='Средний балл',
                size='Сумма баллов', color='Класс' if 'Класс' in detailed_stats.columns else None,
                hover_data=['ФИО'],
                title='Зависимость успеваемости от пропусков',
                labels={'% пропусков': 'Процент пропусков (%)', 'Средний балл': 'Средний балл'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Распределение по сумме баллов
            fig = px.histogram(
                detailed_stats, x='Сумма баллов', nbins=20,
                title='Распределение суммы баллов',
                color_discrete_sequence=['#FFA15A']
            )
            st.plotly_chart(fig, use_container_width=True)

        # Связь количества заданий и среднего балла
        fig = px.scatter(
            detailed_stats, x='Кол-во заданий', y='Средний балл',
            size='Сумма баллов', color='Класс' if 'Класс' in detailed_stats.columns else None,
            hover_data=['ФИО'],
            title='Влияние количества выполненных заданий на средний балл'
        )
        st.plotly_chart(fig, use_container_width=True)

    with tab5:
        st.subheader("🏫 Сравнение классов")

        if 'Класс' in detailed_stats.columns and len(detailed_stats['Класс'].unique()) > 1:
            # Статистика по классам
            class_summary = detailed_stats.groupby('Класс').agg({
                'Средний балл': ['mean', 'std', 'min', 'max'],
                'Сумма баллов': ['sum', 'mean'],
                'Кол-во заданий': 'mean',
                'ФИО': 'count'
            }).round(2)

            class_summary.columns = ['Ср. балл', 'Стд.откл', 'Мин', 'Макс',
                                     'Сумма баллов', 'Ср. сумма', 'Ср. заданий', 'Учеников']
            st.dataframe(class_summary, use_container_width=True)

            # Сравнение классов
            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(
                    class_summary.reset_index(), x='Класс', y='Ср. балл',
                    title='Средний балл по классам',
                    color='Класс',
                    text='Ср. балл'
                )
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    class_summary.reset_index(), x='Класс', y='Сумма баллов',
                    title='Общая сумма баллов по классам',
                    color='Класс',
                    text='Сумма баллов'
                )
                fig.update_traces(texttemplate='%{text:.0f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True, key="class_sum_chart")

            # Радар сравнения классов
            if len(detailed_stats['Класс'].unique()) <= 6:
                st.subheader("🕸️ Радар сравнения классов")

                classes = detailed_stats['Класс'].unique()
                metrics_for_radar = ['Средний балл', 'Сумма баллов', 'Кол-во заданий']
                metrics_for_radar = [m for m in metrics_for_radar if m in class_summary.columns]

                fig = go.Figure()
                for cls in classes:
                    class_data = class_summary.loc[cls]
                    values = []
                    for metric in metrics_for_radar:
                        if metric == 'Средний балл':
                            values.append(class_data['Ср. балл'] / 5 * 100)
                        elif metric == 'Сумма баллов':
                            values.append(class_data['Сумма баллов'] / class_summary['Сумма баллов'].max() * 100)
                        else:
                            values.append(class_data.get(metric, 0))

                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=metrics_for_radar,
                        fill='toself',
                        name=str(cls)
                    ))

                fig.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    title="Сравнение профилей классов",
                    height=500
                )
                st.plotly_chart(fig, use_container_width=True, key="radar_chart")
        else:
            st.info("Для сравнения классов необходимо указать колонку с классами")

    with tab6:
        st.subheader("🎯 Индивидуальный анализ учеников")

        # Поиск ученика
        search_term = st.text_input("🔍 Поиск ученика по фамилии", key="exam_search_main")

        students_list = sorted(detailed_stats['ФИО'].tolist())
        filtered_students = students_list
        if search_term:
            filtered_students = [s for s in students_list if search_term.lower() in s.lower()]

        st.write(f"Найдено учеников: {len(filtered_students)}")

        if len(filtered_students) > 0:
            selected_student = st.selectbox("Выберите ученика для анализа", options=filtered_students,
                                            key="exam_student_main")

            if selected_student:
                _display_exam_student_detail(selected_student, numeric_grades, detailed_stats, class_info)

    # ==================== ВЫГРУЗКА ДАННЫХ ====================
    st.header("💾 ВЫГРУЗКА ДАННЫХ")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Скачать основную статистику
        csv_stats = detailed_stats.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачать статистику учеников (CSV)",
            data=csv_stats,
            file_name=f"exam_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    with col2:
        # Скачать данные по заданиям
        task_data = numeric_grades[question_cols].copy()
        task_data['ФИО'] = numeric_grades.index
        task_data = task_data.reset_index(drop=True)
        csv_tasks = task_data.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачать данные по заданиям (CSV)",
            data=csv_tasks,
            file_name=f"exam_tasks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    with col3:
        # Скачать полный отчет
        full_report = pd.ExcelWriter(f'exam_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                                     engine='xlsxwriter')
        detailed_stats.to_excel(full_report, sheet_name='Статистика', index=False)
        task_data.to_excel(full_report, sheet_name='Данные по заданиям', index=False)

        # Сохраняем в BytesIO
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            detailed_stats.to_excel(writer, sheet_name='Статистика', index=False)
            task_data.to_excel(writer, sheet_name='Данные по заданиям', index=False)

        st.download_button(
            label="📊 Скачать полный отчет (Excel)",
            data=output.getvalue(),
            file_name=f"exam_full_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # ==================== ДЕТАЛЬНАЯ ТАБЛИЦА ====================
    # ==================== ДЕТАЛЬНАЯ ТАБЛИЦА ====================
    st.header("📋 ДЕТАЛЬНАЯ СТАТИСТИКА ПО УЧЕНИКАМ")

    # Выбор колонок для отображения
    display_columns = ['ФИО', 'Класс', 'Средний балл', 'Медиана', 'Максимум', 'Минимум',
                       'Сумма баллов', 'Кол-во заданий', '% пропусков', 'Станд. отклонение']
    existing_columns = [col for col in display_columns if col in detailed_stats.columns]

    # Отображение шкалы оценивания
    if scoring_system:
        with st.expander("📏 Шкала оценивания"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Оценка 2", f"0-{scoring_system['score_3_percent'] - 1}%")
            with col2:
                st.metric("Оценка 3", f"{scoring_system['score_3_percent']}-{scoring_system['score_4_percent'] - 1}%")
            with col3:
                st.metric("Оценка 4", f"{scoring_system['score_4_percent']}-{scoring_system['score_5_percent'] - 1}%")
            with col4:
                st.metric("Оценка 5", f"≥ {scoring_system['score_5_percent']}%")

            # Распределение оценок
            if 'Оценка' in numeric_grades.columns:
                grade_counts = numeric_grades['Оценка'].value_counts().sort_index()
                fig = px.bar(
                    x=grade_counts.index,
                    y=grade_counts.values,
                    title="Распределение итоговых оценок",
                    labels={'x': 'Оценка', 'y': 'Количество учеников'},
                    color=grade_counts.index,
                    color_discrete_sequence=['#D32F2F', '#ED6C02', '#1976D2', '#2E7D32']
                )
                st.plotly_chart(fig, use_container_width=True, key="final_grades_distribution")

    st.dataframe(detailed_stats[existing_columns], use_container_width=True)


def _display_exam_student_detail(student_name, numeric_grades, detailed_stats, class_info):
    """Отображение детальной информации об ученике для экзаменов"""

    # Получаем данные ученика
    student_stats = detailed_stats[detailed_stats['ФИО'] == student_name].iloc[0]

    # Получаем баллы
    if student_name in numeric_grades.index:
        student_grades = numeric_grades.loc[student_name].dropna()
    else:
        st.error(f"Данные по ученику '{student_name}' не найдены")
        return

    # Информационная карточка
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📈 Средний балл", f"{student_stats['Средний балл']:.2f}")
    with col2:
        st.metric("📊 Медиана", f"{student_stats['Медиана']:.2f}")
    with col3:
        st.metric("🎯 Сумма баллов", f"{student_stats['Сумма баллов']:.0f}")
    with col4:
        st.metric("📝 Заданий", student_stats['Кол-во заданий'])

    # График результатов по заданиям
    if len(student_grades) > 1:
        # Убираем колонку с суммой баллов, если она есть
        grades_for_plot = student_grades
        if 'Сумма баллов' in grades_for_plot.index:
            grades_for_plot = grades_for_plot.drop('Сумма баллов')

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=list(range(1, len(grades_for_plot) + 1)),
            y=grades_for_plot.values,
            marker_color='#636EFA',
            text=grades_for_plot.values,
            textposition='auto'
        ))

        # Добавляем линию среднего
        avg_grade = grades_for_plot.mean()
        fig.add_hline(y=avg_grade, line_dash="dash", line_color="red",
                      annotation_text=f"Среднее: {avg_grade:.2f}")

        fig.update_layout(
            title="Результаты по заданиям",
            xaxis_title="Номер задания",
            yaxis_title="Баллы",
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

    # Таблица с результатами
    st.subheader("📋 Результаты по заданиям")

    results_df = pd.DataFrame({
        'Задание': [f"Задание {i + 1}" for i in range(len(student_grades))],
        'Баллы': student_grades.values
    })
    st.dataframe(results_df, use_container_width=True, hide_index=True)

    # Рекомендации
    st.subheader("💡 Рекомендации")

    recommendations = []
    if student_stats['Средний балл'] < 3.0:
        recommendations.append("🔴 **Низкие результаты** - требуется дополнительная подготовка")
    elif student_stats['Средний балл'] < 4.0:
        recommendations.append("🟡 **Средний уровень** - есть потенциал для улучшения")
    else:
        recommendations.append("🌟 **Высокий уровень** - хорошо справились с экзаменом")

    if student_stats['% пропусков'] > 20:
        recommendations.append(
            f"📅 **Пропущено заданий: {student_stats['% пропусков']:.0f}%** - обратите внимание на заполнение")

    # Находим сложные задания
    if len(student_grades) > 0:
        low_scores = student_grades[student_grades < student_grades.mean() * 0.7]
        if len(low_scores) > 0:
            recommendations.append(f"⚠️ **Сложные задания:** {len(low_scores)} заданий выполнены ниже среднего уровня")

    if not recommendations:
        recommendations.append("✅ Хорошие результаты")

    for rec in recommendations:
        if rec.startswith("🔴"):
            st.error(rec)
        elif rec.startswith("🟡"):
            st.warning(rec)
        elif rec.startswith("🌟"):
            st.success(rec)
        else:
            st.info(rec)
# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_exam_detailed_statistics(grades_df, class_info=None):
    """Получение детальной статистики для экзаменационных баллов"""
    try:
        if grades_df is None or grades_df.empty:
            return pd.DataFrame()

        stats = []

        # Определяем колонки с вопросами (исключаем Сумма баллов)
        question_cols = [c for c in grades_df.columns if c != 'Сумма баллов']

        if not question_cols:
            st.warning("Нет колонок с вопросами для анализа")
            return pd.DataFrame()

        # Убедимся, что все колонки числовые
        for col in question_cols:
            if grades_df[col].dtype == 'object':
                grades_df[col] = pd.to_numeric(grades_df[col], errors='coerce')

        for student in grades_df.index:
            if pd.isna(student) or str(student).strip() == '':
                continue

            try:
                # Получаем баллы ученика
                student_scores = grades_df.loc[student][question_cols]

                # Фильтруем некорректные значения (баллы > 100 или < 0)
                valid_scores = student_scores[
                    (student_scores.apply(lambda x: isinstance(x, (int, float)) and 0 <= x <= 100))
                ]

                # Получаем класс ученика
                student_class = "Не распределен"
                if class_info and isinstance(class_info, dict):
                    student_class = class_info.get(student, "Не распределен")

                # Находим сумму баллов
                total_score = grades_df.loc[student].get('Сумма баллов', None)
                if total_score is None or pd.isna(total_score):
                    total_score = valid_scores.sum() if len(valid_scores) > 0 else 0

                if len(valid_scores) > 0:
                    # Вычисляем статистику
                    mean_val = valid_scores.mean()
                    median_val = valid_scores.median()
                    max_val = valid_scores.max()
                    min_val = valid_scores.min()
                    std_val = valid_scores.std() if len(valid_scores) > 1 else 0

                    stats.append({
                        'ФИО': str(student),
                        'Класс': str(student_class),
                        'Средний балл': round(float(mean_val), 2),
                        'Медиана': round(float(median_val), 2),
                        'Максимум': int(max_val),
                        'Минимум': int(min_val),
                        'Станд. отклонение': round(float(std_val), 2),
                        'Кол-во заданий': int(len(valid_scores)),
                        'Пропуски': int(student_scores.isna().sum()),
                        '% пропусков': round(float((student_scores.isna().sum() / len(question_cols)) * 100), 1),
                        'Сумма баллов': float(total_score),
                    })
                else:
                    # Если все баллы некорректны
                    stats.append({
                        'ФИО': str(student),
                        'Класс': str(student_class),
                        'Средний балл': 0,
                        'Медиана': 0,
                        'Максимум': 0,
                        'Минимум': 0,
                        'Станд. отклонение': 0,
                        'Кол-во заданий': 0,
                        'Пропуски': int(student_scores.isna().sum()),
                        '% пропусков': round(float((student_scores.isna().sum() / len(question_cols)) * 100), 1),
                        'Сумма баллов': float(total_score),
                    })

            except Exception as e:
                st.warning(f"Ошибка при обработке ученика {student}: {e}")
                continue

        if stats:
            result_df = pd.DataFrame(stats)
            # Удаляем пустых учеников (с нулевыми баллами и нулевыми заданиями)
            result_df = result_df[~(result_df['Сумма баллов'] == 0)]
            return result_df
        return pd.DataFrame()

    except Exception as e:
        st.error(f"Ошибка при получении статистики: {e}")
        import traceback
        st.code(traceback.format_exc())
        return pd.DataFrame()


def clean_exam_data(numeric_grades, max_reasonable_score=100):
    """Очистка экзаменационных данных от выбросов и некорректных значений"""
    cleaned_df = numeric_grades.copy()

    # Обрабатываем каждую колонку
    for col in cleaned_df.columns:
        if col == 'Сумма баллов':
            continue

        # Заменяем значения > max_reasonable_score на 0
        cleaned_df[col] = cleaned_df[col].apply(
            lambda x: x if (pd.isna(x) or 0 <= x <= max_reasonable_score) else 0
        )

        # Заменяем отрицательные значения на 0
        cleaned_df[col] = cleaned_df[col].apply(
            lambda x: x if (pd.isna(x) or x >= 0) else 0
        )

        # Заменяем NaN на 0
        cleaned_df[col] = cleaned_df[col].fillna(0)

    return cleaned_df

def parse_exam_grades(df, grade_columns=None):
    """Специальная функция для анализа экзаменационных работ с баллами"""
    grades_df = df.copy()

    # Преобразуем все колонки в числовой формат
    for col in grades_df.columns:
        grades_df[col] = pd.to_numeric(grades_df[col], errors='coerce')

    if grade_columns is None:
        grade_columns = []
        # Поиск колонок с баллами
        for col in grades_df.columns:
            all_vals = grades_df[col].dropna()
            if len(all_vals) == 0:
                continue

            # Проверяем, что колонка содержит числовые значения
            numeric_count = 0
            for val in all_vals.head(20):
                try:
                    num_val = float(val)
                    # Баллы могут быть от 0 до 100 (или больше)
                    if 0 <= num_val <= 100:
                        numeric_count += 1
                except:
                    pass

            # Если больше 50% значений - числовые баллы
            if len(all_vals.head(20)) > 0 and numeric_count / len(all_vals.head(20)) > 0.5:
                grade_columns.append(col)

    if not grade_columns:
        st.warning("⚠️ Не удалось найти колонки с баллами")
        return pd.DataFrame(), []

    # Выбираем только нужные колонки
    numeric_grades = grades_df[grade_columns].copy()

    # Заменяем NaN на 0 для корректного подсчета
    numeric_grades = numeric_grades.fillna(0)

    return numeric_grades, grade_columns

def find_total_score_column(df):
    """Поиск колонки с суммой баллов (обычно последняя или с названием 'сумма', 'итого', 'total')"""
    total_keywords = ['сумма', 'итого', 'total', 'балл', 'score', 'всего']

    # Проверяем названия колонок
    for col in df.columns:
        col_lower = str(col).lower()
        if any(keyword in col_lower for keyword in total_keywords):
            return col

    # Если не нашли по названию, берем последнюю числовую колонку
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) > 0:
        return numeric_cols[-1]

    return None

def is_numeric_column(series, threshold=0.8):
    """Проверяет, является ли колонка числовой (номера учеников)"""
    try:
        numeric_vals = pd.to_numeric(series, errors='coerce')
        if numeric_vals.notna().sum() / len(series) > threshold:
            if numeric_vals.dropna().apply(float.is_integer).all():
                return True
    except:
        pass
    return False


def identify_non_grade_columns(df):
    """Определяет колонки, которые точно не содержат оценки"""
    non_grade_columns = []
    for col in df.columns:
        col_lower = str(col).lower()
        if any(word in col_lower for word in ['№', 'номер', 'id', 'п/п', '№ п/п', 'индекс']):
            non_grade_columns.append(col)
            continue
        sample = df[col].dropna().head(20)
        if len(sample) > 0:
            if all(_is_number(str(x)) for x in sample):
                numeric_vals = pd.to_numeric(sample, errors='coerce')
                if not any(2 <= x <= 5 for x in numeric_vals if not pd.isna(x)):
                    non_grade_columns.append(col)
    return non_grade_columns


def get_columns_to_the_right(df, name_column):
    """Возвращает список колонок, которые находятся правее указанной колонки"""
    try:
        col_position = df.columns.get_loc(name_column)
        columns_to_the_right = list(df.columns[col_position + 1:])
        return columns_to_the_right
    except Exception as e:
        st.warning(f"Ошибка при определении колонок правее: {e}")
        return list(df.columns)


def extract_header_names(df):
    """Извлечение названий колонок из первой непустой строки и удаление служебных строк"""

    # Ищем строку с заголовками (содержит 'ФИО', 'Класс', '№', 'studentid' и т.д.)
    header_keywords = ['фио', 'фамилия', 'имя', 'класс', '№', 'номер', 'studentid', 'student id', 'вариант']
    header_row_idx = None

    for i in range(min(len(df), 30)):  # Проверяем первые 30 строк
        row = df.iloc[i]
        # Проверяем, содержит ли строка ключевые слова
        has_keywords = False
        keyword_count = 0
        for cell in row:
            if pd.notna(cell):
                cell_str = str(cell).strip().lower()
                for keyword in header_keywords:
                    if keyword in cell_str:
                        keyword_count += 1
                        if keyword_count >= 2:  # Нашли хотя бы 2 ключевых слова
                            has_keywords = True
                            break
            if has_keywords:
                break
        if has_keywords:
            header_row_idx = i
            break

    # Если не нашли по ключевым словам, ищем строку с нечисловыми значениями
    if header_row_idx is None:
        for i in range(min(len(df), 20)):
            row = df.iloc[i]
            # Проверяем, что строка содержит хотя бы одно слово (не цифры)
            has_words = False
            word_count = 0
            for cell in row:
                if pd.notna(cell):
                    cell_str = str(cell).strip()
                    if not cell_str.replace('.', '').replace(',', '').replace('-', '').isdigit():
                        if len(cell_str) > 1 and any(c.isalpha() for c in cell_str):
                            word_count += 1
                            if word_count >= 2:
                                has_words = True
                                break
            if has_words:
                header_row_idx = i
                break

    if header_row_idx is not None:
        st.write(f"Найдена строка с заголовками на позиции: {header_row_idx + 1}")  # Отладка

        # Используем найденную строку как заголовки
        new_columns = []
        for cell in df.iloc[header_row_idx]:
            if pd.isna(cell) or str(cell).strip() == '':
                new_columns.append(f"Колонка_{len(new_columns) + 1}")
            else:
                col_name = str(cell).strip()
                # Заменяем длинные названия
                if 'studentid' in col_name.lower():
                    col_name = 'studentid'
                elif 'фио' in col_name.lower() or 'фамилия' in col_name.lower() or 'имя' in col_name.lower():
                    col_name = 'ФИО'
                elif 'класс' in col_name.lower():
                    col_name = 'Класс'
                elif 'вариант' in col_name.lower():
                    col_name = 'Вариант'
                new_columns.append(col_name)

        # Обрезаем DataFrame, начиная со следующей строки после заголовка
        df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
        df.columns = new_columns

        # Удаляем строки, которые являются служебными (итоги, средние и т.д.)
        df = remove_service_rows(df)

    return df


def remove_service_rows(df):
    """Удаление служебных строк (итоги, средние, пустые строки)"""
    service_keywords = [
        'итого', 'всего', 'средний', 'ср.', 'общий', 'сумма', 'итог',
        'total', 'average', 'sum', 'mean', 'класс', 'параллель', 'школа',
        'учитель', 'преподаватель', 'директор', 'завуч'
    ]

    rows_to_keep = []
    for idx, row in df.iterrows():
        is_service_row = False

        # Проверяем каждую ячейку в строке
        for cell in row:
            if pd.notna(cell):
                cell_str = str(cell).strip().lower()
                # Проверка на служебные ключевые слова
                for keyword in service_keywords:
                    if keyword in cell_str:
                        is_service_row = True
                        break
                # Проверка на строки, где все ячейки - пустые или NaN
                if cell_str == '' or cell_str == 'nan':
                    continue

        # Если строка не служебная, оставляем
        if not is_service_row and not all(pd.isna(row)):
            rows_to_keep.append(idx)

    return df.iloc[rows_to_keep].reset_index(drop=True)


def clean_student_name(name):
    """Очистка ФИО от служебной информации"""
    if pd.isna(name):
        return None

    name_str = str(name).strip()

    # Список служебных фраз для исключения
    exclude_phrases = [
        r'^класс\s*\d', r'^классы?$', r'^итого', r'^всего',
        r'^средний', r'^ср\.?', r'^общий', r'^сумма', r'^итог',
        r'^\d+$', r'^ученик', r'^студент', r'^группа',
        r'^параллель', r'^школа', r'^классный руководитель',
        r'^фио', r'^ф\.и\.о\.', r'^фамилия', r'^имя',
        r'^протокол', r'^тестирование', r'^предмет', r'^дата',
        r'^№', r'^номер', r'^id', r'^studentid'
    ]

    # Проверяем на служебную информацию
    name_lower = name_str.lower()
    for pattern in exclude_phrases:
        if re.search(pattern, name_lower):
            return None

    # Проверяем, что строка содержит буквы
    if not any(c.isalpha() for c in name_str):
        return None

    # Проверяем, что это не просто номер
    if name_str.replace('.', '').replace(',', '').replace('-', '').replace(' ', '').isdigit():
        return None

    # Проверяем, что есть хотя бы одна буква русского или английского алфавита
    if not any(c.isalpha() for c in name_str):
        return None

    return name_str


def extract_class_info(name):
    """Извлечение информации о классе из ФИО или отдельной колонки"""
    class_patterns = [
        r'(\d+)[\s\-]*[а-яА-Я]?[\s\-]*класс',
        r'(\d+)[\s\-]*клас',
        r'класс[\s\-]*(\d+)',
    ]
    name_str = str(name)
    for pattern in class_patterns:
        match = re.search(pattern, name_str, re.IGNORECASE)
        if match:
            return match.group(1) + " класс"
    return "Не распределен"


def merge_duplicate_students(df, name_column):
    """Объединение данных по дублирующимся ученикам"""
    if name_column not in df.columns:
        return df
    grouped = df.groupby(name_column).agg({
        col: lambda x: pd.Series(x).fillna(method='ffill').iloc[-1] if col != name_column else x.iloc[0]
        for col in df.columns if col != name_column
    })
    return grouped.reset_index()


def load_file(uploaded_file):
    """Загрузка файла с определением формата и удалением служебных строк"""
    try:
        file_name = uploaded_file.name
        st.write(f"Загрузка файла: {file_name}")  # Отладка

        if file_name.endswith('.csv'):
            # Пробуем разные кодировки
            for encoding in ['utf-8', 'cp1251', 'latin1', 'iso-8859-1']:
                try:
                    df = pd.read_csv(uploaded_file, encoding=encoding, skipinitialspace=True, header=None)
                    break
                except:
                    continue
            else:
                df = pd.read_csv(uploaded_file, encoding='utf-8', skipinitialspace=True, header=None, errors='ignore')
        elif file_name.endswith('.xlsx'):
            # Для .xlsx используем openpyxl
            df = pd.read_excel(uploaded_file, engine='openpyxl', header=None)
        elif file_name.endswith('.xls'):
            # Для .xls пробуем разные способы
            try:
                # Сначала пробуем xlrd
                df = pd.read_excel(uploaded_file, engine='xlrd', header=None)
            except Exception as e1:
                st.warning(f"Ошибка с xlrd: {e1}")
                try:
                    # Пробуем openpyxl с конвертацией
                    import tempfile
                    import os
                    # Сохраняем временный файл
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name

                    # Читаем через openpyxl
                    df = pd.read_excel(tmp_path, engine='openpyxl', header=None)
                    os.unlink(tmp_path)
                except Exception as e2:
                    st.error(f"Не удалось прочитать .xls файл: {e2}")
                    return None
        else:
            st.error(f"Неподдерживаемый формат файла: {file_name}")
            return None

        # Обработка пустых первых строк и удаление служебных строк
        df = extract_header_names(df)

        # Дополнительная очистка
        df = df.dropna(how='all')  # Удаляем полностью пустые строки
        df = df.dropna(axis=1, how='all')  # Удаляем полностью пустые колонки

        st.write(f"После очистки: {len(df)} строк, {len(df.columns)} колонок")  # Отладка

        return df
    except Exception as e:
        st.error(f"Ошибка при загрузке файла: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

def convert_grade_to_number(grade):
    """Преобразование оценки в число"""
    if pd.isna(grade):
        return np.nan
    grade_str = str(grade).strip().lower()
    if grade_str in ['н', 'н/а', 'отсутствовал', '-']:
        return np.nan
    try:
        return float(grade_str)
    except:
        return np.nan


def convert_grade_to_number_safe(grade):
    """Безопасное преобразование оценки в число"""
    if pd.isna(grade):
        return np.nan
    grade_str = str(grade).strip().lower()
    if grade_str in ['н', 'н/а', 'отсутствовал', '-', '']:
        return np.nan
    try:
        grade_float = float(grade_str)
        if 2 <= grade_float <= 5:
            return grade_float
        else:
            return np.nan
    except ValueError:
        return np.nan


def display_individual_analysis_modal(data_type, numeric_grades, detailed_stats, class_info):
    """Индивидуальный анализ с выбором ученика"""

    # Проверка наличия данных
    if numeric_grades is None or numeric_grades.empty:
        st.warning("Нет данных об оценках")
        return

    if detailed_stats is None or detailed_stats.empty:
        st.warning("Нет статистических данных")
        return

    # Получаем список учеников
    if 'ФИО' in detailed_stats.columns:
        students_list = sorted(detailed_stats['ФИО'].tolist())
    else:
        students_list = sorted(list(numeric_grades.index))

    if not students_list:
        st.info("Нет данных об учениках")
        return

    # Поиск и выбор ученика
    search_term = st.text_input("🔍 Поиск ученика по фамилии", key=f"{data_type}_search_modal")

    # Фильтруем учеников
    filtered_students = students_list
    if search_term:
        filtered_students = [s for s in students_list if search_term.lower() in s.lower()]

    st.write(f"Найдено учеников: {len(filtered_students)}")

    # Если учеников много, используем selectbox
    if len(filtered_students) > 15:
        selected_student = st.selectbox(
            "Выберите ученика для анализа",
            options=[''] + filtered_students,
            format_func=lambda x: x if x else "⬇️ Выберите ученика...",
            key=f"{data_type}_student_select_modal"
        )

        if selected_student:
            _display_student_detail(selected_student, numeric_grades, detailed_stats, class_info)
        else:
            # Показываем статистику класса
            st.info("👆 Выберите ученика из списка выше для детального анализа")
            col1, col2, col3 = st.columns(3)
            with col1:
                avg_grade = detailed_stats['Средний балл'].mean() if 'Средний балл' in detailed_stats.columns else 0
                st.metric("📈 Средний балл по классу", f"{avg_grade:.2f}")
            with col2:
                if 'Качество знаний (%)' in detailed_stats.columns:
                    quality = detailed_stats['Качество знаний (%)'].mean()
                    st.metric("⭐ Качество знаний", f"{quality:.1f}%")
                else:
                    st.metric("⭐ Медиана", f"{detailed_stats['Медиана'].mean():.2f}")
            with col3:
                st.metric("👥 Всего учеников", len(detailed_stats))
    else:
        # Создаем вкладки для каждого ученика
        max_tabs = min(len(filtered_students), 30)

        if max_tabs > 0:
            tab_names = []
            for student in filtered_students[:max_tabs]:
                short_name = student[:15] + "..." if len(student) > 15 else student
                tab_names.append(short_name)

            tabs = st.tabs(tab_names)

            for i, student in enumerate(filtered_students[:max_tabs]):
                with tabs[i]:
                    _display_student_detail(student, numeric_grades, detailed_stats, class_info)

            if len(filtered_students) > max_tabs:
                st.warning(f"Показаны первые {max_tabs} учеников из {len(filtered_students)}")

def _display_student_detail_card(student_name, numeric_grades, detailed_stats, class_info, data_type):
    """Отображение карточки ученика с детальным анализом"""

    # Получаем данные
    if 'ФИО' in detailed_stats.columns:
        student_stats = detailed_stats[detailed_stats['ФИО'] == student_name].iloc[0] if not detailed_stats[
            detailed_stats['ФИО'] == student_name].empty else None
    else:
        student_stats = detailed_stats[detailed_stats.index == student_name].iloc[0] if not detailed_stats[
            detailed_stats.index == student_name].empty else None

    # Получаем оценки
    if student_name in numeric_grades.index:
        student_grades = numeric_grades.loc[student_name].dropna()
    else:
        found = False
        for name in numeric_grades.index:
            if student_name.lower() in str(name).lower():
                student_grades = numeric_grades.loc[name].dropna()
                student_name = name
                found = True
                break
        if not found:
            st.error(f"Данные по ученику '{student_name}' не найдены")
            return

    # Основные метрики
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_grade = student_stats['Средний балл'] if student_stats is not None else (
            student_grades.mean() if len(student_grades) > 0 else 0)
        st.metric("📈 Средний балл", f"{avg_grade:.2f}")
    with col2:
        if data_type == "attendance":
            quality = student_stats['Качество знаний (%)'] if student_stats is not None else 0
            st.metric("⭐ Качество знаний", f"{quality:.1f}%" if quality > 0 else "Н/Д")
        else:
            total_score = student_stats['Сумма баллов'] if student_stats is not None else student_grades.sum()
            st.metric("🎯 Сумма баллов", f"{total_score:.0f}")
    with col3:
        if data_type == "attendance":
            success = student_stats['Успеваемость (%)'] if student_stats is not None else 0
            st.metric("✅ Успеваемость", f"{success:.1f}%" if success > 0 else "Н/Д")
        else:
            max_score = student_stats['Максимум'] if student_stats is not None else student_grades.max()
            st.metric("🏆 Максимум", f"{max_score:.0f}")
    with col4:
        st.metric("📝 Количество", len(student_grades))

    # Создаем вкладки
    if data_type == "attendance":
        tabs = st.tabs(["📈 Динамика", "📊 Распределение", "📋 Оценки", "💡 Рекомендации"])
    else:
        tabs = st.tabs(["📊 Результаты", "📋 Задания", "📈 Сравнение", "💡 Рекомендации"])

    with tabs[0]:
        if data_type == "attendance":
            if len(student_grades) > 1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(student_grades) + 1)),
                    y=student_grades.values,
                    mode='lines+markers',
                    name='Оценки',
                    line=dict(color='blue', width=3),
                    marker=dict(size=10)
                ))
                avg_grade_val = student_grades.mean()
                fig.add_hline(y=avg_grade_val, line_dash="dash", line_color="green",
                              annotation_text=f"Среднее: {avg_grade_val:.2f}")
                fig.update_layout(title="Динамика оценок", xaxis_title="Номер работы",
                                  yaxis_title="Оценка", yaxis=dict(range=[1.5, 5.5]), height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"Недостаточно оценок для анализа динамики")
        else:
            # Для экзаменов - график результатов
            grades_for_plot = student_grades
            if 'Сумма баллов' in grades_for_plot.index:
                grades_for_plot = grades_for_plot.drop('Сумма баллов')

            if len(grades_for_plot) > 0:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=[f"Вопрос {i + 1}" for i in range(len(grades_for_plot))],
                    y=grades_for_plot.values,
                    marker_color='#636EFA',
                    text=grades_for_plot.values,
                    textposition='auto'
                ))
                avg_grade_val = grades_for_plot.mean()
                fig.add_hline(y=avg_grade_val, line_dash="dash", line_color="red",
                              annotation_text=f"Среднее: {avg_grade_val:.2f}")
                fig.update_layout(title="Результаты по вопросам", xaxis_title="Вопросы",
                                  yaxis_title="Баллы", height=400)
                st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        if data_type == "attendance":
            if len(student_grades) > 0:
                col1, col2 = st.columns(2)
                with col1:
                    fig = px.histogram(x=student_grades.values, nbins=4, title="Распределение оценок",
                                       labels={'x': 'Оценка', 'y': 'Количество'})
                    fig.update_layout(xaxis=dict(tickmode='linear', tick0=2, dtick=1))
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    grade_counts = student_grades.value_counts().sort_index()
                    fig = px.pie(values=grade_counts.values, names=grade_counts.index, title="Соотношение")
                    st.plotly_chart(fig, use_container_width=True)
        else:
            # Для экзаменов - таблица результатов по вопросам
            grades_df = pd.DataFrame({
                'Вопрос': [f"Вопрос {i + 1}" for i in range(len(student_grades))],
                'Баллы': student_grades.values
            })
            st.dataframe(grades_df, use_container_width=True, hide_index=True)

    with tabs[2]:
        if data_type == "attendance":
            grades_df = pd.DataFrame({
                '№': range(1, len(student_grades) + 1),
                'Оценка': student_grades.values,
                'Предмет/Задание': student_grades.index
            })
            st.dataframe(grades_df, use_container_width=True, hide_index=True)
        else:
            # Сравнение со средним по классу
            if student_stats is not None and 'Средний балл' in student_stats:
                class_avg = detailed_stats['Средний балл'].mean()
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=['Ученик', 'Средний по классу'],
                    y=[student_stats['Средний балл'], class_avg],
                    marker_color=['#2E7D32', '#1976D2'],
                    text=[f"{student_stats['Средний балл']:.2f}", f"{class_avg:.2f}"],
                    textposition='auto'
                ))
                fig.update_layout(title="Сравнение со средним баллом по классу", height=400)
                st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        if student_stats is not None:
            recommendations = []

            if data_type == "attendance":
                if student_stats['Средний балл'] < 3.0:
                    recommendations.append("🔴 **Критически низкая успеваемость** - требуется срочная помощь")
                elif student_stats['Средний балл'] < 3.5:
                    recommendations.append("🟡 **Ниже среднего** - есть потенциал для улучшения")
                elif student_stats['Средний балл'] < 4.0:
                    recommendations.append("🟢 **Хороший уровень** - можно стремиться к отлично")
                else:
                    recommendations.append("🌟 **Отличный результат** - так держать!")

                if student_stats['% пропусков'] > 30:
                    recommendations.append(f"📅 **Много пропусков ({student_stats['% пропусков']:.1f}%)**")
                elif student_stats['% пропусков'] > 15:
                    recommendations.append(f"📅 **Пропуски выше нормы ({student_stats['% пропусков']:.1f}%)**")
            else:
                if student_stats['Средний балл'] < 3.0:
                    recommendations.append("🔴 **Низкие результаты** - требуется дополнительная подготовка")
                elif student_stats['Средний балл'] < 4.0:
                    recommendations.append("🟡 **Средний уровень** - есть потенциал для улучшения")
                else:
                    recommendations.append("🌟 **Высокий уровень** - хорошо справились с экзаменом")

                if student_stats['% пропусков'] > 20:
                    recommendations.append(f"📅 **Пропущено заданий: {student_stats['% пропусков']:.0f}%**")

            if len(student_grades) < 5:
                recommendations.append("📝 **Мало данных** - нужно накопить больше информации")

            if not recommendations:
                recommendations.append("✅ Стабильные результаты")

            for rec in recommendations:
                if rec.startswith("🔴"):
                    st.error(rec)
                elif rec.startswith("🟡"):
                    st.warning(rec)
                elif rec.startswith("🌟"):
                    st.success(rec)
                else:
                    st.info(rec)


def _display_student_detail(student_name, numeric_grades, detailed_stats, class_info):
    """Отображение детальной информации об ученике"""
    try:
        # Получаем данные ученика
        if detailed_stats is None or detailed_stats.empty:
            st.error("Нет статистических данных")
            return

        # Ищем ученика в статистике
        if 'ФИО' in detailed_stats.columns:
            student_data = detailed_stats[detailed_stats['ФИО'] == student_name]
            if student_data.empty:
                # Пробуем найти по части имени
                for name in detailed_stats['ФИО'].tolist():
                    if student_name.lower() in name.lower() or name.lower() in student_name.lower():
                        student_name = name
                        student_data = detailed_stats[detailed_stats['ФИО'] == student_name]
                        st.info(f"Найден похожий ученик: {student_name}")
                        break
            if student_data.empty:
                st.error(f"Ученик '{student_name}' не найден в статистике")
                return
            student_stats = student_data.iloc[0]
        else:
            st.error("В статистике нет колонки 'ФИО'")
            return

        # Получаем оценки
        if student_name in numeric_grades.index:
            student_grades = numeric_grades.loc[student_name].dropna()
        else:
            # Поиск по части имени
            found = False
            for name in numeric_grades.index:
                if student_name.lower() in str(name).lower() or str(name).lower() in student_name.lower():
                    student_grades = numeric_grades.loc[name].dropna()
                    student_name = name
                    found = True
                    st.info(f"Найден похожий ученик: {student_name}")
                    break
            if not found:
                st.error(f"Данные по ученику '{student_name}' не найдены")
                return

        # Информационная карточка
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            avg_grade = student_stats.get('Средний балл', student_grades.mean() if len(student_grades) > 0 else 0)
            st.metric("📈 Средний балл", f"{avg_grade:.2f}")
        with col2:
            if 'Качество знаний (%)' in student_stats.index:
                quality = student_stats['Качество знаний (%)']
                st.metric("⭐ Качество знаний", f"{quality:.1f}%")
            elif 'Сумма баллов' in student_grades.index:
                total = student_grades['Сумма баллов']
                st.metric("🎯 Сумма баллов", f"{total:.0f}")
            else:
                st.metric("⭐ Медиана", f"{student_grades.median():.2f}")
        with col3:
            if 'Успеваемость (%)' in student_stats.index:
                success = student_stats['Успеваемость (%)']
                st.metric("✅ Успеваемость", f"{success:.1f}%")
            else:
                st.metric("📊 Максимум", f"{student_grades.max():.0f}")
        with col4:
            st.metric("📝 Количество", len(student_grades))

        # Создаем вкладки
        tab1, tab2, tab3, tab4 = st.tabs(["📈 Динамика", "📊 Распределение", "📋 Подробно", "💡 Рекомендации"])

        with tab1:
            if len(student_grades) > 1:
                grades_for_plot = student_grades
                if 'Сумма баллов' in grades_for_plot.index:
                    grades_for_plot = grades_for_plot.drop('Сумма баллов')

                if len(grades_for_plot) > 1:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=list(range(1, len(grades_for_plot) + 1)),
                        y=grades_for_plot.values,
                        mode='lines+markers',
                        name='Результаты',
                        line=dict(color='blue', width=3),
                        marker=dict(size=10)
                    ))
                    avg_val = grades_for_plot.mean()
                    fig.add_hline(y=avg_val, line_dash="dash", line_color="green",
                                  annotation_text=f"Среднее: {avg_val:.2f}")

                    fig.update_layout(title="Динамика результатов",
                                      xaxis_title="Номер задания/работы",
                                      yaxis_title="Баллы/Оценка",
                                      height=400)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Недостаточно данных для анализа динамики")
            else:
                st.warning(f"Недостаточно данных для анализа динамики (есть {len(student_grades)})")

        with tab2:
            if len(student_grades) > 0:
                grades_for_dist = student_grades
                if 'Сумма баллов' in grades_for_dist.index:
                    grades_for_dist = grades_for_dist.drop('Сумма баллов')

                if len(grades_for_dist) > 0:
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = px.histogram(x=grades_for_dist.values, nbins=10,
                                           title="Распределение",
                                           labels={'x': 'Баллы/Оценка', 'y': 'Количество'})
                        st.plotly_chart(fig, use_container_width=True)
                    with col2:
                        fig = px.box(y=grades_for_dist.values, title="Ящик с усами")
                        st.plotly_chart(fig, use_container_width=True)

        with tab3:
            grades_df = pd.DataFrame({
                '№': range(1, len(student_grades) + 1),
                'Значение': student_grades.values,
                'Задание/Предмет': student_grades.index
            })
            st.dataframe(grades_df, use_container_width=True, hide_index=True)

        with tab4:
            recommendations = []

            avg_grade_val = student_stats.get('Средний балл', student_grades.mean())
            if avg_grade_val < 2.5:
                recommendations.append("🔴 **Критически низкие результаты** - требуется срочная помощь")
            elif avg_grade_val < 3.0:
                recommendations.append("🟡 **Ниже среднего** - есть потенциал для улучшения")
            elif avg_grade_val < 3.5:
                recommendations.append("🟢 **Средний уровень** - рекомендуется больше практики")
            elif avg_grade_val < 4.0:
                recommendations.append("📘 **Хороший уровень** - можно стремиться к отлично")
            else:
                recommendations.append("🌟 **Отличный результат** - так держать!")

            if '% пропусков' in student_stats.index:
                absent_pct = student_stats['% пропусков']
                if absent_pct > 30:
                    recommendations.append(f"📅 **Много пропусков ({absent_pct:.1f}%)** - необходима консультация")
                elif absent_pct > 15:
                    recommendations.append(f"📅 **Пропуски выше нормы ({absent_pct:.1f}%)**")

            if len(student_grades) < 5:
                recommendations.append("📝 **Мало данных** - нужно накопить больше информации")

            if not recommendations:
                recommendations.append("✅ Хорошие результаты")

            for rec in recommendations:
                if rec.startswith("🔴"):
                    st.error(rec)
                elif rec.startswith("🟡"):
                    st.warning(rec)
                elif rec.startswith("🌟"):
                    st.success(rec)
                else:
                    st.info(rec)

    except Exception as e:
        st.error(f"Ошибка при отображении данных ученика: {e}")
        import traceback
        st.code(traceback.format_exc())

def _is_number(s):
    """Проверка, является ли строка числом"""
    try:
        float(s)
        return True
    except ValueError:
        return False


def parse_grades(df, grade_columns=None):
    """Преобразование оценок в числовой формат"""
    grades_df = df.copy()
    VALID_ABSENT = {'н', 'н/а', 'отсутствовал', '-', ''}
    VALID_NUMERIC = {2, 3, 4, 5}

    if grade_columns is None:
        grade_columns = []
        for col in grades_df.columns:
            all_vals = grades_df[col].dropna()
            if len(all_vals) == 0:
                continue
            grade_count = 0
            for val in all_vals.head(20):
                val_str = str(val).strip().lower()
                if val_str in ['2', '3', '4', '5']:
                    grade_count += 1
                elif val_str in VALID_ABSENT:
                    grade_count += 1
                elif _is_number(val_str) and float(val_str) in VALID_NUMERIC:
                    grade_count += 1
            if grade_count / len(all_vals.head(20)) > 0.3:
                grade_columns.append(col)

    if not grade_columns:
        st.warning("⚠️ Не удалось найти колонки с оценками. Убедитесь, что в файле есть оценки 2,3,4,5 или 'н'")
        return pd.DataFrame(), []

    numeric_grades = pd.DataFrame()
    for col in grade_columns:
        valid_grades = []
        for value in grades_df[col]:
            converted = convert_grade_to_number_safe(value)
            valid_grades.append(converted)
        numeric_grades[col] = valid_grades

    return numeric_grades, grade_columns


def filter_valid_grades(grades_df):
    """Очистка ячеек с недопустимыми оценками"""
    filtered_df = grades_df.copy()
    for col in filtered_df.columns:
        filtered_df[col] = filtered_df[col].apply(
            lambda x: x if (pd.isna(x) or (isinstance(x, (int, float)) and 2 <= x <= 5)) else np.nan
        )
    return filtered_df


def get_grades_statistics(grades_df):
    """Получение статистики по оценкам"""
    valid_grades = filter_valid_grades(grades_df)
    statistics = {
        'total_grades': valid_grades.count().sum(),
        'grade_5': (valid_grades == 5).sum().sum(),
        'grade_4': (valid_grades == 4).sum().sum(),
        'grade_3': (valid_grades == 3).sum().sum(),
        'grade_2': (valid_grades == 2).sum().sum(),
        'absences': valid_grades.isna().sum().sum(),
        'avg_grade': valid_grades.mean().mean() if not valid_grades.empty else 0,
    }
    total_valid = statistics['total_grades']
    if total_valid > 0:
        statistics['grade_5_pct'] = (statistics['grade_5'] / total_valid) * 100
        statistics['grade_4_pct'] = (statistics['grade_4'] / total_valid) * 100
        statistics['grade_3_pct'] = (statistics['grade_3'] / total_valid) * 100
        statistics['grade_2_pct'] = (statistics['grade_2'] / total_valid) * 100
    else:
        statistics['grade_5_pct'] = statistics['grade_4_pct'] = statistics['grade_3_pct'] = statistics[
            'grade_2_pct'] = 0
    return statistics


def display_grades_validation(grades_df):
    """Отображение информации о валидации оценок"""
    validation = validate_grades_dataframe(grades_df)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Всего ячеек", validation['total_cells'])
    with col2:
        st.metric("✅ Допустимых оценок", validation['valid_grades'])
    with col3:
        st.metric("📝 Отметок об отсутствии", validation['absent_marks'])
    with col4:
        st.metric("❌ Недопустимых значений", validation['invalid_grades'])
    if validation['invalid_grades'] > 0:
        st.error(f"⚠️ Обнаружено {validation['invalid_grades']} недопустимых значений!")
        if validation['invalid_positions']:
            st.write("**Примеры недопустимых значений:**")
            examples = pd.DataFrame(validation['invalid_positions'][:10])
            st.dataframe(examples, use_container_width=True)
            st.info("💡 Недопустимые значения будут автоматически преобразованы в пропуски")
    return validation['invalid_grades'] == 0


def validate_grades_dataframe(grades_df):
    """Проверка ячеек на допустимые оценки"""
    validation_results = {
        'total_cells': grades_df.size,
        'valid_grades': 0,
        'invalid_grades': 0,
        'absent_marks': 0,
        'invalid_positions': []
    }
    for col in grades_df.columns:
        for idx, value in grades_df[col].items():
            if pd.isna(value):
                validation_results['absent_marks'] += 1
            elif isinstance(value, (int, float)) and 2 <= value <= 5:
                validation_results['valid_grades'] += 1
            else:
                validation_results['invalid_grades'] += 1
                validation_results['invalid_positions'].append({
                    'row': idx,
                    'column': col,
                    'value': value
                })
    return validation_results


def get_detailed_statistics(grades_df, class_info=None):
    """Получение детальной статистики"""
    try:
        if grades_df is None or grades_df.empty:
            return pd.DataFrame()
        stats = []
        for student in grades_df.index:
            if pd.isna(student) or str(student).strip() == '':
                continue
            student_grades = grades_df.loc[student]
            valid_grades = student_grades.dropna()
            valid_numeric_grades = valid_grades[valid_grades.apply(
                lambda x: isinstance(x, (int, float)) and 2 <= x <= 5
            )]
            if len(valid_numeric_grades) > 0:
                student_class = "Не распределен"
                if class_info and isinstance(class_info, dict):
                    student_class = class_info.get(student, "Не распределен")
                std_dev = 0
                if len(valid_numeric_grades) > 1:
                    std_dev = round(float(valid_numeric_grades.std()), 2)
                stats.append({
                    'ФИО': str(student),
                    'Класс': str(student_class),
                    'Средний балл': round(float(valid_numeric_grades.mean()), 2),
                    'Медиана': round(float(valid_numeric_grades.median()), 2),
                    'Мин. оценка': int(valid_numeric_grades.min()),
                    'Макс. оценка': int(valid_numeric_grades.max()),
                    'Станд. отклонение': std_dev,
                    'Кол-во оценок': int(len(valid_numeric_grades)),
                    'Кол-во пропусков': int(student_grades.isna().sum()),
                    'Кол-во некорректных': int(len(valid_grades) - len(valid_numeric_grades)),
                    '% пропусков': round(float((student_grades.isna().sum() / len(grades_df.columns)) * 100), 1) if len(
                        grades_df.columns) > 0 else 0,
                    'Успеваемость (%)': round(
                        float((valid_numeric_grades >= 3).sum() / len(valid_numeric_grades) * 100), 1),
                    'Качество знаний (%)': round(
                        float((valid_numeric_grades >= 4).sum() / len(valid_numeric_grades) * 100), 1),
                })
        if stats:
            return pd.DataFrame(stats)
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Ошибка при получении статистики: {e}")
        return pd.DataFrame()


def prepare_data_for_analysis(df, uploaded_file_name, data_type="attendance"):
    """Подготовка данных для анализа (общая функция)"""
    if df is None:
        return None, None, None, None

    st.subheader("Предпросмотр данных")
    st.dataframe(df.head(10))

    st.subheader("⚙️ Настройка анализа")

    col1, col2, col3 = st.columns(3)
    with col1:
        name_column = st.selectbox(
            "Выберите колонку с ФИО учеников",
            options=['Не выбрано'] + list(df.columns),
            key=f"{data_type}_name_column"
        )
    with col2:
        class_column = st.selectbox(
            "Выберите колонку с классами (или оставьте пустым)",
            options=['Нет колонки с классами'] + list(df.columns),
            key=f"{data_type}_class_column"
        )
    with col3:
        manual_class = None
        if st.checkbox("Назначить классы вручную", key=f"{data_type}_manual_class_check"):
            manual_class = st.text_input("Введите класс для всех учеников", key=f"{data_type}_manual_class")

    if name_column == 'Не выбрано':
        return None, None, None, None

    # Очистка ФИО
    df['clean_name'] = df[name_column].apply(clean_student_name)
    df_clean = df.dropna(subset=['clean_name']).copy()

    student_names = df_clean['clean_name'].astype(str).tolist()
    st.success(f"✅ Найдено {len(student_names)} учеников")

    with st.expander("Показать список учеников"):
        students_df = pd.DataFrame({
            '№': range(1, len(student_names) + 1),
            'ФИО': student_names
        })
        st.dataframe(students_df, use_container_width=True)

    # Сбор информации о классах
    class_info = {}
    if class_column != 'Нет колонки с классами' and class_column in df.columns:
        name_to_class = {}
        for idx, row in df.iterrows():
            clean_name = clean_student_name(row[name_column])
            if clean_name and clean_name in student_names:
                name_to_class[clean_name] = str(row[class_column]) if pd.notna(row[class_column]) else "Не указан"
        for name in student_names:
            class_info[name] = name_to_class.get(name, "Не указан")
    elif manual_class:
        for name in student_names:
            class_info[name] = manual_class
    else:
        for name in student_names:
            class_info[name] = extract_class_info(name)

    # Удаляем временную колонку
    df_clean = df_clean.drop(columns=['clean_name'])
    df_clean.index = student_names

    # Объединение дубликатов
    if st.checkbox("Объединить данные по дублирующимся ученикам", value=True, key=f"{data_type}_merge_duplicates"):
        df_clean = df_clean.groupby(df_clean.index).first()
        student_names = df_clean.index.tolist()
        st.info(f"После объединения дубликатов: {len(df_clean)} учеников")

    # Выбор колонок с оценками
    st.subheader("📝 Выбор колонок с оценками")
    all_columns = list(df_clean.columns)
    grade_columns = st.multiselect(
        "Выберите колонки, содержащие оценки",
        options=all_columns,
        key=f"{data_type}_grade_columns"
    )

    auto_detect = st.button("Автоопределение оценок", key=f"{data_type}_auto_detect")

    if grade_columns or auto_detect:
        if not grade_columns and auto_detect:
            numeric_grades, detected_columns = parse_grades(df_clean)
            grade_columns = detected_columns
        elif grade_columns:
            numeric_grades, _ = parse_grades(df_clean, grade_columns)
        else:
            return None, None, None, None

        if not numeric_grades.empty:
            numeric_grades.index = student_names
            return numeric_grades, grade_columns, class_info, student_names

    return None, None, None, None




def display_comprehensive_analysis(numeric_grades, detailed_stats, class_info, data_type="attendance"):
    """Отображение комплексного анализа (общая функция)"""
    if numeric_grades is None or numeric_grades.empty or detailed_stats is None or detailed_stats.empty:
        st.warning("Недостаточно данных для анализа")
        return

    # Статистика по оценкам
    st.subheader("📊 Статистика по оценкам")
    grade_stats = get_grades_statistics(numeric_grades)

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("5️⃣ Пятерок", grade_stats['grade_5'])
    with col2:
        st.metric("4️⃣ Четверок", grade_stats['grade_4'])
    with col3:
        st.metric("3️⃣ Троек", grade_stats['grade_3'])
    with col4:
        st.metric("2️⃣ Двоек", grade_stats['grade_2'])
    with col5:
        st.metric("📝 Пропусков", grade_stats['absences'])

    # Круговая диаграмма
    fig = px.pie(
        values=[grade_stats['grade_5'], grade_stats['grade_4'],
                grade_stats['grade_3'], grade_stats['grade_2'], grade_stats['absences']],
        names=['5 (Отлично)', '4 (Хорошо)', '3 (Удовл.)', '2 (Неуд.)', 'Пропуски'],
        title='Распределение оценок',
        color_discrete_sequence=['#2E7D32', '#1976D2', '#ED6C02', '#D32F2F', '#9E9E9E']
    )
    st.plotly_chart(fig, use_container_width=True)

    # Расширенная аналитика во вкладках
    st.header("📊 РАСШИРЕННАЯ АНАЛИТИКА")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Распределения",
        "🏆 Рейтинги",
        "📉 Тренды",
        "🔗 Корреляции",
        "📊 Сравнение классов",
        "🎯 Индивидуальный анализ"
    ])

    with tab1:
        st.subheader("📊 Анализ распределений")
        col1, col2 = st.columns(2)
        with col1:
            fig = make_subplots(rows=2, cols=1,
                                subplot_titles=('Распределение средних баллов', 'Накопленное распределение'),
                                vertical_spacing=0.15)
            hist_data = detailed_stats['Средний балл'].dropna()
            fig.add_trace(
                go.Histogram(x=hist_data, nbinsx=20, marker_color='#636EFA', name='Частота', showlegend=False), row=1,
                col=1)
            for threshold, color, name in [(3.0, 'red', 'Порог 3.0'), (3.5, 'orange', 'Порог 3.5'),
                                           (4.0, 'green', 'Порог 4.0')]:
                fig.add_vline(x=threshold, line_dash="dash", line_color=color, row=1, col=1)
            sorted_grades = np.sort(hist_data)
            cumulative = np.arange(1, len(sorted_grades) + 1) / len(sorted_grades) * 100
            fig.add_trace(go.Scatter(x=sorted_grades, y=cumulative, mode='lines', name='Накопленный %',
                                     line=dict(color='#EF553B', width=3), fill='tozeroy'), row=2, col=1)
            fig.update_layout(height=600, showlegend=True)
            fig.update_yaxes(title_text="Количество учеников", row=1, col=1)
            fig.update_yaxes(title_text="Накопленный процент (%)", row=2, col=1)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if 'Класс' in detailed_stats.columns:
                fig = px.box(detailed_stats, x='Класс', y='Средний балл',
                             title='Распределение средних баллов по классам',
                             color='Класс', points='all', hover_data=['ФИО'])
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

            fig = go.Figure()
            fig.add_trace(go.Violin(y=detailed_stats['Средний балл'],
                                    box_visible=True, line_color='black',
                                    meanline_visible=True, fillcolor='lightseagreen',
                                    opacity=0.6, name='Распределение'))
            fig.update_layout(title='Распределение средних баллов (Violin Plot)',
                              yaxis_title='Средний балл', height=400)
            st.plotly_chart(fig, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            levels = {
                'Отличники (≥4.5)': (detailed_stats['Средний балл'] >= 4.5).sum(),
                'Хорошисты (4.0-4.49)': (
                            (detailed_stats['Средний балл'] >= 4.0) & (detailed_stats['Средний балл'] < 4.5)).sum(),
                'Троечники (3.0-3.99)': (
                            (detailed_stats['Средний балл'] >= 3.0) & (detailed_stats['Средний балл'] < 4.0)).sum(),
                'Неуспевающие (<3.0)': (detailed_stats['Средний балл'] < 3.0).sum()
            }
            fig = px.pie(values=list(levels.values()), names=list(levels.keys()),
                         title='Распределение по уровням успеваемости',
                         color_discrete_sequence=['#2E7D32', '#1976D2', '#ED6C02', '#D32F2F'])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if 'Класс' in detailed_stats.columns:
                class_quality = detailed_stats.groupby('Класс')['Качество знаний (%)'].mean().reset_index()
                fig = px.bar(class_quality, x='Класс', y='Качество знаний (%)',
                             title='Качество знаний по классам', color='Качество знаний (%)',
                             color_continuous_scale='RdYlGn', text_auto='.1f')
                fig.update_traces(textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

        with col3:
            if len(numeric_grades.columns) > 1:
                display_students = detailed_stats.nlargest(15, 'Средний балл')['ФИО'].tolist()
                display_subjects = numeric_grades.columns[:10]
                heatmap_data = numeric_grades.loc[display_students, display_subjects]
                fig = px.imshow(heatmap_data, labels=dict(x="Предметы", y="Ученики", color="Оценка"),
                                x=display_subjects, y=display_students,
                                color_continuous_scale='RdYlGn', aspect="auto",
                                title='Тепловая карта успеваемости (топ-15 учеников)')
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🏆 Рейтинги и сравнения")
        col1, col2 = st.columns(2)
        with col1:
            top_10 = detailed_stats.nlargest(10, 'Средний балл')[
                ['ФИО', 'Класс', 'Средний балл', 'Качество знаний (%)']]
            fig = px.bar(top_10, x='Средний балл', y='ФИО', orientation='h',
                         title='Топ-10 лучших учеников', color='Средний балл',
                         color_continuous_scale='Greens', text='Средний балл')
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            bottom_10 = detailed_stats.nsmallest(10, 'Средний балл')[
                ['ФИО', 'Класс', 'Средний балл', 'Кол-во пропусков']]
            fig = px.bar(bottom_10, x='Средний балл', y='ФИО', orientation='h',
                         title='Топ-10 учеников с проблемами', color='Средний балл',
                         color_continuous_scale='Reds', text='Средний балл')
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(yaxis={'categoryorder': 'total descending'})
            st.plotly_chart(fig, use_container_width=True)

        if len(numeric_grades.columns) >= 3:
            st.subheader("🕸️ Сравнение профилей лучших учеников")
            top_n_radar = st.slider("Количество учеников для сравнения", 3, 8, 5, key=f"{data_type}_radar_n")
            top_students_radar = detailed_stats.nlargest(top_n_radar, 'Средний балл')['ФИО'].tolist()
            subjects = numeric_grades.columns[:6]
            subjects_short = [str(s)[:10] for s in subjects]
            fig = go.Figure()
            for student in top_students_radar:
                if student in numeric_grades.index:
                    student_grades = numeric_grades.loc[student][subjects].values
                    fig.add_trace(go.Scatterpolar(r=student_grades, theta=subjects_short,
                                                  fill='toself', name=student[:15]))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                              title=f"Сравнение профилей топ-{top_n_radar} учеников", height=500)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("📉 Анализ трендов и динамики")
        st.write("**Динамика успеваемости класса**")
        trend_data = []
        for student in numeric_grades.index[:20]:
            grades = numeric_grades.loc[student].dropna().values
            if len(grades) > 1:
                for i, grade in enumerate(grades):
                    trend_data.append({
                        'Ученик': student[:20] if len(student) > 20 else student,
                        'Номер работы': i + 1,
                        'Оценка': grade
                    })
        if trend_data:
            trend_df = pd.DataFrame(trend_data)
            fig = px.line(trend_df, x='Номер работы', y='Оценка', color='Ученик',
                          title='Динамика оценок всех учеников', markers=True)
            avg_by_work = trend_df.groupby('Номер работы')['Оценка'].mean().reset_index()
            fig.add_trace(go.Scatter(x=avg_by_work['Номер работы'], y=avg_by_work['Оценка'],
                                     mode='lines+markers', name='Среднее по классу',
                                     line=dict(color='black', width=4), marker=dict(size=8, symbol='diamond')))
            fig.update_layout(height=500, xaxis_title="Номер работы", yaxis_title="Оценка",
                              yaxis=dict(range=[1.5, 5.5]), hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

    with tab4:
        st.subheader("🔗 Корреляционный анализ")
        if len(numeric_grades.columns) > 1:
            corr_columns = numeric_grades.columns[:15]
            corr_data = numeric_grades[corr_columns].copy().dropna()
            if len(corr_data) > 5 and len(corr_data.columns) > 1:
                corr_matrix = corr_data.corr()
                fig = px.imshow(corr_matrix, labels=dict(color="Корреляция"),
                                x=corr_matrix.columns, y=corr_matrix.columns,
                                color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                                title='Матрица корреляций между предметами')
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)

        if '% пропусков' in detailed_stats.columns and 'Средний балл' in detailed_stats.columns:
            st.subheader("📉 Влияние пропусков на успеваемость")
            fig = px.scatter(detailed_stats, x='% пропусков', y='Средний балл',
                             size='Кол-во оценок', color='Класс' if 'Класс' in detailed_stats.columns else None,
                             hover_data=['ФИО'], title='Зависимость успеваемости от пропусков')
            st.plotly_chart(fig, use_container_width=True)

    with tab5:
        st.subheader("🏫 Сравнение классов")
        if 'Класс' in detailed_stats.columns and len(detailed_stats['Класс'].unique()) > 1:
            class_summary = detailed_stats.groupby('Класс').agg({
                'Средний балл': ['mean', 'std', 'min', 'max'],
                'Качество знаний (%)': 'mean',
                'Успеваемость (%)': 'mean',
                'Кол-во пропусков': 'sum',
                'ФИО': 'count'
            }).round(2)
            class_summary.columns = ['Ср. балл', 'Стд.откл', 'Мин', 'Макс', 'Качество %', 'Успеваемость %',
                                     'Всего пропусков', 'Учеников']
            st.dataframe(class_summary, use_container_width=True)

            fig = go.Figure()
            metrics = ['Средний балл', 'Качество знаний (%)', 'Успеваемость (%)']
            for metric in metrics:
                if metric in detailed_stats.columns:
                    class_means = detailed_stats.groupby('Класс')[metric].mean().reset_index()
                    fig.add_trace(go.Bar(name=metric, x=class_means['Класс'], y=class_means[metric],
                                         text=class_means[metric].round(1), textposition='outside'))
            fig.update_layout(title='Сравнение классов по основным метрикам', barmode='group', height=500)
            st.plotly_chart(fig, use_container_width=True)

    with tab6:
        st.subheader("🎯 Индивидуальный анализ")

        # Получаем список учеников
        if 'ФИО' in detailed_stats.columns:
            students_list = sorted(detailed_stats['ФИО'].tolist())
        else:
            students_list = sorted(list(numeric_grades.index))

        if not students_list:
            st.info("Нет данных об учениках")
        else:
            # Добавляем поле поиска
            search_term = st.text_input("🔍 Поиск ученика по фамилии", key=f"{data_type}_search")

            # Фильтруем учеников по поиску
            filtered_students = students_list
            if search_term:
                filtered_students = [s for s in students_list if search_term.lower() in s.lower()]

            # Показываем количество найденных
            st.write(f"Найдено учеников: {len(filtered_students)}")

            # Если учеников много, показываем выбор, если мало - вкладки
            if len(filtered_students) > 15:
                # Если много учеников, используем selectbox для выбора
                selected_student = st.selectbox(
                    "Выберите ученика для анализа",
                    options=filtered_students,
                    key=f"{data_type}_select"
                )

                if selected_student:
                    # Отображаем детали выбранного ученика
                    _display_student_detail(selected_student, numeric_grades, detailed_stats, class_info)
            else:
                # Если учеников мало, создаем вкладки для каждого
                # Ограничиваем количество вкладок для производительности
                max_tabs = min(len(filtered_students), 50)

                # Создаем короткие названия для вкладок
                tab_names = []
                for student in filtered_students[:max_tabs]:
                    # Берем первые 15 символов
                    short_name = student[:15] + "..." if len(student) > 15 else student
                    tab_names.append(f"{short_name}")

                tabs = st.tabs(tab_names)

                # Заполняем каждую вкладку
                for i, student in enumerate(filtered_students[:max_tabs]):
                    with tabs[i]:
                        _display_student_detail(student, numeric_grades, detailed_stats, class_info)

                if len(filtered_students) > max_tabs:
                    st.warning(f"Показаны первые {max_tabs} учеников из {len(filtered_students)}")

    # Детальная таблица статистики
    st.subheader("📋 Детальная статистика по ученикам")
    if 'ФИО' in detailed_stats.columns:
        display_columns = ['ФИО', 'Класс', 'Средний балл', 'Медиана', 'Мин. оценка', 'Макс. оценка',
                           'Кол-во оценок', 'Кол-во пропусков', '% пропусков', 'Успеваемость (%)',
                           'Качество знаний (%)']
        existing_columns = [col for col in display_columns if col in detailed_stats.columns]
        st.dataframe(detailed_stats[existing_columns], use_container_width=True)

        csv = detailed_stats[existing_columns].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Скачать статистику (CSV)",
            data=csv,
            file_name=f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.dataframe(detailed_stats, use_container_width=True)


# ==================== АНАЛИЗ ТЕКУЩЕЙ УСПЕВАЕМОСТИ ====================

# ==================== АНАЛИЗ ТЕКУЩЕЙ УСПЕВАЕМОСТИ ====================

if st.session_state.current_page == "Анализ текущей успеваемости":
    st.title("📊 Анализ текущей успеваемости")
    st.markdown(f"*Разработчик: {__author__}*")

    uploaded_file = st.file_uploader(
        "Загрузите файл с оценками (CSV или Excel)",
        type=['csv', 'xlsx', 'xls']
    )

    if uploaded_file is not None:
        df = load_file(uploaded_file)

        if df is not None:
            numeric_grades, grade_columns, class_info, student_names = prepare_data_for_analysis(df, uploaded_file.name,
                                                                                                 "attendance")

            if numeric_grades is not None and not numeric_grades.empty:
                # Проверка валидности
                st.subheader("🔍 Проверка качества данных")
                display_grades_validation(numeric_grades)

                # Очистка данных
                numeric_grades = filter_valid_grades(numeric_grades)
                numeric_grades.index = student_names

                # Получение статистики
                with st.spinner("Расчет статистики..."):
                    detailed_stats = get_detailed_statistics(numeric_grades, class_info)

                if detailed_stats is not None and not detailed_stats.empty:
                    st.success(f"✅ Получена статистика для {len(detailed_stats)} учеников")
                    st.session_state.attendance_analysis_complete = True
                    st.session_state.attendance_data = {
                        'numeric_grades': numeric_grades,
                        'detailed_stats': detailed_stats,
                        'class_info': class_info,
                        'student_names': student_names
                    }
                    display_comprehensive_analysis(numeric_grades, detailed_stats, class_info, "attendance")

                    # Индивидуальный анализ - только если есть данные
                    st.header("🎯 Индивидуальный анализ учеников")
                    display_individual_analysis_modal("attendance", numeric_grades, detailed_stats, class_info)
                else:
                    st.warning("Не удалось получить статистику по ученикам")
            else:
                st.info("Пожалуйста, выберите колонки с оценками для анализа")

# ==================== АНАЛИЗ ЭКЗАМЕНОВ ====================

elif st.session_state.current_page == "Анализ экзаменов":
    st.title("📝 Анализ экзаменационных работ")
    st.markdown(f"*Разработчик: {__author__}*")

    uploaded_exam = st.file_uploader(
        "Загрузите файл с результатами экзамена",
        type=['csv', 'xlsx', 'xls'],
        key="exam_uploader"
    )

    if uploaded_exam is not None:
        df = load_file(uploaded_exam)

        if df is not None:
            st.subheader("Предпросмотр данных")
            st.dataframe(df.head(10))

            st.subheader("⚙️ Настройка анализа экзамена")

            col1, col2, col3 = st.columns(3)
            with col1:
                # Автоматический поиск колонки с ФИО
                auto_name_column = find_name_column(df)
                name_column = st.selectbox(
                    "Колонка с ФИО учеников",
                    options=['Автоопределение'] + list(df.columns),
                    index=0 if auto_name_column is None else list(df.columns).index(auto_name_column) + 1,
                    key="exam_name_col"
                )

                if name_column == 'Автоопределение':
                    if auto_name_column:
                        name_column = auto_name_column
                        st.info(f"🔍 Автоматически определена колонка с ФИО: {name_column}")
                    else:
                        st.warning("Не удалось автоматически определить колонку с ФИО")
                        name_column = 'Не выбрано'

            with col2:
                class_column = st.selectbox(
                    "Колонка с классами",
                    options=['Нет колонки с классами'] + list(df.columns),
                    key="exam_class_col"
                )

            with col3:
                # Автоопределение колонки с суммой баллов
                suggested_total = find_total_score_column(df)
                total_score_column = st.selectbox(
                    "Колонка с суммой баллов (для анализа)",
                    options=['Не выбрано'] + list(df.columns),
                    index=list(df.columns).index(suggested_total) + 1 if suggested_total else 0,
                    key="exam_total_col"
                )

            if name_column != 'Не выбрано':
                # Очистка ФИО
                df['clean_name'] = df[name_column].apply(clean_student_name)
                df_clean = df.dropna(subset=['clean_name']).copy()

                student_names = df_clean['clean_name'].astype(str).tolist()
                st.success(f"✅ Найдено {len(student_names)} учеников")

                with st.expander("Показать список учеников"):
                    students_df = pd.DataFrame({
                        '№': range(1, len(student_names) + 1),
                        'ФИО': student_names
                    })
                    st.dataframe(students_df, use_container_width=True)

                # Сбор информации о классах
                class_info = {}
                if class_column != 'Нет колонки с классами' and class_column in df.columns:
                    name_to_class = {}
                    for idx, row in df.iterrows():
                        clean_name = clean_student_name(row[name_column])
                        if clean_name and clean_name in student_names:
                            name_to_class[clean_name] = str(row[class_column]) if pd.notna(
                                row[class_column]) else "Не указан"
                    for name in student_names:
                        class_info[name] = name_to_class.get(name, "Не указан")
                else:
                    for name in student_names:
                        class_info[name] = extract_class_info(name)

                # Удаляем временную колонку
                df_clean = df_clean.drop(columns=['clean_name'])
                df_clean.index = student_names

                st.subheader("📝 Выбор колонок с баллами")



                # Определяем колонки, которые не содержат баллы
                exclude_columns = [name_column, class_column, total_score_column, '№', 'studentid', 'Вариант',
                                   'Колонка_']
                exclude_columns = [col for col in exclude_columns if col in df_clean.columns]

                all_columns = list(df_clean.columns)
                numeric_columns = [col for col in all_columns if col not in exclude_columns]

                # Варианты выбора колонок
                col_selection_method = st.radio(
                    "Способ выбора колонок:",
                    ["Выбрать по одной", "Выбрать диапазон (от первой до последней)"],
                    key="exam_col_method"
                )

                grade_columns = []

                if col_selection_method == "Выбрать по одной":
                    grade_columns = st.multiselect(
                        "Выберите колонки с баллами за задания (вопросы)",
                        options=numeric_columns,
                        default=numeric_columns[:20],
                        key="exam_grade_columns_select"
                    )
                else:
                    # Диапазонный выбор
                    if len(numeric_columns) > 0:
                        col1_range, col2_range = st.columns(2)
                        with col1_range:
                            start_col = st.selectbox(
                                "Первая колонка с баллами",
                                options=numeric_columns,
                                index=0,
                                key="exam_start_col"
                            )
                        with col2_range:
                            end_col = st.selectbox(
                                "Последняя колонка с баллами",
                                options=numeric_columns,
                                index=len(numeric_columns) - 1,
                                key="exam_end_col"
                            )

                        if start_col and end_col:
                            start_idx = numeric_columns.index(start_col)
                            end_idx = numeric_columns.index(end_col)
                            if start_idx <= end_idx:
                                grade_columns = numeric_columns[start_idx:end_idx + 1]
                                st.info(f"Выбрано {len(grade_columns)} колонок: от {start_col} до {end_col}")
                            else:
                                st.warning("Первая колонка должна быть раньше последней")

                if grade_columns:
                    # Парсим баллы
                    numeric_grades, _ = parse_exam_grades(df_clean, grade_columns)

                    if numeric_grades is not None and not numeric_grades.empty:
                        numeric_grades.index = student_names

                        # Очищаем данные от выбросов
                        numeric_grades = clean_exam_data(numeric_grades, max_reasonable_score=100)

                        # Переименовываем колонки
                        new_names = {}
                        for i, col in enumerate(grade_columns):
                            new_names[col] = f"вопрос_{i + 1}"
                        numeric_grades = numeric_grades.rename(columns=new_names)

                        # Вычисляем сумму баллов (общий балл)
                        question_cols = [c for c in numeric_grades.columns if c.startswith('вопрос_')]
                        numeric_grades['Сумма баллов'] = numeric_grades[question_cols].sum(axis=1)

                        # Настройка системы оценивания
                        st.subheader("⚙️ НАСТРОЙКА ОЦЕНИВАНИЯ")

                        # Создаем вкладки для настройки
                        tab_config, tab_preview = st.tabs(["⚙️ Настройка", "📊 Предпросмотр"])

                        with tab_config:
                            col1, col2 = st.columns(2)

                            with col1:
                                # Максимальный балл за экзамен
                                total_max_score = st.number_input(
                                    "📊 Максимальный балл за экзамен",
                                    min_value=1,
                                    max_value=1000,
                                    value=100,
                                    step=5,
                                    help="Общая сумма баллов, которую можно получить за экзамен"
                                )

                            with col2:
                                st.write("**🎯 Шкала перевода в оценки (%)**")
                                score_3_percent = st.number_input(
                                    "Порог для '3'",
                                    min_value=0,
                                    max_value=100,
                                    value=50,
                                    step=5,
                                    help="Минимальный процент для оценки 3"
                                )
                                score_4_percent = st.number_input(
                                    "Порог для '4'",
                                    min_value=0,
                                    max_value=100,
                                    value=70,
                                    step=5,
                                    help="Минимальный процент для оценки 4"
                                )
                                score_5_percent = st.number_input(
                                    "Порог для '5'",
                                    min_value=0,
                                    max_value=100,
                                    value=85,
                                    step=5,
                                    help="Минимальный процент для оценки 5"
                                )

                            scoring_system = {
                                'total_max_score': total_max_score,
                                'score_3_percent': score_3_percent,
                                'score_4_percent': score_4_percent,
                                'score_5_percent': score_5_percent
                            }

                            # Проверка корректности
                            if score_3_percent >= score_4_percent or score_4_percent >= score_5_percent:
                                st.error("❌ Пороги должны увеличиваться: 3 < 4 < 5")
                            else:
                                st.success("✅ Шкала настроена корректно")

                        with tab_preview:
                            st.write("**Предварительный просмотр шкалы оценивания:**")

                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Оценка 2", f"0-{score_3_percent - 1}%")
                            with col2:
                                st.metric("Оценка 3", f"{score_3_percent}-{score_4_percent - 1}%")
                            with col3:
                                st.metric("Оценка 4", f"{score_4_percent}-{score_5_percent - 1}%")
                            with col4:
                                st.metric("Оценка 5", f"{score_5_percent}-100%")

                            # Пример расчета
                            st.write("**Примеры расчета:**")
                            example_scores = [20, 40, 55, 75, 90]
                            for score in example_scores:
                                percent = (score / total_max_score) * 100
                                if percent >= score_5_percent:
                                    grade = 5
                                elif percent >= score_4_percent:
                                    grade = 4
                                elif percent >= score_3_percent:
                                    grade = 3
                                else:
                                    grade = 2
                                st.write(f"{score} баллов → {percent:.1f}% → оценка {grade}")

                        # Применяем расчет
                        numeric_grades['Процент'] = numeric_grades['Сумма баллов'].apply(
                            lambda x: (x / scoring_system['total_max_score']) * 100
                        )
                        numeric_grades['Оценка'] = numeric_grades['Сумма баллов'].apply(
                            lambda x: calculate_grade(x, scoring_system)
                        )

                        st.success(f"✅ Расчет выполнен! Средний балл: {numeric_grades['Сумма баллов'].mean():.1f}, "
                                   f"Средний процент: {numeric_grades['Процент'].mean():.1f}%, "
                                   f"Средняя оценка: {numeric_grades['Оценка'].mean():.1f}")

                        # Показываем распределение оценок
                        st.subheader("📊 Распределение оценок")

                        grade_counts = numeric_grades['Оценка'].value_counts().sort_index()
                        col1, col2 = st.columns(2)

                        with col1:
                            fig = px.pie(
                                values=grade_counts.values,
                                names=grade_counts.index,
                                title="Распределение оценок",
                                color=grade_counts.index,
                                color_discrete_sequence=['#D32F2F', '#ED6C02', '#1976D2', '#2E7D32']
                            )
                            st.plotly_chart(fig, use_container_width=True)

                        with col2:
                            # Таблица с распределением
                            grade_dist = pd.DataFrame({
                                'Оценка': [2, 3, 4, 5],
                                'Количество': [grade_counts.get(2, 0), grade_counts.get(3, 0),
                                               grade_counts.get(4, 0), grade_counts.get(5, 0)],
                                'Процент': [grade_counts.get(2, 0) / len(numeric_grades) * 100 if len(
                                    numeric_grades) > 0 else 0,
                                            grade_counts.get(3, 0) / len(numeric_grades) * 100 if len(
                                                numeric_grades) > 0 else 0,
                                            grade_counts.get(4, 0) / len(numeric_grades) * 100 if len(
                                                numeric_grades) > 0 else 0,
                                            grade_counts.get(5, 0) / len(numeric_grades) * 100 if len(
                                                numeric_grades) > 0 else 0]
                            })
                            grade_dist['Процент'] = grade_dist['Процент'].round(1)
                            st.dataframe(grade_dist, use_container_width=True, hide_index=True)



                        # Статистика по баллам
                        st.subheader("📊 Статистика по баллам")

                        # Общая статистика
                        col1_stat, col2_stat, col3_stat, col4_stat = st.columns(4)
                        with col1_stat:
                            avg_score = numeric_grades[
                                numeric_grades.columns].mean().mean() if not numeric_grades.empty else 0
                            st.metric("Средний балл", f"{avg_score:.2f}")
                        with col2_stat:
                            max_score = numeric_grades.max().max() if not numeric_grades.empty else 0
                            st.metric("Максимальный балл", f"{max_score:.0f}")
                        with col3_stat:
                            min_score = numeric_grades.min().min() if not numeric_grades.empty else 0
                            st.metric("Минимальный балл", f"{min_score:.0f}")
                        with col4_stat:
                            total_students = len(numeric_grades)
                            st.metric("Всего учеников", total_students)

                        # Анализ по заданиям
                        st.subheader("📊 Анализ выполнения заданий")

                        # Создаем DataFrame со статистикой по каждому заданию
                        tasks_stats = pd.DataFrame({
                            'Задание': numeric_grades.columns,
                            'Средний балл': numeric_grades.mean().values,
                            'Медиана': numeric_grades.median().values,
                            'Максимум': numeric_grades.max().values,
                            'Минимум': numeric_grades.min().values,
                            'Станд. отклонение': numeric_grades.std().values,
                            'Пропуски (%)': (numeric_grades.isna().sum() / len(numeric_grades) * 100).values
                        }).round(2)

                        # Показываем топ заданий
                        col1_task, col2_task = st.columns(2)
                        with col1_task:
                            st.write("**✅ Лучшие результаты (топ-5 заданий):**")
                            best_tasks = tasks_stats.nlargest(5, 'Средний балл')[['Задание', 'Средний балл']]
                            st.dataframe(best_tasks, use_container_width=True)

                            fig = px.bar(best_tasks, x='Задание', y='Средний балл',
                                         title='Задания с наивысшим средним баллом',
                                         color='Средний балл', color_continuous_scale='Greens')
                            st.plotly_chart(fig, use_container_width=True)

                        with col2_task:
                            st.write("**⚠️ Сложные задания (топ-5):**")
                            worst_tasks = tasks_stats.nsmallest(5, 'Средний балл')[['Задание', 'Средний балл']]
                            st.dataframe(worst_tasks, use_container_width=True)

                            fig = px.bar(worst_tasks, x='Задание', y='Средний балл',
                                         title='Задания с наименьшим средним баллом',
                                         color='Средний балл', color_continuous_scale='Reds')
                            st.plotly_chart(fig, use_container_width=True)

                        # Тепловая карта успеваемости по заданиям
                        # Тепловая карта успеваемости по заданиям
                        st.subheader("🌡️ Тепловая карта успеваемости")

                        students_avg = numeric_grades.mean(axis=1).sort_values(ascending=False)
                        top_students = students_avg.head(20).index.tolist()

                        heatmap_data = numeric_grades.loc[top_students, numeric_grades.columns[:20]] if len(
                            numeric_grades.columns) > 20 else numeric_grades.loc[top_students]

                        fig = px.imshow(heatmap_data,
                                        labels=dict(x="Задания", y="Ученики", color="Баллы"),
                                        title="Тепловая карта успеваемости (топ-20 учеников)",
                                        color_continuous_scale='RdYlGn',
                                        aspect="auto")
                        fig.update_layout(height=600)
                        st.plotly_chart(fig, use_container_width=True, key="heatmap_chart")

                        # Получение детальной статистики
                        with st.spinner("Расчет статистики..."):
                            detailed_stats = get_exam_detailed_statistics(numeric_grades, class_info)

                        if detailed_stats is not None and not detailed_stats.empty:
                            st.success(f"✅ Получена статистика для {len(detailed_stats)} учеников")
                            st.session_state.exam_analysis_complete = True

                            # Сохраняем в session_state
                            exam_name = uploaded_exam.name
                            st.session_state.exam_data[exam_name] = {
                                'numeric_grades': numeric_grades,
                                'detailed_stats': detailed_stats,
                                'class_info': class_info,
                                'student_names': student_names,
                                'scoring_system': scoring_system  # Сохраняем систему оценивания
                            }

                            # Отображаем полную аналитику с передачей scoring_system
                            display_exam_comprehensive_analysis(numeric_grades, detailed_stats, class_info,
                                                                scoring_system)

                            st.header("🎯 Индивидуальный анализ учеников")
                            display_individual_analysis_modal("exam", numeric_grades, detailed_stats, class_info)

# ==================== СРАВНЕНИЕ ЭКЗАМЕНОВ ====================

elif st.session_state.current_page == "Сравнение экзаменов":
    st.title("🔄 Сравнение экзаменов")
    st.markdown(f"*Разработчик: {__author__}*")

    if len(st.session_state.exam_data) < 2:
        st.warning("⚠️ Для сравнения необходимо загрузить минимум 2 экзамена в разделе 'Анализ экзаменов'")
    else:
        exam_names = list(st.session_state.exam_data.keys())

        col1, col2 = st.columns(2)
        with col1:
            exam1 = st.selectbox("Выберите первый экзамен", options=exam_names)
        with col2:
            exam2 = st.selectbox("Выберите второй экзамен", options=exam_names, index=1 if len(exam_names) > 1 else 0)

        if exam1 and exam2 and exam1 != exam2:
            data1 = st.session_state.exam_data[exam1]
            data2 = st.session_state.exam_data[exam2]

            df1 = data1['numeric_grades']
            df2 = data2['numeric_grades']
            stats1 = data1['detailed_stats']
            stats2 = data2['detailed_stats']

            # Получаем систему оценивания (если есть)
            scoring_system1 = data1.get('scoring_system', None)
            scoring_system2 = data2.get('scoring_system', None)

            # Сравнительная статистика
            st.header("📊 Сравнительная статистика")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mean1 = stats1['Средний балл'].mean() if not stats1.empty else 0
                mean2 = stats2['Средний балл'].mean() if not stats2.empty else 0
                st.metric("Средний балл", f"{mean1:.2f}", delta=f"{mean1 - mean2:.2f}", delta_color="normal")
            with col2:
                quality1 = stats1['Качество знаний (%)'].mean() if not stats1.empty else 0
                quality2 = stats2['Качество знаний (%)'].mean() if not stats2.empty else 0
                st.metric("Качество знаний", f"{quality1:.1f}%", delta=f"{quality1 - quality2:.1f}%",
                          delta_color="normal")
            with col3:
                success1 = stats1['Успеваемость (%)'].mean() if not stats1.empty else 0
                success2 = stats2['Успеваемость (%)'].mean() if not stats2.empty else 0
                st.metric("Успеваемость", f"{success1:.1f}%", delta=f"{success1 - success2:.1f}%", delta_color="normal")
            with col4:
                students1 = len(stats1)
                students2 = len(stats2)
                st.metric("Учеников", students1, delta=f"{students1 - students2}", delta_color="off")

            # Распределение оценок
            st.subheader("📈 Сравнение распределений оценок")

            fig = go.Figure()

            grades_stats1 = get_grades_statistics(df1)
            grades_stats2 = get_grades_statistics(df2)

            categories = ['5', '4', '3', '2', 'Пропуски']
            values1 = [grades_stats1['grade_5'], grades_stats1['grade_4'],
                       grades_stats1['grade_3'], grades_stats1['grade_2'], grades_stats1['absences']]
            values2 = [grades_stats2['grade_5'], grades_stats2['grade_4'],
                       grades_stats2['grade_3'], grades_stats2['grade_2'], grades_stats2['absences']]

            fig.add_trace(go.Bar(name=exam1[:20], x=categories, y=values1, marker_color='#636EFA'))
            fig.add_trace(go.Bar(name=exam2[:20], x=categories, y=values2, marker_color='#EF553B'))

            fig.update_layout(title="Сравнение распределения оценок", barmode='group', height=500)
            st.plotly_chart(fig, use_container_width=True)

            # Сравнение средних баллов по заданиям
            if len(df1.columns) > 1 and len(df2.columns) > 1:
                common_columns = set(df1.columns) & set(df2.columns)
                if common_columns:
                    st.subheader("📊 Сравнение средних баллов по заданиям")
                    comparison_df = pd.DataFrame({
                        exam1[:20]: df1[list(common_columns)].mean(),
                        exam2[:20]: df2[list(common_columns)].mean()
                    })

                    fig = go.Figure()
                    fig.add_trace(go.Bar(name=exam1[:20], x=comparison_df.index, y=comparison_df[exam1[:20]],
                                         marker_color='#636EFA', text=comparison_df[exam1[:20]].round(2),
                                         textposition='outside'))
                    fig.add_trace(go.Bar(name=exam2[:20], x=comparison_df.index, y=comparison_df[exam2[:20]],
                                         marker_color='#EF553B', text=comparison_df[exam2[:20]].round(2),
                                         textposition='outside'))
                    fig.update_layout(title="Сравнение средних баллов по заданиям", xaxis_title="Задания",
                                      yaxis_title="Средний балл", barmode='group', height=500)
                    st.plotly_chart(fig, use_container_width=True)

                    # Анализ изменений
                    st.subheader("📉 Анализ изменений")
                    diff = comparison_df[exam1[:20]] - comparison_df[exam2[:20]]

                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**✅ Положительная динамика (улучшение):**")
                        better = diff[diff > 0].sort_values(ascending=False)
                        if not better.empty:
                            for idx, val in better.items():
                                st.write(f"• {idx}: **+{val:.2f}**")
                        else:
                            st.write("Нет улучшений")

                    with col2:
                        st.write("**❌ Отрицательная динамика (ухудшение):**")
                        worse = diff[diff < 0].sort_values()
                        if not worse.empty:
                            for idx, val in worse.items():
                                st.write(f"• {idx}: **{val:.2f}**")
                        else:
                            st.write("Нет ухудшений")

            # Сравнение успеваемости учеников
            st.subheader("👥 Сравнение успеваемости учеников")

            common_students = set(stats1['ФИО'].tolist()) & set(stats2['ФИО'].tolist())
            if common_students:
                student_comparison = pd.DataFrame({
                    'student': list(common_students),
                    exam1[:20]: [stats1[stats1['ФИО'] == s]['Средний балл'].values[0] for s in common_students],
                    exam2[:20]: [stats2[stats2['ФИО'] == s]['Средний балл'].values[0] for s in common_students]
                })

                fig = px.scatter(student_comparison, x=exam1[:20], y=exam2[:20], text='student',
                                 title='Сравнение результатов учеников', trendline="ols")
                fig.update_traces(textposition='top center')
                st.plotly_chart(fig, use_container_width=True)

                # Таблица изменений
                student_comparison['Изменение'] = student_comparison[exam2[:20]] - student_comparison[exam1[:20]]
                student_comparison = student_comparison.sort_values('Изменение', ascending=False)

                col1, col2 = st.columns(2)
                with col1:
                    st.write("**📈 Наибольший прогресс:**")
                    st.dataframe(student_comparison.head(10)[['student', exam1[:20], exam2[:20], 'Изменение']],
                                 use_container_width=True)
                with col2:
                    st.write("**📉 Наибольшее ухудшение:**")
                    st.dataframe(student_comparison.tail(10)[['student', exam1[:20], exam2[:20], 'Изменение']],
                                 use_container_width=True)

# ==================== СТАТИСТИКА ПО КЛАССАМ ====================

elif st.session_state.current_page == "Статистика по классам":
    st.title("🏫 Статистика по классам")
    st.markdown(f"*Разработчик: {__author__}*")

    if not st.session_state.attendance_analysis_complete:
        st.warning("Сначала загрузите данные в разделе 'Анализ текущей успеваемости'")
    else:
        data = st.session_state.attendance_data
        detailed_stats = data['detailed_stats']

        if 'Класс' in detailed_stats.columns and len(detailed_stats['Класс'].unique()) > 1:
            st.subheader("📊 Общая статистика по классам")

            class_summary = detailed_stats.groupby('Класс').agg({
                'Средний балл': ['mean', 'std', 'min', 'max'],
                'Качество знаний (%)': 'mean',
                'Успеваемость (%)': 'mean',
                'Кол-во пропусков': 'sum',
                'ФИО': 'count'
            }).round(2)

            class_summary.columns = ['Ср. балл', 'Стд.откл', 'Мин', 'Макс', 'Качество %', 'Успеваемость %',
                                     'Всего пропусков', 'Учеников']
            st.dataframe(class_summary, use_container_width=True)

            # Визуализация по классам
            st.subheader("📈 Сравнение классов")

            col1, col2 = st.columns(2)

            with col1:
                fig = px.bar(class_summary.reset_index(), x='Класс', y='Ср. балл',
                             title='Средний балл по классам', color='Класс',
                             text='Ср. балл')
                fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(class_summary.reset_index(), x='Класс', y='Качество %',
                             title='Качество знаний по классам', color='Класс',
                             text='Качество %')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

            # Распределение учеников по классам
            st.subheader("👥 Распределение учеников по классам")

            class_counts = detailed_stats['Класс'].value_counts().reset_index()
            class_counts.columns = ['Класс', 'Количество']

            fig = px.pie(class_counts, values='Количество', names='Класс',
                         title='Распределение учеников по классам')
            st.plotly_chart(fig, use_container_width=True)

            # Детальная таблица по классам
            st.subheader("📋 Детальная информация по ученикам")
            selected_class = st.selectbox("Выберите класс", options=sorted(detailed_stats['Класс'].unique()))

            if selected_class:
                class_students = detailed_stats[detailed_stats['Класс'] == selected_class]
                st.dataframe(class_students[['ФИО', 'Средний балл', 'Качество знаний (%)',
                                             'Успеваемость (%)', 'Кол-во пропусков', '% пропусков']],
                             use_container_width=True)

                # Распределение оценок в классе
                st.subheader(f"📊 Распределение успеваемости в {selected_class}")

                fig = px.histogram(class_students, x='Средний балл', nbins=20,
                                   title=f'Распределение средних баллов в {selected_class}',
                                   color_discrete_sequence=['#636EFA'])
                fig.add_vline(x=3.0, line_dash="dash", line_color="red", annotation_text="Порог 3.0")
                fig.add_vline(x=3.5, line_dash="dash", line_color="orange", annotation_text="Порог 3.5")
                fig.add_vline(x=4.0, line_dash="dash", line_color="green", annotation_text="Порог 4.0")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Для отображения статистики по классам необходимо указать колонку с классами при загрузке файла")

# Инструкция по использованию
with st.sidebar:
    st.markdown("---")
    st.header("📖 Краткая инструкция")
    st.markdown("""
    1. **Загрузите файл** с данными
    2. **Выберите колонки** для анализа
    3. **Настройте параметры** при необходимости
    4. **Изучите аналитику** и визуализации

    🔍 **Функции:**
    - Автоопределение ФИО и оценок
    - Объединение дубликатов
    - Распределение по классам
    - Детальная статистика
    - Сравнение экзаменов
    - Сохранение выбора ученика
    """)

# Нижний колонтитул
st.markdown("---")
st.markdown(f"<div style='text-align: center'>© {__year__} {__author__}. Все права защищены.</div>",
            unsafe_allow_html=True)