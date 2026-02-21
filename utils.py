from datetime import datetime, date, timedelta
from typing import List, Tuple
import calendar


def get_available_days(year: int, month: int) -> List[date]:
    """Возвращает список доступных дней для дежурства в указанном месяце"""
    # Доступные дни недели: среда (2), суббота (5), воскресенье (6)
    allowed_weekdays = [2, 5, 6]

    # Первый и последний день месяца
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    # Генерируем все подходящие дни
    available = []
    current = first_day
    while current <= last_day:
        if current.weekday() in allowed_weekdays:
            available.append(current)
        current += timedelta(days=1)

    return available


def format_date_short(d: date) -> str:
    """Форматирует дату как '04ср' или '08сб'"""
    days_ru = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
    return f"{d.day:02d}{days_ru[d.weekday()]}"


def format_date_long(d: date) -> str:
    """Форматирует дату как '4 марта 2024, среда'"""
    months_ru = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
                 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    days_ru = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье']
    return f"{d.day} {months_ru[d.month - 1]} {d.year}, {days_ru[d.weekday()]}"


def get_month_name(month: int) -> str:
    """Возвращает название месяца"""
    months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    return months_ru[month - 1]