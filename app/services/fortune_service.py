import random

FORTUNE_TYPES = {
    'S_KICHI': '諭吉',
    'DAI_KICHI': '大吉',
    'KICHI': '吉',
    'SHO_KICHI': '小吉',
    'KYO': '凶',
    'DAI_KYO': '大凶',
}

def draw_fortune_logic() -> str:
    """Implements the two-stage probability model for drawing a fortune."""
    good_fortunes = [FORTUNE_TYPES['S_KICHI'], FORTUNE_TYPES['DAI_KICHI'], FORTUNE_TYPES['KICHI'], FORTUNE_TYPES['SHO_KICHI']]
    bad_fortunes = [FORTUNE_TYPES['KYO'], FORTUNE_TYPES['DAI_KYO']]

    # First stage: 80% chance for a good fortune pool
    if random.random() <= 0.8:
        # Second stage: Equal chance within the good pool
        return random.choice(good_fortunes)
    else:
        # Second stage: Equal chance within the bad pool
        return random.choice(bad_fortunes)
