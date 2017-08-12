---
layout: post
title:  "Тестирование API"
date:   2017-05-20 12:38:00 +0500
categories: API, testing, Java
---

Делаю очередное тестовое задание.
# Задача: 
написать автотесты для API. Как изветсно я знаю Java и инфраструктуру вокруг нее, поэтому начал искать подходящий инструмент.

# Выбор иструмента
Нагуглил два:
- [Rest-assured](http://rest-assured.io), [github](https://github.com/rest-assured/rest-assured);
- часть фреймворка [Jersey](https://jersey.github.io) для создания RESTful API - [Jersey Test Framework](https://github.com/jersey/jersey/tree/master/test-framework).

Судя по количеству ссылок при поиске и советам сообщества тестировщиков более популярная - Rest-assured, поэтому я выбрал именно ее.
Еще есть [сравнение](http://www.hascode.com/2011/09/rest-assured-vs-jersey-test-framework-testing-your-restful-web-services/#Using_Jersey-Test-Framework) этих фреймворков, оно довольно старое (2011 года), но вполне актуально.

По использованию Rest-assured есть довольно много мануалов, да и [документация](https://github.com/rest-assured/rest-assured/wiki/Usage) довольно подробная и толковая.  

# Результат
Дополню по готовности, если не забуду. :-)

#Дополняю. 
Репозиторий с готовым заданием [здесь](https://github.com/demshin/Xsolla-Promotions-API-Testing). В итоге узнал много нового, могу сказать, что теcтировать API даже интереснее в чем-то, чем UI. Но естественно одно другому не мешает и не заменяет.

REST-Assured и правда отличная библиотека оказалась довольно легко и быстро осваиваемая. Все мануалы практически повторяют официальную документацию, да и еще что-нибудь упускают. Так что читайте её. А по нескольким возникшим проблемам гугл привел меня на Stackoverflow.
