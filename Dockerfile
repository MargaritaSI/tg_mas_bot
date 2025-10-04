FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать остальной код
COPY . /app
COPY images /app/images

# Установим права на доступ к файлам (для SQLite и картинок)
RUN chmod -R 755 /app

COPY images /app/images

# Команда по умолчанию для запуска бота
CMD ["python", "main.py"]
