from starlight.core.session import Session, Exchange


def test_session_add_exchange():
    s = Session(user_id=1, cartridge_id="py", current_node="N01")
    s.add_exchange("system", "Welcome")
    s.add_exchange("user", "Hello")
    assert len(s.conversation) == 2
    assert s.turn_count == 1


def test_context_window():
    s = Session(user_id=1, cartridge_id="py", current_node="N01")
    for i in range(25):
        s.add_exchange("user", f"msg {i}")
    ctx = s.get_context_window(max_messages=10)
    assert len(ctx) == 10


def test_force_verdict():
    s = Session(user_id=1, cartridge_id="py", current_node="N01", max_turns=3)
    for i in range(3):
        s.add_exchange("user", f"answer {i}")
    assert s.should_force_verdict() is True


def test_reset_for_new_node():
    s = Session(user_id=1, cartridge_id="py", current_node="N01")
    s.add_exchange("user", "answer")
    s.reset_for_new_node("N02")
    assert s.current_node == "N02"
    assert len(s.conversation) == 0
    assert s.turn_count == 0
