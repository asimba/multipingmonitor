multipingmonitor
================
Скрипт MultiPingMonitor (mpm.py) предназначен для фонового  мониторинга сетевой  доступности серверов и/или рабочих станций при помощи  утилиты ping. В случае, если потеряно более пяти пакетов (или при использовании операционных систем семейства *nix  -  при задержке более пяти секунд), средствами графического интерфейса отображается  сообщение  об  ошибке, которое будет автоматически убрано при восстановлении устойчивой связи.  
Список контролируемых узлов хранится в файле hosts.list, который должен быть  размещён  в  той  же директории, что и сам скрипт. Для корректной работы скрипта требуется установленная среда Python 2.7.x (https://www.python.org/) и набор библиотек wxPython 3.x.x
(http://www.wxpython.org). Все сообщения могут отображаться на английском и русском языках, в зависимости от локализации  операционной системы. Функционирование протестировано в операционных системах Ubuntu 12.04/Windows 7. Для запуска скрипта в  фоновом режиме  в  операционных системах семейства MS Windows смените расширение файла mpm.py с 'py' на 'pyw'.  Для остановки  работы скрипта,  запущеного  в  фоновом  режиме,  требуется  запустить  скрипт повторно, в следствие чего будет выдан запрос на  прекращение  функционирования.
Скрипт может быть использован Вами совершенно свободно и бесплатно.

(c) Alexey V. Simbarsky
