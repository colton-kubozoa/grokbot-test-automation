# Container for the Playwright + pytest browser suite (Chromium, Firefox, WebKit).
# Base: official Playwright Python image (Python 3.12, browser OS deps included).
FROM mcr.microsoft.com/playwright/python:v1.63.0-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install chromium firefox webkit

COPY . .
RUN chown -R pwuser:pwuser /app

USER pwuser

# Default entrypoint runs the pytest suite under tests/.
CMD ["pytest"]
