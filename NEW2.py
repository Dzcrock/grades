import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import re
import os
import sys

# Информация о разработчике
__author__ = "Даниил Зуев"
__version__ = "2.0.0"
__year__ = "2026"

# Настройка страницы
st.set_page_config(
    page_title="Анализ успеваемости учеников",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Приветствие с информацией о разработчике
st.sidebar.markdown("""
---
### 👨‍💻 О программе
**Разработчик:** Даниил Зуев  
**Версия:** 2.0.0  
**Год:** 2026  

[![GitHub](https://img.shields.io/badge/GitHub-100000?style=flat&logo=github&logoColor=white)](https://github.com/)
[![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=flat&logo=telegram&logoColor=white)](https://t.me/)
""")

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


def extract_header_names(df):
    """Извлечение названий колонок из первой непустой строки"""
    # Если первая строка пустая или содержит NaN
    if df.iloc[0].isna().all() or df.iloc[0].astype(str).str.strip().eq('').all():
        # Ищем первую строку с данными
        for i in range(1, len(df)):
            if not df.iloc[i].isna().all() and not df.iloc[i].astype(str).str.strip().eq('').all():
                # Используем эту строку как названия колонок
                new_columns = df.iloc[i].astype(str).str.strip()
                df = df.iloc[i + 1:].reset_index(drop=True)
                df.columns = new_columns
                break
    return df


def clean_student_name(name):
    """Очистка ФИО от служебной информации"""
    if pd.isna(name):
        return None

    name_str = str(name).strip()

    # Паттерны для исключения (служебная информация)
    exclude_patterns = [
        r'^класс\s*\d', r'^классы?$', r'^итого', r'^всего',
        r'^средний', r'^ср\.?', r'^общий', r'^сумма',
        r'^\d+$', r'^ученик', r'^студент', r'^группа',
        r'^параллель', r'^школа', r'^классный руководитель'
    ]

    # Проверяем на служебную информацию
    for pattern in exclude_patterns:
        if re.search(pattern, name_str, re.IGNORECASE):
            return None

    # Проверяем, что строка содержит хотя бы одну букву
    if not any(c.isalpha() for c in name_str):
        return None

    # Проверяем, что это не просто номер
    if name_str.replace('.', '').replace(',', '').isdigit():
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

    # Группируем по ФИО и объединяем данные
    grouped = df.groupby(name_column).agg({
        col: lambda x: pd.Series(x).fillna(method='ffill').iloc[-1] if col != name_column else x.iloc[0]
        for col in df.columns if col != name_column
    })

    return grouped.reset_index()


def load_file(uploaded_file):
    """Загрузка файла с определением формата"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8', skipinitialspace=True)
        else:
            df = pd.read_excel(uploaded_file, header=None)

        # Обработка пустых первых строк
        df = extract_header_names(df)

        return df
    except Exception as e:
        st.error(f"Ошибка при загрузке файла: {e}")
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


def parse_grades(df, grade_columns=None):
    """Преобразование оценок в числовой формат"""
    grades_df = df.copy()

    if grade_columns is None:
        grade_columns = []
        # Поиск колонок с оценками
        for col in grades_df.columns:
            if grades_df[col].dtype == 'object' or grades_df[col].dtype == 'float64':
                sample_vals = grades_df[col].dropna().head(10).astype(str).str.lower()
                # Проверяем, содержат ли значения оценки
                if any(val in ['2', '3', '4', '5', 'н', 'отсутствовал'] for val in sample_vals):
                    grade_columns.append(col)

    if not grade_columns:
        return pd.DataFrame(), []

    # Преобразование в числовой формат
    numeric_grades = pd.DataFrame()
    for col in grade_columns:
        numeric_grades[col] = grades_df[col].apply(convert_grade_to_number)

    return numeric_grades, grade_columns


def get_detailed_statistics(grades_df, class_info=None):
    """Получение детальной статистики"""
    stats = {}

    for student in grades_df.index:
        student_grades = grades_df.loc[student].dropna()

        if len(student_grades) > 0:
            student_class = class_info.get(student, "Не распределен") if class_info else "Не распределен"

            stats[student] = {
                'ФИО': student,
                'Класс': student_class,
                'Средний балл': student_grades.mean(),
                'Медиана': student_grades.median(),
                'Мода': student_grades.mode().iloc[0] if not student_grades.mode().empty else np.nan,
                'Мин. оценка': student_grades.min(),
                'Макс. оценка': student_grades.max(),
                'Станд. отклонение': student_grades.std(),
                'Кол-во оценок': len(student_grades),
                'Кол-во пропусков': grades_df.loc[student].isna().sum(),
                '% пропусков': (grades_df.loc[student].isna().sum() / len(grades_df.columns)) * 100,
                'Успеваемость (%)': (student_grades >= 3).sum() / len(student_grades) * 100,
                'Качество знаний (%)': (student_grades >= 4).sum() / len(student_grades) * 100,
                'Оценка 5': (student_grades == 5).sum(),
                'Оценка 4': (student_grades == 4).sum(),
                'Оценка 3': (student_grades == 3).sum(),
                'Оценка 2': (student_grades == 2).sum(),
            }

    return pd.DataFrame.from_dict(stats, orient='index')


# Боковое меню
with st.sidebar:
    st.title("📚 Навигация")
    page = st.radio(
        "Выберите раздел",
        ["Анализ текущей успеваемости", "Анализ экзаменов", "Сравнение экзаменов", "Статистика по классам"]
    )
    st.session_state.current_page = page

    st.markdown("---")
    st.markdown("""
    ### 📊 Быстрая статистика
    """)

# Основное содержимое
if st.session_state.current_page == "Анализ текущей успеваемости":
    st.title("📊 Анализ текущей успеваемости")
    st.markdown(f"*Разработчик: {__author__}*")

    # Загрузка файла
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_file = st.file_uploader(
            "Загрузите файл с оценками (CSV или Excel)",
            type=['csv', 'xlsx', 'xls']
        )

    if uploaded_file is not None:
        df = load_file(uploaded_file)

        if df is not None:
            st.subheader("Предпросмотр данных")
            st.dataframe(df.head(10))

            # Настройка анализа
            st.subheader("⚙️ Настройка анализа")

            col1, col2, col3 = st.columns(3)
            with col1:
                name_column = st.selectbox(
                    "Выберите колонку с ФИО учеников",
                    options=['Не выбрано'] + list(df.columns)
                )

            with col2:
                class_column = st.selectbox(
                    "Выберите колонку с классами (или оставьте пустым)",
                    options=['Нет колонки с классами'] + list(df.columns)
                )

            with col3:
                if st.checkbox("Назначить классы вручную"):
                    manual_class = st.text_input("Введите класс для всех учеников", "")
                else:
                    manual_class = None

            if name_column != 'Не выбрано':
                # Очистка ФИО от служебной информации
                df['clean_name'] = df[name_column].apply(clean_student_name)
                df_clean = df.dropna(subset=['clean_name']).copy()
                df_clean = df_clean.set_index('clean_name')

                # Сбор информации о классах
                class_info = {}
                if class_column != 'Нет колонки с классами':
                    for idx, row in df_clean.iterrows():
                        class_info[idx] = str(row[class_column])
                elif manual_class:
                    for idx in df_clean.index:
                        class_info[idx] = manual_class
                else:
                    # Автоматическое определение класса из ФИО
                    for idx in df_clean.index:
                        class_info[idx] = extract_class_info(idx)

                # Объединение дублирующихся учеников
                if st.checkbox("Объединить данные по дублирующимся ученикам", value=True):
                    df_clean = df_clean.groupby(df_clean.index).agg({
                        col: lambda x: x.dropna().iloc[0] if not x.dropna().empty else np.nan
                        for col in df_clean.columns
                    })

                # Выбор колонок с оценками
                st.subheader("📝 Выбор колонок с оценками")

                all_columns = list(df_clean.columns)
                grade_columns = st.multiselect(
                    "Выберите колонки, содержащие оценки",
                    options=all_columns
                )

                if grade_columns or st.button("Автоопределение оценок"):
                    if not grade_columns:
                        numeric_grades, grade_columns = parse_grades(df_clean)
                    else:
                        numeric_grades, _ = parse_grades(df_clean, grade_columns)

                    if not numeric_grades.empty:
                        # Получение детальной статистики
                        detailed_stats = get_detailed_statistics(numeric_grades, class_info)

                        # Общая статистика
                        st.header("📈 Общая статистика")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            avg_class = detailed_stats['Средний балл'].mean()
                            st.metric("Средний балл класса", f"{avg_class:.2f}")
                        with col2:
                            st.metric("Всего учеников", len(detailed_stats))
                        with col3:
                            total_grades = numeric_grades.count().sum()
                            st.metric("Всего оценок", total_grades)
                        with col4:
                            quality = (detailed_stats['Качество знаний (%)'] > 50).sum()
                            st.metric("Качественно успевающих",
                                      f"{quality} ({quality / len(detailed_stats) * 100:.1f}%)")

                        # Распределение по среднему баллу
                        st.subheader("📊 Распределение учеников по среднему баллу")

                        fig = px.histogram(
                            detailed_stats,
                            x='Средний балл',
                            nbins=20,
                            title='Гистограмма распределения средних баллов',
                            color_discrete_sequence=['#636EFA']
                        )
                        fig.add_vline(x=3.0, line_dash="dash", line_color="red", annotation_text="Порог 3.0")
                        fig.add_vline(x=3.5, line_dash="dash", line_color="orange", annotation_text="Порог 3.5")
                        fig.add_vline(x=4.0, line_dash="dash", line_color="green", annotation_text="Порог 4.0")
                        st.plotly_chart(fig, use_container_width=True)

                        # Топ учеников
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("🏆 Топ-10 лучших учеников")
                            top_students = detailed_stats.nlargest(10, 'Средний балл')[
                                ['ФИО', 'Класс', 'Средний балл', 'Качество знаний (%)']]
                            st.dataframe(top_students, use_container_width=True)

                        with col2:
                            st.subheader("⚠️ Топ-10 учеников с проблемами")
                            problem_students = detailed_stats.nsmallest(10, 'Средний балл')[
                                ['ФИО', 'Класс', 'Средний балл', 'Кол-во пропусков', '% пропусков']]
                            st.dataframe(problem_students, use_container_width=True)

                        # Статистика по классам
                        if class_column != 'Нет колонки с классами' or manual_class:
                            st.subheader("🏫 Статистика по классам")

                            class_stats = detailed_stats.groupby('Класс').agg({
                                'Средний балл': ['mean', 'count'],
                                'Качество знаний (%)': 'mean',
                                'Успеваемость (%)': 'mean'
                            }).round(2)

                            class_stats.columns = ['Средний балл', 'Кол-во учеников', 'Качество знаний %',
                                                   'Успеваемость %']
                            st.dataframe(class_stats, use_container_width=True)

                            # Сравнение классов
                            fig = px.bar(
                                class_stats.reset_index(),
                                x='Класс',
                                y='Средний балл',
                                title='Сравнение средних баллов по классам',
                                color='Класс'
                            )
                            st.plotly_chart(fig, use_container_width=True)

                        # Круговая диаграмма распределения оценок
                        st.subheader("🥧 Распределение всех оценок")

                        grade_dist = pd.Series({
                            '5': numeric_grades[numeric_grades == 5].count().sum(),
                            '4': numeric_grades[numeric_grades == 4].count().sum(),
                            '3': numeric_grades[numeric_grades == 3].count().sum(),
                            '2': numeric_grades[numeric_grades == 2].count().sum(),
                            'Пропуски': numeric_grades.isna().sum().sum()
                        })

                        fig = px.pie(
                            values=grade_dist.values,
                            names=grade_dist.index,
                            title='Распределение оценок по всему классу',
                            color_discrete_sequence=px.colors.qualitative.Set3
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Детальная таблица статистики
                        st.subheader("📋 Детальная статистика по ученикам")
                        st.dataframe(detailed_stats, use_container_width=True)

                        # Аналитика по конкретному ученику
                        st.header("👤 Аналитика по ученику")

                        selected_student = st.selectbox(
                            "Выберите ученика",
                            options=detailed_stats['ФИО'].tolist()
                        )

                        if selected_student:
                            student_data = detailed_stats[detailed_stats['ФИО'] == selected_student].iloc[0]
                            student_grades = numeric_grades.loc[selected_student].dropna()

                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("Средний балл", f"{student_data['Средний балл']:.2f}")
                            with col2:
                                st.metric("Качество знаний", f"{student_data['Качество знаний (%)']:.1f}%")
                            with col3:
                                st.metric("Всего оценок", student_data['Кол-во оценок'])
                            with col4:
                                st.metric("Пропуски", f"{student_data['% пропусков']:.1f}%")

                            # Динамика оценок
                            if len(student_grades) > 1:
                                fig = make_subplots(
                                    rows=2, cols=1,
                                    subplot_titles=('Динамика оценок', 'Скользящее среднее (3 оценки)'),
                                    vertical_spacing=0.15
                                )

                                fig.add_trace(
                                    go.Scatter(x=list(range(1, len(student_grades) + 1)),
                                               y=student_grades.values,
                                               mode='lines+markers',
                                               name='Оценки'),
                                    row=1, col=1
                                )

                                # Скользящее среднее
                                if len(student_grades) >= 3:
                                    rolling_mean = student_grades.rolling(3).mean()
                                    fig.add_trace(
                                        go.Scatter(x=list(range(1, len(rolling_mean) + 1)),
                                                   y=rolling_mean.values,
                                                   mode='lines',
                                                   name='Скользящее среднее',
                                                   line=dict(color='red', dash='dash')),
                                        row=2, col=1
                                    )

                                fig.update_layout(height=600)
                                st.plotly_chart(fig, use_container_width=True)

                            # Радар успеваемости
                            categories = ['Математика', 'Русский язык', 'Литература',
                                          'История', 'Биология', 'Физика']
                            if len(student_grades) >= len(categories):
                                fig = go.Figure(data=go.Scatterpolar(
                                    r=student_grades.values[:len(categories)],
                                    theta=categories,
                                    fill='toself'
                                ))
                                fig.update_layout(
                                    polar=dict(
                                        radialaxis=dict(
                                            visible=True,
                                            range=[0, 5]
                                        )),
                                    showlegend=False,
                                    title="Профиль успеваемости по предметам"
                                )
                                st.plotly_chart(fig, use_container_width=True)

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
            st.dataframe(df.head())

            st.subheader("⚙️ Настройка анализа экзамена")

            col1, col2, col3 = st.columns(3)
            with col1:
                name_column = st.selectbox(
                    "Колонка с ФИО учеников",
                    options=['Не выбрано'] + list(df.columns),
                    key="exam_name_col"
                )

            with col2:
                class_column = st.selectbox(
                    "Колонка с классами",
                    options=['Нет колонки с классами'] + list(df.columns),
                    key="exam_class_col"
                )

            with col3:
                total_score_column = st.selectbox(
                    "Колонка с суммой баллов",
                    options=['Нет колонки с суммой'] + list(df.columns),
                    key="exam_total_col"
                )

            if name_column != 'Не выбрано':
                # Очистка ФИО
                df['clean_name'] = df[name_column].apply(clean_student_name)
                df = df.dropna(subset=['clean_name'])
                df = df.set_index('clean_name')

                # Выбор колонок с баллами
                question_columns = st.multiselect(
                    "Выберите колонки с баллами за задания",
                    options=list(df.columns)
                )

                if question_columns:
                    exam_df = df[question_columns].copy()

                    # Добавление информации о классах
                    if class_column != 'Нет колонки с классами':
                        exam_df['Класс'] = df[class_column]

                    if total_score_column != 'Нет колонки с суммой':
                        exam_df['Сумма_баллов'] = df[total_score_column]

                    # Сохранение в сессию
                    exam_name = st.text_input("Название экзамена",
                                              f"Экзамен {datetime.now().strftime('%Y-%m-%d')}")
                    if st.button("💾 Сохранить данные экзамена"):
                        st.session_state.exam_data[exam_name] = exam_df
                        st.success(f"Данные экзамена '{exam_name}' сохранены!")

                    # Аналитика
                    st.header("📊 Детальная аналитика по экзамену")

                    # Общая статистика
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Всего учеников", len(exam_df))
                    with col2:
                        if 'Сумма_баллов' in exam_df.columns:
                            st.metric("Средний балл", f"{exam_df['Сумма_баллов'].mean():.2f}")
                    with col3:
                        st.metric("Всего заданий", len(question_columns))
                    with col4:
                        if 'Сумма_баллов' in exam_df.columns:
                            max_score = exam_df['Сумма_баллов'].max()
                            st.metric("Макс. балл", f"{max_score:.2f}")

                    # Статистика по заданиям
                    st.subheader("📋 Статистика по заданиям")

                    task_stats = pd.DataFrame({
                        'Задание': question_columns,
                        'Средний балл': exam_df[question_columns].mean().values,
                        'Медиана': exam_df[question_columns].median().values,
                        'Максимум': exam_df[question_columns].max().values,
                        'Минимум': exam_df[question_columns].min().values,
                        'Стд. отклонение': exam_df[question_columns].std().values,
                        '% выполнения': (exam_df[question_columns] > 0).mean().values * 100
                    })

                    st.dataframe(task_stats, use_container_width=True)

                    # Визуализация сложности заданий
                    fig = make_subplots(
                        rows=2, cols=2,
                        subplot_titles=('Средний балл по заданиям', 'Процент выполнения',
                                        'Распределение баллов', 'Ящик с усами'),
                        specs=[[{'type': 'bar'}, {'type': 'bar'}],
                               [{'type': 'histogram'}, {'type': 'box'}]]
                    )

                    fig.add_trace(
                        go.Bar(x=question_columns, y=task_stats['Средний балл'],
                               name='Средний балл', marker_color='blue'),
                        row=1, col=1
                    )

                    fig.add_trace(
                        go.Bar(x=question_columns, y=task_stats['% выполнения'],
                               name='% выполнения', marker_color='green'),
                        row=1, col=2
                    )

                    all_scores = exam_df[question_columns].values.flatten()
                    all_scores = all_scores[~np.isnan(all_scores)]

                    fig.add_trace(
                        go.Histogram(x=all_scores, nbinsx=20, name='Распределение'),
                        row=2, col=1
                    )

                    fig.add_trace(
                        go.Box(y=all_scores, name='Баллы'),
                        row=2, col=2
                    )

                    fig.update_layout(height=800, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

                    # Топ учеников
                    if 'Сумма_баллов' in exam_df.columns:
                        st.subheader("🏆 Рейтинг учеников")

                        top_n = st.slider("Количество учеников в рейтинге", 5, 30, 10)

                        ranking = exam_df[['Сумма_баллов']].copy()
                        if 'Класс' in exam_df.columns:
                            ranking['Класс'] = exam_df['Класс']

                        ranking = ranking.sort_values('Сумма_баллов', ascending=False)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.write("**Лучшие ученики:**")
                            st.dataframe(ranking.head(top_n), use_container_width=True)

                        with col2:
                            st.write("**Ученики, требующие внимания:**")
                            st.dataframe(ranking.tail(top_n), use_container_width=True)

elif st.session_state.current_page == "Сравнение экзаменов":
    st.title("🔄 Сравнение экзаменов")
    st.markdown(f"*Разработчик: {__author__}*")

    if len(st.session_state.exam_data) < 2:
        st.warning("⚠️ Для сравнения необходимо загрузить минимум 2 экзамена в разделе 'Анализ экзаменов'")
    else:
        # Выбор экзаменов
        col1, col2 = st.columns(2)
        with col1:
            exam1 = st.selectbox(
                "Выберите первый экзамен",
                options=list(st.session_state.exam_data.keys())
            )
        with col2:
            exam2 = st.selectbox(
                "Выберите второй экзамен",
                options=list(st.session_state.exam_data.keys()),
                index=1 if len(st.session_state.exam_data) > 1 else 0
            )

        if exam1 and exam2 and exam1 != exam2:
            df1 = st.session_state.exam_data[exam1]
            df2 = st.session_state.exam_data[exam2]

            # Сравнительная статистика
            st.header("📊 Сравнительная статистика")

            # Метрики
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                mean1 = df1.mean().mean()
                mean2 = df2.mean().mean()
                st.metric(
                    "Средний балл",
                    f"{mean1:.2f}",
                    f"{(mean1 - mean2):.2f}",
                    delta_color="normal"
                )
            with col2:
                median1 = df1.median().median()
                median2 = df2.median().median()
                st.metric(
                    "Медианный балл",
                    f"{median1:.2f}",
                    f"{(median1 - median2):.2f}"
                )
            with col3:
                max1 = df1.max().max()
                max2 = df2.max().max()
                st.metric(
                    "Максимальный балл",
                    f"{max1:.2f}",
                    f"{(max1 - max2):.2f}"
                )
            with col4:
                std1 = df1.std().std()
                std2 = df2.std().std()
                st.metric(
                    "Стандартное отклонение",
                    f"{std1:.2f}",
                    f"{(std1 - std2):.2f}"
                )

            # График сравнения
            st.subheader("📈 Сравнение распределений")

            # Создаем DataFrame для сравнения
            common_columns = set(df1.select_dtypes(include=[np.number]).columns) & \
                             set(df2.select_dtypes(include=[np.number]).columns)

            if common_columns:
                comparison_df = pd.DataFrame({
                    exam1: df1[list(common_columns)].mean(),
                    exam2: df2[list(common_columns)].mean()
                })

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    name=exam1,
                    x=comparison_df.index,
                    y=comparison_df[exam1],
                    marker_color='#636EFA',
                    text=comparison_df[exam1].round(2),
                    textposition='outside'
                ))
                fig.add_trace(go.Bar(
                    name=exam2,
                    x=comparison_df.index,
                    y=comparison_df[exam2],
                    marker_color='#EF553B',
                    text=comparison_df[exam2].round(2),
                    textposition='outside'
                ))

                fig.update_layout(
                    title="Сравнение средних баллов по заданиям",
                    xaxis_title="Задания",
                    yaxis_title="Средний балл",
                    barmode='group',
                    height=500
                )

                st.plotly_chart(fig, use_container_width=True)

                # Анализ изменений
                st.subheader("📉 Анализ изменений")

                diff = comparison_df[exam1] - comparison_df[exam2]

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

                # Диаграмма рассеяния
                st.subheader("🎯 Корреляция результатов")

                # Общие ученики
                common_students = set(df1.index) & set(df2.index)
                if common_students:
                    student_comparison = pd.DataFrame({
                        'student': list(common_students),
                        exam1: [df1.loc[s].mean() if hasattr(df1.loc[s], 'mean') else df1.loc[s]
                                for s in common_students],
                        exam2: [df2.loc[s].mean() if hasattr(df2.loc[s], 'mean') else df2.loc[s]
                                for s in common_students]
                    })

                    fig = px.scatter(
                        student_comparison,
                        x=exam1,
                        y=exam2,
                        text='student',
                        title='Сравнение результатов учеников',
                        trendline="ols"
                    )
                    fig.update_traces(textposition='top center')
                    st.plotly_chart(fig, use_container_width=True)

elif st.session_state.current_page == "Статистика по классам":
    st.title("🏫 Статистика по классам")
    st.markdown(f"*Разработчик: {__author__}*")

    if not st.session_state.attendance_data:
        st.warning("Сначала загрузите данные в разделе 'Анализ текущей успеваемости'")
    else:
        st.write("Здесь будет отображаться статистика по классам...")

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
    """)

# Нижний колонтитул
st.markdown("---")
st.markdown(f"<div style='text-align: center'>© {__year__} {__author__}. Все права защищены.</div>",
            unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Настройка страницы
st.set_page_config(page_title="Анализ успеваемости учеников", layout="wide")

# Инициализация сессионных переменных
if 'attendance_data' not in st.session_state:
    st.session_state.attendance_data = None
if 'exam_data' not in st.session_state:
    st.session_state.exam_data = {}
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Анализ текущей успеваемости"

