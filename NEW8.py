import streamlit as st
import sys
import subprocess


# Проверка наличия необходимых библиотек
def check_imports():
    """Проверяет наличие всех необходимых библиотек"""
    required_packages = {
        'pandas': 'pandas',
        'numpy': 'numpy',
        'plotly': 'plotly',
        'sklearn': 'scikit-learn'
    }

    missing_packages = []

    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)

    if missing_packages:
        st.warning(f"⚠️ Отсутствуют библиотеки: {', '.join(missing_packages)}")
        st.info("Пытаюсь установить...")

        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                st.success(f"✅ {package} установлен")
            except:
                st.error(f"❌ Не удалось установить {package}")

        st.rerun()

    return True


# Запускаем проверку
check_imports()

# Теперь импортируем все библиотеки
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import re
import os

# Импортируем sklearn с проверкой
try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler

    SKLEARN_AVAILABLE = True
except ImportError as e:
    st.error(f"❌ Ошибка импорта scikit-learn: {e}")
    st.info("Пожалуйста, убедитесь, что scikit-learn установлен: pip install scikit-learn")
    SKLEARN_AVAILABLE = False


    # Создаем заглушку для LinearRegression
    class LinearRegression:
        def __init__(self):
            pass

        def fit(self, X, y):
            pass

        def predict(self, X):
            return np.zeros(len(X))


# Остальной код вашей программы...


def is_numeric_column(series, threshold=0.8):
    """Проверяет, является ли колонка числовой (номера учеников)"""
    try:
        # Пробуем преобразовать в числа
        numeric_vals = pd.to_numeric(series, errors='coerce')
        # Если больше threshold значений успешно преобразованы в числа
        if numeric_vals.notna().sum() / len(series) > threshold:
            # Проверяем, что это скорее всего номера (целые числа в разумном диапазоне)
            if numeric_vals.dropna().apply(float.is_integer).all():
                return True
    except:
        pass
    return False


def identify_non_grade_columns(df):
    """Определяет колонки, которые точно не содержат оценки (возвращает список)"""
    non_grade_columns = []

    for col in df.columns:
        # Проверяем название колонки
        col_lower = str(col).lower()
        if any(word in col_lower for word in ['№', 'номер', 'id', 'п/п', '№ п/п', 'индекс']):
            non_grade_columns.append(col)
            continue

        # Проверяем содержимое колонки
        sample = df[col].dropna().head(20)
        if len(sample) > 0:
            # Если все значения - числа, но не 2-5, и это не текст
            if all(_is_number(str(x)) for x in sample):
                numeric_vals = pd.to_numeric(sample, errors='coerce')
                if not any(2 <= x <= 5 for x in numeric_vals if not pd.isna(x)):
                    non_grade_columns.append(col)

    return non_grade_columns

def get_columns_to_the_right(df, name_column):
    """Возвращает список колонок, которые находятся правее указанной колонки"""
    try:
        # Находим позицию колонки с ФИО
        col_position = df.columns.get_loc(name_column)
        # Берем все колонки правее
        columns_to_the_right = list(df.columns[col_position + 1:])
        return columns_to_the_right
    except Exception as e:
        st.warning(f"Ошибка при определении колонок правее: {e}")
        return list(df.columns)

def debug_dataframe(df, name="DataFrame"):
    """Отладочная функция для проверки DataFrame"""
    st.write(f"--- Отладка: {name} ---")
    st.write(f"Тип: {type(df)}")
    if df is not None:
        st.write(f"Размер: {df.shape}")
        st.write(f"Колонки: {list(df.columns)}")
        st.write(f"Индекс: {list(df.index[:5])}...")
        st.write(f"Типы данных:\n{df.dtypes}")
        st.write(f"Первые 3 строки:\n{df.head(3)}")
    else:
        st.write("DataFrame is None")
    st.write("--- Конец отладки ---")

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
    """Преобразование оценок в числовой формат с проверкой допустимых значений"""
    grades_df = df.copy()

    # Допустимые значения оценок
    VALID_ABSENT = {'н', 'н/а', 'отсутствовал', '-', ''}
    VALID_NUMERIC = {2, 3, 4, 5}

    if grade_columns is None:
        grade_columns = []
        # Поиск колонок с оценками
        for col in grades_df.columns:
            # Получаем все значения в колонке
            all_vals = grades_df[col].dropna()
            if len(all_vals) == 0:
                continue

            # Проверяем, что хотя бы некоторые значения похожи на оценки
            grade_count = 0
            for val in all_vals.head(20):  # Проверяем первые 20 значений
                val_str = str(val).strip().lower()
                if val_str in ['2', '3', '4', '5']:
                    grade_count += 1
                elif val_str in VALID_ABSENT:
                    grade_count += 1
                elif _is_number(val_str) and float(val_str) in VALID_NUMERIC:
                    grade_count += 1

            # Если больше 30% значений похожи на оценки, считаем колонку колонкой с оценками
            if grade_count / len(all_vals.head(20)) > 0.3:
                grade_columns.append(col)

    if not grade_columns:
        st.warning("⚠️ Не удалось найти колонки с оценками. Убедитесь, что в файле есть оценки 2,3,4,5 или 'н'")
        return pd.DataFrame(), []

    # Преобразование в числовой формат
    numeric_grades = pd.DataFrame()

    for col in grade_columns:
        # Преобразуем каждое значение
        valid_grades = []
        for value in grades_df[col]:
            converted = convert_grade_to_number_safe(value)
            valid_grades.append(converted)

        numeric_grades[col] = valid_grades

    return numeric_grades, grade_columns


def convert_grade_to_number_safe(grade):
    """Безопасное преобразование оценки в число"""
    if pd.isna(grade):
        return np.nan

    grade_str = str(grade).strip().lower()

    # Проверка на отметку об отсутствии
    if grade_str in ['н', 'н/а', 'отсутствовал', '-', '']:
        return np.nan

    # Проверка на числовые значения
    try:
        grade_float = float(grade_str)
        # Проверяем, что число в допустимом диапазоне
        if 2 <= grade_float <= 5:
            return grade_float
        else:
            return np.nan  # Число вне диапазона
    except ValueError:
        return np.nan  # Не число


def convert_grade_to_number_with_check(grade):
    """Преобразование оценки в число с проверкой допустимости"""
    if pd.isna(grade):
        return np.nan

    grade_str = str(grade).strip().lower()

    # Проверка на отметку об отсутствии
    if grade_str in ['н', 'н/а', 'отсутствовал', '-', '']:
        return np.nan

    # Проверка на числовые значения
    try:
        grade_float = float(grade_str)
        # Проверяем, что число - целое и в допустимом диапазоне
        if grade_float.is_integer() and 2 <= grade_float <= 5:
            return grade_float
        else:
            return 'invalid'  # Недопустимое числовое значение
    except ValueError:
        return 'invalid'  # Не число и не отметка об отсутствии


def _is_number(s):
    """Проверка, является ли строка числом"""
    try:
        float(s)
        return True
    except ValueError:
        return False


def convert_grade_to_number_with_check(grade):
    """Преобразование оценки в число с проверкой допустимости"""
    if pd.isna(grade):
        return np.nan

    grade_str = str(grade).strip().lower()

    # Проверка на отметку об отсутствии
    if grade_str in ['н', 'н/а', 'отсутствовал', '-', '']:
        return np.nan

    # Проверка на числовые значения
    try:
        grade_float = float(grade_str)
        # Проверяем, что число - целое и в допустимом диапазоне
        if grade_float.is_integer() and 2 <= grade_float <= 5:
            return grade_float
        else:
            return 'invalid'  # Недопустимое числовое значение
    except ValueError:
        return 'invalid'  # Не число и не отметка об отсутствии


def _is_number(s):
    """Проверка, является ли строка числом"""
    try:
        float(s)
        return True
    except ValueError:
        return False


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


def filter_valid_grades(grades_df):
    """Очистка ячеек с недопустимыми оценками (оставляет только 2-5 и пропуски)"""
    filtered_df = grades_df.copy()

    for col in filtered_df.columns:
        filtered_df[col] = filtered_df[col].apply(
            lambda x: x if (pd.isna(x) or (isinstance(x, (int, float)) and 2 <= x <= 5)) else np.nan
        )

    return filtered_df

def get_grades_statistics(grades_df):
    """Получение статистики по оценкам с учетом только допустимых значений"""
    # Фильтруем только допустимые оценки
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

    # Процентное соотношение
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
        invalid_color = "inverse" if validation['invalid_grades'] > 0 else "off"
        st.metric("❌ Недопустимых значений", validation['invalid_grades'])

    if validation['invalid_grades'] > 0:
        st.error(f"⚠️ Обнаружено {validation['invalid_grades']} недопустимых значений!")

        # Показываем примеры недопустимых значений
        if validation['invalid_positions']:
            st.write("**Примеры недопустимых значений:**")
            examples = pd.DataFrame(validation['invalid_positions'][:10])
            st.dataframe(examples, use_container_width=True)

            st.info("💡 Недопустимые значения будут автоматически преобразованы в пропуски")

    return validation['invalid_grades'] == 0


def get_detailed_statistics(grades_df, class_info=None):
    """Получение детальной статистики с обработкой ошибок"""
    try:
        # Проверка входных данных
        if grades_df is None or grades_df.empty:
            return pd.DataFrame()

        stats = []

        # Перебираем учеников по индексу (там должны быть ФИО)
        for student in grades_df.index:
            try:
                # Пропускаем пустые или NaN индексы
                if pd.isna(student) or str(student).strip() == '':
                    continue

                # Получаем оценки ученика
                student_grades = grades_df.loc[student]

                # Убираем пропуски
                valid_grades = student_grades.dropna()

                # Фильтруем только допустимые оценки (2-5)
                valid_numeric_grades = valid_grades[valid_grades.apply(
                    lambda x: isinstance(x, (int, float)) and 2 <= x <= 5
                )]

                if len(valid_numeric_grades) > 0:
                    # Получаем класс ученика
                    student_class = "Не распределен"
                    if class_info and isinstance(class_info, dict):
                        student_class = class_info.get(student, "Не распределен")

                    # Рассчитываем стандартное отклонение
                    std_dev = 0
                    if len(valid_numeric_grades) > 1:
                        std_dev = round(float(valid_numeric_grades.std()), 2)

                    # Создаем запись статистики
                    stats.append({
                        'ФИО': str(student),
                        'Класс': str(student_class),
                        'Средний балл': round(float(valid_numeric_grades.mean()), 2),
                        'Медиана': round(float(valid_numeric_grades.median()), 2),
                        'Мин. оценка': int(valid_numeric_grades.min()),
                        'Макс. оценка': int(valid_numeric_grades.max()),
                        'Станд. отклонение': std_dev,  # Добавляем стандартное отклонение
                        'Кол-во оценок': int(len(valid_numeric_grades)),
                        'Кол-во пропусков': int(student_grades.isna().sum()),
                        'Кол-во некорректных': int(len(valid_grades) - len(valid_numeric_grades)),
                        '% пропусков': round(float((student_grades.isna().sum() / len(grades_df.columns)) * 100),
                                             1) if len(grades_df.columns) > 0 else 0,
                        'Успеваемость (%)': round(
                            float((valid_numeric_grades >= 3).sum() / len(valid_numeric_grades) * 100), 1),
                        'Качество знаний (%)': round(
                            float((valid_numeric_grades >= 4).sum() / len(valid_numeric_grades) * 100), 1),
                    })
            except Exception as e:
                continue

        if stats:
            result_df = pd.DataFrame(stats)
            return result_df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Ошибка при получении статистики: {e}")
        return pd.DataFrame()

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

                # Сохраняем имена в отдельную переменную ДО любой фильтрации
                student_names = df_clean['clean_name'].astype(str).tolist()
                st.success(f"✅ Найдено {len(student_names)} учеников")

                # Показываем список учеников для проверки
                with st.expander("Показать список учеников"):
                    students_df = pd.DataFrame({
                        '№': range(1, len(student_names) + 1),
                        'ФИО': student_names
                    })
                    st.dataframe(students_df, use_container_width=True)
                    # Определяем колонки правее колонки с ФИО
                    columns_to_the_right = get_columns_to_the_right(df, name_column)
                    st.info(f"📐 Найдено {len(columns_to_the_right)} колонок правее колонки с ФИО")

                # Удаляем колонку с именами из данных (она больше не нужна для анализа)
                df_clean = df_clean.drop(columns=['clean_name'])

                # Вместо:
                # df_clean = filter_out_numeric_columns(df_clean)

                # Используйте:
                non_grade_columns = identify_non_grade_columns(df_clean)
                if non_grade_columns:
                    st.info(f"Обнаружены колонки без оценок: {', '.join(map(str, non_grade_columns))}")
                # НЕ УДАЛЯЕМ эти колонки, просто информируем пользователя
                # ВАЖНО: Устанавливаем индекс как имена учеников
                df_clean.index = student_names

                # Сбор информации о классах
                class_info = {}
                if class_column != 'Нет колонки с классами' and class_column in df.columns:
                    # Создаем словарь для быстрого поиска класса по имени
                    name_to_class = {}
                    for idx, row in df.iterrows():
                        clean_name = clean_student_name(row[name_column])
                        if clean_name and clean_name in student_names:
                            name_to_class[clean_name] = str(row[class_column]) if pd.notna(
                                row[class_column]) else "Не указан"

                    # Заполняем class_info для всех учеников
                    for name in student_names:
                        class_info[name] = name_to_class.get(name, "Не указан")

                elif manual_class:
                    for name in student_names:
                        class_info[name] = manual_class
                else:
                    # Автоматическое определение класса из ФИО
                    for name in student_names:
                        class_info[name] = extract_class_info(name)

                # Объединение дублирующихся учеников
                if st.checkbox("Объединить данные по дублирующимся ученикам", value=True):
                    # Группируем по индексу (именам)
                    df_clean = df_clean.groupby(df_clean.index).first()
                    # Обновляем список имен
                    student_names = df_clean.index.tolist()
                    st.info(f"После объединения дубликатов: {len(df_clean)} учеников")

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

                    # Убеждаемся, что индекс сохранился
                    if not numeric_grades.empty:
                        numeric_grades.index = student_names

                        # Проверка валидности оценок
                        st.subheader("🔍 Проверка качества данных")
                        is_valid = display_grades_validation(numeric_grades)

                        if not is_valid:
                            st.warning("⚠️ Обнаружены проблемы с данными. Выполняется автоматическая очистка...")
                            numeric_grades = filter_valid_grades(numeric_grades)
                            numeric_grades.index = student_names  # Восстанавливаем индекс
                            st.success("✅ Данные очищены от недопустимых значений")

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

                        # Круговая диаграмма распределения оценок
                        fig = px.pie(
                            values=[grade_stats['grade_5'], grade_stats['grade_4'],
                                    grade_stats['grade_3'], grade_stats['grade_2'], grade_stats['absences']],
                            names=['5 (Отлично)', '4 (Хорошо)', '3 (Удовл.)', '2 (Неуд.)', 'Пропуски'],
                            title='Распределение оценок (только 2,3,4,5 и отметки об отсутствии)',
                            color_discrete_sequence=['#2E7D32', '#1976D2', '#ED6C02', '#D32F2F', '#9E9E9E']
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        # Получение детальной статистики
                        st.subheader("📊 Детальная статистика")

                        try:
                            # Проверяем, что numeric_grades существует
                            if 'numeric_grades' not in locals() and 'numeric_grades' not in globals():
                                st.error("Ошибка: данные с оценками не найдены")
                                st.stop()

                            if numeric_grades is None or numeric_grades.empty:
                                st.warning("Нет данных для анализа")
                                st.stop()

                            # Показываем информацию об индексах
                            with st.expander("Информация об индексах"):
                                st.write("Индекс numeric_grades (первые 5):", list(numeric_grades.index[:5]))
                                if class_info:
                                    st.write("Ключи class_info (первые 5):", list(class_info.keys())[:5])

                            # Получаем статистику
                            with st.spinner("Расчет статистики..."):
                                detailed_stats = get_detailed_statistics(numeric_grades, class_info)



                            # Проверяем результат
                            if detailed_stats is not None and isinstance(detailed_stats,
                                                                         pd.DataFrame) and not detailed_stats.empty:
                                st.success(f"✅ Получена статистика для {len(detailed_stats)} учеников")

                                st.header("📊 РАСШИРЕННАЯ АНАЛИТИКА")

                                # Создаем вкладки для разных типов визуализаций
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
                                        # 1. Гистограмма с кривой распределения
                                        fig = make_subplots(rows=2, cols=1,
                                                            subplot_titles=('Распределение средних баллов',
                                                                            'Накопленное распределение'),
                                                            vertical_spacing=0.15)

                                        # Гистограмма
                                        hist_data = detailed_stats['Средний балл'].dropna()
                                        fig.add_trace(
                                            go.Histogram(x=hist_data, nbinsx=20,
                                                         marker_color='#636EFA',
                                                         name='Частота',
                                                         showlegend=False),
                                            row=1, col=1
                                        )

                                        # Добавляем вертикальные линии
                                        for threshold, color, name in [(3.0, 'red', 'Порог 3.0'),
                                                                       (3.5, 'orange', 'Порог 3.5'),
                                                                       (4.0, 'green', 'Порог 4.0')]:
                                            fig.add_vline(x=threshold, line_dash="dash",
                                                          line_color=color, row=1, col=1)

                                        # Накопленное распределение
                                        sorted_grades = np.sort(hist_data)
                                        cumulative = np.arange(1, len(sorted_grades) + 1) / len(sorted_grades) * 100

                                        fig.add_trace(
                                            go.Scatter(x=sorted_grades, y=cumulative,
                                                       mode='lines', name='Накопленный %',
                                                       line=dict(color='#EF553B', width=3),
                                                       fill='tozeroy'),
                                            row=2, col=1
                                        )

                                        fig.update_layout(height=600, showlegend=True)
                                        fig.update_yaxes(title_text="Количество учеников", row=1, col=1)
                                        fig.update_yaxes(title_text="Накопленный процент (%)", row=2, col=1)
                                        fig.update_xaxes(title_text="Средний балл", row=2, col=1)

                                        st.plotly_chart(fig, use_container_width=True)

                                    with col2:
                                        # 2. Ящик с усами (box plot) по классам
                                        if 'Класс' in detailed_stats.columns:
                                            fig = px.box(detailed_stats, x='Класс', y='Средний балл',
                                                         title='Распределение средних баллов по классам',
                                                         color='Класс',
                                                         points='all',  # Показываем все точки
                                                         hover_data=['ФИО'])

                                            fig.update_layout(height=500)
                                            st.plotly_chart(fig, use_container_width=True)

                                        # 3. Violin plot (альтернатива box plot)
                                        fig = go.Figure()
                                        fig.add_trace(go.Violin(y=detailed_stats['Средний балл'],
                                                                box_visible=True,
                                                                line_color='black',
                                                                meanline_visible=True,
                                                                fillcolor='lightseagreen',
                                                                opacity=0.6,
                                                                name='Распределение'))

                                        fig.update_layout(title='Распределение средних баллов (Violin Plot)',
                                                          yaxis_title='Средний балл',
                                                          height=400)
                                        st.plotly_chart(fig, use_container_width=True)

                                    # 4. Круговая диаграмма успеваемости
                                    col1, col2, col3 = st.columns(3)

                                    with col1:
                                        # Распределение по уровням успеваемости
                                        levels = {
                                            'Отличники (≥4.5)': (detailed_stats['Средний балл'] >= 4.5).sum(),
                                            'Хорошисты (4.0-4.49)': ((detailed_stats['Средний балл'] >= 4.0) &
                                                                     (detailed_stats['Средний балл'] < 4.5)).sum(),
                                            'Троечники (3.0-3.99)': ((detailed_stats['Средний балл'] >= 3.0) &
                                                                     (detailed_stats['Средний балл'] < 4.0)).sum(),
                                            'Неуспевающие (<3.0)': (detailed_stats['Средний балл'] < 3.0).sum()
                                        }

                                        fig = px.pie(values=list(levels.values()),
                                                     names=list(levels.keys()),
                                                     title='Распределение по уровням успеваемости',
                                                     color_discrete_sequence=['#2E7D32', '#1976D2', '#ED6C02',
                                                                              '#D32F2F'])
                                        st.plotly_chart(fig, use_container_width=True)

                                    with col2:
                                        # Качество знаний по классам
                                        if 'Класс' in detailed_stats.columns:
                                            class_quality = detailed_stats.groupby('Класс')[
                                                'Качество знаний (%)'].mean().reset_index()
                                            fig = px.bar(class_quality, x='Класс', y='Качество знаний (%)',
                                                         title='Качество знаний по классам',
                                                         color='Качество знаний (%)',
                                                         color_continuous_scale='RdYlGn',
                                                         text_auto='.1f')
                                            fig.update_traces(textposition='outside')
                                            st.plotly_chart(fig, use_container_width=True)

                                    with col3:
                                        # Тепловая карта успеваемости
                                        if len(numeric_grades.columns) > 1:
                                            # Берем первые 15 учеников и 10 предметов для наглядности
                                            display_students = detailed_stats.nlargest(15, 'Средний балл')[
                                                'ФИО'].tolist()
                                            display_subjects = numeric_grades.columns[:10]

                                            heatmap_data = numeric_grades.loc[display_students, display_subjects]

                                            fig = px.imshow(heatmap_data,
                                                            labels=dict(x="Предметы", y="Ученики", color="Оценка"),
                                                            x=display_subjects,
                                                            y=display_students,
                                                            color_continuous_scale='RdYlGn',
                                                            aspect="auto",
                                                            title='Тепловая карта успеваемости (топ-15 учеников)')
                                            fig.update_layout(height=500)
                                            st.plotly_chart(fig, use_container_width=True)

                                with tab2:
                                    st.subheader("🏆 Рейтинги и сравнения")

                                    col1, col2 = st.columns(2)

                                    with col1:
                                        # Топ-10 лучших
                                        top_10 = detailed_stats.nlargest(10, 'Средний балл')[
                                            ['ФИО', 'Класс', 'Средний балл', 'Качество знаний (%)']]

                                        fig = px.bar(top_10, x='Средний балл', y='ФИО',
                                                     orientation='h',
                                                     title='Топ-10 лучших учеников',
                                                     color='Средний балл',
                                                     color_continuous_scale='Greens',
                                                     text='Средний балл')
                                        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                                        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
                                        st.plotly_chart(fig, use_container_width=True)

                                    with col2:
                                        # Топ-10 с проблемами
                                        bottom_10 = detailed_stats.nsmallest(10, 'Средний балл')[
                                            ['ФИО', 'Класс', 'Средний балл', 'Кол-во пропусков']]

                                        fig = px.bar(bottom_10, x='Средний балл', y='ФИО',
                                                     orientation='h',
                                                     title='Топ-10 учеников с проблемами',
                                                     color='Средний балл',
                                                     color_continuous_scale='Reds',
                                                     text='Средний балл')
                                        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
                                        fig.update_layout(yaxis={'categoryorder': 'total descending'})
                                        st.plotly_chart(fig, use_container_width=True)

                                    # 3. Радар сравнения лучших учеников
                                    st.subheader("🕸️ Сравнение профилей лучших учеников")

                                    top_n_radar = st.slider("Количество учеников для сравнения", 3, 8, 5)
                                    top_students_radar = detailed_stats.nlargest(top_n_radar, 'Средний балл')[
                                        'ФИО'].tolist()

                                    if len(numeric_grades.columns) >= 3:
                                        # Берем первые 6 предметов для радара
                                        subjects = numeric_grades.columns[:6]
                                        subjects_short = [str(s)[:10] for s in subjects]

                                        fig = go.Figure()

                                        for student in top_students_radar:
                                            if student in numeric_grades.index:
                                                student_grades = numeric_grades.loc[student][subjects].values
                                                fig.add_trace(go.Scatterpolar(
                                                    r=student_grades,
                                                    theta=subjects_short,
                                                    fill='toself',
                                                    name=student[:15]  # Обрезаем длинные имена
                                                ))

                                        fig.update_layout(
                                            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                                            title=f"Сравнение профилей топ-{top_n_radar} учеников",
                                            height=500
                                        )
                                        st.plotly_chart(fig, use_container_width=True)

                                with tab3:
                                    st.subheader("📉 Анализ трендов и динамики")

                                    # 1. Динамика успеваемости класса
                                    st.write("**Динамика успеваемости класса**")

                                    # Создаем DataFrame с динамикой по всем ученикам
                                    trend_data = []
                                    for student in numeric_grades.index[:20]:  # Ограничиваем для наглядности
                                        grades = numeric_grades.loc[student].dropna().values
                                        if len(grades) > 1:
                                            for i, grade in enumerate(grades):
                                                trend_data.append({
                                                    'Ученик': student[:20] if len(student) > 20 else student,
                                                    # Обрезаем длинные имена
                                                    'Номер работы': i + 1,
                                                    'Оценка': grade
                                                })

                                    if trend_data:
                                        trend_df = pd.DataFrame(trend_data)

                                        # Используем line chart вместо scatter plot для соединения точек
                                        fig = px.line(trend_df, x='Номер работы', y='Оценка',
                                                      color='Ученик',
                                                      title='Динамика оценок всех учеников',
                                                      markers=True,  # Добавляем маркеры на линиях
                                                      line_shape='linear')  # Линейное соединение

                                        # Настраиваем отображение
                                        fig.update_traces(line=dict(width=1.5),  # Толщина линий
                                                          marker=dict(size=4))  # Размер маркеров

                                        # Добавляем среднюю линию
                                        avg_by_work = trend_df.groupby('Номер работы')['Оценка'].mean().reset_index()
                                        fig.add_trace(go.Scatter(x=avg_by_work['Номер работы'],
                                                                 y=avg_by_work['Оценка'],
                                                                 mode='lines+markers',
                                                                 name='Среднее по классу',
                                                                 line=dict(color='black', width=4),
                                                                 marker=dict(size=8, symbol='diamond')))

                                        fig.update_layout(
                                            height=500,
                                            xaxis_title="Номер работы",
                                            yaxis_title="Оценка",
                                            yaxis=dict(range=[1.5, 5.5]),  # Фиксируем диапазон оценок
                                            hovermode='x unified'  # Улучшаем отображение подсказок
                                        )

                                        st.plotly_chart(fig, use_container_width=True)

                                    # 2. Индивидуальная динамика (возможность выбрать ученика)
                                    st.subheader("👤 Индивидуальная динамика")

                                    if 'ФИО' in detailed_stats.columns:
                                        selected_student_trend = st.selectbox(
                                            "Выберите ученика для просмотра динамики",
                                            options=['Все ученики'] + sorted(detailed_stats['ФИО'].tolist()),
                                            key="trend_student"
                                        )

                                        if selected_student_trend != 'Все ученики' and selected_student_trend in numeric_grades.index:
                                            # Данные для одного ученика
                                            student_grades = numeric_grades.loc[selected_student_trend].dropna()

                                            if len(student_grades) > 1:
                                                fig = go.Figure()

                                                # Линия с маркерами
                                                fig.add_trace(go.Scatter(
                                                    x=list(range(1, len(student_grades) + 1)),
                                                    y=student_grades.values,
                                                    mode='lines+markers',
                                                    name='Оценки',
                                                    line=dict(color='blue', width=3),
                                                    marker=dict(size=10, symbol='circle'),
                                                    text=[f"Оценка: {g}" for g in student_grades.values],
                                                    hoverinfo='text'
                                                ))

                                                # Добавляем линию среднего
                                                avg_grade = student_grades.mean()
                                                fig.add_hline(
                                                    y=avg_grade,
                                                    line_dash="dash",
                                                    line_color="green",
                                                    annotation_text=f"Среднее: {avg_grade:.2f}",
                                                    annotation_position="bottom right"
                                                )

                                                # Добавляем линию тренда
                                                if len(student_grades) >= 3:
                                                    x = np.array(range(len(student_grades))).reshape(-1, 1)
                                                    y = student_grades.values
                                                    model = LinearRegression()
                                                    model.fit(x, y)
                                                    trend = model.predict(x)

                                                    fig.add_trace(go.Scatter(
                                                        x=list(range(1, len(student_grades) + 1)),
                                                        y=trend,
                                                        mode='lines',
                                                        name='Тренд',
                                                        line=dict(color='red', width=2, dash='dash')
                                                    ))

                                                fig.update_layout(
                                                    title=f"Динамика оценок: {selected_student_trend}",
                                                    xaxis_title="Номер работы",
                                                    yaxis_title="Оценка",
                                                    yaxis=dict(range=[1.5, 5.5]),
                                                    height=400
                                                )

                                                st.plotly_chart(fig, use_container_width=True)
                                            else:
                                                st.info(
                                                    f"У ученика недостаточно оценок для построения графика динамики (нужно минимум 2, есть {len(student_grades)})")
                                    else:
                                        # Альтернативный выбор из индекса
                                        all_students = list(numeric_grades.index)[
                                            :50]  # Ограничиваем для производительности
                                        selected_idx = st.selectbox(
                                            "Выберите ученика для просмотра динамики",
                                            options=['Все ученики'] + all_students,
                                            key="trend_student_idx"
                                        )

                                        if selected_idx != 'Все ученики' and selected_idx in numeric_grades.index:
                                            student_grades = numeric_grades.loc[selected_idx].dropna()

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

                                                avg_grade = student_grades.mean()
                                                fig.add_hline(
                                                    y=avg_grade,
                                                    line_dash="dash",
                                                    line_color="green",
                                                    annotation_text=f"Среднее: {avg_grade:.2f}"
                                                )

                                                fig.update_layout(
                                                    title=f"Динамика оценок: {selected_idx}",
                                                    xaxis_title="Номер работы",
                                                    yaxis_title="Оценка",
                                                    yaxis=dict(range=[1.5, 5.5]),
                                                    height=400
                                                )

                                                st.plotly_chart(fig, use_container_width=True)

                                    # 3. Анализ стабильности (остается без изменений)
                                    st.subheader("📊 Анализ стабильности успеваемости")

                                    if 'Станд. отклонение' in detailed_stats.columns and 'Средний балл' in detailed_stats.columns:
                                        # Добавляем метрики стабильности
                                        detailed_stats['Стабильность'] = 1 - (
                                                    detailed_stats['Станд. отклонение'] / detailed_stats[
                                                'Средний балл'])
                                        detailed_stats['Стабильность'] = detailed_stats['Стабильность'].clip(0, 1) * 100

                                        col1, col2 = st.columns(2)

                                        with col1:
                                            # Стабильность vs Средний балл
                                            fig = px.scatter(detailed_stats, x='Средний балл', y='Стабильность',
                                                             size='Кол-во оценок',
                                                             color='Класс' if 'Класс' in detailed_stats.columns else None,
                                                             hover_data=['ФИО'],
                                                             title='Соотношение успеваемости и стабильности',
                                                             labels={'Стабильность': 'Стабильность (%)'})

                                            # Добавляем линии средних
                                            fig.add_hline(y=detailed_stats['Стабильность'].mean(),
                                                          line_dash="dash", line_color="gray",
                                                          annotation_text=f"Средняя стабильность: {detailed_stats['Стабильность'].mean():.1f}%")
                                            fig.add_vline(x=detailed_stats['Средний балл'].mean(),
                                                          line_dash="dash", line_color="gray",
                                                          annotation_text=f"Средний балл: {detailed_stats['Средний балл'].mean():.2f}")

                                            st.plotly_chart(fig, use_container_width=True)

                                        with col2:
                                            # Гистограмма стабильности
                                            fig = px.histogram(detailed_stats, x='Стабильность', nbins=20,
                                                               title='Распределение стабильности учеников',
                                                               color_discrete_sequence=['#FFA15A'])
                                            fig.add_vline(x=50, line_dash="dash", line_color="red",
                                                          annotation_text="Порог стабильности")
                                            st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.info(
                                            "Для анализа стабильности необходимы колонки 'Станд. отклонение' и 'Средний балл'")

                                with tab4:
                                    st.subheader("🔗 Корреляционный анализ")

                                    # 1. Матрица корреляций
                                    if len(numeric_grades.columns) > 1:
                                        # Выбираем числовые колонки
                                        corr_columns = numeric_grades.columns[:15]
                                        corr_data = numeric_grades[corr_columns].copy()

                                        # Убираем строки с пропусками для корреляции
                                        corr_data = corr_data.dropna()

                                        if len(corr_data) > 5 and len(corr_data.columns) > 1:
                                            corr_matrix = corr_data.corr()

                                            fig = px.imshow(corr_matrix,
                                                            labels=dict(color="Корреляция"),
                                                            x=corr_matrix.columns,
                                                            y=corr_matrix.columns,
                                                            color_continuous_scale='RdBu_r',
                                                            zmin=-1, zmax=1,
                                                            title='Матрица корреляций между предметами')

                                            fig.update_layout(height=600)
                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            st.info("Недостаточно данных для построения матрицы корреляций")

                                    # 2. Связь пропусков и успеваемости
                                    if '% пропусков' in detailed_stats.columns and 'Средний балл' in detailed_stats.columns:
                                        st.subheader("📉 Влияние пропусков на успеваемость")

                                        fig = px.scatter(detailed_stats, x='% пропусков', y='Средний балл',
                                                         size='Кол-во оценок',
                                                         color='Класс' if 'Класс' in detailed_stats.columns else None,
                                                         hover_data=['ФИО'],
                                                         title='Зависимость успеваемости от пропусков',
                                                         labels={'% пропусков': 'Процент пропусков (%)'})

                                        st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.info("Для анализа влияния пропусков необходимы соответствующие данные")

                                    # 3. Сравнение успеваемости и качества знаний
                                    if 'Успеваемость (%)' in detailed_stats.columns and 'Качество знаний (%)' in detailed_stats.columns:
                                        fig = px.scatter(detailed_stats, x='Успеваемость (%)', y='Качество знаний (%)',
                                                         color='Средний балл',
                                                         size='Кол-во оценок',
                                                         hover_data=['ФИО'],
                                                         title='Соотношение успеваемости и качества знаний',
                                                         color_continuous_scale='Viridis')

                                        # Добавляем разделительные линии
                                        fig.add_hline(y=50, line_dash="dash", line_color="gray")
                                        fig.add_vline(x=50, line_dash="dash", line_color="gray")

                                        st.plotly_chart(fig, use_container_width=True)

                                with tab5:
                                    st.subheader("🏫 Сравнение классов")

                                    if 'Класс' in detailed_stats.columns and len(detailed_stats['Класс'].unique()) > 1:
                                        # Статистика по классам
                                        class_summary = detailed_stats.groupby('Класс').agg({
                                            'Средний балл': ['mean', 'std', 'min', 'max'],
                                            'Качество знаний (%)': 'mean',
                                            'Успеваемость (%)': 'mean',
                                            'Кол-во пропусков': 'sum',
                                            'ФИО': 'count'
                                        }).round(2)

                                        class_summary.columns = ['Ср. балл', 'Стд.откл', 'Мин', 'Макс',
                                                                 'Качество %', 'Успеваемость %', 'Всего пропусков',
                                                                 'Учеников']

                                        st.dataframe(class_summary, use_container_width=True)

                                        # Сравнительный график
                                        fig = go.Figure()

                                        metrics = ['Средний балл', 'Качество знаний (%)', 'Успеваемость (%)']
                                        for i, metric in enumerate(metrics):
                                            if metric in detailed_stats.columns:
                                                class_means = detailed_stats.groupby('Класс')[
                                                    metric].mean().reset_index()
                                                fig.add_trace(go.Bar(
                                                    name=metric,
                                                    x=class_means['Класс'],
                                                    y=class_means[metric],
                                                    text=class_means[metric].round(1),
                                                    textposition='outside'
                                                ))

                                        fig.update_layout(
                                            title='Сравнение классов по основным метрикам',
                                            barmode='group',
                                            height=500
                                        )
                                        st.plotly_chart(fig, use_container_width=True)

                                        # Радар сравнения классов
                                        if len(detailed_stats['Класс'].unique()) <= 6:
                                            st.subheader("🕸️ Радар сравнения классов")

                                            classes = detailed_stats['Класс'].unique()
                                            metrics_for_radar = ['Средний балл', 'Качество знаний (%)',
                                                                 'Успеваемость (%)',
                                                                 'Стабильность' if 'Стабильность' in detailed_stats.columns else None]
                                            metrics_for_radar = [m for m in metrics_for_radar if
                                                                 m and m in detailed_stats.columns]

                                            # Нормализуем метрики для радара
                                            fig = go.Figure()

                                            for cls in classes:
                                                class_data = detailed_stats[detailed_stats['Класс'] == cls]
                                                values = []
                                                for metric in metrics_for_radar:
                                                    if metric == 'Средний балл':
                                                        values.append(
                                                            class_data[metric].mean() / 5 * 100)  # Нормализуем к 100
                                                    else:
                                                        values.append(class_data[metric].mean())

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
                                            st.plotly_chart(fig, use_container_width=True)
                                    else:
                                        st.info("Для сравнения классов необходимо указать колонку с классами")

                                with tab6:
                                    st.subheader("🎯 Индивидуальный анализ")

                                    # Выбор ученика для детального анализа
                                    if 'ФИО' in detailed_stats.columns:
                                        selected_student = st.selectbox(
                                            "Выберите ученика для детального анализа",
                                            options=sorted(detailed_stats['ФИО'].tolist()),
                                            key="individual_analysis"
                                        )

                                        if selected_student:
                                            # Данные ученика
                                            student_data = \
                                            detailed_stats[detailed_stats['ФИО'] == selected_student].iloc[0]

                                            # Получаем оценки ученика
                                            if selected_student in numeric_grades.index:
                                                student_grades = numeric_grades.loc[selected_student].dropna()

                                                # Метрики ученика
                                                col1, col2, col3, col4 = st.columns(4)
                                                with col1:
                                                    st.metric("Средний балл", f"{student_data['Средний балл']:.2f}")
                                                    st.metric("Медиана", f"{student_data['Медиана']:.2f}")
                                                with col2:
                                                    st.metric("Качество знаний",
                                                              f"{student_data['Качество знаний (%)']:.1f}%")
                                                    st.metric("Успеваемость",
                                                              f"{student_data['Успеваемость (%)']:.1f}%")
                                                with col3:
                                                    st.metric("Всего оценок", student_data['Кол-во оценок'])
                                                    st.metric("Пропуски", f"{student_data['% пропусков']:.1f}%")
                                                with col4:
                                                    if 'Стабильность' in student_data:
                                                        st.metric("Стабильность",
                                                                  f"{student_data['Стабильность']:.1f}%")
                                                    st.metric("Разброс", f"{student_data['Станд. отклонение']:.2f}")

                                                # Комплексный график
                                                fig = make_subplots(
                                                    rows=2, cols=2,
                                                    subplot_titles=('Динамика оценок', 'Распределение оценок',
                                                                    'Сравнение со средним по классу',
                                                                    'Профиль успеваемости'),
                                                    specs=[[{'type': 'scatter'}, {'type': 'pie'}],
                                                           [{'type': 'bar'}, {'type': 'scatterpolar'}]],
                                                    vertical_spacing=0.15,
                                                    horizontal_spacing=0.15
                                                )

                                                # 1. Динамика оценок
                                                grades_values = student_grades.values
                                                fig.add_trace(
                                                    go.Scatter(x=list(range(1, len(grades_values) + 1)),
                                                               y=grades_values,
                                                               mode='lines+markers',
                                                               name='Оценки',
                                                               line=dict(color='blue', width=2),
                                                               marker=dict(size=8)),
                                                    row=1, col=1
                                                )

                                                # Добавляем линию тренда
                                                if len(grades_values) > 1:
                                                    x = np.array(range(len(grades_values))).reshape(-1, 1)
                                                    y = grades_values
                                                    model = LinearRegression()
                                                    model.fit(x, y)
                                                    trend = model.predict(x)
                                                    fig.add_trace(
                                                        go.Scatter(x=list(range(1, len(grades_values) + 1)),
                                                                   y=trend,
                                                                   mode='lines',
                                                                   name='Тренд',
                                                                   line=dict(color='red', dash='dash')),
                                                        row=1, col=1
                                                    )

                                                # 2. Распределение оценок
                                                grade_counts = student_grades.value_counts().sort_index()
                                                fig.add_trace(
                                                    go.Pie(labels=grade_counts.index,
                                                           values=grade_counts.values,
                                                           name='Распределение'),
                                                    row=1, col=2
                                                )

                                                # 3. Сравнение со средним по классу
                                                if 'Класс' in detailed_stats.columns:
                                                    student_class = student_data['Класс']
                                                    class_avg = \
                                                    detailed_stats[detailed_stats['Класс'] == student_class][
                                                        'Средний балл'].mean()

                                                    fig.add_trace(
                                                        go.Bar(x=['Ученик', 'Среднее по классу'],
                                                               y=[student_data['Средний балл'], class_avg],
                                                               name='Сравнение',
                                                               marker_color=['blue', 'gray']),
                                                        row=2, col=1
                                                    )

                                                # 4. Профиль успеваемости (радар)
                                                if len(numeric_grades.columns) >= 3:
                                                    subjects = numeric_grades.columns[:6]
                                                    subjects_short = [str(s)[:10] for s in subjects]
                                                    student_profile = []
                                                    for subj in subjects:
                                                        if subj in student_grades.index:
                                                            student_profile.append(student_grades[subj])
                                                        else:
                                                            student_profile.append(np.nan)

                                                    fig.add_trace(
                                                        go.Scatterpolar(r=student_profile,
                                                                        theta=subjects_short,
                                                                        fill='toself',
                                                                        name='Профиль'),
                                                        row=2, col=2
                                                    )

                                                fig.update_layout(height=800, showlegend=True)
                                                st.plotly_chart(fig, use_container_width=True)

                                                # Рекомендации
                                                st.subheader("💡 Рекомендации")

                                                recommendations = []

                                                if student_data['Средний балл'] < 3.0:
                                                    recommendations.append(
                                                        "🔴 Требуется срочное внимание! Низкая успеваемость.")
                                                elif student_data['Средний балл'] < 3.5:
                                                    recommendations.append("🟡 Есть потенциал для улучшения.")

                                                if student_data['% пропусков'] > 20:
                                                    recommendations.append(
                                                        f"📝 Высокий процент пропусков ({student_data['% пропусков']:.1f}%). Рекомендуется выяснить причину.")

                                                if 'Стабильность' in student_data and student_data['Стабильность'] < 50:
                                                    recommendations.append(
                                                        "📊 Нестабильная успеваемость. Рекомендуется обратить внимание на регулярность.")

                                                if len(student_grades) < 5:
                                                    recommendations.append("📋 Мало оценок для объективного анализа.")

                                                if not recommendations:
                                                    recommendations.append("✅ Стабильная успеваемость. Так держать!")

                                                for rec in recommendations:
                                                    st.write(rec)
                                    else:
                                        st.info("Для индивидуального анализа необходима колонка с ФИО")

                                # Показываем структуру данных
                                with st.expander("Структура данных"):
                                    st.write("Колонки:", list(detailed_stats.columns))
                                    st.write("Первые 3 строки:")
                                    st.dataframe(detailed_stats.head(3))

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
                                    if 'Средний балл' in detailed_stats.columns and 'ФИО' in detailed_stats.columns:
                                        top_students = detailed_stats.nlargest(10, 'Средний балл')[
                                            ['ФИО', 'Класс', 'Средний балл', 'Качество знаний (%)']]
                                        st.dataframe(top_students, use_container_width=True)

                                with col2:
                                    st.subheader("⚠️ Топ-10 учеников с проблемами")
                                    if 'Средний балл' in detailed_stats.columns and 'ФИО' in detailed_stats.columns:
                                        problem_students = detailed_stats.nsmallest(10, 'Средний балл')[
                                            ['ФИО', 'Класс', 'Средний балл', 'Кол-во пропусков', '% пропусков']]
                                        st.dataframe(problem_students, use_container_width=True)

                                # Статистика по классам
                                if ('class_column' in locals() and class_column != 'Нет колонки с классами') or (
                                        'manual_class' in locals() and manual_class):
                                    if 'Класс' in detailed_stats.columns:
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

                                if 'ФИО' in detailed_stats.columns:
                                    # Выбираем колонки для отображения
                                    display_columns = ['ФИО', 'Класс', 'Средний балл', 'Медиана',
                                                       'Мин. оценка', 'Макс. оценка', 'Кол-во оценок',
                                                       'Кол-во пропусков', '% пропусков', 'Успеваемость (%)',
                                                       'Качество знаний (%)']

                                    # Берем только существующие колонки
                                    existing_columns = [col for col in display_columns if col in detailed_stats.columns]

                                    st.dataframe(
                                        detailed_stats[existing_columns],
                                        use_container_width=True,
                                        column_config={
                                            "ФИО": st.column_config.TextColumn("ФИО", width="medium"),
                                            "Класс": st.column_config.TextColumn("Класс", width="small"),
                                            "Средний балл": st.column_config.NumberColumn("Ср. балл", format="%.2f"),
                                            "Медиана": st.column_config.NumberColumn("Медиана", format="%.2f"),
                                            "Мин. оценка": st.column_config.NumberColumn("Мин", format="%d"),
                                            "Макс. оценка": st.column_config.NumberColumn("Макс", format="%d"),
                                            "Кол-во оценок": st.column_config.NumberColumn("Кол-во", format="%d"),
                                            "Кол-во пропусков": st.column_config.NumberColumn("Пропуски", format="%d"),
                                            "% пропусков": st.column_config.NumberColumn("% проп.", format="%.1f%%"),
                                            "Успеваемость (%)": st.column_config.NumberColumn("Усп.%", format="%.1f%%"),
                                            "Качество знаний (%)": st.column_config.NumberColumn("Кач.%",
                                                                                                 format="%.1f%%"),
                                        }
                                    )

                                    # Кнопка для скачивания
                                    csv = detailed_stats[existing_columns].to_csv(index=False).encode('utf-8')
                                    st.download_button(
                                        label="📥 Скачать статистику (CSV)",
                                        data=csv,
                                        file_name=f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                        mime="text/csv"
                                    )
                                else:
                                    st.warning("В данных нет колонки с ФИО")
                                    st.dataframe(detailed_stats, use_container_width=True)

                                # Аналитика по конкретному ученику
                                st.header("👤 Аналитика по ученику")

                                if 'ФИО' in detailed_stats.columns:
                                    # Сортируем ФИО для удобства поиска
                                    students_list = sorted(detailed_stats['ФИО'].tolist())

                                    selected_student = st.selectbox(
                                        "Выберите ученика",
                                        options=students_list,
                                        key="student_selector"
                                    )

                                    if selected_student:
                                        # Находим данные ученика
                                        student_data = detailed_stats[detailed_stats['ФИО'] == selected_student].iloc[0]

                                        # Проверяем, существует ли ученик в numeric_grades
                                        if selected_student in numeric_grades.index:
                                            student_grades = numeric_grades.loc[selected_student].dropna()
                                        else:
                                            # Пробуем найти похожее имя
                                            found = False
                                            for name in numeric_grades.index:
                                                if selected_student.lower() in str(name).lower() or str(
                                                        name).lower() in selected_student.lower():
                                                    student_grades = numeric_grades.loc[name].dropna()
                                                    st.info(f"Найден похожий ученик: {name}")
                                                    found = True
                                                    break

                                            if not found:
                                                st.warning(
                                                    f"Данные по ученику '{selected_student}' не найдены в исходных данных")
                                                student_grades = pd.Series(dtype=float)

                                        # Отображаем метрики
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
                                                subplot_titles=(f'Динамика оценок: {selected_student}',
                                                                'Скользящее среднее (3 оценки)'),
                                                vertical_spacing=0.15
                                            )

                                            fig.add_trace(
                                                go.Scatter(x=list(range(1, len(student_grades) + 1)),
                                                           y=student_grades.values,
                                                           mode='lines+markers',
                                                           name='Оценки',
                                                           line=dict(color='blue', width=2),
                                                           marker=dict(size=8)),
                                                row=1, col=1
                                            )

                                            # Добавляем линию среднего значения
                                            avg_grade = student_grades.mean()
                                            fig.add_hline(y=avg_grade, line_dash="dash", line_color="green",
                                                          annotation_text=f"Среднее: {avg_grade:.2f}",
                                                          annotation_position="bottom right",
                                                          row=1, col=1)

                                            # Скользящее среднее
                                            if len(student_grades) >= 3:
                                                rolling_mean = student_grades.rolling(3, min_periods=1).mean()
                                                fig.add_trace(
                                                    go.Scatter(x=list(range(1, len(rolling_mean) + 1)),
                                                               y=rolling_mean.values,
                                                               mode='lines',
                                                               name='Скользящее среднее (3)',
                                                               line=dict(color='red', width=2, dash='dash')),
                                                    row=2, col=1
                                                )

                                                # Добавляем исходные точки на второй график для сравнения
                                                fig.add_trace(
                                                    go.Scatter(x=list(range(1, len(student_grades) + 1)),
                                                               y=student_grades.values,
                                                               mode='markers',
                                                               name='Оценки',
                                                               marker=dict(color='blue', size=6),
                                                               showlegend=False),
                                                    row=2, col=1
                                                )

                                            fig.update_layout(
                                                height=600,
                                                showlegend=True,
                                                hovermode='x unified'
                                            )
                                            fig.update_xaxes(title_text="Номер работы", row=2, col=1)
                                            fig.update_yaxes(title_text="Оценка", range=[1.5, 5.5], row=1, col=1)
                                            fig.update_yaxes(title_text="Оценка", range=[1.5, 5.5], row=2, col=1)

                                            st.plotly_chart(fig, use_container_width=True)
                                        else:
                                            st.info(
                                                f"У ученика недостаточно оценок для построения графика динамики (нужно минимум 2, есть {len(student_grades)})")

                                        # Радар успеваемости
                                        if len(student_grades) >= 3:
                                            # Получаем названия предметов из колонок
                                            subject_columns = numeric_grades.columns[
                                                :min(6, len(numeric_grades.columns))]
                                            categories = [str(col)[:15] for col in subject_columns]

                                            # Берем первые несколько оценок для радара
                                            radar_values = student_grades.values[:len(categories)]

                                            fig = go.Figure(data=go.Scatterpolar(
                                                r=radar_values,
                                                theta=categories,
                                                fill='toself',
                                                line=dict(color='blue', width=2),
                                                marker=dict(size=8)
                                            ))

                                            fig.update_layout(
                                                polar=dict(
                                                    radialaxis=dict(
                                                        visible=True,
                                                        range=[0, 5],
                                                        tickmode='linear',
                                                        tick0=2,
                                                        dtick=1
                                                    )),
                                                showlegend=False,
                                                title=f"Профиль успеваемости по предметам: {selected_student}",
                                                height=400
                                            )
                                            st.plotly_chart(fig, use_container_width=True)
                                else:
                                    st.info("Нет данных для анализа по ученикам")

                            else:
                                st.warning("Не удалось получить статистику по ученикам")
                                st.info("Возможные причины:\n"
                                        "• Нет данных с оценками\n"
                                        "• Оценки не соответствуют формату (2-5)\n"
                                        "• Проблемы с определением учеников")

                        except Exception as e:
                            st.error(f"Ошибка при расчете статистики: {e}")
                            st.exception(e)

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
                # Очистка ФИО от служебной информации
                df['clean_name'] = df[name_column].apply(clean_student_name)
                df_clean = df.dropna(subset=['clean_name']).copy()

                # Сохраняем имена в отдельную переменную
                student_names = df_clean['clean_name'].astype(str).tolist()
                st.success(f"✅ Найдено {len(student_names)} учеников")

                # Показываем список учеников
                with st.expander("Показать список учеников"):
                    students_df = pd.DataFrame({
                        '№': range(1, len(student_names) + 1),
                        'ФИО': student_names
                    })
                    st.dataframe(students_df, use_container_width=True)

                # Определяем колонки, которые точно не содержат оценки (но НЕ УДАЛЯЕМ их)
                non_grade_columns = identify_non_grade_columns(df_clean)
                if non_grade_columns:
                    st.info(f"Обнаружены колонки без оценок: {', '.join(map(str, non_grade_columns))}")

                # Удаляем только колонку с именами (она больше не нужна)
                if 'clean_name' in df_clean.columns:
                    df_clean = df_clean.drop(columns=['clean_name'])

                # Устанавливаем индекс как имена учеников
                df_clean.index = student_names

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

                    # Удаляем колонку с классами из данных, чтобы не мешала
                    if class_column in df_clean.columns:
                        df_clean = df_clean.drop(columns=[class_column])

                elif manual_class:
                    for name in student_names:
                        class_info[name] = manual_class
                else:
                    for name in student_names:
                        class_info[name] = extract_class_info(name)

                # Объединение дублирующихся учеников
                if st.checkbox("Объединить данные по дублирующимся ученикам", value=True):
                    df_clean = df_clean.groupby(df_clean.index).first()
                    student_names = df_clean.index.tolist()
                    st.info(f"После объединения дубликатов: {len(df_clean)} учеников")

                # Выбор колонок с оценками
                st.subheader("📝 Выбор колонок с оценками")

                all_columns = list(df_clean.columns)
                grade_columns = st.multiselect(
                    "Выберите колонки, содержащие оценки",
                    options=all_columns,
                    default=[col for col in all_columns if col not in non_grade_columns][:10]
                    # По умолчанию выбираем первые 10 колонок с возможными оценками
                )

                if grade_columns or st.button("Автоопределение оценок"):
                    if not grade_columns:
                        # Автоопределение колонок с оценками
                        numeric_grades, grade_columns = parse_grades(df_clean)
                    else:
                        # Используем выбранные колонки
                        numeric_grades, _ = parse_grades(df_clean, grade_columns)

                    if not numeric_grades.empty:
                        # Убеждаемся, что индекс сохранился
                        numeric_grades.index = student_names

                        # Проверка валидности оценок
                        st.subheader("🔍 Проверка качества данных")
                        is_valid = display_grades_validation(numeric_grades)

                        if not is_valid:
                            st.warning("⚠️ Обнаружены проблемы с данными. Выполняется очистка ячеек...")
                            # Фильтруем только значения, оставляя допустимые
                            numeric_grades = numeric_grades.applymap(
                                lambda x: x if pd.isna(x) or (2 <= x <= 5) else np.nan)
                            st.success("✅ Ячейки с недопустимыми значениями очищены")

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

                        # Круговая диаграмма распределения оценок
                        fig = px.pie(
                            values=[grade_stats['grade_5'], grade_stats['grade_4'],
                                    grade_stats['grade_3'], grade_stats['grade_2'], grade_stats['absences']],
                            names=['5 (Отлично)', '4 (Хорошо)', '3 (Удовл.)', '2 (Неуд.)', 'Пропуски'],
                            title='Распределение оценок (только 2,3,4,5 и отметки об отсутствии)',
                            color_discrete_sequence=['#2E7D32', '#1976D2', '#ED6C02', '#D32F2F', '#9E9E9E']
                        )
                        st.plotly_chart(fig, use_container_width=True)

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


def manual_grade_correction(grades_df):
    """Ручное исправление недопустимых оценок"""
    st.subheader("✏️ Ручное исправление оценок")

    # Находим ячейки с недопустимыми значениями
    invalid_cells = []
    for col in grades_df.columns:
        for idx, value in grades_df[col].items():
            if not pd.isna(value) and not (isinstance(value, (int, float)) and 2 <= value <= 5):
                invalid_cells.append({
                    'Ученик': idx,
                    'Колонка': col,
                    'Текущее значение': value
                })

    if invalid_cells:
        st.warning(f"Найдено {len(invalid_cells)} ячеек с недопустимыми значениями")

        # Создаем DataFrame для редактирования
        edit_df = pd.DataFrame(invalid_cells)
        edit_df['Новое значение'] = ''

        # Редактирование через data_editor
        edited_df = st.data_editor(
            edit_df,
            column_config={
                "Ученик": st.column_config.TextColumn("Ученик", disabled=True),
                "Колонка": st.column_config.TextColumn("Колонка", disabled=True),
                "Текущее значение": st.column_config.TextColumn("Текущее значение", disabled=True),
                "Новое значение": st.column_config.SelectboxColumn(
                    "Новое значение",
                    options=['', '2', '3', '4', '5', 'н'],
                    required=False
                )
            },
            hide_index=True,
            use_container_width=True
        )

        if st.button("✅ Применить исправления"):
            for _, row in edited_df.iterrows():
                if row['Новое значение']:
                    student = row['Ученик']
                    col = row['Колонка']
                    new_val = row['Новое значение']

                    if new_val == 'н':
                        grades_df.loc[student, col] = np.nan
                    else:
                        grades_df.loc[student, col] = float(new_val)

            st.success("Исправления применены!")
            st.rerun()
    else:
        st.success("✓ Все оценки допустимы (только 2,3,4,5 и отметки об отсутствии)")

    return grades_df


def get_student_stats(grades_df, student_name):
    """Получение статистики по конкретному ученику"""
    if student_name in grades_df.index:
        student_grades = grades_df.loc[student_name].dropna()

        # Дополнительная проверка на допустимые значения
        valid_grades = student_grades[student_grades.apply(lambda x: 2 <= x <= 5)]

        stats = {
            'mean': valid_grades.mean() if len(valid_grades) > 0 else 0,
            'median': valid_grades.median() if len(valid_grades) > 0 else 0,
            'count': len(valid_grades),
            'absent_count': student_grades.isna().sum(),
            'invalid_count': len(student_grades) - len(valid_grades),  # Недопустимые оценки
            'grades_distribution': valid_grades.value_counts().sort_index(),
            'grades_trend': valid_grades.values if len(valid_grades) > 1 else []
        }
        return stats
    return None


def identify_problem_students(grades_df, threshold=3.0, min_grades=3):
    """Выявление учеников с проблемами"""
    problems = []

    for student in grades_df.index:
        # Фильтруем только допустимые оценки
        student_grades = grades_df.loc[student].dropna()
        valid_grades = student_grades[student_grades.apply(lambda x: 2 <= x <= 5)]

        if len(valid_grades) >= min_grades:
            avg_grade = valid_grades.mean()
            recent_grades = valid_grades.tail(3).mean() if len(valid_grades) >= 3 else avg_grade

            problems_found = []

            if avg_grade < threshold:
                problems_found.append(f"Низкий средний балл: {avg_grade:.2f}")

            if recent_grades < avg_grade * 0.8:
                problems_found.append("Падение успеваемости")

            # Проверяем пропуски
            absent_count = student_grades.isna().sum()
            if absent_count > len(student_grades) * 0.3:
                problems_found.append(f"Много пропусков ({absent_count})")

            # Проверяем недопустимые оценки
            invalid_count = len(student_grades) - len(valid_grades)
            if invalid_count > 0:
                problems_found.append(f"Некорректные оценки ({invalid_count})")

            if problems_found:
                problems.append({
                    'student': student,
                    'avg_grade': avg_grade,
                    'recent_avg': recent_grades,
                    'problems': problems_found,
                    'grades': valid_grades.values
                })

    return problems
