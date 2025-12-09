from datetime import datetime, timedelta
from typing import Tuple


class SM2Algorithm:
    """
    SuperMemo-2 (SM-2) 间隔重复算法实现

    用户反馈评分:
    - 0 (Again): 完全不认识
    - 3 (Hard): 模糊记忆
    - 4 (Good): 认识但稍慢
    - 5 (Easy): 秒杀
    """

    @staticmethod
    def calculate_next_review(
        quality: int,
        prev_interval: int,
        prev_ease_factor: float,
        prev_repetitions: int
    ) -> Tuple[int, float, int, datetime]:
        """
        计算下次复习时间和相关参数

        Args:
            quality: 用户反馈质量 (0-5)
            prev_interval: 上次复习间隔 (天)
            prev_ease_factor: 上次难度因子
            prev_repetitions: 连续正确次数

        Returns:
            (new_interval, new_ease_factor, new_repetitions, next_review_at)
        """
        # 如果评分低于3，重置进度
        if quality < 3:
            new_interval = 1
            new_ease_factor = prev_ease_factor
            new_repetitions = 0
        else:
            # 计算新的难度因子
            new_ease_factor = prev_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
            new_ease_factor = max(1.3, new_ease_factor)  # 设置下限

            # 计算新的间隔
            if prev_repetitions == 0:
                new_interval = 1
            elif prev_repetitions == 1:
                new_interval = 6
            else:
                new_interval = int(prev_interval * new_ease_factor)

            new_repetitions = prev_repetitions + 1

        # 计算下次复习时间
        next_review_at = datetime.utcnow() + timedelta(days=new_interval)

        return new_interval, new_ease_factor, new_repetitions, next_review_at

    @staticmethod
    def get_status_from_quality(quality: int, prev_status: int) -> int:
        """
        根据评分和当前状态确定新状态

        状态:
        - 0: 未学
        - 1: 学习中
        - 2: 复习中
        - 3: 已掌握
        """
        if quality < 3:
            return 1  # 学习中
        elif quality == 3:
            return 2  # 复习中
        elif quality >= 4 and prev_status >= 2:
            return 3  # 已掌握
        else:
            return 2  # 复习中
