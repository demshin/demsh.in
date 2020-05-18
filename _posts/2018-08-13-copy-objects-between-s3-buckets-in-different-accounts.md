---
layout: post
title: "Перенос или копирование объектов между S3 buckets в разных аккаунтах"
date: 2018-08-13 15:50:00 +0500
categories: aws s3 s3bucket
---

На текущем проекте используем известные решительно всем [AWS](https://aws.amazon.com) - Amazon Web Services. Там есть решительно все, что нужно для современных веб-сервисов. В заметке пойдет речь об одном из сервисов Amazon, [S3](https://aws.amazon.com/s3) - Simple Storage Services.

## Боль

На проекте мы используем несколько аккаунтов AWS и получилось так, что нужно перенести кучу данных в S3 bucket одного аккаунта на другой. А это для меня оказалось неочевидным, поэтому пришлось немного разобраться. А результат, кроме выполненной работы, эта статья.

## Коротко

Нужно пользователю целевого аккаунта, у которого есть права писать в целевой бакет, дать права на чтение (как минимум) из бакета-источника. Дальше воспользоваться [aws-cli](https://aws.amazon.com/cli).

## Более подробно

### Что понадобится

- **S3 buckets** 2 штуки `source` и `destination`(по одной на каждый аккаунт)
- **IAM User** (например, `copy_user`) с доступом **Programmatic access** через **Access key ID** и **secret access key** (в целевом аакаунте AWS)
- User Policy для пользователя выше

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListAllMyBuckets"],
      "Resource": "arn:aws:s3:::*"
    },
    {
      "Effect": "Allow",
      "Action": [
            "s3:GetObject",
            "s3:PutObject"
        ],
      "Resource": [
             "arn:aws:s3:::source/*","arn:aws:s3:::destination/*"
        ]
    },
    {
      "Effect": "Allow",
      "Action": [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ],
      "Resource": [
             "arn:aws:s3:::source/*","arn:aws:s3:::destination/*"
        ]
    }
  ]
}
```

- **Bucket Policy** для бакета `source`, что бы дать пользователю из целевого аккаунта доступ к нему

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowAll",
      "Effect": "Allow",
      "Principal": {
        "AWS": ["arn:aws:iam::111122223333:user/copy_user"]
      },
      "Action": ["s3:*"],
      "Resource": ["arn:aws:s3:::from-source", "arn:aws:s3:::from-source/*"]
    }
  ]
}
```

- [AWS CLI tool](https://aws.amazon.com/cli) (есть на каждом инстансе [EC2](https://aws.amazon.com/ec2‎))
- Инстанс [EC2](https://aws.amazon.com/ec2‎) c Linux.

Дальше куча вариантов с помощью консольной утилиты AWS. Простейший - скопировать все:

`aws s3 cp s3://source/ s3://destination/ --recursive`

Спасибо за внимание! Написать мне [demshin@gmail.com](mailto: demshin@gmail.com) или [@demshin](https://t.me/demshin).
