# app/services/fortune_service.py

import random

FORTUNE_TYPES = {
    'S_KICHI': '諭吉',
    'DAI_KICHI': '大吉',
    'KICHI': '吉',
    'CHU_KICHI': '中吉',    # <-- 新增
    'SHO_KICHI': '小吉',
    'KYO': '凶',
    'DAI_KYO': '大凶',
}

FORTUNE_RANKS = {
    FORTUNE_TYPES['S_KICHI']: 7,    # <-- 更新
    FORTUNE_TYPES['DAI_KICHI']: 6, # <-- 更新
    FORTUNE_TYPES['KICHI']: 5,     # <-- 更新
    FORTUNE_TYPES['CHU_KICHI']: 4, # <-- 新增
    FORTUNE_TYPES['SHO_KICHI']: 3, # <-- 更新
    FORTUNE_TYPES['KYO']: 2,       # <-- 更新
    FORTUNE_TYPES['DAI_KYO']: 1,   # <-- 更新
}

def draw_fortune_logic() -> str:
    """Implements the two-stage probability model for drawing a fortune."""
    good_fortunes = [
        FORTUNE_TYPES['S_KICHI'], 
        FORTUNE_TYPES['DAI_KICHI'], 
        FORTUNE_TYPES['KICHI'], 
        FORTUNE_TYPES['CHU_KICHI'], # <-- 新增
        FORTUNE_TYPES['SHO_KICHI']
    ]
    bad_fortunes = [FORTUNE_TYPES['KYO'], FORTUNE_TYPES['DAI_KYO']]

    # First stage: 80% chance for a good fortune pool
    if random.random() <= 0.8:
        # Second stage: Equal chance within the good pool
        return random.choice(good_fortunes)
    else:
        # Second stage: Equal chance within the bad pool
        return random.choice(bad_fortunes)