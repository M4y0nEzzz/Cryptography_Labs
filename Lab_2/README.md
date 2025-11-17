# Лаба 2: Стеганография в изображениях (LSB)

## Утилита
### Вставка сообщения из терминала
```txt
    python src/main.py encode --cover imgs/checkerboard.png --out imgs/checkerboard_stego.png --text "Сообшение"
```
### Вставка сообщения из файла
```txt
    python src/main.py encode --cover imgs/gradient.png --out imgs/gradient_stego.png --text-file message.txt
``` 
#### --text-file - это путь к файлу с сообщением

### Ограничение payload
```txt
    python src/main.py encode --cover imgs/noise_texture.png --out imgs/noise_texture_stego_1p.png --text-file secret.txt --payload-percent 1
```
#### --payload-percent — сколько процентов от доступной ёмкости использовать (например: 0.1, 0.5, 1, 5)

### Число LSB на канал
```txt
   python src/main.py encode --cover imgs/gradient.png --out imgs/gradient_stego.png --text "test" --bits 1
```
#### --bits — сколько младших битов канала использовать

### Извлечение сообщения в терминал
```txt
   python src/main.py decode --stego imgs/checkerboard_stego.png
```
### Извлечение сообщения в файл
```txt
   python src/main.py decode --stego imgs/gradient_stego.png --out-text-file recovered.txt
```
#### --out-text-file — путь к файлу, куда сохранить

### Режим эксперимента 
```txt
   python src/main.py experiment --imgs-dir imgs
```

## Тесты
- **Встроить сообщение в checkerboard.png с payload 0.5%**
```txt
    python src/main.py encode --cover imgs/checkerboard.png --out imgs/checkerboard_stego_0p5.png --text "Cool_test_1" --payload-percent 0.5
```
- **Извлечь сообщение из checkerboard_stego_0p5.png**
```txt
    python src/main.py decode --stego imgs/checkerboard_stego_0p5.png
```
- **Запустить полный эксперимент по всем PNG в imgs/**
```txt
    python src/main.py experiment --imgs-dir imgs
```