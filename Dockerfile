FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ARG AUTOREPLYER_REF=65b9a73896ffd86850e04c7ac13e89ab90986c99
ADD https://codeload.github.com/TheBigChanges/AutoReplyer/tar.gz/${AUTOREPLYER_REF} /tmp/upstream.tar.gz
RUN mkdir /opt/AutoReplyer && tar -xzf /tmp/upstream.tar.gz --strip-components=1 -C /opt/AutoReplyer && rm /tmp/upstream.tar.gz
ENV AUTOREPLYER_SOURCE=/opt/AutoReplyer PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY dist ./dist
COPY server ./server
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["python", "-m", "server.run"]
