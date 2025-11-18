# Лабораторная работа №2. Стеганография в изображениях (LSB).

## Вход и выход.
   **Поддерживаются 3 режима работы**:
   1) Режим вставки (encode)
      ```bash
          python src/main.py encode --cover imgs/checkerboard.png --out imgs/checkerboard_stego.png --text "Сообщение" --payload-percent 0.5
      ```
    
      
   2) Режим извлечения (decode)
      ```bash
          python src/main.py decode --stego imgs/checkerboard_stego.png
      ```

      
   3) Режим эксперимента (experiment)
      ```bash
          python src/main.py experiment --imgs-dir imgs --bits 1
      ```

      
    
## Вставка и извлечение.
```python
def text_to_bytes(text: str, encoding: str = "utf-8") -> bytes:
    return text.encode(encoding)

def bytes_to_text(data: bytes, encoding: str = "utf-8") -> str:
    return data.decode(encoding, errors="replace")

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
# Расчет емкости
def _capacity_bits_rgb(width: int, height: int, bits_per_channel: int = 1) -> int:
    if bits_per_channel != 1:
        raise ValueError("Only 1 LSB per channel is supported in this implementation")
    return width * height * 3 * bits_per_channel
```


```python
def _build_payload_bits(message: bytes) -> list[int]:
    msg_len = len(message)
    if msg_len > 0xFFFFFFFF:
        raise ValueError("Message too long for 32-bit length header")
    header = msg_len.to_bytes(4, "big")
    full = header + message
    return bytes_to_bits(full)

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


Алгоритм встраивания:
```python
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

    for i in range(n):
        if bit_idx >= total_bits:
            break
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

    # Ограничение по payload
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
        bits.append(b & 1)
        if len(bits) >= n_bits:
            break
    return bits
```

Функция для извлечения сообщения из изображения:
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


## Вычисление метрик.

### PSNR (Peak Signal-to-Noise Ratio)
PSNR измеряет сходство между исходным и стего- изображениями.

```python
def psnr_rgb(cover: bytes, stego: bytes) -> float:
    if len(cover) != len(stego):
        raise ValueError("PSNR: lengths differ")
    n = len(cover)
    if n == 0:
        return float("nan")
    
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

### SSIM (Structural Similarity Index Measure)
SSIM оценивает структурное сходство изображений, учитывая три компоненты:
- Яркость;
- Контраст;
- Структура.

```python
def _rgb_to_gray_list(rgb_bytes: bytes, width: int, height: int) -> list[float]:
    gray: list[float] = []
    n_pixels = width * height
    it = iter(rgb_bytes)
    for _ in range(n_pixels):
        r = next(it)
        g = next(it)
        b = next(it)
        y = 0.299 * r + 0.587 * g + 0.114 * b
        gray.append(y)
    return gray

def ssim_gray_from_lists(x: list[float], y: list[float]) -> float:
    if len(x) != len(y):
        raise ValueError("SSIM: lengths differ")
    n = len(x)
    if n == 0:
        return float("nan")

    # Средняяя яркость
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    var_x = 0.0
    var_y = 0.0
    cov_xy = 0.0

    for a, b in zip(x, y):
        dx = a - mean_x
        dy = b - mean_y
        var_x += dx * dx
        var_y += dy * dy
        cov_xy += dx * dy
    
    # Дисперсия и ковариация
    var_x /= n
    var_y /= n
    cov_xy /= n

    L = 255.0
    C1 = (0.01 * L) ** 2
    C2 = (0.03 * L) ** 2

    
    num = (2 * mean_x * mean_y + C1) * (2 * cov_xy + C2)
    den = (mean_x * mean_x + mean_y * mean_y + C1) * (var_x + var_y + C2)
    
    if den == 0:
        return 1.0
    return num / den

def ssim_rgb(cover: bytes, stego: bytes, width: int, height: int) -> float:
    if len(cover) != len(stego):
        raise ValueError("SSIM: lengths differ")
    
    gray_cov = _rgb_to_gray_list(cover, width, height)
    gray_stego = _rgb_to_gray_list(stego, width, height)
    return ssim_gray_from_lists(gray_cov, gray_stego)
```


### Статический стегоанализ. Хи-квадрат тест.
Этот тест проверяет, насколько распеделение младших битов отличается от нормального.
Рассматриваются пары (2k ; 2k+1). Кажыдй пиксель рассматривается как часть пары для проверки на
изменение распределения значений в младших битах.

Реализация:
```python
def _channel_histogram(rgb_bytes: bytes, channel: int) -> list[int]:
    if channel not in (0, 1, 2):
        raise ValueError("channel must be 0 (R), 1 (G) or 2 (B)")
    
    n_pixels = len(rgb_bytes) // 3
    hist = [0] * 256
    base = channel
    
    for i in range(n_pixels):
        v = rgb_bytes[3 * i + base]
        hist[v] += 1
        
    return hist

def hi2_lsb_channel(rgb_bytes: bytes, channel: int) -> Tuple[float, int]:
    hist = _channel_histogram(rgb_bytes, channel)
    chi2 = 0.0
    used_pairs = 0

    # Анализ пар (2k, 2k+1)
    for k in range(0, 256, 2):
        o0 = hist[k]      
        o1 = hist[k + 1] 
        s = o0 + o1
        
        if s == 0:
            continue
            
        e = s / 2.0
        
        
        chi2 += (o0 - e) * (o0 - e) / e + (o1 - e) * (o1 - e) / e
        used_pairs += 1

    df = max(used_pairs - 1, 1)
    return chi2, df

def hi2_lsb_all_channels(rgb_bytes: bytes) -> dict:
    result = {}
    for ch, name in enumerate(("R", "G", "B")):
        chi2, df = hi2_lsb_channel(rgb_bytes, ch)
        result[name] = {"chi2": chi2, "df": df}
    return result
```

p-value - вероятность того, что наблюдаемое распределение младших битов можно объяснить случайно.
Чем оно меньше, тем более вероятно, что изменения в изображении произошли не случайно.

Расчет p-value для определения значимости результатов теста:
```python
    p_value = 1 - stats.chi2.cdf(chi2, df)
```

Карты разности:
В карте разности отображаются различия между исходным и стего-изображением, 
что позволяет наглядно увидеть, 
где и насколько сильно изменилось изображение после встраивания скрытого сообщения.

```python
def diff_map_png(cover_rgb: bytes, stego_rgb: bytes, width: int, height: int, output_path: Path):
    diff = []
    for a, b in zip(cover_rgb, stego_rgb):
        diff_val = abs(a - b) * 50
        diff.append(min(255, int(diff_val)))
    
    diff_img = Image.frombytes("L", (width, height), bytes(diff))
    diff_img.save(output_path)
```


## Тесты

1) Вставим сообщение "криптография" в изображение checkerboard.png:
      ```bash
          python src/main.py encode --cover imgs/checkerboard.png --out imgs/checkerboard_stego.png --text "криптография"
      ```
      Теперь извлечем сообщение из того же изображения:
      ```bash
          python src/main.py decode --stego imgs/checkerboard_stego.png
      ```
2) Проведем эксперимент по payload:
      ```bash
           python src/main.py experiment --imgs-dir imgs
      ```
