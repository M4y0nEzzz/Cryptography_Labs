from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
import base64


# Шифрование
def encrypt(message: str, key: str) -> str:
    # Превращаем строковый ключ в байты
    key_bytes = key.encode("utf-8")
    if len(key_bytes) not in (16, 24, 32):
        raise ValueError("Ключ должен быть длиной 16, 24 или 32 байта")

    # Генерация случайного IV
    iv = get_random_bytes(16)

    # Создание шифра AES (CBC)
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)

    # Шифрование с PKCS#7 паддингом
    encrypted_bytes = cipher.encrypt(pad(message.encode("utf-8"), AES.block_size))

    # Конкатенация IV и зашифрованных данных
    encrypted_message = iv + encrypted_bytes

    # Возвращаем в Base64
    return base64.b64encode(encrypted_message).decode("utf-8")


# Дешифрование
def decrypt(encrypted_message: str, key: str) -> str:
    key_bytes = key.encode("utf-8")
    if len(key_bytes) not in (16, 24, 32):
        raise ValueError("Ключ должен быть длиной 16, 24 или 32 байта")

    # Декодирование из Base64
    encrypted_data = base64.b64decode(encrypted_message)

    # Извлекаем IV
    iv = encrypted_data[:16]
    encrypted_bytes = encrypted_data[16:]

    # Создаём шифр AES (CBC) для расшифровки
    cipher = AES.new(key_bytes, AES.MODE_CBC, iv)

    # Расшифровываем и убираем паддинг
    decrypted_bytes = unpad(cipher.decrypt(encrypted_bytes), AES.block_size)

    return decrypted_bytes.decode("utf-8")


if __name__ == "__main__":
    message = "Тестовое сообщение"
    key = "СЮДА КЛЮЧ ВСТАВЛЯТЬ"  # 16 байтный ключ

    # encrypted = encrypt(message, key)
    encrypted = "СЮДА ВСТАВЛЯТЬ ЗАКОДИРОВАННОЕ СООБЩЕНИЕ"
    print("Зашифрованное сообщение:", encrypted)

    decrypted = decrypt(encrypted, key)
    print("Расшифрованное сообщение:", decrypted)




# Задание: дано сообщение, нужно выбрать правильный ключ.
#             Vh0BxVz49RrtSiFfLGT+HTm+xeSlTj+TnnzryHvkj4aI1lo7pOD1FXossGI6SndO
#             1) NecoshaBalbesina
#             2) PmNasheVso123456
#             3) SecretEncryptKey
#
#             7jn3Dcp4ALr6b/TrzqjHc2lpzWcmj6EDdibqQBnN3E7OrZrurKLiIqTfuhVS7zSu
#             1) AleksandrZeifman
#             2) Stendof2Strellka
#             3) DikiyOgurecSsweg

#             7HNePeusr8MnAodqg3dCWxV256G5PBAw3asFGZJSQMbwKw21x3N7V8/0IO61dEUKFbWFQDsRTuqc/Kf5+J3FLbuVgOdCUF9R6DwxCwaguSg=
#             1) GinessOneLoveDab
#             2) SipinNashPapaPma
#             3) JbiDvaPolChasa30
#
#             Pb6pr5GYTGbpQVXMFJq4yaGi9RBHv2Mkea67FYssBO4uRCo+HqB5VQ+2EiYaKn4NJsow9OUsmJQv1+4IA4CeS6vexRdSnFkYSiAFGLnqCnW6Gd5HYVhirbVayQAed+und5oWI2GJjvEKyJWTvEiHPki7x3X8oA9c8Bp2Cg9ooMK96gn9hNg2OZpLvjkDTR/xIeBQPq0LpmWo0/lYwNoKiSPhE9v5hrbUPESE2H7uEYe31DPpzAJlUTGNu95I51MQixF3/4LSDInPotHCZb4DqitsNOI171rZke4l7jWAH/s=
#             1) NecoshaSal'to360
#             2) NerviPiloramy228
#             3) NuIPustNeChorosh
#
#             PZbpemQB4bJANtp6ERsZ6ZCbBpjCpzv/EaDMz5qARul8Q6t1TgPZI9BF9r5VYhgM5onfvH5VT2CqsTpzs8UzJ8/5+72rTCRH5qVcrz/iZt5QaFaixotnnopVbhUApn9SSS79vv8CRGYI8dvg99f3JGNoHnxQ8xRzuCEsQZfyT1FGhlydeILBDUxmjzI5hBviuJle/YaT74vRNCP/FpUOka0olhJ+9/L+h3yEY71CIpcsDahZxh3aQBhHgLTQ51ch/fp5krktIFS95AGFbcQ3oA==
#             1) YouShallNotPass1
#             2) Andrey_Michalich
#             3) ProKabanaHaHaHa5