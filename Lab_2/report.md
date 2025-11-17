# Лабораторная работа №2. Стеганография в изображениях (LSB).

## Утилита. Вход и выход.
   **Поддерживаются 3 режима работы**:
   1) Режим кодирования (encode)
      ```bash
          python src/main.py encode --cover imgs/checkerboard.png --out imgs/checkerboard_stego.png --text "Сообщение" --payload-percent 0.5
      ```
    
      
   2) Режим декодирования (decode)
      ```bash
          python src/main.py decode --stego imgs/checkerboard_stego.png
      ```

      
   3) Режим эксперимента (experiment)
      ```bash
          python src/main.py experiment --imgs-dir imgs --bits 1
      ```

      
    
## Встраивание и извлечение.
Для начала выполняются определенные преобразования для успешного encode и decode.
```python
# Преобразования текст->байты и наоборот
def text_to_bytes(text: str, encoding: str = "utf-8") -> bytes:
    return text.encode(encoding)

def bytes_to_text(data: bytes, encoding: str = "utf-8") -> str:
    return data.decode(encoding, errors="replace")

# Преобразования байты->список_битов и наоборот
def bytes_to_bits(data: bytes) -> list[int]:
    bits: list[int] = []
    for b in data:
        for i in range(7, -1, -1):
            bits.append((b >> i) & 1)
    return bits

def bits_to_bytes(bits: list[int]) -> bytes:
    if len(bits) % 8 != 0:
        raise ValueError("bits length is not multiple of 8")
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i+8]:
            byte = (byte << 1) | (bit & 1)
        out.append(byte)
    return bytes(out)
```
```python
# Payload. [32-битная длина сообщения в байтах][байты сообщения]
def _build_payload_bits(message: bytes) -> list[int]:
    msg_len = len(message)
    if msg_len > 0xFFFFFFFF:
        raise ValueError("Message too long for 32-bit length header")
    header = msg_len.to_bytes(4, "big")
    full = header + message
    return bytes_to_bits(full)

# Извлечение 32-битной длины и самих данных
def _parse_payload_bits(bits: list[int]) -> bytes:
    if len(bits) < 32:
        raise ValueError("Not enough bits for length header")

    len_bits = bits[:32]
    length_bytes = bits_to_bytes(len_bits)
    msg_len = int.from_bytes(length_bytes, "big")

    total_bits_needed = 32 + msg_len * 8
    if len(bits) < total_bits_needed:
        raise ValueError(
            f"Not enough bits for message: need {total_bits_needed}, got {len(bits)}"
        )

    msg_bits = bits[32:32 + msg_len * 8]
    return bits_to_bytes(msg_bits)
```
Расчет емкости и управление нагрузкой:
```python
def _capacity_bits_rgb(width: int, height: int, bits_per_channel: int = 1) -> int:
    if bits_per_channel != 1:
        raise ValueError("Only 1 LSB per channel is supported in this implementation")
    return width * height * 3 * bits_per_channel
```


Основной алгоритм встраивания:
```python
# Вставка сообщения в младшие биты
def _embed_bits_lsb_rgb(
    rgb_bytes: bytes,
    width: int,
    height: int,
    message_bits: list[int],
    bits_per_channel: int = 1,
) -> bytes:
    capacity = _capacity_bits_rgb(width, height, bits_per_channel)
    total_bits = len(message_bits)
    if total_bits > capacity:
        raise ValueError(
            f"Message too large: need {total_bits} bits, capacity {capacity} bits"
        )
    
    data = bytearray(rgb_bytes)
    bit_idx = 0
    n = len(data)
    
    # Построчный обход: row-major порядок
    # Внутри пикселя: каналы R, G, B
    for i in range(n):
        if bit_idx >= total_bits:
            break
        # Замена младшего бита: (pixel & 0xFE) | message_bit
        b = data[i]
        b = (b & 0xFE) | (message_bits[bit_idx] & 1)
        data[i] = b
        bit_idx += 1
        
    return bytes(data)
```

Непосредственно функция кодирования:
```python
def lsb_encode_image(
    cover_path: str | Path,
    stego_path: str | Path,
    message: bytes,
    bits_per_channel: int = 1,
    payload_frac: float | None = None,
) -> None:
    cover_path = Path(cover_path)
    stego_path = Path(stego_path)

    img = Image.open(cover_path).convert("RGB")
    w, h = img.size
    rgb = img.tobytes()
    capacity_bits = _capacity_bits_rgb(w, h, bits_per_channel)
    all_payload_bits = _build_payload_bits(message)

    # Ограничение по payload_frac
    if payload_frac is not None:
        if not (0.0 < payload_frac <= 1.0):
            raise ValueError("payload_frac must be in (0, 1]")
        max_bits = int(capacity_bits * payload_frac)
        max_bits = (max_bits // 8) * 8  # выравнивание по байтам
        if max_bits < 32 + 8:
            raise ValueError(
                f"payload_frac={payload_frac} too small: "
                f"only {max_bits} bits < 40 bits (header+1byte)"
            )
        if len(all_payload_bits) > max_bits:
            msg_bits_available = max_bits - 32
            msg_bytes_available = msg_bits_available // 8
            if msg_bytes_available <= 0:
                raise ValueError("Not enough space for any message bytes")
            trimmed_message = message[:msg_bytes_available]
            all_payload_bits = _build_payload_bits(trimmed_message)

    stego_rgb = _embed_bits_lsb_rgb(
        rgb_bytes=rgb,
        width=w,
        height=h,
        message_bits=all_payload_bits,
        bits_per_channel=bits_per_channel,
    )
    stego_img = Image.frombytes("RGB", (w, h), stego_rgb)
    stego_img.save(stego_path)
```

Алгоритм извлечения:
```python
def _extract_bits_lsb_rgb(
    rgb_bytes: bytes,
    width: int,
    height: int,
    n_bits: int,
    bits_per_channel: int = 1,
) -> list[int]:
    capacity = _capacity_bits_rgb(width, height, bits_per_channel)
    if n_bits > capacity:
        raise ValueError(
            f"Requested {n_bits} bits, but capacity is {capacity} bits"
        )
    
    bits: list[int] = []
    for b in rgb_bytes:
        bits.append(b & 1)  # извлечение младшего бита
        if len(bits) >= n_bits:
            break
    return bits
```

Функция для декодирвоания:
```python
def lsb_decode_image(
    stego_path: str | Path,
    bits_per_channel: int = 1,
) -> bytes:
    stego_path = Path(stego_path)
    img = Image.open(stego_path).convert("RGB")
    w, h = img.size
    rgb = img.tobytes()

    header_bits = _extract_bits_lsb_rgb(
        rgb_bytes=rgb,
        width=w,
        height=h,
        n_bits=32,
        bits_per_channel=bits_per_channel,
    )
    header_bytes = bits_to_bytes(header_bits)
    msg_len = int.from_bytes(header_bytes, "big")

    total_bits = 32 + msg_len * 8
    all_bits = _extract_bits_lsb_rgb(
        rgb_bytes=rgb,
        width=w,
        height=h,
        n_bits=total_bits,
        bits_per_channel=bits_per_channel,
    )

    message = _parse_payload_bits(all_bits)
    return message
```
Порядок обхода пикселей - построчный, внутри пикселя по каналам.


## Вычисление метрик. Оценка незаметности и проверка обнаружимости.

### PSNR (Peak Signal-to-Noise Ratio)
PSNR измеряет отношение максимально возможной мощности сигнала к мощности шума, вносимого стеганографическими изменениями.

```python
def psnr_rgb(cover: bytes, stego: bytes) -> float:
    if len(cover) != len(stego):
        raise ValueError("PSNR: lengths differ")
    n = len(cover)
    if n == 0:
        return float("nan")
    
    # Вычисление MSE (Mean Squared Error)
    mse = 0.0
    for a, b in zip(cover, stego):
        d = a - b
        mse += d * d
    mse /= n
    if mse == 0:
        return float("inf")
    
    max_i = 255.0
    return 10.0 * math.log10((max_i * max_i) / mse)
```
Использованные формулы:
```txt
MSE = (1/N) × Σ(i=1 to N) (I_original(i) - I_stego(i))²
PSNR = 10 × log₁₀(MAX² / MSE)
```
`MAX = 255`. 

Диапазон результатов и их анализ:
> 50+ дБ - отличное качество с невидимыми искажениями;
> 40-50 дБ - хорошее качество, искажения заметны едва-едва;
> 30-40 дБ - искажения заметны, качество так себе;
> менее 30 дБ - ужасное качество с сильнми искажениями.

### SSIM (Structural Similarity Index)
SSIM оценивает структурное сходство изображений, учитывая три компоненты:
- Яркость;
- Контраст;
- Структура.

```python
def _rgb_to_gray_list(rgb_bytes: bytes, width: int, height: int) -> list[float]:
    """Преобразование RGB в grayscale с использованием коэффициентов яркости"""
    gray: list[float] = []
    n_pixels = width * height
    it = iter(rgb_bytes)
    for _ in range(n_pixels):
        r = next(it)
        g = next(it)
        b = next(it)
        # Стандартные коэффициенты яркости
        y = 0.299 * r + 0.587 * g + 0.114 * b
        gray.append(y)
    return gray

def ssim_gray_from_lists(x: list[float], y: list[float]) -> float:
    """Вычисление SSIM для grayscale изображений"""
    if len(x) != len(y):
        raise ValueError("SSIM: lengths differ")
    n = len(x)
    if n == 0:
        return float("nan")

    # Вычисление средних значений
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    # Вычисление дисперсий и ковариации
    var_x = 0.0
    var_y = 0.0
    cov_xy = 0.0

    for a, b in zip(x, y):
        dx = a - mean_x
        dy = b - mean_y
        var_x += dx * dx
        var_y += dy * dy
        cov_xy += dx * dy

    var_x /= n
    var_y /= n
    cov_xy /= n

    # Константы стабилизации
    L = 255.0  # Динамический диапазон
    C1 = (0.01 * L) ** 2
    C2 = (0.03 * L) ** 2

    # Формула SSIM
    num = (2 * mean_x * mean_y + C1) * (2 * cov_xy + C2)
    den = (mean_x * mean_x + mean_y * mean_y + C1) * (var_x + var_y + C2)
    
    if den == 0:
        return 1.0
    return num / den

def ssim_rgb(cover: bytes, stego: bytes, width: int, height: int) -> float:
    """SSIM по яркостной компоненте между RGB-изображениями"""
    if len(cover) != len(stego):
        raise ValueError("SSIM: lengths differ")
    
    gray_cov = _rgb_to_gray_list(cover, width, height)
    gray_stego = _rgb_to_gray_list(stego, width, height)
    return ssim_gray_from_lists(gray_cov, gray_stego)
```
Анализ результатов:
> 0.95-1.00 - практически идентичные изображения;
> 0.9-0.95 - сходство изображений очень высокое;
> 0.8-0.9 - сходство неплохое;
> менее 0.8 - различия сильно заметны.


### Статический стегоанализ. Хи-квадрат тест.

В теории хи-квадрат теста имеются две гипотезы:
1) LSB распределены равномерно, сообщения нет;
2) LSB содержит структуру, сообщение есть.

Принцип:
При LSB-встраивании пары значений (2k, 2k+1) имеют тенденцию к "выравниванию", так как встраивание случайных битов делает распределение более равномерным.

Реализация:
```python
def _channel_histogram(rgb_bytes: bytes, channel: int) -> list[int]:
    """Построение гистограммы для указанного канала"""
    if channel not in (0, 1, 2):
        raise ValueError("channel must be 0 (R), 1 (G) or 2 (B)")
    
    n_pixels = len(rgb_bytes) // 3
    hist = [0] * 256
    base = channel
    
    for i in range(n_pixels):
        v = rgb_bytes[3 * i + base]  # Доступ к каналу R, G или B
        hist[v] += 1
        
    return hist

def hi2_lsb_channel(rgb_bytes: bytes, channel: int) -> Tuple[float, int]:
    """χ²-тест для одного канала изображения"""
    hist = _channel_histogram(rgb_bytes, channel)
    chi2 = 0.0
    used_pairs = 0

    # Анализ пар (2k, 2k+1)
    for k in range(0, 256, 2):
        o0 = hist[k]      # Наблюдаемая частота для 2k
        o1 = hist[k + 1]  # Наблюдаемая частота для 2k+1
        s = o0 + o1
        
        if s == 0:
            continue  # Пропуск пустых пар
            
        e = s / 2.0  # Ожидаемая частота при равномерном распределении
        
        # Вычисление χ² статистики для пары
        chi2 += (o0 - e) * (o0 - e) / e + (o1 - e) * (o1 - e) / e
        used_pairs += 1

    # Степени свободы: количество пар - 1
    df = max(used_pairs - 1, 1)
    return chi2, df

def hi2_lsb_all_channels(rgb_bytes: bytes) -> dict:
    """χ²-тест для всех цветовых каналов"""
    result = {}
    for ch, name in enumerate(("R", "G", "B")):
        chi2, df = hi2_lsb_channel(rgb_bytes, ch)
        result[name] = {"chi2": chi2, "df": df}
    return result
```

Расчет p-value
```python
import scipy.stats as stats

def calculate_p_value(chi2_stat: float, df: int) -> float:
    """Расчет p-value по χ² статистике и степеням свободы"""
    return 1 - stats.chi2.cdf(chi2_stat, df)
```

Критерии обнаружения:
- p-value > 0.05: Нет статистически значимых свидетельств стеганографии

- p-value ≤ 0.05: Обнаружены статистически значимые аномалии (стеганография)

- p-value ≤ 0.01: Сильные свидетельства стеганографии

- p-value ≤ 0.001: Очень сильные свидетельства стеганографии


Карты разности:
Назначение: Пространственная визуализация модифицированных пикселей.

```python
def diff_map_png(cover_rgb: bytes, stego_rgb: bytes, width: int, height: int, output_path: Path):
    """Создание карты разности между изображениями"""
    diff = []
    for a, b in zip(cover_rgb, stego_rgb):
        # Усиление разности для наглядности
        diff_val = abs(a - b) * 50  # Коэффициент усиления
        diff.append(min(255, int(diff_val)))
    
    diff_img = Image.frombytes("L", (width, height), bytes(diff))
    diff_img.save(output_path)
```
Интерпретация результатов:
- Равномерное распределение: Случайный характер изменений (хорошо);
- Структурные паттерны: Систематические изменения (плохо);
- Скопления изменений: Локализованные модификации.


## Влияние payload. Анализ и сравнение.

Эксперимент-мод:
```python
def run_experiment(args: argparse.Namespace) -> None:
    imgs_dir = Path(args.imgs_dir)
    covers: List[Path] = sorted(imgs_dir.glob("*.png"))
    bits_per_channel = args.bits
    payload_percents = [0.1, 0.5, 1.0, 5.0]
    rows: list[dict] = []

    for cover_path in covers:
        cover_rgb, w, h = load_image(cover_path)
        capacity_bits = w * h * 3 * bits_per_channel

        for p in payload_percents:
            payload_frac = p / 100.0
            max_bits = int(capacity_bits * payload_frac)
            max_bits = (max_bits // 8) * 8  # Выравнивание по байтам
            
            if max_bits < 32 + 8:  # Минимум: заголовок + 1 байт данных
                continue
                
            msg_bytes_avail = (max_bits - 32) // 8
            message = os.urandom(msg_bytes_avail)  # Случайные данные
            
            # Создание стего-изображения
            stego_path = Path("results") / f"{cover_path.stem}_lsb_{p}.png"
            lsb_encode_image(cover_path, stego_path, message, bits_per_channel, payload_frac)
            
            # Расчет метрик
            stego_rgb, w2, h2 = load_image(stego_path)
            psnr_val = psnr_rgb(cover_rgb, stego_rgb)
            ssim_val = ssim_rgb(cover_rgb, stego_rgb, w, h)
            chi2_cover = hi2_lsb_all_channels(cover_rgb)
            chi2_stego = hi2_lsb_all_channels(stego_rgb)
            
            row = {
                "cover": str(cover_path),
                "payload_percent": p,
                "psnr": psnr_val,
                "ssim": ssim_val,
                "chi2_cover": chi2_cover,
                "chi2_stego": chi2_stego,
            }
            rows.append(row)
```
# ДОПИСАТЬ!


