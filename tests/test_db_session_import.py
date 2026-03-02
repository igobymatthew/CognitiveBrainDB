from cognitivebrain.db import SessionLocal, get_db_session


def test_db_session_objects_are_importable():
    assert SessionLocal is not None
    assert callable(get_db_session)
