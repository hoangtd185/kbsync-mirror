FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kbsync/ kbsync/
COPY main.py ask.py ./

RUN useradd --create-home app && mkdir -p articles runs && chown app articles runs
USER app

# `docker run <image>` runs the daily sync once and exits; `docker run <image> ask.py "..."` queries the bot.
ENTRYPOINT ["python"]
CMD ["main.py"]
