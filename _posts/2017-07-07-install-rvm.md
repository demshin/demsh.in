---
layout: post
title: "Установка RVM на macOS"
date: 2017-07-07 22:22:22 +0500
categories: rvm ruby
---

Как видно из моего [резюме](https://demsh.in/about) я начал работать в компании [360bound](http://360bound.com). А там новый для меня стек технологий.

Работаю я в macOS (и ничего другого не хочется :-)) и установить [RVM](https://rvm.io) по инструкции с офсайта не вышло. RVM - это Ruby Version Manager, тулза, которая позволяет при разработке удобно управлять разным окружением для Ruby (версии интерпретаторов, наборы gem'ов и т.д.). Непродолжительное гугление привело к результатам.

Все проводилось на macOS Sierra 10.12.5, с установленным Command Line Tools и Brew Ports.

- ставим `gpg`: `brew install gpg`
- ставим ключи безопасности для RVM: `command curl -sSL https://rvm.io/mpapis.asc | gpg --import -`
- ставим непосредственно RVM: `\curl -L https://get.rvm.io | bash -s stable`
- в номом окне терминала проверяем, что RVM установился: `rvm -v`
