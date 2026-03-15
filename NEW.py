import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from datetime import datetime
import io

# Настройка страницы
st.set_page_config(page_title="Анализ успеваемости учеников", layout="wide")

# Инициализация сессионных переменных
if 'attendance_data' not in st.session_state:
    st.session_state.attendance_data = None
if 'exam_data' not in st.session_state:
    st.session_state.exam_data = {}
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Анализ текущей успеваемости"


def load_file(uploaded_file):
    """Загрузка файла с определением формата"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        return df
    except Exception as e:
        st.error(f"Ошибка при загрузке файла: {e}")
        return None


def parse_grades(df):
    """Преобразование оценок в числовой формат"""
    grades_df = df.copy()
    grade_columns = []

    # Поиск колонок с оценками
    for col in grades_df.columns:
        if grades_df[col].dtype == 'object' or grades_df[col].dtype == 'float64':
            # Проверяем, содержит ли колонка оценки
            unique_vals = grades_df[col].dropna().unique()
            if len(unique_vals) > 0:
                # Проверяем, что значения похожи на оценки
                possible_grades = [2, 3, 4, 5, '2', '3', '4', '5', 'н', 'Н', 'н/а']
                if any(str(val) in possible_grades for val in unique_vals):
                    grade_columns.append(col)

    if not grade_columns:
        st.warning("Не удалось автоматически определить колонки с оценками. Пожалуйста, выберите их вручную.")
        return df, []

    # Преобразование в числовой формат
    numeric_grades = pd.DataFrame()
    for col in grade_columns:
        numeric_grades[col] = grades_df[col].apply(lambda x: convert_grade_to_number(x))

    return numeric_grades, grade_columns


def convert_grade_to_number(grade):
    """Преобразование оценки в число"""
    if pd.isna(grade) or grade == 'н' or grade == 'Н' or grade == 'н/а':
        return np.nan
    try:
        return float(grade)
    except:
        return np.nan


def get_student_stats(grades_df, student_name):
    """Получение статистики по конкретному ученику"""
    if student_name in grades_df.index:
        student_grades = grades_df.loc[student_name]
        valid_grades = student_grades.dropna()

        stats = {
            'mean': valid_grades.mean() if len(valid_grades) > 0 else 0,
            'median': valid_grades.median() if len(valid_grades) > 0 else 0,
            'count': len(valid_grades),
            'absent_count': student_grades.isna().sum(),
            'grades_distribution': valid_grades.value_counts().sort_index(),
            'grades_trend': valid_grades.values if len(valid_grades) > 1 else []
        }
        return stats
    return None


def identify_problem_students(grades_df, threshold=3.0, min_grades=3):
    """Выявление учеников с проблемами"""
    problems = []

    for student in grades_df.index:
        student_grades = grades_df.loc[student].dropna()

        if len(student_grades) >= min_grades:
            avg_grade = student_grades.mean()
            recent_grades = student_grades.tail(3).mean() if len(student_grades) >= 3 else avg_grade

            problems_found = []

            if avg_grade < threshold:
                problems_found.append(f"Низкий средний балл: {avg_grade:.2f}")

            if recent_grades < avg_grade * 0.8:
                problems_found.append("Падение успеваемости")

            if student_grades.isna().sum() > len(student_grades) * 0.3:
                problems_found.append("Много пропусков")

            if problems_found:
                problems.append({
                    'student': student,
                    'avg_grade': avg_grade,
                    'recent_avg': recent_grades,
                    'problems': problems_found,
                    'grades': student_grades.values
                })

    return problems


# Боковое меню
with st.sidebar:
    st.title("Навигация")
    page = st.radio(
        "Выберите раздел",
        ["Анализ текущей успеваемости", "Анализ экзаменов", "Сравнение экзаменов"]
    )
    st.session_state.current_page = page

# Основное содержимое
if st.session_state.current_page == "Анализ текущей успеваемости":
    st.title("📊 Анализ текущей успеваемости")

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
            st.dataframe(df.head())

            # Ручной выбор колонок
            st.subheader("Настройка анализа")

            col1, col2 = st.columns(2)
            with col1:
                name_column = st.selectbox(
                    "Выберите колонку с именами учеников",
                    options=['Не выбрано'] + list(df.columns)
                )

            if name_column != 'Не выбрано':
                df = df.set_index(name_column)

                # Автоматическое определение колонок с оценками
                numeric_grades, auto_grade_columns = parse_grades(df)

                if auto_grade_columns:
                    st.success(f"Автоматически обнаружены колонки с оценками: {', '.join(auto_grade_columns)}")

                    if st.checkbox("Выбрать колонки вручную"):
                        grade_columns = st.multiselect(
                            "Выберите колонки с оценками",
                            options=list(df.columns),
                            default=auto_grade_columns
                        )
                    else:
                        grade_columns = auto_grade_columns

                    if grade_columns:
                        # Создаем DataFrame только с оценками
                        grades_df = df[grade_columns].applymap(convert_grade_to_number)

                        # Общая аналитика
                        st.header("📈 Общая аналитика")

                        # Статистика по классу
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Средний балл класса", f"{grades_df.mean().mean():.2f}")
                        with col2:
                            st.metric("Медианный балл", f"{grades_df.median().median():.2f}")
                        with col3:
                            st.metric("Всего оценок", grades_df.count().sum())
                        with col4:
                            st.metric("Пропусков", grades_df.isna().sum().sum())

                        # Визуализации
                        st.subheader("Распределение оценок")

                        # Подготовка данных для визуализации
                        all_grades = []
                        for student in grades_df.index:
                            for grade in grades_df.loc[student].dropna():
                                all_grades.append({'Ученик': student, 'Оценка': grade})

                        grades_viz_df = pd.DataFrame(all_grades)

                        if not grades_viz_df.empty:
                            # Гистограмма оценок
                            fig = px.histogram(
                                grades_viz_df,
                                x='Оценка',
                                title='Распределение оценок по классу',
                                nbins=20,
                                color_discrete_sequence=['#636EFA']
                            )
                            st.plotly_chart(fig, use_container_width=True)

                            # Тепловая карта успеваемости
                            st.subheader("Тепловая карта успеваемости")

                            # Адаптация размера под количество учеников
                            height = max(400, len(grades_df) * 20)

                            fig = px.imshow(
                                grades_df.values,
                                labels=dict(x="Задания/Даты", y="Ученики", color="Оценка"),
                                x=grades_df.columns,
                                y=grades_df.index,
                                aspect="auto",
                                color_continuous_scale='RdYlGn',
                                zmin=2, zmax=5,
                                height=height
                            )
                            fig.update_layout(title="Успеваемость по ученикам и заданиям")
                            st.plotly_chart(fig, use_container_width=True)

                            # Поиск учеников с проблемами
                            st.header("⚠️ Ученики с проблемами")

                            threshold = st.slider(
                                "Порог среднего балла для выявления проблем",
                                min_value=2.0,
                                max_value=4.0,
                                value=3.0,
                                step=0.1
                            )

                            problems = identify_problem_students(grades_df, threshold=threshold)

                            if problems:
                                for problem in problems:
                                    with st.expander(
                                            f"**{problem['student']}** - Средний балл: {problem['avg_grade']:.2f}"):
                                        st.write("**Проблемы:**")
                                        for p in problem['problems']:
                                            st.write(f"- {p}")

                                        # График динамики
                                        if len(problem['grades']) > 1:
                                            fig = px.line(
                                                x=range(1, len(problem['grades']) + 1),
                                                y=problem['grades'],
                                                title=f"Динамика оценок {problem['student']}",
                                                labels={'x': 'Задание №', 'y': 'Оценка'}
                                            )
                                            fig.update_layout(showlegend=False)
                                            st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.success("Учеников с проблемами не обнаружено!")

                            # Аналитика по конкретному ученику
                            st.header("👤 Аналитика по ученику")

                            selected_student = st.selectbox(
                                "Выберите ученика",
                                options=grades_df.index
                            )

                            if selected_student:
                                stats = get_student_stats(grades_df, selected_student)

                                if stats:
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("Средний балл", f"{stats['mean']:.2f}")
                                    with col2:
                                        st.metric("Медиана", f"{stats['median']:.2f}")
                                    with col3:
                                        st.metric("Всего оценок", stats['count'])
                                    with col4:
                                        st.metric("Пропусков", stats['absent_count'])

                                    # Распределение оценок ученика
                                    if not stats['grades_distribution'].empty:
                                        fig = px.pie(
                                            values=stats['grades_distribution'].values,
                                            names=stats['grades_distribution'].index,
                                            title=f"Распределение оценок {selected_student}"
                                        )
                                        st.plotly_chart(fig, use_container_width=True)

                                    # Динамика оценок
                                    if len(stats['grades_trend']) > 1:
                                        fig = px.line(
                                            x=range(1, len(stats['grades_trend']) + 1),
                                            y=stats['grades_trend'],
                                            title=f"Динамика оценок {selected_student}",
                                            labels={'x': 'Задание №', 'y': 'Оценка'}
                                        )
                                        st.plotly_chart(fig, use_container_width=True)

elif st.session_state.current_page == "Анализ экзаменов":
    st.title("📝 Анализ экзаменационных работ")

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

            st.subheader("Настройка анализа экзамена")

            col1, col2 = st.columns(2)
            with col1:
                name_column = st.selectbox(
                    "Колонка с именами",
                    options=['Не выбрано'] + list(df.columns),
                    key="exam_name_col"
                )

            with col2:
                total_score_column = st.selectbox(
                    "Колонка с суммой баллов (если есть)",
                    options=['Не выбрано'] + list(df.columns),
                    key="total_col"
                )

            if name_column != 'Не выбрано':
                df = df.set_index(name_column)

                # Выбор колонок с баллами за задания
                question_columns = st.multiselect(
                    "Выберите колонки с баллами за задания",
                    options=list(df.columns)
                )

                if question_columns:
                    exam_df = df[question_columns].copy()

                    # Если выбрана колонка с суммой, добавляем её отдельно
                    if total_score_column != 'Не выбрано' and total_score_column in df.columns:
                        exam_df['Сумма_баллов'] = df[total_score_column]

                    # Сохраняем в сессию
                    exam_name = st.text_input("Название экзамена", "Экзамен " + datetime.now().strftime("%Y-%m-%d"))
                    if st.button("Сохранить данные экзамена"):
                        st.session_state.exam_data[exam_name] = exam_df
                        st.success(f"Данные экзамена '{exam_name}' сохранены!")

                    # Аналитика
                    st.header("📊 Аналитика по экзамену")

                    # Статистика по вопросам
                    st.subheader("Статистика по заданиям")

                    question_stats = pd.DataFrame({
                        'Средний балл': exam_df[question_columns].mean(),
                        'Максимум': exam_df[question_columns].max(),
                        'Минимум': exam_df[question_columns].min(),
                        'Медиана': exam_df[question_columns].median(),
                        'Стандартное отклонение': exam_df[question_columns].std()
                    })

                    st.dataframe(question_stats)

                    # Визуализация сложности заданий
                    fig = px.bar(
                        question_stats,
                        y='Средний балл',
                        title='Средний балл по заданиям',
                        labels={'index': 'Задание', 'value': 'Средний балл'}
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Распределение общего балла
                    if total_score_column != 'Не выбрано':
                        fig = px.histogram(
                            exam_df,
                            x='Сумма_баллов',
                            title='Распределение общего балла',
                            nbins=20
                        )
                        st.plotly_chart(fig, use_container_width=True)

                        # Топ учеников
                        st.subheader("Топ учеников")
                        top_n = st.slider("Количество учеников в топе", 5, 20, 10)
                        top_students = exam_df.nlargest(top_n, 'Сумма_баллов')[['Сумма_баллов']]
                        st.dataframe(top_students)

else:  # Сравнение экзаменов
    st.title("🔄 Сравнение экзаменов")

    if len(st.session_state.exam_data) < 2:
        st.warning("Для сравнения необходимо загрузить минимум 2 экзамена в разделе 'Анализ экзаменов'")
    else:
        # Выбор экзаменов для сравнения
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

            # Общая статистика
            st.header("Сравнительная статистика")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Средний балл",
                    f"{df1.mean().mean():.2f}",
                    f"{(df1.mean().mean() - df2.mean().mean()):.2f}"
                )
            with col2:
                st.metric(
                    "Медианный балл",
                    f"{df1.median().median():.2f}",
                    f"{(df1.median().median() - df2.median().median()):.2f}"
                )
            with col3:
                st.metric(
                    "Максимальный балл",
                    f"{df1.max().max():.2f}",
                    f"{(df1.max().max() - df2.max().max()):.2f}"
                )

            # Сравнение распределений
            st.subheader("Сравнение распределений")

            # Создаем DataFrame для сравнения
            comparison_df = pd.DataFrame({
                exam1: df1.mean(),
                exam2: df2.mean()
            })

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=exam1,
                x=comparison_df.index,
                y=comparison_df[exam1],
                marker_color='blue'
            ))
            fig.add_trace(go.Bar(
                name=exam2,
                x=comparison_df.index,
                y=comparison_df[exam2],
                marker_color='red'
            ))

            fig.update_layout(
                title="Сравнение средних баллов по заданиям",
                xaxis_title="Задания",
                yaxis_title="Средний балл",
                barmode='group'
            )

            st.plotly_chart(fig, use_container_width=True)

            # Анализ проблемных мест
            st.subheader("Анализ изменений")

            diff = comparison_df[exam1] - comparison_df[exam2]

            col1, col2 = st.columns(2)
            with col1:
                st.write("**Задания, где стало лучше:**")
                better = diff[diff > 0].sort_values(ascending=False)
                if not better.empty:
                    for idx, val in better.items():
                        st.write(f"✅ {idx}: улучшение на {val:.2f}")
                else:
                    st.write("Нет улучшений")

            with col2:
                st.write("**Задания, где стало хуже:**")
                worse = diff[diff < 0].sort_values()
                if not worse.empty:
                    for idx, val in worse.items():
                        st.write(f"❌ {idx}: ухудшение на {abs(val):.2f}")
                else:
                    st.write("Нет ухудшений")

# Инструкция по использованию
with st.sidebar:
    st.markdown("---")
    st.header("📖 Инструкция")
    st.markdown("""
    1. **Анализ текущей успеваемости**
       - Загрузите файл с оценками (2-5, н/н)
       - При необходимости выберите нужные колонки вручную
       - Просмотрите общую статистику и графики
       - Изучите проблемных учеников

    2. **Анализ экзаменов**
       - Загрузите файл с баллами за экзамен
       - Укажите колонки с заданиями
       - Сохраните несколько экзаменов для сравнения

    3. **Сравнение экзаменов**
       - Выберите два сохраненных экзамена
       - Проанализируйте изменения
    """)
    # Альтернативный вариант с автоматическим запуском
    if __name__ == "__main__":
        import os
        import sys

        # Проверяем, запущен ли скрипт через streamlit
        if not hasattr(sys, 'argv') or len(sys.argv) > 0 and 'streamlit' not in sys.argv[0]:
            print("\n" + "=" * 50)
            print("⚠️  НЕПРАВИЛЬНЫЙ ЗАПУСК")
            print("=" * 50)
            print("\nЭто приложение должно запускаться через Streamlit.")
            print("\n✅ Правильная команда для запуска:")
            print(f"   streamlit run {os.path.basename(__file__)}")
            print("\n📋 Или используйте:")
            print("   python -m streamlit run", os.path.basename(__file__))
            print("\n" + "=" * 50)

            # Попытка автоматического запуска
            response = input("\nХотите автоматически запустить приложение через Streamlit? (да/нет): ")
            if response.lower() in ['да', 'y', 'yes', 'д']:
                os.system(f'streamlit run {os.path.basename(__file__)}')
            else:
                print("\nЗапуск отменен. Используйте указанную выше команду для запуска.")# Альтернативный вариант с автоматическим запуском
if __name__ == "__main__":
    import os
    import sys

    # Проверяем, запущен ли скрипт через streamlit
    if not hasattr(sys, 'argv') or len(sys.argv) > 0 and 'streamlit' not in sys.argv[0]:
        print("\n" + "="*50)
        print("⚠️  НЕПРАВИЛЬНЫЙ ЗАПУСК")
        print("="*50)
        print("\nЭто приложение должно запускаться через Streamlit.")
        print("\n✅ Правильная команда для запуска:")
        print(f"   streamlit run {os.path.basename(__file__)}")
        print("\n📋 Или используйте:")
        print("   python -m streamlit run", os.path.basename(__file__))
        print("\n" + "="*50)

        # Попытка автоматического запуска
        response = input("\nХотите автоматически запустить приложение через Streamlit? (да/нет): ")
        if response.lower() in ['да', 'y', 'yes', 'д']:
            os.system(f'streamlit run {os.path.basename(__file__)}')
        else:
            print("\nЗапуск отменен. Используйте указанную выше команду для запуска.")