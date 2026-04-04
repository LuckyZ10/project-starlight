from datetime import datetime, timedelta
from starlight.core.spaced_rep import ReviewCard, calculate_next_review, get_due_cards, retention_rate


def test_first_review_pass():
    card = ReviewCard(node_id="N01", cartridge_id="py")
    result = calculate_next_review(card, quality=4)
    assert result.interval == 1
    assert result.repetition == 1
    assert result.next_review is not None


def test_second_review_pass():
    card = ReviewCard(node_id="N01", cartridge_id="py", repetition=1)
    result = calculate_next_review(card, quality=4)
    assert result.interval == 6
    assert result.repetition == 2


def test_third_review_pass():
    card = ReviewCard(node_id="N01", cartridge_id="py", repetition=2, interval=6, ease_factor=2.5)
    result = calculate_next_review(card, quality=4)
    assert result.interval == round(6 * 2.5)  # 15
    assert result.repetition == 3


def test_fail_resets():
    card = ReviewCard(node_id="N01", cartridge_id="py", repetition=5, interval=30)
    result = calculate_next_review(card, quality=1)
    assert result.repetition == 0
    assert result.interval == 1


def test_ease_factor_floor():
    card = ReviewCard(node_id="N01", cartridge_id="py", ease_factor=1.3)
    result = calculate_next_review(card, quality=0)
    assert result.ease_factor >= 1.3


def test_get_due_cards():
    now = datetime.utcnow()
    cards = [
        ReviewCard(node_id="N01", cartridge_id="py", next_review=now - timedelta(days=1)),
        ReviewCard(node_id="N02", cartridge_id="py", next_review=now + timedelta(days=1)),
        ReviewCard(node_id="N03", cartridge_id="py", next_review=now - timedelta(days=3)),
    ]
    due = get_due_cards(cards, now)
    assert len(due) == 2
    assert due[0].node_id == "N03"  # most overdue first


def test_retention_rate():
    r = retention_rate(1, 2.5)
    assert 0 < r <= 1
    assert r > 0.9  # 1天后保持率应该很高
