# Лаба 1: Шифрование изображений (XOR + AES-CTR)

## Установка необходимых библиотек
pip install -r requirements.txt

## Запуск
python src/main.py --algo xor --key "secret" --input imgs/checkerboard.png
python src/main.py --algo aes-ctr --key "secret" --nonce "0011223344556677" --input imgs/gradient.png

## Результаты
imgs/*_xor.png, *_aes-ctr.png, *_dec.png — шифротексты и обратимость
results/*_hist_*.png — гистограммы
results/*_metrics.json — метрики
results/*_meta.json — метаданные
results/summary_all.(json|csv) — сводка при --run-all