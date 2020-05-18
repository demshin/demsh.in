---
layout: post
title: "Приватный Docker Registry с сертификатом от LetsEncrypt и хранением данных на S3"
date: 2018-11-06 16:38:00 +0500
categories: docker registry ssl letsecrypt s3
---

## Почему и зачем

Потому что понадобилось на работе. Был у нас свой Docker Registry, который делал не я. Начал поднимать свой, а он не поднимается, потому что встроенная функциональность по получению сертификатов от LetsEncrypt [сломана](https://github.com/docker/distribution/issues/2545). Пришлось пилить [свой костыль](https://github.com/demshin/private-docker-registry-ssl-s3).

## Как пользоваться

В readme есть инструкция. Но там кое-что упущено. Необходимо создать на AWS bucket, где будут храниться данные Registry и пользователя с политикой доступа к этому S3 bucket (нужны access key и secret key).

Все вопросы в telegram [@demshin](https://t.me/demshin).
