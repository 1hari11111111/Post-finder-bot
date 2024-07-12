FROM python-3.11.1
RUN gunicorn app:app & python3 main.py
