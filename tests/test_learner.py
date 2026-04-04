from starlight.core.learner import LearnerProfile, ZPDZone


def test_initial_state():
    learner = LearnerProfile(user_id=1)
    assert learner.knowledge_level == 0.0
    assert learner.zpd_zone == ZPDZone.ZPD


def test_update_from_pass():
    learner = LearnerProfile(user_id=1)
    learner.update_from_assessment(score=85, verdict="PASS", turn_count=3)
    assert learner.knowledge_level > 0
    assert learner.confidence > 0.5
    assert learner.total_xp > 0
    assert learner.nodes_completed == 1


def test_update_from_fail():
    learner = LearnerProfile(user_id=1, confidence=0.5)
    learner.update_from_assessment(score=30, verdict="FAIL", turn_count=5, error_type="concept")
    assert learner.confidence < 0.5
    assert learner.zpd_zone == ZPDZone.ABOVE
    assert len(learner.error_patterns) == 1


def test_difficulty_modifier():
    learner = LearnerProfile(user_id=1, zpd_zone=ZPDZone.BELOW)
    assert learner.get_difficulty_modifier() < 1.0
    learner.zpd_zone = ZPDZone.ABOVE
    assert learner.get_difficulty_modifier() > 1.0


def test_zpd_transition():
    learner = LearnerProfile(user_id=1)
    learner.update_from_assessment(score=95, verdict="PASS", turn_count=1)
    assert learner.zpd_zone == ZPDZone.BELOW
    learner.update_from_assessment(score=40, verdict="FAIL", turn_count=5)
    assert learner.zpd_zone == ZPDZone.ABOVE


def test_warning():
    learner = LearnerProfile(user_id=1, confidence=0.1)
    assert learner.get_warning() is not None
