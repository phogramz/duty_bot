#!/usr/bin/env python3
import psutil
import time
import os
from datetime import datetime


def log_resources():
    """Логирует использование ресурсов"""
    while True:
        # Память
        mem = psutil.virtual_memory()
        # Процесс бота (ищем python bot.py)
        bot_process = None
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent']):
            try:
                cmd = ' '.join(proc.info['cmdline'] or [])
                if 'bot.py' in cmd:
                    bot_process = proc.info
                    break
            except:
                pass

        # Общая статистика
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"\n[{timestamp}] {'=' * 40}")
        print(f"📊 ОБЩАЯ ПАМЯТЬ:")
        print(f"   Всего: {mem.total / 1024 / 1024:.1f} MB")
        print(f"   Доступно: {mem.available / 1024 / 1024:.1f} MB")
        print(f"   Используется: {mem.used / 1024 / 1024:.1f} MB ({mem.percent}%)")
        print(f"   Swap: {psutil.swap_memory().used / 1024 / 1024:.1f} MB")

        if bot_process:
            print(f"\n🤖 ПРОЦЕСС БОТА:")
            print(f"   PID: {bot_process['pid']}")
            print(f"   Память: {bot_process['memory_percent']:.1f}% от общей")
            print(f"   CPU: {bot_process['cpu_percent']:.1f}%")

        # Топ процессов по памяти
        print(f"\n🔥 ТОП-5 процессов по памяти:")
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
            try:
                processes.append((proc.info['memory_percent'], proc.info['name'], proc.info['pid']))
            except:
                pass

        for mem_percent, name, pid in sorted(processes, reverse=True)[:5]:
            print(f"   {name} (PID {pid}): {mem_percent:.1f}%")

        time.sleep(10)


if __name__ == "__main__":
    try:
        log_resources()
    except KeyboardInterrupt:
        print("\nМониторинг остановлен")