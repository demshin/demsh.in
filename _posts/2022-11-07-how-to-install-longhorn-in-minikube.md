---
layout: post
title:  "Как установить Longhorn в Minikube"
date:   2022-11-07 21:32:00 +0500
categories: kubernetes longhorn minikube howto
---

## Как установить Longhorn в Minikube

В этой статье я расскажу как установить Longhorn в Minikube.

### Установка Minikube

В macOS это проще всего сделать с помощью Homebrew:

```bash
❯ brew install minikube
```

### Запуск Minikube

Для Longhorn требуется Kubernetes версии 1.18 или выше (справедливо для Longhorn v1.3.2), поэтому запускаем Minikube с соответствующей версией Kubernetes и минимум 3 ноды.

```bash
❯ minikube start --kubernetes-version=v1.18.0 --nodes=3
```

### Подготовка node к установке Longhorn

Для установки Longhorn требуется пакет `open-iscsi` на каждой ноде. Для этого запускаем команду для каждой ноды:

```bash
❯ minikube ssh -n <node_name> "sudo apt update && sudo apt install -y open-iscsi"
```

Список нод можно получить командой:

```bash
❯ minikube node list
```

### Установка Longhorn

```bash
❯ helm repo add longhorn https://charts.longhorn.io
❯ helm repo update
❯ helm install longhorn longhorn/longhorn --namespace longhorn-system --create-namespace --version 1.3.2
```

### Проверка установки

```bash
❯ kubectl get pods -n longhorn-system
```
