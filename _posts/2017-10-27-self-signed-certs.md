---
layout: post
title:  "Установка самоподписанного сертификата"
date:   2017-10-25 13:15:00 +0500
categories: openssl, certificates, https
---

## Суть проблемы

Недавно я описывал [как установить сертификат](demshin.github.io/openssl,/certificates,/https/2017/09/16/certificates.html).
Это простой способ для получения шифрованного соединения, но способ этот платный, т.к. за сертификат нужно платить.
Но иногда (а на самом деле почти всегда) нам нужно получить **https** в процессе разработки. Для этого и существуют
самоподписанные сертификаты (selfsigned certificates).

## Что делать

Процесс во многом напоминает установку обычного сертификата, но с большими упрощениями.

### Создание SSL-сертификата

`sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/nginx/crt/yourdomain.key -out /etc/nginx/crt/yourdomain.crt
`

Запустится визард, как при создании ключа и генерации запроса на создание сертфиката, с такими же вопросами. Подробнее
в моей [статье](demshin.github.io/openssl,/certificates,/https/2017/09/16/certificates.html).

### Настройка Nginx

На этом этапе все идентично настройке с обычными сертификатами, смотреть эту же самую статью.

### Браузер

Любой современный браузер будет ругаться при соединении с таким сревером, что логично, сертификат самоподписанный и
ничего не гарантирует. В процессе разработки игнорируйте эти сообщения, а на продакшен-сервере никогда не используйте
самоподписанные сертификаты.

## Заключение

Вот собственно и все. Вопросы в мой Telegram [@demshin](https://t.me/demshin).
