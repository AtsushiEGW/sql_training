FROM python:3.12-slim

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*


# --- 非rootユーザー作成　---
ARG USER_NAME=dev
ARG USER_UID=1000
ARG USER_GID=1000

RUN groupadd --gid $USER_GID $USER_NAME \
    && useradd --uid $USER_UID --gid $USER_GID -m -s /bin/bash $USER_NAME

WORKDIR /workspace

COPY requirements.txt /workspace/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 作業ディレクトリをユーザーの所有に
RUN chown -R $USER_UID:$USER_GID /workspace /home/$USER_NAME

# 以降は非rootユーザーで実行
USER $USER_UID:$USER_GID

CMD ["bash", "-lc", "sleep infinity"]