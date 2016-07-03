import random
from string import ascii_lowercase, digits

CHARS = ascii_lowercase + digits
SETTINGS = 'hackrtrackr/hackrtrackr/settings.py'

def generate_key(chars, length):
    new_key = ''
    for _ in range(length):
        new_key += random.choice(chars)
    return new_key

with open(SETTINGS, 'a') as f:
    f.write("SECRET_KEY = '")
    f.write(generate_key(CHARS, 43))
    f.write("'")
